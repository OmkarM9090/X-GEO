"""Domain exceptions.

Every error raised by the service layer derives from :class:`AppError`, which is
both a Starlette ``HTTPException`` (so FastAPI can render it) and a plain
``Exception``. Validation-style errors additionally derive from ``ValueError``
so pure-Python callers (unit tests, crawler utilities, scripts) can catch them
without importing FastAPI.

The rendered payload is defined by :class:`app.schemas.common.ErrorResponse` and
always contains a top-level ``message`` field for client convenience.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status


class AppError(HTTPException):
    """Base class for all expected, client-facing errors."""

    code: str = "error"
    status_code_default: int = status.HTTP_400_BAD_REQUEST
    message_template: str = "Request failed"

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
        headers: dict[str, str] | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.message_template
        self.code = code or self.code
        self.details = details or {}
        super().__init__(
            status_code=status_code or self.status_code_default,
            detail=self.message,
            headers=headers,
        )


class InvalidInputError(AppError, ValueError):
    """Malformed input that Pydantic could not catch (URLs, files, CSV...)."""

    code = "invalid_input"
    status_code_default = status.HTTP_422_UNPROCESSABLE_ENTITY


class NotFoundError(AppError):
    """Requested resource does not exist (or is not visible to this tenant)."""

    code = "not_found"
    status_code_default = status.HTTP_404_NOT_FOUND

    def __init__(self, resource: str, identifier: str | Any = "") -> None:
        super().__init__(f"{resource} with id '{identifier}' not found")


class UnauthorizedError(AppError):
    """Missing or invalid credentials (401 + WWW-Authenticate)."""

    code = "unauthorized"
    status_code_default = status.HTTP_401_UNAUTHORIZED

    def __init__(self, message: str = "Not authenticated", *, scheme: str = "Bearer") -> None:
        super().__init__(message, headers={"WWW-Authenticate": scheme})


class ForbiddenError(AppError):
    """Authenticated but not allowed to touch this resource (403)."""

    code = "forbidden"
    status_code_default = status.HTTP_403_FORBIDDEN

    def __init__(self, message: str = "Access denied") -> None:
        super().__init__(message)


class ConflictError(AppError):
    """Uniqueness / state conflict (409)."""

    code = "conflict"
    status_code_default = status.HTTP_409_CONFLICT


class QuotaExceededError(AppError):
    """Plan quota exhausted (402)."""

    code = "quota_exceeded"
    status_code_default = status.HTTP_402_PAYMENT_REQUIRED

    def __init__(self, message: str = "Monthly credit limit reached") -> None:
        super().__init__(message)


class SSRFBlockedError(AppError, ValueError):
    """Target resolves to a private/blocked address."""

    code = "ssrf_blocked"
    status_code_default = status.HTTP_422_UNPROCESSABLE_ENTITY

    def __init__(self, target: str, *, resolved_ip: str | None = None) -> None:
        message = f"SSRF blocked: {target}"
        if resolved_ip:
            message = f"{message} resolves to blocked address {resolved_ip}"
        super().__init__(message)


class CrawlFailedError(AppError):
    """The crawler could not produce content for a URL (502)."""

    code = "crawl_failed"
    status_code_default = status.HTTP_502_BAD_GATEWAY

    def __init__(self, url: str, reason: str) -> None:
        super().__init__(
            f"Crawl failed for {url}: {reason}", details={"url": url, "reason": reason}
        )


class RateLimitError(AppError):
    """Too many requests (429 + Retry-After)."""

    code = "rate_limited"
    status_code_default = status.HTTP_429_TOO_MANY_REQUESTS

    def __init__(self, retry_after_seconds: int = 60) -> None:
        super().__init__(
            "Rate limit exceeded. Please try again later.",
            headers={"Retry-After": str(retry_after_seconds)},
            details={"retry_after_seconds": retry_after_seconds},
        )


class ExternalServiceError(AppError):
    """An upstream dependency (Supabase, OpenAI, ...) failed (502)."""

    code = "external_service_error"
    status_code_default = status.HTTP_502_BAD_GATEWAY

    def __init__(self, service: str, detail: str) -> None:
        super().__init__(f"{service} request failed: {detail}", details={"service": service})


class ServiceUnavailableError(AppError):
    """Temporary inability to serve traffic (503)."""

    code = "service_unavailable"
    status_code_default = status.HTTP_503_SERVICE_UNAVAILABLE


class ConfigurationError(AppError):
    """The server is missing configuration required for this feature (500)."""

    code = "configuration_error"
    status_code_default = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(self, feature: str, missing: list[str]) -> None:
        super().__init__(
            f"{feature} is not configured. Missing: {', '.join(missing)}",
            details={"feature": feature, "missing": missing},
        )


__all__ = [
    "AppError",
    "ConfigurationError",
    "ConflictError",
    "CrawlFailedError",
    "ExternalServiceError",
    "ForbiddenError",
    "InvalidInputError",
    "NotFoundError",
    "QuotaExceededError",
    "RateLimitError",
    "SSRFBlockedError",
    "ServiceUnavailableError",
    "UnauthorizedError",
]
