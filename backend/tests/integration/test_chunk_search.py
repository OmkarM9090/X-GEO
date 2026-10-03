"""Chunk ingest + hybrid retrieval against real pgvector and tsvector indexes."""

from __future__ import annotations

import uuid

from httpx import AsyncClient

from app.config import get_settings
from app.schemas.chunk import ChunkSearchRequest
from app.services.chunk_service import ChunkService

DOCUMENT = """# Citation share benchmark

Generative engines cite pages that publish verifiable statistics. Our benchmark
shows that evidence-dense pages earn 41% more citations than prose-only pages.

## Methodology

We analysed 1,200 answers across four generative engines in 2024 and recorded
every citation, its position and the cited passage length.

## Pineapple protocol

The pineapple protocol is an internal nickname for our deferred-embedding queue,
which batches embedding calls and retries failures with exponential backoff.
"""


async def bootstrap_audit(client: AsyncClient, headers: dict[str, str]):
    project = (
        await client.post(
            "/api/v1/projects",
            json={"name": "Benchmark", "domain_url": "https://93.184.216.34"},
            headers=headers,
        )
    ).json()
    audit = (
        await client.post(
            "/api/v1/audits",
            json={
                "project_id": project["id"],
                "target_url": "https://93.184.216.34/benchmark",
                "run_async": False,
            },
            headers=headers,
        )
    ).json()
    return uuid.UUID(audit["id"])


class TestIngest:
    async def test_ingest_persists_and_embeds_chunks(
        self, client: AsyncClient, auth_headers, db_session
    ):
        audit_id = await bootstrap_audit(client, auth_headers)
        service = ChunkService(db_session)
        result = await service.ingest_markdown(audit_id, DOCUMENT, embed=True)

        assert result.chunks_created > 0
        assert result.chunks_embedded == result.chunks_created

        listing = await client.get(f"/api/v1/audits/{audit_id}/chunks", headers=auth_headers)
        body = listing.json()
        assert body["total"] == result.chunks_created
        assert all(item["has_embedding"] is True for item in body["items"])
        assert all(item["chunk_index"] >= 0 for item in body["items"])

    async def test_reingest_replaces_previous_chunks(
        self, client: AsyncClient, auth_headers, db_session
    ):
        audit_id = await bootstrap_audit(client, auth_headers)
        service = ChunkService(db_session)
        first = await service.ingest_markdown(audit_id, DOCUMENT, embed=True)
        second = await service.ingest_markdown(
            audit_id, "# Short\n\nOne small paragraph.", embed=True
        )

        assert second.chunks_created == 1
        listing = await client.get(f"/api/v1/audits/{audit_id}/chunks", headers=auth_headers)
        assert listing.json()["total"] == 1
        assert first.chunks_created > second.chunks_created

    async def test_embed_texts_falls_back_to_deterministic_vectors(
        self, client: AsyncClient, auth_headers, db_session
    ):
        await bootstrap_audit(client, auth_headers)
        service = ChunkService(db_session)
        vectors = await service.embed_texts(["evidence density", "citation share"])
        assert len(vectors) == 2
        assert all(len(vector) == get_settings().EMBEDDING_DIMENSIONS for vector in vectors)
        assert vectors[0] != vectors[1]


class TestSearch:
    async def test_every_mode_returns_ranked_hits(
        self, client: AsyncClient, auth_headers, db_session
    ) -> None:
        audit_id = await bootstrap_audit(client, auth_headers)
        service = ChunkService(db_session)
        await service.ingest_markdown(audit_id, DOCUMENT, embed=True)

        # PostgreSQL full-text search ANDs the query terms, so natural-language
        # questions belong to the semantic/hybrid modes.
        queries = {
            "semantic": "how many more citations do evidence dense pages earn",
            "hybrid": "how many more citations do evidence dense pages earn",
            "full_text": "citation benchmark",
        }
        for mode, query in queries.items():
            response = await service.search(
                ChunkSearchRequest(
                    query=query,
                    audit_id=audit_id,
                    mode=mode,  # type: ignore[arg-type]
                    limit=5,
                )
            )
            assert response.mode == mode
            assert response.results, (mode, query)
            assert response.results[0].score > 0
            assert all(
                result.chunk.audit_id == audit_id for result in response.results
            ), "results must be scoped to the audit"

    async def test_full_text_requires_all_terms(
        self, client: AsyncClient, auth_headers, db_session
    ):
        """`websearch_to_tsquery` ANDs the terms, so unknown words miss."""
        audit_id = await bootstrap_audit(client, auth_headers)
        service = ChunkService(db_session)
        await service.ingest_markdown(audit_id, DOCUMENT, embed=True)
        response = await service.search(
            ChunkSearchRequest(
                query="pineapple quantum zebra",
                audit_id=audit_id,
                mode="full_text",
            )
        )
        assert response.results == []

    async def test_full_text_finds_exact_phrase(
        self, client: AsyncClient, auth_headers, db_session
    ):
        audit_id = await bootstrap_audit(client, auth_headers)
        service = ChunkService(db_session)
        await service.ingest_markdown(audit_id, DOCUMENT, embed=True)

        response = await service.search(
            ChunkSearchRequest(query="pineapple protocol", audit_id=audit_id, mode="full_text")
        )
        assert response.results
        assert "pineapple protocol" in response.results[0].chunk.content.lower()

    async def test_search_only_returns_own_audit_chunks(
        self, client: AsyncClient, auth_headers, other_auth_headers, db_session
    ):
        mine = await bootstrap_audit(client, auth_headers)
        theirs = await bootstrap_audit(client, other_auth_headers)
        service = ChunkService(db_session)
        await service.ingest_markdown(theirs, DOCUMENT, embed=True)

        response = await service.search(
            ChunkSearchRequest(query="pineapple protocol", audit_id=mine, mode="full_text")
        )
        assert response.results == []

    async def test_http_search_endpoint(self, client: AsyncClient, auth_headers, db_session):
        audit_id = await bootstrap_audit(client, auth_headers)
        await ChunkService(db_session).ingest_markdown(audit_id, DOCUMENT, embed=True)

        response = await client.post(
            f"/api/v1/audits/{audit_id}/search",
            json={"query": "citation benchmark", "mode": "hybrid", "limit": 3},
            headers=auth_headers,
        )
        assert response.status_code == 200
        body = response.json()
        assert body["results"]
        first = body["results"][0]
        assert set(first) == {"chunk", "score", "source"}
        assert first["chunk"]["audit_id"] == str(audit_id)

    async def test_limit_is_respected(self, client: AsyncClient, auth_headers, db_session):
        audit_id = await bootstrap_audit(client, auth_headers)
        service = ChunkService(db_session)
        await service.ingest_markdown(audit_id, DOCUMENT, embed=True)
        response = await service.search(
            ChunkSearchRequest(query="citation", audit_id=audit_id, mode="hybrid", limit=1)
        )
        assert len(response.results) == 1


class TestAlignmentScore:
    async def test_alignment_is_computed_from_tracked_queries(
        self, client: AsyncClient, auth_headers, db_session
    ) -> None:
        project = (
            await client.post(
                "/api/v1/projects",
                json={"name": "Aligned", "domain_url": "https://93.184.216.34"},
                headers=auth_headers,
            )
        ).json()
        audit = (
            await client.post(
                "/api/v1/audits",
                json={
                    "project_id": project["id"],
                    "target_url": "https://93.184.216.34/aligned",
                    "run_async": False,
                    "tracked_prompts": ["how many more citations do evidence dense pages earn"],
                },
                headers=auth_headers,
            )
        ).json()
        audit_id = uuid.UUID(audit["id"])
        service = ChunkService(db_session)
        await service.ingest_markdown(audit_id, DOCUMENT, embed=True)

        score = await service.alignment_score(
            audit_id, ["how many more citations do evidence dense pages earn"]
        )
        assert score is not None
        assert 0.0 <= score <= 1.0

    async def test_alignment_is_none_without_queries(
        self, client: AsyncClient, auth_headers, db_session
    ) -> None:
        audit_id = await bootstrap_audit(client, auth_headers)
        service = ChunkService(db_session)
        await service.ingest_markdown(audit_id, DOCUMENT, embed=True)
        assert await service.alignment_score(audit_id, []) is None
