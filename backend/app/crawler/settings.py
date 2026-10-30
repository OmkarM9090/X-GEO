"""Scrapy settings.

Two consumers:

* the ``scrapy`` CLI / ``CrawlerProcess`` reads the module-level constants
  (``scrapy crawl page -a url=...`` with ``SCRAPY_SETTINGS_MODULE=app.crawler.settings``);
* :func:`build_scrapy_settings` produces a settings dict derived from
  :class:`app.config.Settings`, used by the in-process spider runner so runtime
  configuration (user agent, timeouts, size caps) has a single source of truth.

``ROBOTSTXT_OBEY`` is intentionally ``False``: robots.txt is evaluated once, in
:class:`app.crawler.fetchers.FetchPipeline`, so the decision is recorded on the
crawl job instead of being silently applied by the transport.
"""

from __future__ import annotations

from typing import Any

from app.config import Settings, get_settings

BOT_NAME = "x-geo"
SPIDER_MODULES = ["app.crawler.spiders"]
NEWSPIDER_MODULE = "app.crawler.spiders"

ROBOTSTXT_OBEY = False
COOKIES_ENABLED = False
TELNETCONSOLE_ENABLED = False
AJAXCRAWL_ENABLED = False

CONCURRENT_REQUESTS = 8
CONCURRENT_REQUESTS_PER_DOMAIN = 4
DOWNLOAD_DELAY = 0.25
RANDOMIZE_DOWNLOAD_DELAY = True
DOWNLOAD_TIMEOUT = 10
DOWNLOAD_MAXSIZE = 5_000_000
DOWNLOAD_WARNSIZE = 1_000_000
REDIRECT_ENABLED = True
REDIRECT_MAX_TIMES = 5

RETRY_ENABLED = True
RETRY_TIMES = 2
RETRY_HTTP_CODES = [500, 502, 503, 504, 522, 524, 408, 429]

AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 0.25
AUTOTHROTTLE_MAX_DELAY = 5.0
AUTOTHROTTLE_TARGET_CONCURRENCY = 2.0

# Fail open on 4xx/5xx so the pipeline (and tests) can inspect the response.
HTTPERROR_ALLOWED_CODES = [403, 404, 410, 429, 500, 502, 503, 504]

ITEM_PIPELINES = {
    "app.crawler.pipelines.extractor.ExtractorPipeline": 100,
    "app.crawler.pipelines.cleaner.CleanerPipeline": 200,
}

REQUEST_FINGERPRINTER_IMPLEMENTATION = "2.7"
FEED_EXPORT_ENCODING = "utf-8"
LOG_LEVEL = "WARNING"
LOG_STDOUT = False
USER_AGENT = "X-GEO-Bot/1.0 (+https://x-geo.dev/bot)"


def build_scrapy_settings(settings: Settings | None = None, **overrides: Any) -> dict[str, Any]:
    """Scrapy settings dict derived from application settings."""
    settings = settings or get_settings()
    config: dict[str, Any] = {
        "BOT_NAME": BOT_NAME,
        "SPIDER_MODULES": SPIDER_MODULES,
        "NEWSPIDER_MODULE": NEWSPIDER_MODULE,
        "ROBOTSTXT_OBEY": False,
        "COOKIES_ENABLED": COOKIES_ENABLED,
        "TELNETCONSOLE_ENABLED": False,
        "USER_AGENT": settings.CRAWLER_USER_AGENT,
        "DOWNLOAD_TIMEOUT": settings.CRAWLER_TIMEOUT_SECONDS,
        "DOWNLOAD_MAXSIZE": settings.CRAWLER_MAX_RESPONSE_BYTES,
        "RETRY_TIMES": max(0, settings.CRAWLER_MAX_RETRIES - 1),
        "CONCURRENT_REQUESTS": CONCURRENT_REQUESTS,
        "CONCURRENT_REQUESTS_PER_DOMAIN": CONCURRENT_REQUESTS_PER_DOMAIN,
        "DOWNLOAD_DELAY": DOWNLOAD_DELAY,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_TARGET_CONCURRENCY": AUTOTHROTTLE_TARGET_CONCURRENCY,
        "HTTPERROR_ALLOWED_CODES": [403, 404, 410, 429, 500, 502, 503, 504],
        "ITEM_PIPELINES": dict(ITEM_PIPELINES),
        "REQUEST_FINGERPRINTER_IMPLEMENTATION": REQUEST_FINGERPRINTER_IMPLEMENTATION,
        "FEED_EXPORT_ENCODING": "utf-8",
        "LOG_LEVEL": "WARNING",
        "LOG_STDOUT": False,
        "FEED_EXPORT_INDENT": None,
        "DEFAULT_REQUEST_HEADERS": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en",
        },
    }
    config.update(overrides)
    return config


__all__ = ["build_scrapy_settings"]
