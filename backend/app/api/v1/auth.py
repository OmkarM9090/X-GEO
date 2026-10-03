"""Authentication routes.

The service layer talks to Supabase GoTrue; these endpoints expose a stable,
documented contract for the frontend.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status

from app.api.deps import AuthServiceDep, BearerToken, CurrentClaims, CurrentUser
from app.core.middleware import rate_limit
from app.schemas.auth import (
    AuthMeResponse,
    AuthSessionResponse,
    DevTokenRequest,
    RefreshTokenRequest,
    SignInRequest,
    SignOutResponse,
    SignUpRequest,
    SignUpResponse,
)
from app.schemas.common import ErrorResponse

router = APIRouter()

#: Credential endpoints are rate limited harder than the rest of the API.
_auth_rate_limit = rate_limit("auth", limit_attr="AUTH_RATE_LIMIT_PER_MINUTE")

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Invalid or missing credentials"},
    429: {"model": ErrorResponse, "description": "Too many attempts"},
}


@router.post(
    "/signup",
    response_model=SignUpResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account",
    dependencies=[Depends(_auth_rate_limit)],
    responses=ERROR_RESPONSES,
)
async def sign_up(data: SignUpRequest, service: AuthServiceDep) -> SignUpResponse:
    """Register a new user with the identity provider and create the local row."""
    return await service.sign_up(data)


@router.post(
    "/signin",
    response_model=AuthSessionResponse,
    summary="Exchange credentials for tokens",
    dependencies=[Depends(_auth_rate_limit)],
    responses=ERROR_RESPONSES,
)
async def sign_in(data: SignInRequest, service: AuthServiceDep) -> AuthSessionResponse:
    """Authenticate with email + password."""
    return await service.sign_in(data)


@router.post(
    "/refresh",
    response_model=AuthSessionResponse,
    summary="Refresh an access token",
    dependencies=[Depends(_auth_rate_limit)],
    responses=ERROR_RESPONSES,
)
async def refresh_token(data: RefreshTokenRequest, service: AuthServiceDep) -> AuthSessionResponse:
    """Rotate the access token using a refresh token."""
    return await service.refresh(data.refresh_token)


@router.post(
    "/signout",
    response_model=SignOutResponse,
    summary="Revoke the current session",
)
async def sign_out(token: BearerToken, service: AuthServiceDep) -> SignOutResponse:
    """Invalidate the Supabase session (best effort; tokens stay valid until expiry)."""
    await service.sign_out(token)
    return SignOutResponse(message="Signed out")


@router.get(
    "/me",
    response_model=AuthMeResponse,
    summary="Current identity",
    responses={401: ERROR_RESPONSES[401]},
)
async def read_me(
    user: CurrentUser, claims: CurrentClaims, service: AuthServiceDep
) -> AuthMeResponse:
    """Return the local profile plus plan/credit information."""
    return AuthMeResponse(
        user=user,  # type: ignore[arg-type]  # pydantic validates from_attributes
        supabase_uid=claims.subject,
        role=claims.role,
        credits_remaining=await service.credits_remaining(user.id),
    )


@router.post(
    "/dev-token",
    response_model=AuthSessionResponse,
    summary="Mint a local development token (DEBUG only)",
    description=(
        "Development convenience: signs a Supabase-shaped JWT with `SUPABASE_JWT_SECRET` "
        "so the API can be exercised without a Supabase project. Requires `DEBUG=true`, "
        "`ENVIRONMENT=development` and `AUTH_DEV_TOKEN_ENABLED=true`; never available in "
        "staging or production."
    ),
    responses={500: {"model": ErrorResponse, "description": "Development tokens are disabled"}},
)
async def issue_dev_token(data: DevTokenRequest, service: AuthServiceDep) -> AuthSessionResponse:
    """Issue a locally signed token for local development and demos."""
    return await service.issue_dev_token(data)


__all__ = ["router"]
