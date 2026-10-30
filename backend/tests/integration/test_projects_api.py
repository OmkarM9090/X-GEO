"""Projects API: CRUD, tenancy isolation, pagination, validation."""

from __future__ import annotations

import uuid

from httpx import AsyncClient

PROJECT_PAYLOAD = {
    "name": "Acme Inc",
    "domain_url": "https://93.184.216.34",
    "description": "Example project",
}


async def create_project(client: AsyncClient, headers: dict[str, str], **overrides):
    payload = {**PROJECT_PAYLOAD, **overrides}
    return await client.post("/api/v1/projects", json=payload, headers=headers)


class TestCreateProject:
    async def test_creates_project(self, client: AsyncClient, auth_headers) -> None:
        response = await create_project(client, auth_headers)
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["name"] == "Acme Inc"
        assert body["domain_url"] == "https://93.184.216.34"
        assert body["is_active"] is True
        uuid.UUID(body["id"])

    async def test_normalises_the_domain(self, client: AsyncClient, auth_headers) -> None:
        response = await create_project(
            client, auth_headers, domain_url="https://93.184.216.34/pricing?utm=1"
        )
        assert response.json()["domain_url"] == "https://93.184.216.34"

    async def test_rejects_duplicate_domain(self, client: AsyncClient, auth_headers) -> None:
        assert (await create_project(client, auth_headers)).status_code == 201
        duplicate = await create_project(client, auth_headers, name="Other name")
        assert duplicate.status_code == 409

    async def test_allows_same_domain_for_different_users(
        self, client: AsyncClient, auth_headers, other_auth_headers
    ) -> None:
        assert (await create_project(client, auth_headers)).status_code == 201
        assert (await create_project(client, other_auth_headers)).status_code == 201

    async def test_rejects_private_and_local_urls(self, client: AsyncClient, auth_headers) -> None:
        for blocked in ("http://127.0.0.1:8000", "http://localhost:8000", "http://169.254.169.254"):
            response = await create_project(client, auth_headers, domain_url=blocked)
            assert response.status_code == 422, blocked

    async def test_rejects_missing_scheme(self, client: AsyncClient, auth_headers) -> None:
        response = await create_project(client, auth_headers, domain_url="example.com")
        assert response.status_code == 422

    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post("/api/v1/projects", json=PROJECT_PAYLOAD)
        assert response.status_code == 401

    async def test_rejects_blank_name(self, client: AsyncClient, auth_headers) -> None:
        response = await create_project(client, auth_headers, name="")
        assert response.status_code == 422


class TestProjectReads:
    async def test_list_is_paginated_and_tenant_scoped(
        self, client: AsyncClient, auth_headers, other_auth_headers
    ) -> None:
        for index in range(3):
            await create_project(
                client,
                auth_headers,
                name=f"Project {index}",
                domain_url=f"https://93.184.216.{index + 10}",
            )
        await create_project(client, other_auth_headers, domain_url="https://93.184.216.99")

        response = await client.get("/api/v1/projects?limit=2&skip=0", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 3
        assert len(body["items"]) == 2
        assert body["has_more"] is True

        page_two = await client.get("/api/v1/projects?limit=2&skip=2", headers=auth_headers)
        assert page_two.json()["has_more"] is False
        assert len(page_two.json()["items"]) == 1

    async def test_search_filters_by_name(self, client: AsyncClient, auth_headers) -> None:
        await create_project(client, auth_headers, name="Alpha", domain_url="https://93.184.216.11")
        await create_project(client, auth_headers, name="Beta", domain_url="https://93.184.216.12")
        response = await client.get("/api/v1/projects?search=alpha", headers=auth_headers)
        assert response.json()["total"] == 1

    async def test_detail_includes_counts(self, client: AsyncClient, auth_headers) -> None:
        project = (await create_project(client, auth_headers)).json()
        response = await client.get(f"/api/v1/projects/{project['id']}", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["audit_count"] == 0
        assert body["domain_count"] == 0
        assert body["latest_pcs_score"] is None

    async def test_other_tenant_is_forbidden(
        self, client: AsyncClient, auth_headers, other_auth_headers
    ) -> None:
        project = (await create_project(client, auth_headers)).json()
        response = await client.get(f"/api/v1/projects/{project['id']}", headers=other_auth_headers)
        assert response.status_code == 403
        assert response.json()["code"] == "forbidden"

    async def test_unknown_project_is_404(self, client: AsyncClient, auth_headers) -> None:
        response = await client.get(f"/api/v1/projects/{uuid.uuid4()}", headers=auth_headers)
        assert response.status_code == 404


class TestProjectMutations:
    async def test_update_name_and_status(self, client: AsyncClient, auth_headers) -> None:
        project = (await create_project(client, auth_headers)).json()
        response = await client.patch(
            f"/api/v1/projects/{project['id']}",
            json={"name": "Renamed", "is_active": False},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["name"] == "Renamed"
        assert response.json()["is_active"] is False

    async def test_update_rejects_duplicate_domain(self, client: AsyncClient, auth_headers) -> None:
        first = (await create_project(client, auth_headers)).json()
        await create_project(client, auth_headers, domain_url="https://93.184.216.20")
        response = await client.patch(
            f"/api/v1/projects/{first['id']}",
            json={"domain_url": "https://93.184.216.20"},
            headers=auth_headers,
        )
        assert response.status_code == 409

    async def test_delete_project(self, client: AsyncClient, auth_headers) -> None:
        project = (await create_project(client, auth_headers)).json()
        response = await client.delete(f"/api/v1/projects/{project['id']}", headers=auth_headers)
        assert response.status_code == 204
        assert (
            await client.get(f"/api/v1/projects/{project['id']}", headers=auth_headers)
        ).status_code == 404

    async def test_other_tenant_cannot_delete(
        self, client: AsyncClient, auth_headers, other_auth_headers
    ) -> None:
        project = (await create_project(client, auth_headers)).json()
        response = await client.delete(
            f"/api/v1/projects/{project['id']}", headers=other_auth_headers
        )
        assert response.status_code == 403
        assert (
            await client.get(f"/api/v1/projects/{project['id']}", headers=auth_headers)
        ).status_code == 200

    async def test_delete_cascades_to_audits(self, client: AsyncClient, auth_headers) -> None:
        project = (await create_project(client, auth_headers)).json()
        audit = await client.post(
            "/api/v1/audits",
            json={
                "project_id": project["id"],
                "target_url": "https://93.184.216.34/article",
                "run_async": False,
            },
            headers=auth_headers,
        )
        assert audit.status_code == 201
        await client.delete(f"/api/v1/projects/{project['id']}", headers=auth_headers)
        assert (
            await client.get(f"/api/v1/audits/{audit.json()['id']}", headers=auth_headers)
        ).status_code == 404
