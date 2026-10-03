"""Audits API: creation, credit accounting, reads, explainability, deletion."""

from __future__ import annotations

import uuid

from httpx import AsyncClient

PROJECT_DOMAIN = "https://93.184.216.34"
TARGET_URL = "https://93.184.216.34/guide"


async def bootstrap(client: AsyncClient, headers: dict[str, str]):
    """Project + one queued audit (no crawling)."""
    project = (
        await client.post(
            "/api/v1/projects",
            json={"name": "Acme Inc", "domain_url": PROJECT_DOMAIN},
            headers=headers,
        )
    ).json()
    audit = (
        await client.post(
            "/api/v1/audits",
            json={"project_id": project["id"], "target_url": TARGET_URL, "run_async": False},
            headers=headers,
        )
    ).json()
    return project, audit


class TestCreateAudit:
    async def test_creates_queued_audit(self, client: AsyncClient, auth_headers) -> None:
        project, audit = await bootstrap(client, auth_headers)
        assert audit["project_id"] == project["id"]
        assert audit["target_url"] == TARGET_URL
        assert audit["status"] == "queued"
        assert audit["pcs_score"] is None
        uuid.UUID(audit["domain_id"])

    async def test_consumes_one_credit(self, client: AsyncClient, auth_headers) -> None:
        assert (await client.get("/api/v1/auth/me", headers=auth_headers)).json()[
            "credits_remaining"
        ] == 100
        await bootstrap(client, auth_headers)
        assert (await client.get("/api/v1/auth/me", headers=auth_headers)).json()[
            "credits_remaining"
        ] == 99

    async def test_creates_a_pending_crawl_job(self, client: AsyncClient, auth_headers) -> None:
        _, audit = await bootstrap(client, auth_headers)
        crawls = (
            await client.get(f"/api/v1/crawls?audit_id={audit['id']}", headers=auth_headers)
        ).json()
        assert crawls["total"] == 1
        assert crawls["items"][0]["status"] == "pending"
        assert crawls["items"][0]["url"] == TARGET_URL

    async def test_registers_tracked_prompts(self, client: AsyncClient, auth_headers) -> None:
        project = (
            await client.post(
                "/api/v1/projects",
                json={"name": "Acme", "domain_url": PROJECT_DOMAIN},
                headers=auth_headers,
            )
        ).json()
        response = await client.post(
            "/api/v1/audits",
            json={
                "project_id": project["id"],
                "target_url": TARGET_URL,
                "run_async": False,
                "tracked_prompts": ["what is generative engine optimisation", "geo tools"],
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        detail = (
            await client.get(f"/api/v1/projects/{project['id']}", headers=auth_headers)
        ).json()
        assert detail["tracked_prompt_count"] == 2

    async def test_rejects_url_outside_the_project_domain(
        self, client: AsyncClient, auth_headers
    ) -> None:
        project = (
            await client.post(
                "/api/v1/projects",
                json={"name": "Acme", "domain_url": PROJECT_DOMAIN},
                headers=auth_headers,
            )
        ).json()
        response = await client.post(
            "/api/v1/audits",
            json={
                "project_id": project["id"],
                "target_url": "https://93.184.216.99/guide",
                "run_async": False,
            },
            headers=auth_headers,
        )
        assert response.status_code == 422

    async def test_rejects_private_target(self, client: AsyncClient, auth_headers) -> None:
        project = await client.post(
            "/api/v1/projects",
            json={"name": "Acme", "domain_url": "http://127.0.0.1"},
            headers=auth_headers,
        )
        # Registering the private domain itself is already rejected.
        assert project.status_code == 422

    async def test_quota_exceeded(
        self, client: AsyncClient, auth_headers, user, db_session
    ) -> None:
        user.monthly_credits_used = user.monthly_credits_limit
        await db_session.flush()
        project = (
            await client.post(
                "/api/v1/projects",
                json={"name": "Acme", "domain_url": PROJECT_DOMAIN},
                headers=auth_headers,
            )
        ).json()
        response = await client.post(
            "/api/v1/audits",
            json={"project_id": project["id"], "target_url": TARGET_URL, "run_async": False},
            headers=auth_headers,
        )
        assert response.status_code == 402
        assert response.json()["code"] == "quota_exceeded"

    async def test_unknown_project_is_404(self, client: AsyncClient, auth_headers) -> None:
        response = await client.post(
            "/api/v1/audits",
            json={"project_id": str(uuid.uuid4()), "target_url": TARGET_URL, "run_async": False},
            headers=auth_headers,
        )
        assert response.status_code == 404

    async def test_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/audits",
            json={"project_id": str(uuid.uuid4()), "target_url": TARGET_URL},
        )
        assert response.status_code == 401


class TestAuditReads:
    async def test_list_and_filter_by_project(self, client: AsyncClient, auth_headers) -> None:
        project, audit = await bootstrap(client, auth_headers)
        other_project = (
            await client.post(
                "/api/v1/projects",
                json={"name": "Other", "domain_url": "https://93.184.216.77"},
                headers=auth_headers,
            )
        ).json()

        response = await client.get(
            f"/api/v1/audits?project_id={project['id']}", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert response.json()["items"][0]["id"] == audit["id"]

        empty = await client.get(
            f"/api/v1/audits?project_id={other_project['id']}", headers=auth_headers
        )
        assert empty.json()["total"] == 0

    async def test_filter_by_status(self, client: AsyncClient, auth_headers) -> None:
        await bootstrap(client, auth_headers)
        queued = await client.get("/api/v1/audits?status=queued", headers=auth_headers)
        completed = await client.get("/api/v1/audits?status=completed", headers=auth_headers)
        assert queued.json()["total"] == 1
        assert completed.json()["total"] == 0

    async def test_detail_includes_crawl_history(self, client: AsyncClient, auth_headers) -> None:
        _, audit = await bootstrap(client, auth_headers)
        response = await client.get(f"/api/v1/audits/{audit['id']}", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["chunk_count"] == 0
        assert body["embedded_chunk_count"] == 0
        assert len(body["crawl_jobs"]) == 1
        assert body["score_breakdown"] is None

    async def test_scores_endpoint_exposes_weights(self, client: AsyncClient, auth_headers) -> None:
        from app.config import get_settings

        _, audit = await bootstrap(client, auth_headers)
        response = await client.get(f"/api/v1/audits/{audit['id']}/scores", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["audit_id"] == audit["id"]
        assert body["weights"] == get_settings().PCS_WEIGHTS
        assert body["scores"]["pcs"] is None

    async def test_other_tenant_is_forbidden(
        self, client: AsyncClient, auth_headers, other_auth_headers
    ) -> None:
        _, audit = await bootstrap(client, auth_headers)
        response = await client.get(f"/api/v1/audits/{audit['id']}", headers=other_auth_headers)
        assert response.status_code == 403
        assert response.json()["code"] == "forbidden"


class TestAuditChunks:
    async def test_chunk_list_is_empty_before_crawling(
        self, client: AsyncClient, auth_headers
    ) -> None:
        _, audit = await bootstrap(client, auth_headers)
        response = await client.get(f"/api/v1/audits/{audit['id']}/chunks", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["items"] == []
        assert body["total"] == 0

    async def test_search_returns_empty_results(self, client: AsyncClient, auth_headers) -> None:
        _, audit = await bootstrap(client, auth_headers)
        response = await client.post(
            f"/api/v1/audits/{audit['id']}/search",
            json={"query": "citation share", "mode": "hybrid"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["query"] == "citation share"
        assert body["results"] == []

    async def test_search_rejects_blank_query(self, client: AsyncClient, auth_headers) -> None:
        _, audit = await bootstrap(client, auth_headers)
        response = await client.post(
            f"/api/v1/audits/{audit['id']}/search",
            json={"query": ""},
            headers=auth_headers,
        )
        assert response.status_code == 422


class TestDeleteAudit:
    async def test_delete_audit(self, client: AsyncClient, auth_headers) -> None:
        _, audit = await bootstrap(client, auth_headers)
        response = await client.delete(f"/api/v1/audits/{audit['id']}", headers=auth_headers)
        assert response.status_code == 204
        assert (
            await client.get(f"/api/v1/audits/{audit['id']}", headers=auth_headers)
        ).status_code == 404

    async def test_delete_audit_cascades_to_crawl_jobs(
        self, client: AsyncClient, auth_headers
    ) -> None:
        _, audit = await bootstrap(client, auth_headers)
        await client.delete(f"/api/v1/audits/{audit['id']}", headers=auth_headers)
        crawls = await client.get(f"/api/v1/crawls?audit_id={audit['id']}", headers=auth_headers)
        assert crawls.json()["total"] == 0
