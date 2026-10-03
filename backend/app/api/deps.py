"""FastAPI dependency injection.

Routes depend on the aliases defined here (``DbSession``, ``CurrentUser``,
``CurrentClaims``, ``PaginationDep``) and never construct services or sessions
themselves. Authentication always goes through :class:`AuthService`, so
verification, JIT provisioning and activation checks live in one place.

Framework-level providers (settings, pagination, request id, client IP) live in
:mod:`app.core.dependencies`; they are re-exported here so route modules keep a
single import site.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db as _get_db
from app.core.dependencies import (
    PaginationDep,
    RequestIdDep,
    SettingsDep,
    client_ip,
    get_app_settings,
    get_pagination,
    get_request_id,
)
from app.core.exceptions import UnauthorizedError
from app.core.security import TokenClaims, extract_bearer_token
from app.models.user import User
from app.services.auth_service import AuthService


async def get_db() -> AsyncIterator[AsyncSession]:
    """Request-scoped transactional session (re-exported for route modules)."""
    async for session in _get_db():
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_auth_service(db: DbSession, settings: SettingsDep) -> AuthService:
    """Auth service bound to the request session."""
    return AuthService(db, settings=settings)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


async def get_bearer_token(
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> str:
    """Raw bearer token from the ``Authorization`` header."""
    return extract_bearer_token(authorization)


BearerToken = Annotated[str, Depends(get_bearer_token)]


async def get_current_claims(
    token: BearerToken,
    service: AuthServiceDep,
) -> TokenClaims:
    """Verified JWT claims of the caller (401 when absent/invalid)."""
    return await service.verify_token(token)


CurrentClaims = Annotated[TokenClaims, Depends(get_current_claims)]


async def get_current_user(
    claims: CurrentClaims,
    service: AuthServiceDep,
) -> User:
    """Local user row for the authenticated caller.

    Provisions the shadow row on first sight (``AUTH_AUTO_PROVISION_USERS``) and
    rejects deactivated accounts.
    """
    return await service.resolve_user(claims)


CurrentUser = Annotated[User, Depends(get_current_user)]


async def get_optional_user(
    service: AuthServiceDep,
    authorization: Annotated[str | None, Header(alias="Authorization")] = None,
) -> User | None:
    """Current user when a valid token is present, ``None`` otherwise."""
    if not authorization:
        return None
    try:
        claims = await service.verify_token(extract_bearer_token(authorization))
        return await service.resolve_user(claims)
    except UnauthorizedError:
        return None


OptionalUser = Annotated[User | None, Depends(get_optional_user)]


__all__ = [
    "AuthServiceDep",
    "BearerToken",
    "CurrentClaims",
    "CurrentUser",
    "DbSession",
    "OptionalUser",
    "PaginationDep",
    "RequestIdDep",
    "SettingsDep",
    "client_ip",
    "get_app_settings",
    "get_auth_service",
    "get_bearer_token",
    "get_current_claims",
    "get_current_user",
    "get_db",
    "get_optional_user",
    "get_pagination",
    "get_request_id",
]
