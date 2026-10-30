"""HTML boilerplate stripping and markdown conversion.

Used both as a Scrapy item pipeline (:class:`CleanerPipeline`) and as a pure
function library (:func:`html_to_markdown`) by the crawl service and tests.

Pipeline order: ``ExtractorPipeline`` → ``CleanerPipeline`` → item export.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from lxml import html as lxml_html

from app.core.security import sanitize_crawled_content

#: Elements removed wholesale (navigation chrome, embeds, non-content markup).
BOILERPLATE_TAGS = (
    "script",
    "style",
    "noscript",
    "template",
    "iframe",
    "svg",
    "canvas",
    "form",
    "nav",
    "header",
    "footer",
    "aside",
    "dialog",
)

#: class/id substrings that identify chrome even when tags are generic <div>s.
BOILERPLATE_PATTERNS = re.compile(
    r"(?i)(?:^|[-_\s])("
    r"nav|navbar|navigation|menu|breadcrumb|sidebar|side-bar|footer|header|topbar|"
    r"cookie|consent|gdpr|banner|popup|modal|overlay|advert|advertis|ads?|sponsor|"
    r"promo|newsletter|subscribe|social|share|related|recommend|comment|disqus|"
    r"skip-link|screen-reader|sr-only|visually-hidden"
    r")(?:$|[-_\s])"
)
#: Containers that usually hold the article body.
MAIN_CONTENT_SELECTORS = (
    "main",
    "article",
    "[role=main]",
    ".post-content",
    ".entry-content",
    ".article-body",
    ".markdown-body",
    "#content",
    ".content",
)

#: GFM table: a pipe row immediately followed by a `---` separator row.
_MD_TABLE_RE = re.compile(
    r"^\s*\|?[^\n|]*\|[^\n]*\n"  # header row containing a pipe
    r"\s*\|?\s*:?-{3,}:?\s*"  # first separator cell
    r"(?:\|\s*:?-{3,}:?\s*)*\|?\s*$",  # remaining cells, trailing pipe optional
    re.MULTILINE,
)

#: Tags whose text content is never part of the readable document.
NON_CONTENT_TAGS = ("script", "style", "noscript", "template")

#: A candidate region must hold at least this share of the document text to be
#: treated as the main content (below it, the page is kept as-is).
MIN_CONTENT_SHARE = 0.25

_WHITESPACE_RE = re.compile(r"[ \t\x0b\f\r]+")
_MULTI_BLANK_RE = re.compile(r"\n{3,}")
_MD_LINK_RE = re.compile(r"\[[^\]]*\]\(<?(https?://[^)>\s]+)>?\)")


@dataclass(frozen=True, slots=True)
class CleanResult:
    """Cleaned representation of one HTML document."""

    markdown: str
    text: str
    word_count: int
    boilerplate_ratio: float
    has_lists: bool
    has_tables: bool
    avg_paragraph_words: float
    external_link_count: int
    removed_elements: int


def _parse(html: str) -> Any:
    """Parse HTML into an lxml tree (tolerant of malformed markup)."""
    try:
        return lxml_html.fromstring(html or "<html></html>")
    except Exception:
        return lxml_html.fromstring("<html><body></body></html>")


def strip_boilerplate(html: str) -> tuple[str, int]:
    """Remove navigation/chrome markup, returning ``(html, removed_count)``."""
    tree = _parse(html)
    removed = 0

    for tag in BOILERPLATE_TAGS:
        for element in tree.iter(tag):
            parent = element.getparent()
            if parent is not None:
                parent.remove(element)
                removed += 1

    # Drop generic containers whose class/id looks like chrome.
    for element in list(tree.iter()):
        attributes = " ".join(
            filter(None, (element.get("class"), element.get("id"), element.get("role")))
        )
        if attributes and BOILERPLATE_PATTERNS.search(attributes):
            parent = element.getparent()
            if parent is not None:
                parent.remove(element)
                removed += 1

    # Comments carry no content.
    for comment in tree.xpath("//comment()"):
        parent = comment.getparent()
        if parent is not None:
            parent.remove(comment)
            removed += 1

    return lxml_html.tostring(tree, encoding="unicode"), removed


def _without_non_content(tree: Any) -> Any:
    """Copy of ``tree`` without scripts, styles, templates or comments."""
    measurable = _parse(lxml_html.tostring(tree, encoding="unicode"))
    for tag in NON_CONTENT_TAGS:
        for element in list(measurable.iter(tag)):
            parent = element.getparent()
            if parent is not None:
                parent.remove(element)
    for comment in measurable.xpath("//comment()"):
        parent = comment.getparent()
        if parent is not None:
            parent.remove(comment)
    return measurable


def select_main_content(html: str) -> tuple[str, float]:
    """Return the densest main-content fragment plus the boilerplate ratio.

    The ratio (0 = every byte is content, 1 = nothing survived) feeds the
    machine-readability score. Script/style text is excluded from the
    measurement so it cannot mask the real article body, and a candidate is only
    accepted when it holds a meaningful share of the document
    (:data:`MIN_CONTENT_SHARE`).
    """
    tree = _parse(html)
    measurable = _without_non_content(tree)
    full_text = " ".join(measurable.text_content().split())
    full_length = len(full_text)
    whole_document = lxml_html.tostring(measurable, encoding="unicode")
    if full_length == 0:
        return whole_document, 1.0

    best_html = whole_document
    best_length = 0
    for selector in MAIN_CONTENT_SELECTORS:
        try:
            matches = measurable.cssselect(selector)
        except Exception:
            continue
        for match in matches:
            candidate = " ".join(match.text_content().split())
            if len(candidate) > best_length:
                best_length = len(candidate)
                best_html = lxml_html.tostring(match, encoding="unicode")

    if best_length == 0 or best_length < MIN_CONTENT_SHARE * full_length:
        return whole_document, 0.0
    ratio = 1.0 - min(1.0, best_length / full_length)
    return best_html, max(0.0, min(1.0, ratio))


def html_to_text(html: str) -> str:
    """Extract readable text (used for lexical and lexical-overlap analysis)."""
    tree = _without_non_content(_parse(html))
    text = tree.text_content()
    text = _WHITESPACE_RE.sub(" ", text)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip()).strip()


def html_to_markdown(html: str, *, base_url: str | None = None) -> CleanResult:
    """Convert HTML to sanitised markdown plus quality statistics.

    Steps: strip boilerplate → isolate main content → html2text → prompt
    injection sanitisation → statistics for the scoring rubric.
    """
    import html2text

    stripped_html, removed = strip_boilerplate(html)
    main_html, boilerplate_ratio = select_main_content(stripped_html)

    converter = html2text.HTML2Text()
    converter.body_width = 0
    converter.ignore_images = False
    converter.ignore_emphasis = False
    converter.protect_links = True
    converter.unicode_snob = True
    converter.single_line_break = False

    raw_markdown = converter.handle(main_html)
    markdown = sanitize_crawled_content(raw_markdown)
    markdown = _MULTI_BLANK_RE.sub("\n\n", markdown).strip()

    text = html_to_text(main_html)
    words = markdown.split()
    paragraphs = [paragraph for paragraph in re.split(r"\n\s*\n", markdown) if paragraph.strip()]
    paragraph_word_counts = [len(paragraph.split()) for paragraph in paragraphs]

    external_links = 0
    if base_url:
        from app.crawler.utils import is_same_site

        external_links = sum(
            1 for href in _MD_LINK_RE.findall(markdown) if not is_same_site(href, base_url)
        )
    else:
        external_links = len(_MD_LINK_RE.findall(markdown))

    return CleanResult(
        markdown=markdown,
        text=text,
        word_count=len(words),
        boilerplate_ratio=boilerplate_ratio,
        has_lists=bool(re.search(r"^\s*(?:[-*+]|\d+\.)\s+", markdown, re.MULTILINE)),
        has_tables=bool(_MD_TABLE_RE.search(markdown)),
        avg_paragraph_words=(
            sum(paragraph_word_counts) / len(paragraph_word_counts)
            if paragraph_word_counts
            else 0.0
        ),
        external_link_count=external_links,
        removed_elements=removed,
    )


class CleanerPipeline:
    """Scrapy pipeline: adds ``markdown``/``clean_text``/stats to each item."""

    def __init__(self) -> None:
        self.items_processed = 0

    @classmethod
    def from_crawler(cls, crawler: Any) -> CleanerPipeline:  # noqa: ARG003 - Scrapy hook
        return cls()

    def process_item(self, item: Any, spider: Any) -> Any:  # noqa: ARG002 - Scrapy hook
        html = item.get("html") if hasattr(item, "get") else None
        if not html:
            return item
        result = html_to_markdown(html, base_url=item.get("final_url") or item.get("url"))
        item["markdown"] = result.markdown
        item["clean_text"] = result.text
        item["word_count"] = result.word_count
        item["boilerplate_ratio"] = result.boilerplate_ratio
        item["has_lists"] = result.has_lists
        item["has_tables"] = result.has_tables
        item["avg_paragraph_words"] = result.avg_paragraph_words
        item["external_link_count"] = result.external_link_count
        self.items_processed += 1
        return item


__all__ = [
    "BOILERPLATE_PATTERNS",
    "BOILERPLATE_TAGS",
    "CleanResult",
    "CleanerPipeline",
    "html_to_markdown",
    "html_to_text",
    "select_main_content",
    "strip_boilerplate",
]
