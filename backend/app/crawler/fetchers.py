"""Fetcher implementations and the fetch pipeline.

Transports are interchangeable behind :class:`BaseFetcher`:

* :class:`ScrapyFetcher` — default; runs the Scrapy spider in a subprocess so the
  API/Celery process never owns a Twisted reactor;
* :class:`HttpFetcher` — async httpx, used as the last-resort fallback and by the
  test suite (deterministic, no subprocess);
* :class:`PlaywrightFetcher` — headless Chromium for client-rendered pages.

:class:`FetchPipeline` adds the cross-cutting concerns: robots.txt evaluation
(recorded on the crawl job) and automatic SPA fallback, plus a fallback
transport when the primary one fails.

SSRF: every URL **and every redirect hop** is validated, and requests are pinned
to the resolved IP (``SSRF_PIN_RESOLVED_IP``) with the original ``Host`` header
and TLS SNI, which closes the DNS-rebinding window between check and fetch.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urljoin, urlparse

import httpx

from app.config import Settings, get_settings
from app.core.logging_config import get_logger
from app.core.security import ResolvedTarget, check_ssrf_async
from app.crawler.utils import (
    DEFAULT_MAX_BYTES,
    CrawlError,
    FetchError,
    FetchResult,
    ResponseTooLargeError,
    RobotsDisallowedError,
    RobotsPolicy,
    UnsupportedContentTypeError,
    extract_sitemap_hint,
    header_dict,
    is_html_content_type,
    looks_like_spa,
    parse_robots,
)

logger = get_logger(__name__)

#: Backend root (…/backend) so the spider subprocess can import `app`.
BACKEND_ROOT = Path(__file__).resolve().parents[2]
#: Subprocess time budget beyond the download timeout (interpreter + reactor).
SUBPROCESS_GRACE_SECONDS = 20
MAX_REDIRECTS = 5


class BaseFetcher(Protocol):
    """Transport contract used by :class:`~app.services.crawl_service.CrawlService`."""

    name: str

    async def fetch(self, url: str, *, force_playwright: bool = False) -> FetchResult: ...


@dataclass(slots=True)
class RobotsOutcome:
    """Robots decision plus the raw file, ready to be stored on the crawl job."""

    policy: RobotsPolicy
    raw_text: str | None = None
    sitemap_url: str | None = None

    @property
    def allowed(self) -> bool:
        return self.policy.allowed


# ---------------------------------------------------------------------------
# Low level request helper (SSRF-safe, IP pinned)
# ---------------------------------------------------------------------------
def _connect_url(target: ResolvedTarget, url: str) -> str:
    """URL with the host replaced by the vetted IP (keeps path/query)."""
    parsed = urlparse(url)
    ip = target.primary_ip
    host = f"[{ip}]" if ":" in ip else ip
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"
    return f"{target.scheme}://{host}:{target.port}{path}"


async def request_pinned(
    url: str,
    *,
    target: ResolvedTarget | None = None,
    settings: Settings | None = None,
    headers: dict[str, str] | None = None,
    timeout: float | None = None,
    max_redirects: int = MAX_REDIRECTS,
) -> httpx.Response:
    """GET ``url`` with SSRF validation on every redirect hop.

    Raises :class:`FetchError` for transport problems and
    :class:`~app.core.exceptions.SSRFBlockedError` when a hop resolves to a
    blocked address.
    """
    settings = settings or get_settings()
    current_url = url
    current_target = target or await check_ssrf_async(url)
    request_timeout = timeout or settings.CRAWLER_TIMEOUT_SECONDS

    async with httpx.AsyncClient(
        timeout=request_timeout,
        follow_redirects=False,
        headers={
            "User-Agent": settings.CRAWLER_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en",
            **(headers or {}),
        },
    ) as client:
        for hop in range(max_redirects + 1):
            if settings.SSRF_PIN_RESOLVED_IP:
                connect_url = _connect_url(current_target, current_url)
                extensions: dict[str, Any] = {"sni_hostname": current_target.hostname}
                request_headers = {"Host": current_target.host_header}
            else:  # pragma: no cover - opt-out path for exotic environments
                connect_url = current_url
                extensions = {}
                request_headers = {}

            try:
                response = await client.get(
                    connect_url, headers=request_headers, extensions=extensions
                )
            except httpx.HTTPError as exc:
                raise FetchError(str(exc)) from exc

            location = response.headers.get("location")
            if (
                response.status_code in {301, 302, 303, 307, 308}
                and location
                and hop < max_redirects
            ):
                next_url = urljoin(current_url, location)
                current_target = await check_ssrf_async(next_url)
                current_url = next_url
                continue
            return response

    raise FetchError(f"Too many redirects (>{max_redirects})")  # pragma: no cover


async def fetch_robots(
    target: ResolvedTarget,
    *,
    settings: Settings | None = None,
) -> RobotsOutcome:
    """Fetch and parse ``/robots.txt`` (missing or unreachable => allowed)."""
    settings = settings or get_settings()
    robots_url = f"{target.scheme}://{target.host_header}/robots.txt"
    text: str | None = None
    try:
        response = await request_pinned(
            robots_url,
            target=target,
            headers={"Accept": "text/plain,*/*;q=0.8"},
            timeout=min(5.0, float(settings.CRAWLER_TIMEOUT_SECONDS)),
        )
        if response.status_code < 400:
            text = response.text
    except CrawlError as exc:
        logger.info("crawl.robots_unavailable", url=robots_url, error=str(exc))
    except Exception as exc:
        logger.info("crawl.robots_error", url=robots_url, error=str(exc))

    policy = parse_robots(text, target.url, user_agent=settings.CRAWLER_USER_AGENT)
    return RobotsOutcome(policy=policy, raw_text=text, sitemap_url=policy.sitemap_url)


# ---------------------------------------------------------------------------
# Transports
# ---------------------------------------------------------------------------
class HttpFetcher:
    """Plain async HTTP transport (httpx)."""

    name = "httpx"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def fetch(
        self, url: str, *, force_playwright: bool = False  # noqa: ARG002 - BaseFetcher protocol
    ) -> FetchResult:
        target = await check_ssrf_async(url)
        started = time.perf_counter()
        response = await request_pinned(url, target=target, settings=self.settings)
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        content = response.content
        max_bytes = self.settings.CRAWLER_MAX_RESPONSE_BYTES or DEFAULT_MAX_BYTES
        if len(content) > max_bytes:
            raise ResponseTooLargeError(f"{len(content)} bytes > {max_bytes} byte budget")
        if response.status_code >= 400:
            raise FetchError(f"HTTP {response.status_code} for {url}")
        content_type = response.headers.get("content-type", "")
        if not is_html_content_type(content_type):
            raise UnsupportedContentTypeError(f"Content-Type {content_type!r} is not HTML")

        html = response.text
        final_url = str(response.url)
        return FetchResult(
            url=url,
            final_url=final_url,
            status_code=response.status_code,
            content_type=content_type,
            html=html,
            response_time_ms=elapsed_ms,
            size_bytes=len(content),
            method=self.name,
            is_spa_detected=looks_like_spa(html),
            sitemap_url=extract_sitemap_hint(html, final_url),
            headers=header_dict(response.headers),
        )


class ScrapyFetcher:
    """Runs :class:`~app.crawler.spiders.page_spider.PageSpider` in a subprocess."""

    name = "scrapy"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def fetch(
        self, url: str, *, force_playwright: bool = False  # noqa: ARG002 - BaseFetcher protocol
    ) -> FetchResult:
        import anyio

        return await anyio.to_thread.run_sync(self._fetch_sync, url)

    def _fetch_sync(self, url: str) -> FetchResult:
        from app.crawler.spiders.page_spider import RESULT_MARKER

        timeout = self.settings.CRAWLER_TIMEOUT_SECONDS + SUBPROCESS_GRACE_SECONDS
        command = [
            sys.executable,
            "-m",
            "app.crawler.spiders.page_spider",
            "--url",
            url,
            "--timeout",
            str(self.settings.CRAWLER_TIMEOUT_SECONDS),
            "--max-bytes",
            str(self.settings.CRAWLER_MAX_RESPONSE_BYTES),
            "--user-agent",
            self.settings.CRAWLER_USER_AGENT,
        ]
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join(
            filter(None, [str(BACKEND_ROOT), env.get("PYTHONPATH", "")])
        )
        env.setdefault("PYTHONUNBUFFERED", "1")

        try:
            completed = subprocess.run(
                command,
                cwd=str(BACKEND_ROOT),
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise FetchError(f"Scrapy crawl exceeded {timeout}s") from exc

        payload: dict[str, Any] | None = None
        for line in completed.stdout.splitlines():
            if line.startswith(RESULT_MARKER):
                try:
                    payload = json.loads(line[len(RESULT_MARKER) :])
                except json.JSONDecodeError:
                    payload = None
                break

        if payload is None:
            tail = (completed.stderr or "").strip().splitlines()[-3:]
            raise FetchError(
                f"Scrapy produced no result (exit {completed.returncode}): {' | '.join(tail)}"
            )
        if not payload.get("ok") or not payload.get("item"):
            raise FetchError(str(payload.get("error") or "unknown Scrapy failure"))

        item = payload["item"]
        html = item.get("html") or ""
        return FetchResult(
            url=item.get("url", url),
            final_url=item.get("final_url", url),
            status_code=int(item.get("status_code") or 0),
            content_type=item.get("content_type") or "",
            html=html,
            response_time_ms=int(item.get("response_time_ms") or 0),
            size_bytes=int(item.get("size_bytes") or len(html.encode("utf-8"))),
            method=self.name,
            is_spa_detected=looks_like_spa(html),
            sitemap_url=extract_sitemap_hint(html, item.get("final_url") or url),
            headers=header_dict(item.get("headers") or {}),
        )


class PlaywrightFetcher:
    """Headless Chromium transport for client-rendered pages."""

    name = "playwright"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def fetch(
        self, url: str, *, force_playwright: bool = False  # noqa: ARG002 - BaseFetcher protocol
    ) -> FetchResult:
        from app.crawler.playwright_fallback import (
            PlaywrightUnavailableError,
            chromium_available,
            render_page,
        )

        if not chromium_available():
            raise PlaywrightUnavailableError(
                "Chromium is not installed; run 'playwright install chromium'"
            )
        await check_ssrf_async(url)
        rendered = await render_page(url, timeout_ms=self.settings.PLAYWRIGHT_TIMEOUT_MS)
        if rendered.status_code and rendered.status_code >= 400:
            raise FetchError(f"HTTP {rendered.status_code} for {url}")
        if not is_html_content_type(rendered.content_type):
            raise UnsupportedContentTypeError(f"Content-Type {rendered.content_type!r} is not HTML")
        return FetchResult(
            url=url,
            final_url=rendered.final_url,
            status_code=rendered.status_code,
            content_type=rendered.content_type,
            html=rendered.html,
            response_time_ms=rendered.response_time_ms,
            size_bytes=rendered.size_bytes,
            method=self.name,
            is_spa_detected=False,  # rendered: JavaScript has already executed
            sitemap_url=extract_sitemap_hint(rendered.html, rendered.final_url),
            headers=rendered.headers,
        )


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
class FetchPipeline:
    """Primary transport + robots.txt evaluation + SPA/failure fallbacks."""

    name = "auto"

    def __init__(
        self,
        *,
        primary: BaseFetcher,
        http: HttpFetcher,
        playwright: PlaywrightFetcher,
        settings: Settings | None = None,
    ) -> None:
        self.primary = primary
        self.http = http
        self.playwright = playwright
        self.settings = settings or get_settings()

    async def _robots(self, target: ResolvedTarget) -> RobotsOutcome:
        if not self.settings.CRAWLER_RESPECT_ROBOTS_TXT:
            return RobotsOutcome(policy=RobotsPolicy(allowed=True, reason="robots checks disabled"))
        return await fetch_robots(target, settings=self.settings)

    async def fetch(self, url: str, *, force_playwright: bool = False) -> FetchResult:
        target = await check_ssrf_async(url)

        robots = await self._robots(target)
        if not robots.allowed:
            logger.warning(
                "crawl.robots_disallowed", url=url, user_agent=self.settings.CRAWLER_USER_AGENT
            )
            raise RobotsDisallowedError(f"robots.txt disallows {url}")

        if force_playwright or self.primary.name == PlaywrightFetcher.name:
            result = await self.playwright.fetch(url, force_playwright=True)
        else:
            try:
                result = await self.primary.fetch(url, force_playwright=force_playwright)
            except CrawlError as exc:
                if self.primary is self.http:
                    raise
                logger.warning(
                    "crawl.primary_failed_fallback", transport=self.primary.name, error=str(exc)
                )
                result = await self.http.fetch(url, force_playwright=force_playwright)

            if result.is_spa_detected:
                try:
                    rendered = await self.playwright.fetch(url, force_playwright=True)
                    rendered.playwright_fallback_used = True
                    rendered.is_spa_detected = True
                    logger.info("crawl.spa_rendered", url=url, transport=rendered.method)
                    result = rendered
                except Exception as exc:
                    logger.info("crawl.playwright_unavailable", url=url, error=str(exc))

        result.robots_allowed = robots.allowed
        result.robots_txt = robots.raw_text
        result.sitemap_url = result.sitemap_url or robots.sitemap_url
        return result


def get_fetcher(settings: Settings | None = None, *, engine: str | None = None) -> FetchPipeline:
    """Build the fetch pipeline for the configured engine."""
    settings = settings or get_settings()
    engine = (engine or settings.CRAWLER_ENGINE).lower()
    http = HttpFetcher(settings)
    playwright = PlaywrightFetcher(settings)
    transports: dict[str, BaseFetcher] = {
        "httpx": http,
        "scrapy": ScrapyFetcher(settings),
        "playwright": playwright,
    }
    primary = transports.get(engine, transports["scrapy"])
    return FetchPipeline(primary=primary, http=http, playwright=playwright, settings=settings)


__all__ = [
    "BACKEND_ROOT",
    "BaseFetcher",
    "FetchPipeline",
    "HttpFetcher",
    "PlaywrightFetcher",
    "RobotsOutcome",
    "ScrapyFetcher",
    "fetch_robots",
    "get_fetcher",
    "request_pinned",
]
