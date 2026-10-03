"""Authentication business logic.

Supabase GoTrue is the identity provider: it owns credentials, password hashing,
refresh tokens and signing keys. This service:

* proxies signup / signin / refresh / signout to GoTrue;
* verifies access tokens (HS256 shared secret **or** asymmetric JWKS keys);
* maintains the local *shadow* user row used for tenant isolation, plans and
  credit accounting, provisioning it just-in-time on first authenticated call.

No route touches Supabase directly — everything funnels through here.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.exceptions import (
    ConfigurationError,
    ConflictError,
    ExternalServiceError,
    ForbiddenError,
    InvalidInputError,
    UnauthorizedError,
)
from app.core.logging_config import get_logger
from app.core.security import TokenClaims, create_local_token, decode_jwt_async
from app.models.user import PlanTier, User
from app.repositories.user_repo import UserRepository
from app.schemas.auth import (
    AuthSession,
    AuthSessionResponse,
    AuthUser,
    DevTokenRequest,
    SignInRequest,
    SignUpRequest,
    SignUpResponse,
)

logger = get_logger(__name__)

#: Supabase GoTrue endpoints (relative to ``SUPABASE_URL``).
SIGNUP_PATH = "/auth/v1/signup"
TOKEN_PATH = "/auth/v1/token"
LOGOUT_PATH = "/auth/v1/logout"
ADMIN_USERS_PATH = "/auth/v1/admin/users"

#: Namespace used to derive stable local identities for development tokens.
_DEV_NAMESPACE = uuid.UUID("6f1a1a4e-5f9e-4a2c-9d1b-2f0f0f2c9d10")


def dev_supabase_uid(email: str) -> str:
    """Deterministic local identity for a development token (stable across runs).

    Shared with ``scripts/seed_db.py`` so seeded demo data is visible to the
    account created by ``POST /api/v1/auth/dev-token``.
    """
    return f"dev-{uuid.uuid5(_DEV_NAMESPACE, email.strip().lower())}"


@dataclass(frozen=True, slots=True)
class GoTrueSession:
    """Normalised GoTrue session payload."""

    access_token: str
    refresh_token: str | None
    expires_in: int | None
    token_type: str
    user_id: str | None
    email: str | None
    full_name: str | None
    confirmed: bool


class AuthService:
    """Authentication + local user management."""

    def __init__(self, session: AsyncSession, *, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.users = UserRepository(session)

    # -- token verification --------------------------------------------------
    async def verify_token(self, token: str) -> TokenClaims:
        """Verify a Supabase access token and return its claims."""
        return await decode_jwt_async(token, settings=self.settings)

    async def resolve_user(self, claims: TokenClaims) -> User:
        """Return the local user for a verified token, provisioning if needed."""
        user = await self.users.get_by_supabase_uid(claims.subject)
        if user is not None:
            if not user.is_active:
                raise ForbiddenError("Account is deactivated")
            await self._touch(user, claims)
            return user

        if not self.settings.AUTH_AUTO_PROVISION_USERS:
            raise UnauthorizedError("No local account exists for this identity")

        user = await self._provision(claims)
        logger.info("auth.user_provisioned", user_id=str(user.id), supabase_uid=claims.subject)
        return user

    async def _touch(self, user: User, claims: TokenClaims) -> None:
        """Refresh the cached profile + last-seen timestamp (best effort)."""
        await self.users.set_last_seen(user.id)
        if claims.email and claims.email.lower() != user.email:
            await self.users.sync_profile(user, email=claims.email)

    async def _provision(self, claims: TokenClaims) -> User:
        """Create the local shadow row for a Supabase identity."""
        email = claims.email or f"{claims.subject}@users.noreply.x-geo.dev"
        plan_tier = PlanTier.FREE.value
        try:
            return await self.users.create_from_identity(
                supabase_uid=claims.subject,
                email=email,
                full_name=None,
                plan_tier=plan_tier,
            )
        except IntegrityError:
            # Concurrent first request: another task created the row first.
            await self.session.rollback()
            existing = await self.users.get_by_supabase_uid(claims.subject)
            if existing is None:  # pragma: no cover - defensive
                raise
            return existing

    # -- GoTrue proxy --------------------------------------------------------
    def _require_supabase(self) -> None:
        missing = [
            name
            for name, value in (
                ("SUPABASE_URL", self.settings.SUPABASE_URL),
                ("SUPABASE_ANON_KEY", self.settings.SUPABASE_ANON_KEY),
            )
            if not value or self.settings._looks_like_placeholder(value)
        ]
        if missing:
            raise ConfigurationError("Supabase authentication", missing)

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.settings.supabase_url_normalised,
            timeout=self.settings.SUPABASE_TIMEOUT_SECONDS,
            headers={
                "apikey": self.settings.SUPABASE_ANON_KEY,
                "Content-Type": "application/json",
            },
        )

    @staticmethod
    def _session_from_payload(payload: dict[str, Any]) -> GoTrueSession:
        user = payload.get("user") or {}
        metadata = user.get("user_metadata") or {}
        return GoTrueSession(
            access_token=payload.get("access_token") or "",
            refresh_token=payload.get("refresh_token"),
            expires_in=payload.get("expires_in"),
            token_type=payload.get("token_type") or "bearer",
            user_id=user.get("id"),
            email=user.get("email"),
            full_name=metadata.get("full_name") or metadata.get("name"),
            confirmed=bool(user.get("email_confirmed_at") or user.get("confirmed_at")),
        )

    @staticmethod
    def _raise_for_gotrue_error(response: httpx.Response, action: str) -> None:
        if response.status_code < 400:
            return
        try:
            payload = response.json()
        except ValueError:  # pragma: no cover - non-JSON upstream error
            payload = {}
        message = (
            payload.get("msg")
            or payload.get("error_description")
            or payload.get("error")
            or payload.get("message")
            or response.text[:200]
            or "unknown error"
        )
        if response.status_code in {400, 401, 403, 422}:
            # Invalid credentials -> 401, everything else is a client mistake.
            if "invalid" in str(message).lower() and "credential" in str(message).lower():
                raise UnauthorizedError(f"{action} failed: invalid email or password")
            raise InvalidInputError(f"{action} failed: {message}")
        if response.status_code == 429:
            raise InvalidInputError(f"{action} failed: too many attempts, try again later")
        raise ExternalServiceError("Supabase", f"{response.status_code} {message}")

    async def sign_up(self, data: SignUpRequest) -> SignUpResponse:
        """Create a Supabase user (admin API when available) + local row."""
        self._require_supabase()
        metadata = {"full_name": data.full_name} if data.full_name else {}

        async with self._client() as client:
            if (
                self.settings.SUPABASE_SERVICE_ROLE_KEY
                and not self.settings._looks_like_placeholder(
                    self.settings.SUPABASE_SERVICE_ROLE_KEY
                )
            ):
                # Pre-confirmed account creation for B2B onboarding.
                response = await client.post(
                    ADMIN_USERS_PATH,
                    json={
                        "email": data.email,
                        "password": data.password,
                        "email_confirm": True,
                        "user_metadata": metadata,
                    },
                    headers={
                        "apikey": self.settings.SUPABASE_SERVICE_ROLE_KEY,
                        "Authorization": f"Bearer {self.settings.SUPABASE_SERVICE_ROLE_KEY}",
                    },
                )
                self._raise_for_gotrue_error(response, "Sign up")
                created = response.json()
                supabase_uid = str(created.get("id") or "")
                confirmed = True
                session_payload: dict[str, Any] | None = None
            else:
                response = await client.post(
                    SIGNUP_PATH,
                    json={"email": data.email, "password": data.password, "data": metadata},
                )
                self._raise_for_gotrue_error(response, "Sign up")
                payload = response.json()
                session_payload = payload if payload.get("access_token") else None
                user_payload = payload.get("user") or payload
                supabase_uid = str(user_payload.get("id") or "")
                confirmed = bool(
                    user_payload.get("email_confirmed_at") or user_payload.get("confirmed_at")
                )

        if not supabase_uid:
            raise ExternalServiceError("Supabase", "signup response did not contain a user id")

        existing = await self.users.get_by_supabase_uid(supabase_uid)
        if existing is None:
            try:
                user = await self.users.create_from_identity(
                    supabase_uid=supabase_uid,
                    email=data.email,
                    full_name=data.full_name,
                )
            except IntegrityError:
                await self.session.rollback()
                raise ConflictError("An account with this email already exists") from None
        else:
            user = existing

        session = None
        if session_payload is not None:
            gotrue_session = self._session_from_payload(session_payload)
            session = self._to_auth_session(gotrue_session)

        return SignUpResponse(
            user=AuthUser.model_validate(user),
            session=session,
            requires_email_confirmation=not confirmed,
            message=(
                None
                if confirmed
                else "Check your inbox to confirm your email address before signing in."
            ),
        )

    async def sign_in(self, data: SignInRequest) -> AuthSessionResponse:
        """Exchange email/password for a Supabase session."""
        self._require_supabase()
        async with self._client() as client:
            response = await client.post(
                TOKEN_PATH,
                params={"grant_type": "password"},
                json={"email": data.email, "password": data.password},
            )
            self._raise_for_gotrue_error(response, "Sign in")
            gotrue_session = self._session_from_payload(response.json())

        if not gotrue_session.access_token:
            raise ExternalServiceError(
                "Supabase", "signin response did not contain an access token"
            )

        user = await self._user_after_login(gotrue_session, data.email)
        return AuthSessionResponse(
            session=self._to_auth_session(gotrue_session), user=AuthUser.model_validate(user)
        )

    async def refresh(self, refresh_token: str) -> AuthSessionResponse:
        """Rotate an expiring access token."""
        self._require_supabase()
        async with self._client() as client:
            response = await client.post(
                TOKEN_PATH,
                params={"grant_type": "refresh_token"},
                json={"refresh_token": refresh_token},
            )
            self._raise_for_gotrue_error(response, "Token refresh")
            gotrue_session = self._session_from_payload(response.json())

        if not gotrue_session.access_token:
            raise UnauthorizedError("Refresh token is no longer valid")

        user = await self._user_after_login(gotrue_session, gotrue_session.email or "")
        return AuthSessionResponse(
            session=self._to_auth_session(gotrue_session), user=AuthUser.model_validate(user)
        )

    async def sign_out(self, access_token: str) -> None:
        """Revoke the Supabase session (best effort)."""
        if not self.settings.supabase_auth_configured:
            return
        try:
            async with self._client() as client:
                await client.post(LOGOUT_PATH, headers={"Authorization": f"Bearer {access_token}"})
        except httpx.HTTPError as exc:  # pragma: no cover - network failure
            logger.warning("auth.signout_failed", error=str(exc))

    async def _user_after_login(self, gotrue_session: GoTrueSession, email: str) -> User:
        """Return (or create) the local user row right after a successful login."""
        if gotrue_session.user_id:
            user = await self.users.get_by_supabase_uid(gotrue_session.user_id)
            if user is not None:
                await self.users.set_last_seen(user.id)
                return user

        existing = await self.users.get_by_email(email) if email else None
        if existing is not None:
            # Adopt the Supabase identity for a pre-existing local row.
            existing.supabase_uid = gotrue_session.user_id or existing.supabase_uid
            await self.session.flush()
            await self.users.set_last_seen(existing.id)
            return existing

        return await self.users.create_from_identity(
            supabase_uid=gotrue_session.user_id or str(uuid.uuid4()),
            email=email or f"{gotrue_session.user_id}@users.noreply.x-geo.dev",
            full_name=gotrue_session.full_name,
        )

    def _to_auth_session(self, gotrue_session: GoTrueSession) -> AuthSession:
        expires_at = None
        if gotrue_session.expires_in:
            expires_at = datetime.fromtimestamp(
                datetime.now(tz=UTC).timestamp() + gotrue_session.expires_in, tz=UTC
            )
        return AuthSession(
            access_token=gotrue_session.access_token,
            refresh_token=gotrue_session.refresh_token,
            token_type=gotrue_session.token_type,
            expires_in=gotrue_session.expires_in,
            expires_at=expires_at,
        )

    # -- development helper --------------------------------------------------
    def dev_tokens_enabled(self) -> bool:
        """Whether the DEBUG-only local token endpoint may be used.

        Available in development/test environments only; the settings validator
        refuses to start staging/production with ``AUTH_DEV_TOKEN_ENABLED=true``.
        """
        return bool(
            self.settings.AUTH_DEV_TOKEN_ENABLED
            and self.settings.DEBUG
            and self.settings.is_development
        )

    async def issue_dev_token(self, data: DevTokenRequest) -> AuthSessionResponse:
        """Mint a locally signed token and ensure the matching user row exists."""
        if not self.dev_tokens_enabled():
            raise ConfigurationError(
                "Development tokens", ["AUTH_DEV_TOKEN_ENABLED=true and DEBUG=true in development"]
            )

        supabase_uid = dev_supabase_uid(data.email)
        user = await self.users.get_by_supabase_uid(supabase_uid)
        if user is None:
            user = await self.users.get_by_email(data.email)
            if user is None:
                user = await self.users.create_from_identity(
                    supabase_uid=supabase_uid,
                    email=data.email,
                    full_name=data.full_name or data.email.split("@")[0],
                )
            else:
                user.supabase_uid = supabase_uid
                await self.session.flush()

        token = create_local_token(
            subject=supabase_uid,
            email=user.email,
            settings=self.settings,
        )
        logger.warning("auth.dev_token_issued", user_id=str(user.id), email=user.email)
        return AuthSessionResponse(
            session=AuthSession(
                access_token=token,
                refresh_token=None,
                expires_in=self.settings.AUTH_DEV_TOKEN_TTL_SECONDS,
            ),
            user=AuthUser.model_validate(user),
        )

    # -- helpers -------------------------------------------------------------
    async def credits_remaining(self, user_id: uuid.UUID) -> int:
        """Remaining monthly credits for the user."""
        return await self.users.credits_remaining(user_id)

    async def consume_credits(self, user_id: uuid.UUID, amount: int = 1) -> bool:
        """Consume credits, returning False when the plan allowance is exhausted."""
        return await self.users.consume_credits(user_id, amount)

    @staticmethod
    def fingerprint(token: str) -> str:
        """Short, stable token identifier for logs."""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]


__all__ = ["AuthService", "GoTrueSession", "dev_supabase_uid"]
