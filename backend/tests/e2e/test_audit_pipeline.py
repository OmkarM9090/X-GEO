"""End-to-end: register a site, crawl it, chunk, score and retrieve.

The ``local_site`` fixture serves a small deterministic website over real HTTP
(robots.txt + sitemap + an article with JSON-LD, a table and an embedded
prompt-injection attempt), so the whole pipeline runs for real:

    ProjectService → AuditService → CrawlService → FetchPipeline (robots →
    httpx) → cleaner → ChunkService (pgvector) → PCS scoring → retrieval API
"""

from __future__ import annotations

import uuid

from httpx import AsyncClient

from app.repositories.audit_repo import AuditRepository
from app.services.crawl_service import CrawlService


async def bootstrap(client: AsyncClient, headers: dict[str, str], site: str):
    project = (
        await client.post(
            "/api/v1/projects",
            json={"name": "Fixture Site", "domain_url": site},
            headers=headers,
        )
    ).json()
    audit = (
        await client.post(
            "/api/v1/audits",
            json={
                "project_id": project["id"],
                "target_url": f"{site}/article",
                "run_async": False,
                "tracked_prompts": ["how do generative engines choose citations"],
            },
            headers=headers,
        )
    ).json()
    return project, audit


class TestFullAuditPipeline:
    async def test_crawl_chunk_score_and_search(
        self, client: AsyncClient, db_session, auth_headers, local_site, allow_localhost
    ) -> None:
        project, audit = await bootstrap(client, auth_headers, local_site)
        audit_id = uuid.UUID(audit["id"])

        crawls = (
            await client.get(f"/api/v1/crawls?audit_id={audit['id']}", headers=auth_headers)
        ).json()
        assert crawls["total"] == 1
        job_id = uuid.UUID(crawls["items"][0]["id"])

        outcome = await CrawlService(db_session).run_job(job_id)
        assert outcome.claimed is True
        assert outcome.status == "completed", outcome.error
        assert outcome.word_count > 50
        assert outcome.chunks_created > 0
        assert outcome.pcs_score is not None

        # -- audit detail -----------------------------------------------------
        detail = (await client.get(f"/api/v1/audits/{audit_id}", headers=auth_headers)).json()
        assert detail["status"] == "completed"
        assert detail["word_count"] == outcome.word_count
        assert detail["chunk_count"] == outcome.chunks_created
        assert detail["embedded_chunk_count"] == outcome.chunks_created
        assert detail["json_ld_data"] == {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": "GEO Readiness",
            "author": "X-GEO",
        }

        scores = detail["score_breakdown"]
        assert scores is not None
        for component in (
            "technical_readiness",
            "evidentiary_density",
            "machine_readability",
        ):
            assert detail[f"{component}_score"] is not None
            assert 0.0 <= detail[f"{component}_score"] <= 1.0
        assert 0.0 <= detail["pcs_score"] <= 1.0
        assert set(scores) >= {"technical", "evidentiary", "machine_readability", "pcs"}
        assert set(scores["pcs"]) >= {"weights", "components", "missing", "effective_weight"}

        # -- crawl job metadata ----------------------------------------------
        job = (await client.get(f"/api/v1/crawls/{job_id}/status", headers=auth_headers)).json()
        assert job["job"]["status"] == "completed"
        assert job["job"]["http_status_code"] == 200
        assert job["job"]["method"] == "httpx"
        assert job["job"]["robots_txt_allowed"] is True
        assert job["job"]["is_spa_detected"] is False
        assert job["job"]["playwright_fallback_used"] is False
        assert job["is_terminal"] is True

        # -- domain signals cached from robots.txt / sitemap -------------------
        repo = AuditRepository(db_session)
        domain = await repo.get_domain(uuid.UUID(project["id"]), local_site)
        assert domain is not None
        assert domain.robots_txt_allows_crawl is True
        assert domain.robots_txt is not None
        assert domain.sitemap_url == f"{local_site}/sitemap.xml"
        assert domain.has_json_ld is True
        assert domain.meta_description_present is True
        assert domain.canonical_set is True

        # -- retrieval --------------------------------------------------------
        search = await client.post(
            f"/api/v1/audits/{audit_id}/search",
            json={"query": "citation share statistics", "mode": "hybrid", "limit": 5},
            headers=auth_headers,
        )
        assert search.status_code == 200
        results = search.json()["results"]
        assert results
        assert all(result["score"] > 0 for result in results)

        # -- content hygiene --------------------------------------------------
        listing = (
            await client.get(f"/api/v1/audits/{audit_id}/chunks", headers=auth_headers)
        ).json()
        corpus = "\n".join(item["content"] for item in listing["items"])
        assert "Ignore all previous instructions" not in corpus
        assert "[SANITIZED]" in corpus  # injection attempt was neutralised
        assert "window.__DATA__" not in corpus  # scripts never reach the corpus

    async def test_running_the_job_twice_is_idempotent(
        self, client: AsyncClient, db_session, auth_headers, local_site, allow_localhost
    ) -> None:
        _, audit = await bootstrap(client, auth_headers, local_site)
        crawls = (
            await client.get(f"/api/v1/crawls?audit_id={audit['id']}", headers=auth_headers)
        ).json()
        job_id = uuid.UUID(crawls["items"][0]["id"])

        service = CrawlService(db_session)
        first = await service.run_job(job_id)
        second = await service.run_job(job_id)

        assert first.claimed is True
        assert second.claimed is False
        assert second.status == "completed"
        assert second.chunks_created == 0

        detail = (await client.get(f"/api/v1/audits/{audit['id']}", headers=auth_headers)).json()
        assert detail["chunk_count"] == first.chunks_created

    async def test_disallowed_path_still_audited_with_flag(
        self, client: AsyncClient, db_session, auth_headers, local_site, allow_localhost
    ) -> None:
        """/private is Disallowed in robots.txt: crawl is best-effort and flagged."""
        project = (
            await client.post(
                "/api/v1/projects",
                json={"name": "Robots", "domain_url": local_site},
                headers=auth_headers,
            )
        ).json()
        audit = (
            await client.post(
                "/api/v1/audits",
                json={
                    "project_id": project["id"],
                    "target_url": f"{local_site}/private",
                    "run_async": False,
                },
                headers=auth_headers,
            )
        ).json()
        crawls = (
            await client.get(f"/api/v1/crawls?audit_id={audit['id']}", headers=auth_headers)
        ).json()
        job_id = crawls["items"][0]["id"]
        outcome = await CrawlService(db_session).run_job(uuid.UUID(job_id))

        # The crawler honours robots.txt: the page is never fetched.
        assert outcome.status == "failed"
        assert "robots" in (outcome.error or "").lower()

        job = (await client.get(f"/api/v1/crawls/{job_id}/status", headers=auth_headers)).json()
        assert job["job"]["robots_txt_allowed"] is False

    async def test_audit_of_unreachable_host_fails_gracefully(
        self, client: AsyncClient, db_session, auth_headers, allow_localhost
    ) -> None:
        """A closed port inside the allowlist must fail the job, not crash it."""
        project = (
            await client.post(
                "/api/v1/projects",
                json={"name": "Dead", "domain_url": "http://127.0.0.1:9"},
                headers=auth_headers,
            )
        ).json()
        audit = (
            await client.post(
                "/api/v1/audits",
                json={
                    "project_id": project["id"],
                    "target_url": "http://127.0.0.1:9/",
                    "run_async": False,
                },
                headers=auth_headers,
            )
        ).json()
        crawls = (
            await client.get(f"/api/v1/crawls?audit_id={audit['id']}", headers=auth_headers)
        ).json()
        job_id = uuid.UUID(crawls["items"][0]["id"])

        service = CrawlService(db_session)
        outcome = await service.run_job(job_id)
        assert outcome.status == "failed"
        assert outcome.error is not None
        assert outcome.should_retry is True

        # Retries are drained until the audit is marked failed for good.
        attempts = 0
        while outcome.should_retry and attempts < 10:
            outcome = await service.run_job(job_id)
            attempts += 1
        assert outcome.should_retry is False

        job = (await client.get(f"/api/v1/crawls/{job_id}/status", headers=auth_headers)).json()
        assert job["job"]["status"] == "failed"

        detail = (await client.get(f"/api/v1/audits/{audit['id']}", headers=auth_headers)).json()
        assert detail["status"] == "failed"
        assert detail["error_message"]
