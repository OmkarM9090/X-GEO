"""Security primitives: URL validation, SSRF prevention, JWT handling, hashing.

This module is deliberately dependency-light (stdlib + PyJWT + httpx) so it can
be reused by the Scrapy/Playwright workers, CLI scripts and the API layer.

SSRF model
----------
1. :func:`validate_url` normalises and syntactically validates a URL
   (http/https only, no control characters, IDN hosts converted to punycode).
2. :func:`check_ssrf` resolves **every** A/AAAA record for the host and rejects
   the target when any of them is private, loopback, link-local, multicast,
   reserved or otherwise non-globally-routable. Operators can punch holes with
   ``SSRF_ALLOWLIST`` (exact hostname or CIDR) for staging targets they own.
3. :func:`resolve_target` returns the vetted addresses so callers can *pin* the
   connection and defeat DNS-rebinding between check and fetch.
"""

from __future__ import annotations

import hashlib
import hmac
import ipaddress
import re
import secrets
import socket
import time
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import urlparse, urlunparse

import anyio
import jwt
import structlog
from jwt import algorithms as jwt_algorithms

from app.config import Settings, get_settings
from app.core.exceptions import (  # noqa: F401  (re-exported for convenience in callers)
    ConfigurationError,
    InvalidInputError,
    NotFoundError,
    SSRFBlockedError,
    UnauthorizedError,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_URL_LENGTH = 2048
ALLOWED_SCHEMES = frozenset({"http", "https"})
DEFAULT_PORTS = {"http": 80, "https": 443}
#: Detects a scheme prefix in strings that never reached the "://" check.
_SCHEME_PREFIX_RE = re.compile(r"^([A-Za-z][A-Za-z0-9+.\-]*):")

#: Prompt-injection / markup patterns stripped from crawled content before it is
#: ever handed to an LLM (defence in depth for Phase 3 simulations).
DANGEROUS_CONTENT_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"(?is)<\s*script[^>]*>.*?<\s*/\s*script\s*>", " "),
    (r"(?is)<\s*style[^>]*>.*?<\s*/\s*style\s*>", " "),
    (r"(?is)<!--.*?-->", " "),
    (r"(?i)ignore\s+(all\s+)?(the\s+)?previous\s+instructions?", "[SANITIZED]"),
    (r"(?i)disregard\s+(all\s+)?(the\s+)?previous\s+instructions?", "[SANITIZED]"),
    (r"(?i)you\s+are\s+now\s+", "[SANITIZED]"),
    (r"(?i)new\s+instructions?\s*:", "[SANITIZED]"),
    (r"(?i)system\s*:\s*", "[SANITIZED]"),
    (r"(?i)assistant\s*:\s*", "[SANITIZED]"),
    (r"(?i)developer\s+mode\s*:", "[SANITIZED]"),
    (r"(?is)\{\{.*?\}\}", " "),  # template injection markers
)

_ZERO_WIDTH_CHARS = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff"), None)

# scrypt parameters (RFC 7914 recommended interactive profile)
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SCRYPT_DKLEN = 32
SCRYPT_SALT_BYTES = 16
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128


# ---------------------------------------------------------------------------
# URL validation + normalisation
# ---------------------------------------------------------------------------
def _strip_control_chars(value: str, *, keep_layout: bool = False) -> str:
    """Remove control characters (including NUL) from user supplied text.

    ``keep_layout`` preserves ``\\n``/``\\r``/``\\t`` so that Markdown structure
    survives sanitisation; URL validation keeps the strict default (where the
    caller's whitespace check then rejects any embedded newline or tab).
    """
    preserved = {"\n", "\r", "\t"} if keep_layout else ()
    return "".join(
        char for char in value if unicodedata.category(char) != "Cc" or char in preserved
    )


def _idna_encode(host: str) -> str:
    """Convert an internationalised hostname to its ASCII (punycode) form."""
    try:
        return host.encode("idna").decode("ascii")
    except (UnicodeError, UnicodeDecodeError):
        # Underscores and other RFC-violating but real-world hostnames.
        return host


def validate_url(url: str, *, allow_private_hosts: bool = False) -> str:
    """Validate and normalise a URL, returning the canonical string form.

    Raises :class:`~app.core.exceptions.InvalidInputError` (a ``ValueError``) for
    anything that is not a plain ``http(s)`` URL pointing at a hostname or IP.

    >>> validate_url("HTTPS://Example.com/")
    'https://example.com'
    """
    if not isinstance(url, str):
        raise InvalidInputError("URL must be a string")

    original = url
    url = url.strip()
    if not url:
        raise InvalidInputError("URL must not be empty")
    # Control characters are rejected rather than stripped: silently joining
    # "https://example.com/\x00http://internal" would hide an injection attempt.
    if any(unicodedata.category(char) == "Cc" for char in url):
        raise InvalidInputError("URL must not contain whitespace or control characters")
    if len(url) > MAX_URL_LENGTH:
        raise InvalidInputError(f"URL exceeds the maximum length of {MAX_URL_LENGTH} characters")
    if any(char.isspace() for char in url):
        raise InvalidInputError("URL must not contain whitespace")

    if "://" not in url:
        prefixed = _SCHEME_PREFIX_RE.match(url)
        if prefixed:
            raise InvalidInputError(
                f"Unsupported URL scheme {prefixed.group(1).lower()!r}: "
                "only http and https are allowed"
            )
        raise InvalidInputError(
            f"Invalid URL format: {original!r} (missing scheme, expected http:// or https://)"
        )

    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    if scheme not in ALLOWED_SCHEMES:
        raise InvalidInputError(
            f"Unsupported URL scheme {scheme or '(none)'!r}: only http and https are allowed"
        )
    if not parsed.netloc or not parsed.hostname:
        raise InvalidInputError(f"Invalid URL format: {original!r} (missing host)")

    hostname = _idna_encode(parsed.hostname.lower())
    if "." not in hostname and not _is_ip_literal(hostname) and not allow_private_hosts:
        raise InvalidInputError(
            f"Invalid URL host {hostname!r}: expected a fully qualified domain name or IP address"
        )

    try:
        port = parsed.port
    except ValueError as exc:  # invalid port -> urlparse raises ValueError
        raise InvalidInputError(f"Invalid URL port in {original!r}: {exc}") from exc

    # IPv6 literals must stay bracketed so that `urlparse().port` keeps working.
    netloc_host = f"[{hostname}]" if _is_ipv6_literal(hostname) else hostname
    netloc = netloc_host
    if port and port != DEFAULT_PORTS.get(scheme):
        netloc = f"{netloc_host}:{port}"

    path = parsed.path or ""
    normalised = urlunparse((scheme, netloc, path, parsed.params, parsed.query, parsed.fragment))
    # `https://example.com/` -> `https://example.com`
    if not parsed.query and not parsed.fragment:
        normalised = normalised.rstrip("/") or normalised
    return normalised


def validate_domain(url: str) -> str:
    """Return the normalised origin (``scheme://host[:port]``) of a URL."""
    normalised = validate_url(url)
    parsed = urlparse(normalised)
    netloc = parsed.netloc
    return f"{parsed.scheme}://{netloc}"


def _is_ip_literal(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
    except ValueError:
        return False
    return True


def _is_ipv6_literal(host: str) -> bool:
    try:
        return ipaddress.ip_address(host).version == 6
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# SSRF prevention
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class UrlPolicy:
    """Pre-compiled SSRF rules for the current settings."""

    blocked_networks: tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]
    allowed_networks: tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]
    allowed_hosts: frozenset[str]
    strict_mode: bool

    def is_allowed_host(self, hostname: str) -> bool:
        hostname = hostname.lower().rstrip(".")
        if hostname in self.allowed_hosts:
            return True
        # Allow suffix matching for convenience: allowlisting `example.com`
        # implicitly allows `staging.example.com`.
        return any(
            hostname.endswith(f".{allowed}") for allowed in self.allowed_hosts if "." in allowed
        )

    def is_allowed_address(self, ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        return any(ip in network for network in self.allowed_networks)

    def is_blocked_address(self, ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
        # The explicit denylist is authoritative: some addresses Python marks as
        # `is_global` (multicast, 192.0.0.0/24, benchmarking ranges) are still
        # never legitimate crawl targets.
        if any(ip in network for network in self.blocked_networks):
            return True
        return bool(self.strict_mode and not ip.is_global)


def build_url_policy(settings: Settings | None = None) -> UrlPolicy:
    """Compile the SSRF policy from settings (called per validation)."""
    settings = settings or get_settings()
    blocked: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for cidr in settings.SSRF_BLOCKED_RANGES:
        try:
            blocked.append(ipaddress.ip_network(cidr, strict=False))
        except ValueError:  # pragma: no cover - misconfiguration
            logger.warning("ssrf.invalid_blocked_range", cidr=cidr)

    allowed_networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    allowed_hosts: set[str] = set()
    for entry in settings.SSRF_ALLOWLIST:
        entry = entry.strip().lower()
        if not entry:
            continue
        try:
            allowed_networks.append(ipaddress.ip_network(entry, strict=False))
        except ValueError:
            allowed_hosts.add(entry)

    return UrlPolicy(
        blocked_networks=tuple(blocked),
        allowed_networks=tuple(allowed_networks),
        allowed_hosts=frozenset(allowed_hosts),
        strict_mode=settings.SSRF_STRICT_MODE,
    )


@dataclass(frozen=True, slots=True)
class ResolvedTarget:
    """A URL that passed SSRF validation together with its vetted addresses."""

    url: str
    scheme: str
    hostname: str
    port: int
    ip_addresses: tuple[ipaddress.IPv4Address | ipaddress.IPv6Address, ...]

    @property
    def primary_ip(self) -> str:
        return str(self.ip_addresses[0])

    @property
    def host_header(self) -> str:
        default_port = DEFAULT_PORTS.get(self.scheme)
        if self.port and self.port != default_port:
            return f"{self.hostname}:{self.port}"
        return self.hostname


def _resolve_host(
    hostname: str, port: int | None
) -> tuple[ipaddress.IPv4Address | ipaddress.IPv6Address, ...]:
    """Resolve every A/AAAA record for a hostname."""
    try:
        infos = socket.getaddrinfo(hostname, port or 0, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise InvalidInputError(f"DNS resolution failed for {hostname}: {exc}") from exc

    addresses: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for _family, _type, _proto, _canonical, sockaddr in infos:
        try:
            addresses.append(ipaddress.ip_address(sockaddr[0]))
        except ValueError:  # pragma: no cover - defensive
            continue
    if not addresses:
        raise InvalidInputError(f"DNS resolution returned no addresses for {hostname}")
    # Preserve order but remove duplicates.
    return tuple(dict.fromkeys(addresses))


def resolve_target(url: str, *, policy: UrlPolicy | None = None) -> ResolvedTarget:
    """Validate a URL, resolve it and assert every address is publicly routable."""
    policy = policy or build_url_policy()
    settings = get_settings()
    # Single-label hosts (e.g. an internal wiki) are only acceptable when the
    # operator explicitly allowlisted them.
    hostname_hint = urlparse(url).hostname or ""
    allow_private_hostnames = policy.is_allowed_host(hostname_hint)
    normalised = validate_url(url, allow_private_hosts=allow_private_hostnames)
    parsed = urlparse(normalised)
    hostname = parsed.hostname or ""
    port = parsed.port or DEFAULT_PORTS.get(parsed.scheme, 80)

    if policy.is_allowed_host(hostname):
        addresses = _resolve_host(hostname, port)
        return ResolvedTarget(normalised, parsed.scheme, hostname, port, addresses)

    addresses = _resolve_host(hostname, port)
    for address in addresses:
        if policy.is_allowed_address(address):
            continue
        if policy.is_blocked_address(address):
            logger.warning(
                "ssrf.blocked",
                url=redact_url(normalised),
                hostname=hostname,
                resolved_ip=str(address),
            )
            raise SSRFBlockedError(hostname, resolved_ip=str(address))

    if settings.SSRF_STRICT_MODE and not addresses:  # pragma: no cover - defensive
        raise SSRFBlockedError(hostname)
    return ResolvedTarget(normalised, parsed.scheme, hostname, port, addresses)


def check_ssrf(url: str, *, policy: UrlPolicy | None = None) -> ResolvedTarget:
    """Validate a URL and reject private/internal targets.

    Raises :class:`SSRFBlockedError` (a ``ValueError``) when the target resolves
    to a blocked address. Returns the vetted :class:`ResolvedTarget`.
    """
    return resolve_target(url, policy=policy)


async def check_ssrf_async(url: str, *, policy: UrlPolicy | None = None) -> ResolvedTarget:
    """Async wrapper around :func:`check_ssrf` (DNS resolution off the loop)."""
    return await anyio.to_thread.run_sync(lambda: resolve_target(url, policy=policy))


def is_url_safe(url: str) -> bool:
    """Boolean convenience wrapper (never raises)."""
    try:
        check_ssrf(url)
    except (ValueError, OSError):
        return False
    return True


# ---------------------------------------------------------------------------
# Password hashing (scrypt, stdlib only)
# ---------------------------------------------------------------------------
def _assert_password_policy(password: str) -> None:
    if not isinstance(password, str):
        raise InvalidInputError("Password must be a string")
    if len(password) < PASSWORD_MIN_LENGTH:
        raise InvalidInputError(f"Password must be at least {PASSWORD_MIN_LENGTH} characters long")
    if len(password) > PASSWORD_MAX_LENGTH:
        raise InvalidInputError(f"Password must be at most {PASSWORD_MAX_LENGTH} characters long")
    if not password.strip():
        raise InvalidInputError("Password must not be blank")


def hash_password(password: str) -> str:
    """Hash a password with scrypt, returning ``scrypt$n$r$p$salt$hash``.

    Supabase remains the identity provider for end users; this helper exists for
    locally managed/service accounts and for future self-hosted auth.
    """
    _assert_password_policy(password)
    salt = secrets.token_bytes(SCRYPT_SALT_BYTES)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=SCRYPT_DKLEN,
    )
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    """Constant-time verification of a :func:`hash_password` digest."""
    if not encoded or not password:
        return False
    try:
        scheme, n, r, p, salt_hex, digest_hex = encoded.split("$")
        if scheme != "scrypt":
            return False
        expected = bytes.fromhex(digest_hex)
        candidate = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
        )
    except (ValueError, TypeError):  # malformed stored hash
        return False
    return hmac.compare_digest(candidate, expected)


def password_needs_rehash(encoded: str) -> bool:
    """True when a stored hash was produced with weaker parameters."""
    try:
        scheme, n, r, p, _salt, _digest = encoded.split("$")
    except ValueError:
        return True
    return scheme != "scrypt" or (int(n), int(r), int(p)) != (SCRYPT_N, SCRYPT_R, SCRYPT_P)


# ---------------------------------------------------------------------------
# JWT / bearer tokens
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class TokenClaims:
    """Normalised view over a Supabase (or development) access token."""

    subject: str
    email: str | None
    role: str | None
    audience: str | None
    expires_at: datetime | None
    claims: Mapping[str, Any]

    @property
    def is_service_role(self) -> bool:
        return self.role == "service_role"


def extract_bearer_token(authorization: str | None) -> str:
    """Pull the token out of an ``Authorization: Bearer <jwt>`` header."""
    if not authorization:
        raise UnauthorizedError("Missing Authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise UnauthorizedError("Authorization header must use the Bearer scheme")
    return token.strip()


def _claims_from_payload(payload: Mapping[str, Any]) -> TokenClaims:
    subject = payload.get("sub")
    if not subject:
        raise UnauthorizedError("Token is missing the 'sub' claim")
    expires_at: datetime | None = None
    if (exp := payload.get("exp")) is not None:
        try:
            expires_at = datetime.fromtimestamp(int(exp), tz=UTC)
        except (TypeError, ValueError, OSError):  # pragma: no cover - defensive
            expires_at = None
    return TokenClaims(
        subject=str(subject),
        email=payload.get("email"),
        role=payload.get("role"),
        audience=payload.get("aud"),
        expires_at=expires_at,
        claims=payload,
    )


def _hmac_secret(settings: Settings) -> str:
    if not settings.SUPABASE_JWT_SECRET or settings._looks_like_placeholder(
        settings.SUPABASE_JWT_SECRET
    ):
        raise ConfigurationError("JWT verification", ["SUPABASE_JWT_SECRET"])
    return settings.SUPABASE_JWT_SECRET


def _decode_options(settings: Settings, *, audience: str | None = None) -> dict[str, Any]:
    _audience = audience if audience is not None else settings.SUPABASE_JWT_AUDIENCE
    return {
        "algorithms": list(settings.SUPABASE_JWT_ALGORITHMS),
        "audience": _audience,
        # Always verify `aud` when one is configured: a token minted for another
        # service with the same shared secret must not authenticate here.
        "options": {"require": ["exp", "sub"], "verify_aud": bool(_audience)},
    }


def decode_jwt(
    token: str, *, settings: Settings | None = None, audience: str | None = None
) -> TokenClaims:
    """Verify and decode a JWT signed with a shared secret (HS256/384/512)."""
    settings = settings or get_settings()
    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError(f"Invalid authentication token: {exc}") from exc

    algorithm = (header.get("alg") or "").upper()
    if not algorithm.startswith("HS"):
        raise UnauthorizedError(
            f"Unsupported token algorithm {algorithm or 'unknown'}: "
            "use decode_jwt_async() for asymmetric (ES/RS) Supabase tokens"
        )

    try:
        payload = jwt.decode(
            token,
            _hmac_secret(settings),
            issuer=settings.auth_issuer,
            **_decode_options(settings, audience=audience),
        )
    except jwt.ExpiredSignatureError as exc:
        raise UnauthorizedError("Authentication token has expired") from exc
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError(f"Invalid authentication token: {exc}") from exc
    return _claims_from_payload(payload)


# --- JWKS (asymmetric Supabase signing keys) --------------------------------
_JWKS_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


def clear_jwks_cache() -> None:
    """Drop the cached JWKS document (tests, key rotation)."""
    _JWKS_CACHE.clear()


async def _fetch_jwks(url: str, *, ttl_seconds: int, force: bool = False) -> dict[str, Any]:
    import httpx  # imported lazily: only needed for asymmetric tokens

    cached = _JWKS_CACHE.get(url)
    now = time.monotonic()
    if cached and not force and (now - cached[0]) < ttl_seconds:
        return cached[1]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, headers={"Accept": "application/json"})
            response.raise_for_status()
            document = response.json()
    except Exception as exc:
        logger.warning("jwks.fetch_failed", url=url, error=str(exc))
        if cached:
            return cached[1]
        raise UnauthorizedError("Unable to verify token signing keys") from exc

    _JWKS_CACHE[url] = (now, document)
    return document


async def decode_jwt_async(
    token: str, *, settings: Settings | None = None, audience: str | None = None
) -> TokenClaims:
    """Verify a token, using Supabase's JWKS for asymmetric algorithms."""
    settings = settings or get_settings()
    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError as exc:
        raise UnauthorizedError(f"Invalid authentication token: {exc}") from exc

    algorithm = (header.get("alg") or "").upper()
    if algorithm.startswith("HS"):
        return decode_jwt(token, settings=settings, audience=audience)
    if algorithm not in {"ES256", "ES384", "ES512", "RS256", "RS384", "RS512"}:
        raise UnauthorizedError(f"Unsupported token algorithm: {algorithm or 'unknown'}")
    if not settings.supabase_url_normalised:
        raise ConfigurationError("JWT verification", ["SUPABASE_URL"])

    jwks = await _fetch_jwks(
        settings.supabase_jwks_url, ttl_seconds=settings.SUPABASE_JWKS_CACHE_SECONDS
    )
    key_id = header.get("kid")
    candidates = [key for key in jwks.get("keys", []) if key_id is None or key.get("kid") == key_id]
    if not candidates:
        raise UnauthorizedError("Token signing key is not published by the identity provider")

    for jwk in candidates:
        try:
            key: Any = (
                jwt_algorithms.RSAAlgorithm.from_jwk(jwk)
                if algorithm.startswith("RS")
                else jwt_algorithms.ECAlgorithm.from_jwk(jwk)
            )
            payload = jwt.decode(
                token,
                key,
                issuer=settings.auth_issuer,
                **_decode_options(settings, audience=audience),
            )
            return _claims_from_payload(payload)
        except jwt.ExpiredSignatureError as exc:
            raise UnauthorizedError("Authentication token has expired") from exc
        except jwt.InvalidTokenError:
            continue
    raise UnauthorizedError("Invalid authentication token: signature verification failed")


def create_local_token(
    *,
    subject: str,
    email: str | None = None,
    role: str = "authenticated",
    settings: Settings | None = None,
    ttl_seconds: int | None = None,
    audience: str | None = None,
) -> str:
    """Mint a Supabase-shaped token with the shared secret.

    Used by the DEBUG-only ``/auth/dev-token`` endpoint and by the test suite —
    never by production request handling.
    """
    settings = settings or get_settings()
    now = datetime.now(tz=UTC)
    ttl = ttl_seconds or settings.AUTH_DEV_TOKEN_TTL_SECONDS
    payload: dict[str, Any] = {
        "sub": subject,
        "aud": audience or settings.SUPABASE_JWT_AUDIENCE,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl)).timestamp()),
        "iss": settings.auth_issuer or "x-geo-local",
    }
    if email:
        payload["email"] = email
    return jwt.encode(payload, _hmac_secret(settings), algorithm="HS256")


def token_fingerprint(token: str) -> str:
    """Stable, non-reversible token identifier safe for logs."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Misc helpers
# ---------------------------------------------------------------------------
def generate_request_id() -> str:
    """Opaque request correlation id."""
    return secrets.token_hex(16)


def redact_url(url: str) -> str:
    """Strip credentials, query string and fragment before logging a URL."""
    try:
        parsed = urlparse(url)
    except ValueError:  # pragma: no cover - defensive
        return "<unparsable-url>"
    netloc = parsed.hostname or ""
    if parsed.port:
        netloc = f"{netloc}:{parsed.port}"
    return urlunparse((parsed.scheme, netloc, parsed.path, "", "", ""))


def sanitize_crawled_content(raw_text: str, *, max_length: int | None = None) -> str:
    """Remove prompt-injection markers and control characters from crawled text.

    Applied to every page (and every chunk) before the content can be embedded,
    quoted, or handed to an LLM.
    """
    cleaned = raw_text or ""
    for pattern, replacement in DANGEROUS_CONTENT_PATTERNS:
        cleaned = re.sub(pattern, replacement, cleaned)
    cleaned = cleaned.translate(_ZERO_WIDTH_CHARS)
    cleaned = cleaned.replace("\r\n", "\n").replace("\r", "\n")
    cleaned = _strip_control_chars(cleaned, keep_layout=True)
    if max_length is not None and len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    return cleaned


def constant_time_compare(left: str, right: str) -> bool:
    """Timing-safe string comparison."""
    return hmac.compare_digest(left.encode("utf-8"), right.encode("utf-8"))


def hash_ip(ip: str) -> str:
    """Pseudonymise an IP address for analytics/logging."""
    return hashlib.sha256(ip.encode("utf-8")).hexdigest()[:16]


def as_sequence(value: Sequence[str] | str) -> list[str]:
    """Normalise a string-or-sequence setting into a list of strings."""
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return list(value)
