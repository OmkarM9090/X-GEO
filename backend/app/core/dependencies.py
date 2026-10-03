"""Framework-level FastAPI dependencies shared across the application.

:mod:`app.api.deps` composes the request-scoped aliases used by routes
(``DbSession``, ``CurrentUser``, …). The primitives in this module are the ones
that carry no knowledge of authentication or persistence — settings,
pagination, request metadata — so non-HTTP entrypoints (tasks, scripts, health
probes) can build the exact same objects without importing request plumbing.

Keeping them here also means ``app/api/deps.py`` stays a thin composition layer
instead of a grab-bag of unrelated providers.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Query, Request

from app.config import Settings, get_settings
from app.schemas.common import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE, Pagination


def get_app_settings() -> Settings:
    """Application settings (overridable in tests via ``dependency_overrides``)."""
    return get_settings()


SettingsDep = Annotated[Settings, Depends(get_app_settings)]


def get_pagination(
    skip: int = Query(0, ge=0, description="Records to skip (offset)"),
    limit: int = Query(
        DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Page size (max 100)"
    ),
) -> Pagination:
    """Validated pagination parameters for every list endpoint."""
    return Pagination(skip=skip, limit=limit)


PaginationDep = Annotated[Pagination, Depends(get_pagination)]


def get_request_id(request: Request) -> str:
    """Request correlation id, set by :class:`RequestLoggingMiddleware`."""
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        return str(request_id)
    return request.headers.get("X-Request-ID", "")


RequestIdDep = Annotated[str, Depends(get_request_id)]


def client_ip(request: Request) -> str:
    """Socket peer address (never a client-controlled forwarding header)."""
    client = request.client
    return client.host if client and client.host else "unknown"


__all__ = [
    "PaginationDep",
    "RequestIdDep",
    "SettingsDep",
    "client_ip",
    "get_app_settings",
    "get_pagination",
    "get_request_id",
]
