"""Headless Chromium rendering for client-rendered (SPA) pages.

The renderer is used when :func:`app.crawler.utils.looks_like_spa` flags a
document, or when a crawl explicitly requests ``force_playwright``.

Security: the browser is inside our network, so every request it makes is
re-validated against the SSRF policy (sub-resources included) and blocked when
it targets a private address.
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import Settings, get_settings
from app.core.logging_config import get_logger
from app.crawler.utils import CrawlError, header_dict

logger = get_logger(__name__)

#: Resource types skipped to make rendering fast (they do not affect text).
BLOCKED_RESOURCE_TYPES = {"image", "media", "font"}
#: Upper bound on how long we wait for network idle after DOM ready.
NETWORK_IDLE_TIMEOUT_MS = 3000


class PlaywrightUnavailableError(CrawlError):
    """Playwright or its Chromium build is not installed."""


@dataclass(slots=True)
class RenderedPage:
    """Output of a headless render."""

    html: str
    status_code: int
    content_type: str
    final_url: str
    response_time_ms: int
    size_bytes: int
    headers: dict[str, str]


def _browser_search_roots() -> list[Path]:
    """Directories Playwright may have installed browsers into."""
    import os

    roots: list[Path] = []
    configured = os.environ.get("PLAYWRIGHT_BROWSERS_PATH")
    if configured and configured != "0":
        roots.append(Path(configured))
    elif configured == "0":  # browsers bundled inside the wheel
        try:
            import playwright

            roots.append(
                Path(playwright.__file__).parent / "driver" / "package" / ".local-browsers"
            )
        except ImportError:  # pragma: no cover
            pass
    else:
        roots.append(Path.home() / ".cache" / "ms-playwright")
    roots.append(Path("/ms-playwright"))  # Docker image location
    roots.append(Path("/root/.cache/ms-playwright"))
    return roots


_CHROMIUM_CANDIDATES = (
    "chrome-linux/chrome",
    "chrome-linux/headless_shell",
    "chrome-linux64/chrome",
    "chrome-win/chrome.exe",
    "chrome-mac/Chromium.app/Contents/MacOS/Chromium",
)
_chromium_available: bool | None = None


def chromium_available(*, refresh: bool = False) -> bool:
    """True when the Chromium binary required by Playwright is installed.

    Filesystem based (no browser launch, no reactor), cached for the process.
    """
    global _chromium_available
    if _chromium_available is not None and not refresh:
        return _chromium_available
    found = False
    for root in _browser_search_roots():
        try:
            if not root.is_dir():
                continue
            for entry in root.glob("chromium*"):
                for candidate in _CHROMIUM_CANDIDATES:
                    if (entry / candidate).exists():
                        found = True
                        break
                if found:
                    break
        except OSError:  # pragma: no cover - unreadable directory
            continue
        if found:
            break
    _chromium_available = found
    return found


class PlaywrightRenderer:
    """Process-wide Chromium driver with a reusable browser instance."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._playwright: Any | None = None
        self._browser: Any | None = None
        self._lock = asyncio.Lock()
        self._blocked_host_cache: dict[str, bool] = {}

    # -- lifecycle -----------------------------------------------------------
    async def _ensure_browser(self):
        from playwright.async_api import async_playwright

        async with self._lock:
            if self._browser is not None and self._browser.is_connected():
                return self._browser
            if self._playwright is None:
                self._playwright = await async_playwright().start()
            self._browser = await self._playwright.chromium.launch(
                headless=self.settings.PLAYWRIGHT_HEADLESS,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--disable-background-networking",
                ],
            )
            logger.info("playwright.browser_started", headless=self.settings.PLAYWRIGHT_HEADLESS)
            return self._browser

    async def close(self) -> None:
        """Shut the browser down (application shutdown)."""
        async with self._lock:
            if self._browser is not None:
                try:
                    await self._browser.close()
                except Exception as exc:
                    logger.warning("playwright.close_failed", error=str(exc))
                self._browser = None
            if self._playwright is not None:
                try:
                    await self._playwright.stop()
                except Exception as exc:
                    logger.warning("playwright.stop_failed", error=str(exc))
                self._playwright = None

    # -- SSRF guard for sub-resources ---------------------------------------
    async def _is_request_allowed(self, url: str) -> bool:
        from urllib.parse import urlparse

        from app.core.security import check_ssrf_async

        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"}:
            return True  # data:, blob:, about: - no network egress
        host = (parsed.hostname or "").lower()
        cached = self._blocked_host_cache.get(host)
        if cached is not None:
            return not cached
        try:
            await check_ssrf_async(url)
            allowed = True
        except Exception:
            allowed = False
        self._blocked_host_cache[host] = not allowed
        return allowed

    # -- rendering -----------------------------------------------------------
    async def render(self, url: str, *, timeout_ms: int | None = None) -> RenderedPage:
        """Render ``url`` in Chromium and return the resulting HTML."""
        timeout = timeout_ms or self.settings.PLAYWRIGHT_TIMEOUT_MS
        started = time.perf_counter()
        browser = await self._ensure_browser()
        context = await browser.new_context(
            user_agent=self.settings.CRAWLER_USER_AGENT,
            java_script_enabled=True,
            ignore_https_errors=False,
        )
        blocked = 0

        async def route_handler(route, request):
            nonlocal blocked
            if request.resource_type in BLOCKED_RESOURCE_TYPES:
                await route.abort()
                return
            if not await self._is_request_allowed(request.url):
                blocked += 1
                logger.warning("playwright.subresource_blocked", url=request.url)
                await route.abort()
                return
            await route.continue_()

        page = await context.new_page()
        await page.route("**/*", route_handler)
        try:
            response = await page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            # Best effort: let client-side rendering settle, but never fail on it.
            with contextlib.suppress(Exception):
                await page.wait_for_load_state("networkidle", timeout=NETWORK_IDLE_TIMEOUT_MS)
            html = await page.content()
            headers = header_dict(await response.all_headers()) if response else {}
            status = response.status if response else 0
            final_url = page.url
            content_type = (response.headers.get("content-type") if response else "") or "text/html"
        finally:
            await context.close()

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        logger.info(
            "playwright.rendered",
            url=url,
            status=status,
            size_bytes=len(html),
            duration_ms=elapsed_ms,
            blocked_requests=blocked,
        )
        return RenderedPage(
            html=html,
            status_code=status,
            content_type=content_type,
            final_url=final_url,
            response_time_ms=elapsed_ms,
            size_bytes=len(html.encode("utf-8")),
            headers=headers,
        )


_renderer: PlaywrightRenderer | None = None


def get_renderer(settings: Settings | None = None) -> PlaywrightRenderer:
    """Return the process-wide renderer singleton."""
    global _renderer
    if _renderer is None:
        _renderer = PlaywrightRenderer(settings)
    return _renderer


async def render_page(url: str, *, timeout_ms: int | None = None) -> RenderedPage:
    """Convenience wrapper around the shared renderer."""
    if not chromium_available():
        raise PlaywrightUnavailableError(
            "Chromium is not installed. Run 'playwright install chromium' "
            "(the Docker image does this at build time)."
        )
    return await get_renderer().render(url, timeout_ms=timeout_ms)


async def shutdown_renderer() -> None:
    """Stop Chromium at application shutdown."""
    global _renderer
    if _renderer is not None:
        await _renderer.close()
        _renderer = None


__all__ = [
    "BLOCKED_RESOURCE_TYPES",
    "PlaywrightRenderer",
    "PlaywrightUnavailableError",
    "RenderedPage",
    "chromium_available",
    "get_renderer",
    "render_page",
    "shutdown_renderer",
]
