"""Scrapy + Playwright crawl pipeline.

Layers
------
``spiders/``    Scrapy spiders (pure Scrapy, run in a subprocess)
``pipelines/``  item pipelines: boilerplate stripping (cleaner) and metadata
                extraction (extractor), also usable as pure functions
``fetchers``    transport abstraction + robots.txt + SPA fallback
``settings``    Scrapy configuration derived from application settings
``utils``       URL validation, SSRF helpers, SPA detection, result types
"""

from app.crawler.utils import (
    CrawlError,
    FetchError,
    FetchResult,
    ResponseTooLargeError,
    RobotsDisallowedError,
    UnsupportedContentTypeError,
    looks_like_spa,
    parse_robots,
    validate_crawl_target,
)

__all__ = [
    "CrawlError",
    "FetchError",
    "FetchResult",
    "ResponseTooLargeError",
    "RobotsDisallowedError",
    "UnsupportedContentTypeError",
    "looks_like_spa",
    "parse_robots",
    "validate_crawl_target",
]
