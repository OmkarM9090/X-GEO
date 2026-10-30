"""Authentication request/response schemas.

The wire format intentionally mirrors Supabase's GoTrue responses so the frontend
can treat our endpoints and the Supabase SDK interchangeably.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.schemas.common import MessageResponse

PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128


class SignUpRequest(BaseModel):
    """Create a Supabase-backed account and its local shadow row."""

    email: EmailStr
    password: str = Field(min_length=PASSWORD_MIN_LENGTH, max_length=PASSWORD_MAX_LENGTH)
    full_name: str | None = Field(default=None, max_length=200)
    workspace_name: str | None = Field(default=None, max_length=200)


class SignInRequest(BaseModel):
    """Exchange credentials for a token pair."""

    email: EmailStr
    password: str = Field(min_length=1, max_length=PASSWORD_MAX_LENGTH)


class RefreshTokenRequest(BaseModel):
    """Exchange a refresh token for a new token pair."""

    refresh_token: str = Field(min_length=8)


class AuthUser(BaseModel):
    """Public projection of the local user row."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    full_name: str | None = None
    plan_tier: str
    monthly_credits_used: int
    monthly_credits_limit: int
    is_active: bool
    created_at: datetime


class AuthSession(BaseModel):
    """Token pair returned by signup/signin/refresh."""

    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    expires_in: int | None = Field(default=None, description="Access token lifetime in seconds")
    expires_at: datetime | None = None


class AuthSessionResponse(BaseModel):
    """Session + user, returned by signin and refresh."""

    session: AuthSession
    user: AuthUser


class SignUpResponse(BaseModel):
    """Signup result.

    ``session`` is ``None`` when the identity provider requires e-mail
    confirmation before issuing tokens.
    """

    user: AuthUser
    session: AuthSession | None = None
    requires_email_confirmation: bool = False
    message: str | None = None


class AuthMeResponse(BaseModel):
    """Current identity, merging token claims with the local user row."""

    user: AuthUser
    supabase_uid: str
    role: str | None = None
    credits_remaining: int


class SignOutResponse(MessageResponse):
    """Sign-out acknowledgement."""


class DevTokenRequest(BaseModel):
    """DEBUG-only: mint a local token without a Supabase project."""

    email: EmailStr
    full_name: str | None = Field(default=None, max_length=200)


__all__ = [
    "AuthMeResponse",
    "AuthSession",
    "AuthSessionResponse",
    "AuthUser",
    "DevTokenRequest",
    "RefreshTokenRequest",
    "SignInRequest",
    "SignOutResponse",
    "SignUpRequest",
    "SignUpResponse",
]
