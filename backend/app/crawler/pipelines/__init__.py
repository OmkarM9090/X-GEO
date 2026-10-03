"""Scrapy item pipelines (cleaner + extractor) and their pure helpers."""

from app.crawler.pipelines.cleaner import (
    CleanerPipeline,
    CleanResult,
    html_to_markdown,
    html_to_text,
    select_main_content,
    strip_boilerplate,
)
from app.crawler.pipelines.extractor import (
    ExtractorPipeline,
    Heading,
    PageMetadata,
    extract_json_ld,
    extract_metadata,
    validate_heading_structure,
)

__all__ = [
    "CleanResult",
    "CleanerPipeline",
    "ExtractorPipeline",
    "Heading",
    "PageMetadata",
    "extract_json_ld",
    "extract_metadata",
    "html_to_markdown",
    "html_to_text",
    "select_main_content",
    "strip_boilerplate",
    "validate_heading_structure",
]
