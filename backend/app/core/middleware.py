"""HTTP middleware: request correlation, timing, access logs, tenant context.

Layering (outermost first, as registered in :mod:`app.main`):

``TenantContextMiddleware`` → ``RequestLoggingMiddleware`` → routes

* :class:`RequestLoggingMiddleware` — pure-ASGI (no ``BaseHTTPMiddleware``
  overhead/streaming caveats). Generates or propagates ``X-Request-ID``, records
  the duration, emits one structured access log line per request and stamps the
  ``X-Request-ID`` / ``X-Process-Time-Ms`` response headers.
* :class:`TenantContextMiddleware` — best-effort decoding of the bearer token so
  the tenant/user identifiers are attached to every log line emitted deeper in
  the stack. It never rejects a request; authentication remains the job of
  :mod:`app.api.deps`.
* :class:`SlidingWindowRateLimiter` — in-process limiter, with a Redis backed
  variant used automatically when Redis is reachable.
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Protocol

from fastapi import Request, Response
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.config import get_settings
from app.core.exceptions import RateLimitError
from app.core.logging_config import bind_request_context, clear_request_context, get_logger
from app.core.security import extract_bearer_token, generate_request_id

logger = get_logger(__name__)

#: Response headers added to every request.
SECURITY_HEADERS: tuple[tuple[bytes, bytes], ...] = (
    (b"x-content-type-options", b"nosniff"),
    (b"referrer-policy", b"no-referrer"),
    (b"x-permitted-cross-domain-policies", b"none"),
)
# NOTE: X-Frame-Options / CSP are intentionally NOT set here. The API is also
# consumed from embedded previews and dashboards, so framing policy belongs to
# the edge proxy (nginx/Cloudflare) where it can be tuned per environment.

_SKIP_ACCESS_LOG_PATHS = frozenset({"/api/v1/health", "/api/v1/health/", "/favicon.ico"})


class RequestLoggingMiddleware:
    """Request id + timing + structured access logging."""

    def __init__(self, app: ASGIApp, *, access_log: bool | None = None) -> None:
        self.app = app
        self._access_log_override = access_log

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        settings = get_settings()
        access_log = (
            settings.ACCESS_LOG_ENABLED
            if self._access_log_override is None
            else self._access_log_override
        )

        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        header_name = settings.REQUEST_ID_HEADER.lower()
        request_id = headers.get(header_name) or generate_request_id()
        path = scope.get("path", "")
        method = scope.get("method", "GET")

        bind_request_context(request_id=request_id, method=method, path=path)
        started = time.perf_counter()
        status_code = 500
        response_started = False

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code, response_started
            if message["type"] == "http.response.start":
                status_code = message["status"]
                response_started = True
                duration_ms = round((time.perf_counter() - started) * 1000, 2)
                raw_headers = list(message.get("headers") or [])
                raw_headers.extend(SECURITY_HEADERS)
                raw_headers.append(
                    (
                        settings.REQUEST_ID_HEADER.lower().encode("latin-1"),
                        request_id.encode("latin-1"),
                    )
                )
                raw_headers.append((b"x-process-time-ms", str(duration_ms).encode("latin-1")))
                message = {**message, "headers": raw_headers}
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            if access_log and path not in _SKIP_ACCESS_LOG_PATHS:
                log = logger.warning if status_code >= 500 else logger.info
                log(
                    "http.request",
                    status_code=status_code,
                    duration_ms=duration_ms,
                    client=scope.get("client", ("unknown", 0))[0],
                    user_agent=headers.get("user-agent", "")[:120],
                    response_started=response_started,
                )
            clear_request_context()


class TenantContextMiddleware:
    """Bind the caller's tenant/user id to the logging context.

    The token is decoded **without** raising: unauthenticated or invalid requests
    simply continue with an empty context and are rejected later by the auth
    dependency with a proper 401 response.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        authorization = None
        for key, value in scope.get("headers", []):
            if key.lower() == b"authorization":
                authorization = value.decode("latin-1")
                break

        if authorization:
            try:
                import jwt as pyjwt

                token = extract_bearer_token(authorization)
                payload = pyjwt.decode(token, options={"verify_signature": False})
                bind_request_context(tenant_id=payload.get("sub"), token_role=payload.get("role"))
            except Exception:
                pass

        await self.app(scope, receive, send)


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class RateLimitResult:
    """Outcome of a single rate-limit check."""

    allowed: bool
    limit: int
    remaining: int
    reset_after_seconds: int


class RateLimiter(Protocol):
    """Minimal interface shared by the memory and Redis implementations."""

    async def hit(self, key: str, *, limit: int, window_seconds: int) -> RateLimitResult: ...


class SlidingWindowRateLimiter:
    """Fixed-window counter backed by a dict of deques.

    Suitable for a single process (development, tests, single-worker deployments).
    """

    def __init__(self, *, max_keys: int = 20_000) -> None:
        self._hits: dict[str, deque[float]] = {}
        self._lock = asyncio.Lock()
        self._max_keys = max_keys

    async def hit(self, key: str, *, limit: int, window_seconds: int) -> RateLimitResult:
        now = time.monotonic()
        cutoff = now - window_seconds
        async with self._lock:
            bucket = self._hits.setdefault(key, deque())
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            allowed = len(bucket) < limit
            if allowed:
                bucket.append(now)
            remaining = max(0, limit - len(bucket))
            if not bucket:
                self._hits.pop(key, None)
            elif len(self._hits) > self._max_keys:
                self._prune(cutoff)
        return RateLimitResult(
            allowed=allowed,
            limit=limit,
            remaining=remaining,
            reset_after_seconds=window_seconds,
        )

    def _prune(self, cutoff: float) -> None:
        for key in [key for key, bucket in self._hits.items() if not bucket or bucket[-1] < cutoff]:
            self._hits.pop(key, None)

    def reset(self) -> None:
        self._hits.clear()


class RedisRateLimiter:
    """Fixed-window counter in Redis (shared across workers/pods)."""

    def __init__(self, url: str, *, prefix: str = "xgeo:ratelimit") -> None:
        self._url = url
        self._prefix = prefix
        self._client: Any | None = None

    async def _get_client(self) -> Any:
        if self._client is None:
            from redis.asyncio import Redis

            self._client = Redis.from_url(self._url, encoding="utf-8", decode_responses=True)
        return self._client

    async def hit(self, key: str, *, limit: int, window_seconds: int) -> RateLimitResult:
        client = await self._get_client()
        redis_key = f"{self._prefix}:{key}"
        async with client.pipeline(transaction=True) as pipe:
            pipe.incr(redis_key, 1)
            pipe.ttl(redis_key)
            count, ttl = await pipe.execute()
        if ttl is None or ttl < 0:
            await client.expire(redis_key, window_seconds)
            ttl = window_seconds
        return RateLimitResult(
            allowed=int(count) <= limit,
            limit=limit,
            remaining=max(0, limit - int(count)),
            reset_after_seconds=int(ttl) or window_seconds,
        )


_limiter: RateLimiter | None = None


def get_rate_limiter() -> RateLimiter:
    """Return the process-wide rate limiter (Redis when configured)."""
    global _limiter
    if _limiter is None:
        settings = get_settings()
        if settings.ENVIRONMENT == "production" and settings.REDIS_URL:
            _limiter = RedisRateLimiter(settings.REDIS_URL)
        else:
            _limiter = SlidingWindowRateLimiter()
    return _limiter


def set_rate_limiter(limiter: RateLimiter | None) -> None:
    """Override the limiter (tests, custom deployments)."""
    global _limiter
    _limiter = limiter


def reset_rate_limiter_state() -> None:
    """Clear in-memory counters (test isolation)."""
    if isinstance(_limiter, SlidingWindowRateLimiter):
        _limiter.reset()


def client_identifier(request: Request) -> str:
    """Rate-limit bucket key for a request.

    Uses the socket peer address. ``X-Forwarded-For`` is deliberately ignored:
    it is client controlled unless a trusted proxy strips it, and trusting it
    here would let attackers trivially bypass the limiter.
    """
    client = request.client
    return client.host if client and client.host else "unknown"


def rate_limit(
    scope: str,
    *,
    limit_attr: str = "RATE_LIMIT_PER_MINUTE",
    window_seconds: int = 60,
) -> Callable[[Request, Response], Awaitable[None]]:
    """Build a FastAPI dependency enforcing a per-client rate limit."""

    async def dependency(request: Request, response: Response) -> None:
        settings = get_settings()
        if not settings.RATE_LIMIT_ENABLED:
            return
        limit = int(getattr(settings, limit_attr))
        if limit <= 0:
            return
        result = await get_rate_limiter().hit(
            f"{scope}:{client_identifier(request)}", limit=limit, window_seconds=window_seconds
        )
        response.headers["X-RateLimit-Limit"] = str(result.limit)
        response.headers["X-RateLimit-Remaining"] = str(result.remaining)
        if not result.allowed:
            logger.warning("rate_limit.exceeded", scope=scope, client=client_identifier(request))
            raise RateLimitError(result.reset_after_seconds)

    return dependency


__all__ = [
    "RedisRateLimiter",
    "RequestLoggingMiddleware",
    "SlidingWindowRateLimiter",
    "TenantContextMiddleware",
    "client_identifier",
    "get_rate_limiter",
    "rate_limit",
    "reset_rate_limiter_state",
    "set_rate_limiter",
]
