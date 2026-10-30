"""Scrapy spiders."""

from app.crawler.spiders.page_spider import PageSpider, run_page_spider

__all__ = ["PageSpider", "run_page_spider"]
