"""Crawler utilities: fetch result types, URL validation/SSRF, robots.txt, SPA detection.

Pure helpers only (no network I/O) so this module is safe to import from tests,
Scrapy pipelines and the API process alike.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlparse, urlunparse

from app.core.exceptions import SSRFBlockedError
from app.core.security import check_ssrf, check_ssrf_async, validate_url

#: Responses larger than this are rejected before parsing.
#: Lazily built offline tldextract instance (see :func:`_tld_extract`).
_TLD_EXTRACTOR: Any | None = None

DEFAULT_MAX_BYTES = 5_000_000
#: Content types we are willing to parse.
HTML_CONTENT_TYPES = ("text/html", "application/xhtml+xml", "application/xml", "text/xml")
#: Marker phrases that indicate a client-rendered (SPA) shell.
_SPA_MARKERS = (
    'id="root"',
    "id='root'",
    'id="app"',
    "id='app'",
    "__next_data__",
    "window.__nuxt__",
    "ng-version",
    "data-reactroot",
    "v-app",
)
_MIN_SPA_TEXT_WORDS = 120

_CONTENT_TYPE_RE = re.compile(r"^\s*(?P<mime>[a-z0-9.+-]+/[a-z0-9.+-]+)", re.IGNORECASE)
_SCRIPT_TAG_RE = re.compile(r"(?is)<script[^>]*>.*?</script>")


class CrawlError(Exception):
    """Base class for crawler failures (mapped to audit error messages)."""


class RobotsDisallowedError(CrawlError):
    """The target's robots.txt forbids fetching the URL."""


class FetchError(CrawlError):
    """The transport failed (DNS, TLS, timeout, connection reset...)."""


class ResponseTooLargeError(CrawlError):
    """The response exceeded the configured size budget."""


class UnsupportedContentTypeError(CrawlError):
    """The response is not HTML/XML."""


def describe_crawl_error(exc: BaseException) -> str:
    """Human-readable, non-leaky description of a crawl failure."""
    if isinstance(exc, RobotsDisallowedError):
        return "Blocked by robots.txt"
    if isinstance(exc, ResponseTooLargeError):
        return "Response exceeded the maximum allowed size"
    if isinstance(exc, UnsupportedContentTypeError):
        return "Target did not return an HTML document"
    if isinstance(exc, FetchError):
        return f"Fetch failed: {exc}"
    if isinstance(exc, SSRFBlockedError):
        return "Target resolves to a blocked (private) address"
    return f"{type(exc).__name__}: {exc}"


@dataclass(slots=True)
class FetchResult:
    """Normalised result of fetching one URL, whatever the transport."""

    url: str
    final_url: str
    status_code: int
    content_type: str
    html: str
    response_time_ms: int
    size_bytes: int
    method: str
    is_spa_detected: bool = False
    playwright_fallback_used: bool = False
    robots_allowed: bool = True
    robots_txt: str | None = None
    sitemap_url: str | None = None
    headers: dict[str, str] = field(default_factory=dict)

    @property
    def is_html(self) -> bool:
        mime = _CONTENT_TYPE_RE.match(self.content_type or "")
        if mime is None:
            return False
        return mime.group("mime").lower() in HTML_CONTENT_TYPES


@dataclass(frozen=True, slots=True)
class RobotsPolicy:
    """Outcome of evaluating robots.txt for one target."""

    allowed: bool
    sitemap_url: str | None = None
    raw_text: str | None = None
    reason: str = ""


def parse_robots(
    robots_txt: str | None, url: str, *, user_agent: str, allow_missing: bool = True
) -> RobotsPolicy:
    """Evaluate ``robots_txt`` for ``url``.

    Missing robots.txt (``None``/empty) is treated as *allowed*, which matches
    RFC 9309 behaviour for absent files. Parsing problems fail open but are
    reported through :attr:`RobotsPolicy.reason` so they surface in logs.
    """
    if not robots_txt or not robots_txt.strip():
        return RobotsPolicy(allowed=allow_missing, raw_text=robots_txt, reason="no robots.txt")

    try:
        from protego import Protego
    except ImportError:  # pragma: no cover - protego ships with Scrapy
        return RobotsPolicy(allowed=True, raw_text=robots_txt, reason="robots parser unavailable")

    try:
        parser = Protego.parse(robots_txt)
        allowed = parser.can_fetch(url, user_agent)
        sitemaps = list(getattr(parser, "sitemaps", []) or [])
    except Exception as exc:
        return RobotsPolicy(allowed=True, raw_text=robots_txt, reason=f"robots parse error: {exc}")

    return RobotsPolicy(
        allowed=bool(allowed),
        sitemap_url=sitemaps[0] if sitemaps else None,
        raw_text=robots_txt,
        reason="allowed" if allowed else "disallowed",
    )


# ---------------------------------------------------------------------------
# URL helpers
# ---------------------------------------------------------------------------
def normalize_url(url: str) -> str:
    """Validate and normalise a URL (scheme/host lowercase, no fragment)."""
    normalized = validate_url(url)
    parsed = urlparse(normalized)
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, parsed.query, ""))


def _tld_extract(host: str) -> Any:
    """Offline PSL lookup (bundled snapshot, no HTTP requests at crawl time)."""
    global _TLD_EXTRACTOR
    if _TLD_EXTRACTOR is None:
        import tldextract

        # `suffix_list_urls=()` pins tldextract to the snapshot shipped in the
        # wheel: a crawl worker must never make surprise outbound calls, and the
        # public suffix list would otherwise be fetched on first use.
        _TLD_EXTRACTOR = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None)
    return _TLD_EXTRACTOR(host)


def host_of(url: str) -> str:
    """Hostname of a URL, lowercased (empty string when malformed)."""
    try:
        return (urlparse(url).hostname or "").lower()
    except ValueError:  # pragma: no cover - defensive
        return ""


def registrable_host(host: str) -> str:
    """Best-effort eTLD+1 (``blog.example.co.uk`` → ``example.co.uk``)."""
    host = (host or "").lower().strip(".")
    if not host or host.replace(".", "").isdigit():
        return host
    try:

        extracted = _tld_extract(host)
        if extracted.domain and extracted.suffix:
            return f"{extracted.domain}.{extracted.suffix}"
    except Exception:
        pass
    parts = host.split(".")
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def is_same_site(candidate_url: str, base_url: str) -> bool:
    """True when both URLs belong to the same registrable domain."""
    return registrable_host(host_of(candidate_url)) == registrable_host(host_of(base_url))


def absolutize(base_url: str, href: str) -> str | None:
    """Resolve a possibly relative href against ``base_url`` (http/https only)."""
    if not href:
        return None
    href = href.strip()
    if href.startswith(("mailto:", "tel:", "javascript:", "data:", "#")):
        return None
    absolute = urljoin(base_url, href)
    scheme = urlparse(absolute).scheme.lower()
    if scheme not in {"http", "https"}:
        return None
    return absolute.split("#", 1)[0]


def validate_crawl_target(url: str) -> str:
    """Validate + SSRF-check a URL before it is handed to a transport.

    Synchronous variant; async callers should use
    :func:`app.core.security.check_ssrf_async` to keep DNS off the event loop.
    """
    normalized = normalize_url(url)
    check_ssrf(normalized)
    return normalized


def is_html_content_type(content_type: str | None) -> bool:
    """True when a Content-Type header denotes an HTML/XML document."""
    mime = _CONTENT_TYPE_RE.match(content_type or "")
    if not mime:
        return False
    return mime.group("mime").lower() in HTML_CONTENT_TYPES


# ---------------------------------------------------------------------------
# SPA detection
# ---------------------------------------------------------------------------
def visible_text_length(html: str) -> int:
    """Word count of the HTML with script/style blocks removed."""
    stripped = _SCRIPT_TAG_RE.sub(" ", html or "")
    stripped = re.sub(r"(?is)<style[^>]*>.*?</style>", " ", stripped)
    stripped = re.sub(r"(?s)<[^>]+>", " ", stripped)
    return len(stripped.split())


def looks_like_spa(html: str, *, min_words: int = _MIN_SPA_TEXT_WORDS) -> bool:
    """Heuristic SPA/CSR detection.

    True when the served HTML looks like an application shell: a known framework
    mount point, or very little server-rendered text relative to the document.
    """
    if not html:
        return False
    lowered = html.lower()
    if any(marker.lower() in lowered for marker in _SPA_MARKERS):
        # A framework marker alone is weak evidence — require thin content too,
        # unless the page is essentially an empty shell.
        return visible_text_length(html) < min_words or "<noscript" in lowered
    return visible_text_length(html) < max(20, min_words // 4)


def extract_sitemap_hint(html: str, base_url: str) -> str | None:
    """Find a sitemap declared in the document head."""
    match = re.search(r'(?is)<link[^>]+rel=["\']?sitemap["\']?[^>]*>', html or "")
    if not match:
        return None
    href = re.search(r'href=["\']([^"\']+)["\']', match.group(0), re.IGNORECASE)
    if not href:
        return None
    return absolutize(base_url, href.group(1))


def truncate_text(text: str, limit: int) -> str:
    """Truncate ``text`` to ``limit`` characters with an ellipsis marker."""
    if limit <= 0 or len(text) <= limit:
        return text
    return text[:limit] + "…[truncated]"


def header_dict(headers: Any) -> dict[str, str]:
    """Normalise httpx/Scrapy headers into a plain lowercase dict."""
    try:
        return {str(key).lower(): str(value) for key, value in dict(headers).items()}
    except Exception:
        return {}


__all__ = [
    "DEFAULT_MAX_BYTES",
    "HTML_CONTENT_TYPES",
    "CrawlError",
    "FetchError",
    "FetchResult",
    "ResponseTooLargeError",
    "RobotsDisallowedError",
    "RobotsPolicy",
    "UnsupportedContentTypeError",
    "absolutize",
    "check_ssrf",
    "check_ssrf_async",
    "describe_crawl_error",
    "extract_sitemap_hint",
    "header_dict",
    "host_of",
    "is_html_content_type",
    "is_same_site",
    "looks_like_spa",
    "normalize_url",
    "parse_robots",
    "registrable_host",
    "truncate_text",
    "validate_crawl_target",
    "validate_url",
    "visible_text_length",
]
