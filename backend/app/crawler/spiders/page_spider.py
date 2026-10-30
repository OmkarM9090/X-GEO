"""Static-page spider.

The spider itself is a plain Scrapy ``Spider``. Because Twisted reactors cannot
be restarted inside a process, the programmatic entry point
(:func:`run_page_spider`) is designed to run inside a **subprocess**, which
:class:`app.crawler.fetchers.ScrapyFetcher` launches. That keeps the API/Celery
process free of reactor state while still using a real Scrapy crawl
(downloader middlewares, retries, autothrottle, item pipelines).

CLI::

    python -m app.crawler.spiders.page_spider --url https://example.com --timeout 20
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any

import scrapy
from scrapy import signals
from scrapy.crawler import CrawlerProcess

from app.crawler.settings import build_scrapy_settings
from app.crawler.utils import validate_crawl_target

#: Marker used to hand structured data from the subprocess back to the parent.
RESULT_MARKER = "XGEO_RESULT_JSON:"


class PageSpider(scrapy.Spider):
    """Fetch a single URL and emit its raw HTML plus transport metadata."""

    name = "page"

    def __init__(
        self,
        url: str | None = None,
        user_agent: str | None = None,
        max_bytes: int | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        if not url:
            raise ValueError("PageSpider requires a 'url' argument")
        # Validate + SSRF-check before a single byte leaves the process.
        self.start_url = validate_crawl_target(url)
        self.user_agent = user_agent
        self.max_bytes = max_bytes
        self.last_error: str | None = None
        self.last_status: int | None = None

    def start_requests(self):
        headers = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"}
        if self.user_agent:
            headers["User-Agent"] = self.user_agent
        yield scrapy.Request(
            self.start_url,
            callback=self.parse,
            errback=self.on_error,
            dont_filter=True,
            headers=headers,
            meta={"request_started": time.monotonic()},
        )

    def parse(self, response):
        started = response.meta.get("request_started")
        latency = response.meta.get("download_latency")
        elapsed_ms = (
            int(latency * 1000)
            if latency
            else int((time.monotonic() - (started or time.monotonic())) * 1000)
        )

        body = response.body
        if self.max_bytes and len(body) > self.max_bytes:
            self.last_error = f"Response exceeded {self.max_bytes} bytes"
            return

        html = response.text
        self.last_status = response.status
        yield {
            "url": self.start_url,
            "final_url": response.url,
            "status_code": response.status,
            "content_type": response.headers.get("Content-Type", b"").decode("latin-1"),
            "html": html,
            "response_time_ms": elapsed_ms,
            "size_bytes": len(body),
            "headers": {
                key.decode("latin-1").lower(): value.decode("latin-1")
                for key, value in response.headers.items()
            },
        }

    def on_error(self, failure: Any) -> None:
        self.last_error = str(failure.value)
        self.logger.warning(
            "page_spider.request_failed", extra={"url": self.start_url, "error": self.last_error}
        )


def run_page_spider(
    url: str,
    *,
    settings: dict[str, Any] | None = None,
    timeout: int | None = None,
    user_agent: str | None = None,
    max_bytes: int | None = None,
) -> dict[str, Any]:
    """Run one crawl to completion (blocking; call inside a subprocess).

    Returns ``{"ok": bool, "item": {...} | None, "error": str | None}``.
    """
    config = settings or build_scrapy_settings()
    if timeout:
        config["DOWNLOAD_TIMEOUT"] = timeout
    if max_bytes:
        config["DOWNLOAD_MAXSIZE"] = max_bytes

    collected: list[dict[str, Any]] = []
    errors: list[str] = []

    process = CrawlerProcess(config, install_root_handler=False)
    crawler = process.create_crawler(PageSpider)

    def _collect_item(item: Any, response: Any, spider: Any) -> None:  # noqa: ARG001
        try:
            collected.append(dict(item))
        except Exception as exc:
            errors.append(f"item collection failed: {exc}")

    def _collect_error(failure: Any, response: Any, spider: Any) -> None:  # noqa: ARG001
        errors.append(str(failure.value))

    crawler.signals.connect(_collect_item, signal=signals.item_scraped)
    crawler.signals.connect(_collect_error, signal=signals.spider_error)

    process.crawl(crawler, url=url, user_agent=user_agent, max_bytes=max_bytes)
    process.start()  # blocks until the reactor stops

    spider = getattr(crawler, "spider", None)
    spider_error = getattr(spider, "last_error", None)
    if collected:
        return {"ok": True, "item": collected[0], "error": None}
    return {
        "ok": False,
        "item": None,
        "error": spider_error or (errors[0] if errors else "crawl produced no item"),
    }


def main(argv: list[str] | None = None) -> int:
    """Console entry point used by ``ScrapyFetcher`` (prints a marker line)."""
    parser = argparse.ArgumentParser(description="Fetch a single page with Scrapy.")
    parser.add_argument("--url", required=True)
    parser.add_argument("--timeout", type=int, default=None)
    parser.add_argument("--user-agent", default=None)
    parser.add_argument("--max-bytes", type=int, default=None)
    args = parser.parse_args(argv)

    try:
        payload = run_page_spider(
            args.url,
            timeout=args.timeout,
            user_agent=args.user_agent,
            max_bytes=args.max_bytes,
        )
    except Exception as exc:
        payload = {"ok": False, "item": None, "error": f"{type(exc).__name__}: {exc}"}

    sys.stdout.write(RESULT_MARKER + json.dumps(payload) + "\n")
    sys.stdout.flush()
    return 0 if payload.get("ok") else 1


if __name__ == "__main__":  # pragma: no cover - exercised via subprocess
    raise SystemExit(main())
