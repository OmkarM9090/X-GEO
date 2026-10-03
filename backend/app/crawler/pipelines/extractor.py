"""Metadata, JSON-LD, heading and link extraction.

Used both as a Scrapy item pipeline (:class:`ExtractorPipeline`) and as a pure
function library (:func:`extract_metadata`).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any

from lxml import html as lxml_html

from app.crawler.utils import absolutize, host_of, is_same_site, registrable_host

#: Tags considered "semantic HTML" for the machine-readability score.
SEMANTIC_TAGS = ("main", "article", "section", "header", "footer", "nav", "aside", "figure", "time")
SEMANTIC_PRIMARY = ("main", "article")
SEMANTIC_SECONDARY = ("section", "header", "footer")

_OG_RE = re.compile(
    r'<meta[^>]+property=["\'](og:[^"\']+)["\'][^>]+content=["\']([^"\']*)["\']', re.I
)


@dataclass(frozen=True, slots=True)
class Heading:
    """One heading in document order."""

    level: int
    text: str


@dataclass(frozen=True, slots=True)
class PageMetadata:
    """Everything the scorers and the UI need from a page's markup."""

    url: str
    final_url: str
    title: str | None = None
    meta_description: str | None = None
    canonical_url: str | None = None
    lang: str | None = None
    viewport: str | None = None
    robots_meta: str | None = None
    has_json_ld: bool = False
    json_ld_data: dict | list | None = None
    json_ld_types: tuple[str, ...] = ()
    headings: tuple[Heading, ...] = ()
    heading_structure_valid: bool = False
    has_canonical: bool = False
    has_meta_description: bool = False
    has_lang: bool = False
    has_viewport: bool = False
    has_sitemap: bool = False
    sitemap_url: str | None = None
    semantic_html_score: float = 0.0
    internal_links: tuple[str, ...] = ()
    external_links: tuple[str, ...] = ()
    images_total: int = 0
    images_missing_alt: int = 0
    open_graph: dict[str, str] = field(default_factory=dict)

    @property
    def external_link_count(self) -> int:
        return len(self.external_links)

    @property
    def h1_count(self) -> int:
        return sum(1 for heading in self.headings if heading.level == 1)

    def as_dict(self) -> dict[str, Any]:
        """JSON-serialisable projection (item pipelines, debugging)."""
        return {
            "url": self.url,
            "final_url": self.final_url,
            "title": self.title,
            "meta_description": self.meta_description,
            "canonical_url": self.canonical_url,
            "lang": self.lang,
            "has_json_ld": self.has_json_ld,
            "json_ld_types": list(self.json_ld_types),
            "headings": [{"level": h.level, "text": h.text} for h in self.headings],
            "heading_structure_valid": self.heading_structure_valid,
            "internal_links": len(self.internal_links),
            "external_links": len(self.external_links),
            "images_total": self.images_total,
            "images_missing_alt": self.images_missing_alt,
        }


def _parse(html: str) -> Any:
    try:
        return lxml_html.fromstring(html or "<html></html>")
    except Exception:
        return lxml_html.fromstring("<html><body></body></html>")


def _meta_content(tree: Any, *, name: str | None = None, prop: str | None = None) -> str | None:
    if name:
        nodes = tree.xpath(
            f'//meta[translate(@name, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")="{name.lower()}"]/@content'
        )
    else:
        nodes = tree.xpath(f'//meta[@property="{prop}"]/@content')
    if nodes and nodes[0].strip():
        return nodes[0].strip()
    return None


def extract_json_ld(html: str) -> tuple[list[Any], tuple[str, ...]]:
    """Parse every ``application/ld+json`` block, tolerating malformed JSON."""
    blocks = re.findall(
        r'(?is)<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html or ""
    )
    parsed: list[Any] = []
    types: list[str] = []
    for block in blocks:
        text = block.strip()
        if not text:
            continue
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Some sites embed multiple objects or trailing commas.
            try:
                data = json.loads(re.sub(r",\s*([}\]])", r"\1", text))
            except json.JSONDecodeError:
                continue
        parsed.append(data)
        for candidate in data if isinstance(data, list) else [data]:
            if isinstance(candidate, dict):
                type_value = candidate.get("@type")
                if isinstance(type_value, str):
                    types.append(type_value)
                elif isinstance(type_value, list):
                    types.extend(str(item) for item in type_value)
    return parsed, tuple(dict.fromkeys(types))


def extract_headings(tree: Any) -> tuple[Heading, ...]:
    """Headings in document order."""
    headings: list[Heading] = []
    for level in range(1, 7):
        for element in tree.iter(f"h{level}"):
            text = " ".join((element.text_content() or "").split())
            if text:
                headings.append(Heading(level=level, text=text))
    # lxml iterates per tag, so restore document order.
    order = {element: index for index, element in enumerate(tree.iter())}
    elements_by_text: list[tuple[int, Heading]] = []
    for level in range(1, 7):
        for element in tree.iter(f"h{level}"):
            text = " ".join((element.text_content() or "").split())
            if text:
                elements_by_text.append((order.get(element, 0), Heading(level=level, text=text)))
    if elements_by_text:
        headings = [
            heading for _index, heading in sorted(elements_by_text, key=lambda item: item[0])
        ]
    return tuple(headings)


def validate_heading_structure(headings: tuple[Heading, ...]) -> bool:
    """True when the heading tree is well formed: exactly one H1, no skipped levels."""
    if not headings:
        return False
    if sum(1 for heading in headings if heading.level == 1) != 1:
        return False
    previous = 0
    for heading in headings:
        if previous and heading.level > previous + 1:
            return False
        previous = heading.level
    return True


def _semantic_score(tree: Any) -> float:
    present = {tag for tag in SEMANTIC_TAGS if next(tree.iter(tag), None) is not None}
    score = 0.0
    if present & set(SEMANTIC_PRIMARY):
        score += 0.45
    if present & set(SEMANTIC_SECONDARY):
        score += 0.30
    if "figure" in present or "time" in present:
        score += 0.25
    return round(min(1.0, score), 3)


def extract_metadata(html: str, *, base_url: str | None = None) -> PageMetadata:
    """Extract titles, meta tags, JSON-LD, headings and links from a document."""
    tree = _parse(html)
    url = base_url or ""

    title = None
    title_nodes = tree.xpath("//title/text()")
    if title_nodes:
        title = " ".join(title_nodes[0].split()) or None

    meta_description = _meta_content(tree, name="description")
    robots_meta = _meta_content(tree, name="robots")

    canonical_nodes = tree.xpath(
        '//link[translate(@rel, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")="canonical"]/@href'
    )
    canonical_url = None
    if canonical_nodes:
        canonical_url = absolutize(url, canonical_nodes[0]) or canonical_nodes[0].strip() or None

    lang_nodes = tree.xpath("/html/@lang | /html/@xml:lang")
    lang = lang_nodes[0].strip() if lang_nodes and lang_nodes[0].strip() else None
    viewport = _meta_content(tree, name="viewport")

    sitemap_hrefs = tree.xpath(
        '//link[contains(translate(@rel, "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz"), "sitemap")]/@href'
    )
    sitemap_url = absolutize(url, sitemap_hrefs[0]) if sitemap_hrefs else None

    json_ld_data, json_ld_types = extract_json_ld(html)
    headings = extract_headings(tree)

    internal: list[str] = []
    external: list[str] = []
    seen: set[str] = set()
    for href in tree.xpath("//a/@href"):
        absolute = absolutize(url, href)
        if not absolute or absolute in seen:
            continue
        seen.add(absolute)
        if url and is_same_site(absolute, url):
            internal.append(absolute)
        else:
            external.append(absolute)

    images = tree.xpath("//img")
    missing_alt = sum(1 for image in images if not (image.get("alt") or "").strip())

    open_graph = {match.group(1): match.group(2) for match in _OG_RE.finditer(html or "")}

    return PageMetadata(
        url=url,
        final_url=url,
        title=title,
        meta_description=meta_description,
        canonical_url=canonical_url,
        lang=lang,
        viewport=viewport,
        robots_meta=robots_meta,
        has_json_ld=bool(json_ld_data),
        json_ld_data=json_ld_data[0] if len(json_ld_data) == 1 else (json_ld_data or None),
        json_ld_types=json_ld_types,
        headings=headings,
        heading_structure_valid=validate_heading_structure(headings),
        has_canonical=bool(canonical_url),
        has_meta_description=bool(meta_description),
        has_lang=bool(lang),
        has_viewport=bool(viewport),
        has_sitemap=bool(sitemap_url),
        sitemap_url=sitemap_url,
        semantic_html_score=_semantic_score(tree),
        internal_links=tuple(internal[:500]),
        external_links=tuple(external[:500]),
        images_total=len(images),
        images_missing_alt=missing_alt,
        open_graph=open_graph,
    )


class ExtractorPipeline:
    """Scrapy pipeline: attaches :class:`PageMetadata` to each scraped item."""

    def __init__(self) -> None:
        self.items_processed = 0

    @classmethod
    def from_crawler(cls, crawler: Any) -> ExtractorPipeline:  # noqa: ARG003 - Scrapy hook
        return cls()

    def process_item(self, item: Any, spider: Any) -> Any:  # noqa: ARG002 - Scrapy hook
        html = item.get("html") if hasattr(item, "get") else None
        if not html:
            return item
        metadata = extract_metadata(html, base_url=item.get("final_url") or item.get("url"))
        item["metadata"] = metadata.as_dict()
        item["title"] = metadata.title
        item["meta_description"] = metadata.meta_description
        item["canonical_url"] = metadata.canonical_url
        item["has_json_ld"] = metadata.has_json_ld
        item["heading_structure_valid"] = metadata.heading_structure_valid
        self.items_processed += 1
        return item


__all__ = [
    "Heading",
    "PageMetadata",
    "ExtractorPipeline",
    "extract_headings",
    "extract_json_ld",
    "extract_metadata",
    "host_of",
    "registrable_host",
    "validate_heading_structure",
]
