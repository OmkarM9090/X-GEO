"""Health, readiness and application wiring."""

from __future__ import annotations

from httpx import AsyncClient

from app.config import get_settings


class TestHealthEndpoints:
    async def test_health_is_public_and_ok(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "healthy"
        assert body["environment"] == "test"
        assert body["version"] == get_settings().APP_VERSION
        assert body["details"]["service"] == get_settings().APP_NAME

    async def test_database_health_reports_pgvector(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/health/db")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "healthy"
        assert body["pgvector_version"] is not None
        assert body["latency_ms"] >= 0

    async def test_readiness(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/health/ready")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "healthy"
        assert body["details"]["pgvector"] is not None

    async def test_request_id_header_round_trips(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/health", headers={"X-Request-ID": "trace-me-123"})
        assert response.headers.get("X-Request-ID") == "trace-me-123"

    async def test_security_headers_present(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/health")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"


class TestApplicationWiring:
    async def test_root_banner(self, client: AsyncClient) -> None:
        response = await client.get("/")
        assert response.status_code == 200
        assert response.json()["name"] == get_settings().APP_NAME

    async def test_openapi_schema_is_served(self, client: AsyncClient) -> None:
        response = await client.get("/api/openapi.json")
        assert response.status_code == 200
        schema = response.json()
        assert "/api/v1/projects" in schema["paths"]
        assert schema["info"]["title"] == get_settings().APP_NAME

    async def test_unknown_route_is_404(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/does-not-exist")
        assert response.status_code == 404

    async def test_docs_available_in_debug(self, client: AsyncClient) -> None:
        assert (await client.get("/api/docs")).status_code == 200
        assert (await client.get("/api/redoc")).status_code == 200

    async def test_protected_route_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/projects")
        assert response.status_code == 401
        assert "WWW-Authenticate" in response.headers

    async def test_cors_headers_for_configured_origin(self, client: AsyncClient) -> None:
        origin = get_settings().ALLOWED_ORIGINS[0]
        response = await client.options(
            "/api/v1/projects",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code in {200, 204}
        assert response.headers.get("access-control-allow-origin") in {origin, "*"}
