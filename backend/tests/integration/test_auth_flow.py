"""Authentication: dev tokens, auto-provisioning, /auth/me and rejection paths.

Supabase is not configured in the test environment, so account creation through
``/auth/signup`` is expected to fail with a configuration error. Development and
demo environments authenticate with ``/auth/dev-token`` instead (a DEBUG-only
endpoint), which is what most of this module exercises.
"""

from __future__ import annotations

from httpx import AsyncClient

from app.services.auth_service import AuthService


async def issue_token(client: AsyncClient, email: str = "founder@example.com"):
    """Mint a debug token through the HTTP API."""
    return await client.post(
        "/api/v1/auth/dev-token", json={"email": email, "full_name": "Founder"}
    )


class TestDevTokenFlow:
    async def test_dev_token_is_available_in_test_env(self, client: AsyncClient) -> None:
        response = await issue_token(client)
        assert response.status_code == 200
        body = response.json()
        assert body["session"]["access_token"]
        assert body["session"]["token_type"] == "bearer"
        assert body["session"]["expires_in"] > 0
        assert body["user"]["email"] == "founder@example.com"

    async def test_token_authenticates_and_provisions_user(self, client: AsyncClient) -> None:
        token = (await issue_token(client)).json()["session"]["access_token"]
        response = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 200
        body = response.json()
        assert body["user"]["email"] == "founder@example.com"
        assert body["supabase_uid"].startswith("dev-")
        assert body["credits_remaining"] == body["user"]["monthly_credits_limit"]
        assert body["role"] == "authenticated"

    async def test_second_login_reuses_the_same_user(self, client: AsyncClient) -> None:
        first = (await issue_token(client)).json()
        second = (await issue_token(client)).json()
        assert first["user"]["id"] == second["user"]["id"]
        assert first["user"]["email"] == second["user"]["email"]

    async def test_dev_token_requires_debug_mode(self, client: AsyncClient, monkeypatch) -> None:
        from app.config import get_settings

        monkeypatch.setattr(get_settings(), "AUTH_DEV_TOKEN_ENABLED", False, raising=False)
        response = await issue_token(client, email="disabled@example.com")
        assert response.status_code == 500
        assert response.json()["code"] == "configuration_error"


class TestAuthenticationFailures:
    async def test_missing_header(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401
        assert "Missing Authorization header" in response.json()["message"]

    async def test_garbage_token(self, client: AsyncClient) -> None:
        response = await client.get(
            "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-jwt"}
        )
        assert response.status_code == 401

    async def test_expired_token(
        self, client: AsyncClient, expired_auth_headers: dict[str, str]
    ) -> None:
        response = await client.get("/api/v1/auth/me", headers=expired_auth_headers)
        assert response.status_code == 401
        assert "expired" in response.json()["message"].lower()

    async def test_wrong_scheme(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/auth/me", headers={"Authorization": "Basic abc"})
        assert response.status_code == 401

    async def test_error_body_shape(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/auth/me")
        body = response.json()
        assert set(body) >= {"message", "code", "detail", "request_id"}


class TestCredits:
    async def test_credit_consumption_is_atomic(self, db_session, user) -> None:
        service = AuthService(db_session)
        for _ in range(user.monthly_credits_limit):
            assert await service.consume_credits(user.id, 1) is True
        assert await service.consume_credits(user.id, 1) is False

    async def test_consuming_multiple_credits_at_once(self, db_session, user) -> None:
        service = AuthService(db_session)
        assert await service.consume_credits(user.id, 5) is True
        assert await service.credits_remaining(user.id) == user.monthly_credits_limit - 5
        assert await service.consume_credits(user.id, user.monthly_credits_limit) is False

    async def test_remaining_credits_endpoint(self, client: AsyncClient, auth_headers) -> None:
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["credits_remaining"] == 100


class TestSignUpRequiresSupabase:
    async def test_sign_up_reports_configuration_error(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/auth/signup",
            json={"email": "new-user@example.com", "password": "supersecret123"},
        )
        assert response.status_code == 500
        assert response.json()["code"] == "configuration_error"

    async def test_sign_up_rejects_short_password_before_calling_supabase(
        self, client: AsyncClient
    ) -> None:
        response = await client.post(
            "/api/v1/auth/signup", json={"email": "weak@example.com", "password": "short"}
        )
        assert response.status_code == 422
        assert response.json()["code"] == "validation_error"

    async def test_sign_in_requires_supabase(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/auth/signin",
            json={"email": "user@example.com", "password": "supersecret123"},
        )
        assert response.status_code == 500
        assert response.json()["code"] == "configuration_error"


class TestSignOut:
    async def test_sign_out_acknowledges(self, client: AsyncClient, auth_headers) -> None:
        response = await client.post("/api/v1/auth/signout", headers=auth_headers)
        assert response.status_code == 200
        assert "message" in response.json()

    async def test_sign_out_requires_authentication(self, client: AsyncClient) -> None:
        assert (await client.post("/api/v1/auth/signout")).status_code == 401
