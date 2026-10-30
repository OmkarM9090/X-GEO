"""Repository layer: atomic claims, idempotent upserts and tenancy scoping."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.models.audit import AuditStatus
from app.models.crawl import CrawlMethod, CrawlStatus
from app.models.user import PlanTier
from app.repositories.audit_repo import AuditRepository
from app.repositories.chunk_repo import ChunkRepository
from app.repositories.crawl_repo import CrawlRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.user_repo import UserRepository
from tests.factories import ProjectFactory, UserFactory


@pytest.fixture
async def project(db_session, user):
    instance = ProjectFactory(user_id=user.id, name="Acme", domain_url="https://93.184.216.34")
    db_session.add(instance)
    await db_session.flush()
    await db_session.refresh(instance)
    return instance


@pytest.fixture
async def audit(db_session, project):
    repo = AuditRepository(db_session)
    domain = await repo.get_or_create_domain(project_id=project.id, url="https://93.184.216.34")
    instance = await repo.create(
        project_id=project.id,
        domain_id=domain.id,
        target_url="https://93.184.216.34/guide",
        status=AuditStatus.QUEUED.value,
    )
    await db_session.flush()
    return instance


class TestUserRepository:
    async def test_consume_credits_stops_at_the_limit(self, db_session, user) -> None:
        repo = UserRepository(db_session)
        assert await repo.consume_credits(user.id, amount=user.monthly_credits_limit) is True
        assert await repo.consume_credits(user.id, amount=1) is False
        back = await repo.get_by_id(user.id)
        assert back.monthly_credits_used == user.monthly_credits_limit

    async def test_consume_credits_rejects_overdraft_without_partial_charge(
        self, db_session, user
    ) -> None:
        repo = UserRepository(db_session)
        assert await repo.consume_credits(user.id, amount=user.monthly_credits_limit + 1) is False
        back = await repo.get_by_id(user.id)
        assert back.monthly_credits_used == 0

    async def test_credits_remaining(self, db_session, user) -> None:
        repo = UserRepository(db_session)
        assert await repo.credits_remaining(user.id) == user.monthly_credits_limit
        await repo.consume_credits(user.id, amount=3)
        assert await repo.credits_remaining(user.id) == user.monthly_credits_limit - 3

    async def test_set_plan_updates_limit(self, db_session, user) -> None:
        repo = UserRepository(db_session)
        await repo.set_plan(user.id, PlanTier.PRO.value)
        refreshed = await repo.get_by_id(user.id)
        assert refreshed.plan_tier == PlanTier.PRO.value
        assert refreshed.monthly_credits_limit == 200

    async def test_create_from_identity_then_lookup(self, db_session) -> None:
        repo = UserRepository(db_session)
        created = await repo.create_from_identity(
            supabase_uid="uid-1", email="one@example.com", full_name="One"
        )
        assert (await repo.get_by_supabase_uid("uid-1")).id == created.id
        assert (await repo.get_by_email("one@example.com")).id == created.id

    async def test_duplicate_identity_is_rejected_by_the_database(self, db_session) -> None:
        from sqlalchemy.exc import IntegrityError

        repo = UserRepository(db_session)
        await repo.create_from_identity(
            supabase_uid="uid-2", email="two@example.com", full_name="Two"
        )
        with pytest.raises(IntegrityError):
            await repo.create_from_identity(
                supabase_uid="uid-3", email="two@example.com", full_name="Three"
            )
        await db_session.rollback()

    async def test_lookup_by_email(self, db_session, user) -> None:
        repo = UserRepository(db_session)
        assert (await repo.get_by_email(user.email.upper())).id == user.id


class TestProjectRepository:
    async def test_pagination_has_stable_ordering(self, db_session, user) -> None:
        repo = ProjectRepository(db_session)
        for index in range(5):
            db_session.add(
                ProjectFactory(
                    user_id=user.id,
                    name=f"Project {index}",
                    domain_url=f"https://93.184.216.{index + 10}",
                )
            )
        await db_session.flush()

        first_page, total = await repo.list_for_user(user.id, skip=0, limit=2)
        second_page, _ = await repo.list_for_user(user.id, skip=2, limit=2)
        assert total == 5
        assert len(first_page) == 2
        assert {project.id for project in first_page}.isdisjoint(
            {project.id for project in second_page}
        )

    async def test_search_matches_name(self, db_session, user, project) -> None:
        repo = ProjectRepository(db_session)
        matches, total = await repo.list_for_user(user.id, search="acm")
        assert total == 1
        assert matches[0].id == project.id

    async def test_tenant_isolation(self, db_session, project) -> None:
        repo = ProjectRepository(db_session)
        stranger = UserFactory()
        db_session.add(stranger)
        await db_session.flush()
        items, total = await repo.list_for_user(stranger.id)
        assert total == 0
        assert items == []
        assert await repo.get_for_user(project.id, stranger.id) is None

    async def test_stats_counts_audits_and_domains(self, db_session, user, project) -> None:
        repo = ProjectRepository(db_session)
        stats = await repo.stats(project.id)
        assert stats.audit_count == 0
        assert stats.domain_count == 0


class TestAuditRepository:
    async def test_claim_for_processing_moves_queued_to_crawling(self, db_session, audit) -> None:
        repo = AuditRepository(db_session)
        claimed = await repo.claim_for_processing(audit.id)
        assert claimed is not None
        assert claimed.status == AuditStatus.CRAWLING.value

    async def test_completed_audit_cannot_be_claimed(self, db_session, audit) -> None:
        repo = AuditRepository(db_session)
        await repo.set_status(audit.id, AuditStatus.COMPLETED.value)
        assert await repo.claim_for_processing(audit.id) is None

    async def test_domain_upsert_is_idempotent(self, db_session, project) -> None:
        repo = AuditRepository(db_session)
        first = await repo.get_or_create_domain(project_id=project.id, url="https://93.184.216.34")
        second = await repo.get_or_create_domain(project_id=project.id, url="https://93.184.216.34")
        assert first.id == second.id

    async def test_prompt_upsert_is_idempotent(self, db_session, project) -> None:
        repo = AuditRepository(db_session)
        created = await repo.upsert_prompts(project.id, ["what is geo", "geo tools"])
        again = await repo.upsert_prompts(project.id, ["what is geo", "geo tools", "best geo"])
        assert created == 2
        assert again == 1
        prompts = await repo.list_prompt_texts(project.id)
        assert len(prompts) == 3

    async def test_update_domain_signals_persists_crawler_flags(self, db_session, project) -> None:
        repo = AuditRepository(db_session)
        domain = await repo.get_or_create_domain(project_id=project.id, url="https://93.184.216.34")
        await repo.update_domain_signals(
            domain.id,
            has_json_ld=True,
            has_sitemap=True,
            robots_txt_allows_crawl=True,
            robots_txt="User-agent: *",
            meta_description_present=True,
            canonical_set=True,
            sitemap_url="https://93.184.216.34/sitemap.xml",
        )
        refreshed = await repo.get_domain(project.id, "https://93.184.216.34")
        assert refreshed.has_json_ld is True
        assert refreshed.has_sitemap is True
        assert refreshed.robots_txt_allows_crawl is True
        assert refreshed.meta_description_present is True
        assert refreshed.sitemap_url.endswith("/sitemap.xml")

    async def test_save_scores_and_artifact(self, db_session, audit) -> None:
        repo = AuditRepository(db_session)
        await repo.save_crawl_artifact(
            audit.id,
            raw_html="<html><body>hello</body></html>",
            clean_markdown="# Hello",
            word_count=1,
            json_ld_data={"@type": "Article"},
        )
        await repo.save_scores(
            audit.id,
            technical_readiness_score=0.8,
            semantic_alignment_score=None,
            evidentiary_density_score=0.5,
            machine_readability_score=0.7,
            pcs_score=0.66,
            score_breakdown={"weights": {}},
        )
        refreshed = await repo.get_by_id(audit.id)
        assert refreshed.word_count == 1
        assert refreshed.json_ld_data == {"@type": "Article"}
        assert refreshed.pcs_score == pytest.approx(0.66)

    async def test_list_stale_only_returns_stuck_crawling_audits(self, db_session, audit) -> None:
        repo = AuditRepository(db_session)
        # Queued audits are never "stale" — only a crawling one is stuck.
        recent = datetime.now(tz=UTC) - timedelta(minutes=5)
        assert await repo.list_stale(older_than=recent) == []

        await repo.set_status(audit.id, AuditStatus.CRAWLING.value)
        assert await repo.list_stale(older_than=recent) == []

        cutoff = datetime.now(tz=UTC) + timedelta(minutes=1)
        assert [row.id for row in await repo.list_stale(older_than=cutoff)] == [audit.id]

    async def test_get_with_jobs_eager_loads(self, db_session, audit) -> None:
        crawls = CrawlRepository(db_session)
        await crawls.create(
            audit_id=audit.id,
            url=audit.target_url,
            method=CrawlMethod.SCRAPY.value,
            status=CrawlStatus.PENDING.value,
        )
        repo = AuditRepository(db_session)
        loaded = await repo.get_with_jobs(audit.id)
        assert len(loaded.crawl_jobs) == 1

    async def test_project_average_ignores_missing_scores(self, db_session, project, audit) -> None:
        repo = AuditRepository(db_session)
        assert await repo.project_average_pcs(project.id) is None
        await repo.save_scores(
            audit.id,
            technical_readiness_score=1.0,
            semantic_alignment_score=None,
            evidentiary_density_score=1.0,
            machine_readability_score=1.0,
            pcs_score=0.5,
        )
        assert await repo.project_average_pcs(project.id) == pytest.approx(0.5)


class TestCrawlRepository:
    async def test_mark_running_is_a_single_use_claim(self, db_session, audit) -> None:
        repo = CrawlRepository(db_session)
        job = await repo.create(
            audit_id=audit.id,
            url=audit.target_url,
            method=CrawlMethod.SCRAPY.value,
            status=CrawlStatus.PENDING.value,
        )
        claimed = await repo.mark_running(job.id)
        assert claimed is not None
        assert claimed.status == CrawlStatus.RUNNING.value
        assert await repo.mark_running(job.id) is None

    async def test_mark_completed_records_transport_metadata(self, db_session, audit) -> None:
        repo = CrawlRepository(db_session)
        job = await repo.create(
            audit_id=audit.id,
            url=audit.target_url,
            method=CrawlMethod.HTTPX.value,
            status=CrawlStatus.RUNNING.value,
        )
        await repo.mark_completed(
            job.id,
            http_status_code=200,
            content_type="text/html",
            response_time_ms=120,
            response_size_bytes=2048,
            is_spa_detected=False,
            playwright_fallback_used=False,
            robots_txt_allowed=True,
            method=CrawlMethod.HTTPX.value,
        )
        completed = await repo.get_by_id(job.id)
        assert completed.status == CrawlStatus.COMPLETED.value
        assert completed.http_status_code == 200
        assert completed.response_size_bytes == 2048
        assert completed.robots_txt_allowed is True
        assert completed.finished_at is not None

    async def test_increment_retry_counts_up(self, db_session, audit) -> None:
        repo = CrawlRepository(db_session)
        job = await repo.create(
            audit_id=audit.id,
            url=audit.target_url,
            method=CrawlMethod.SCRAPY.value,
            status=CrawlStatus.PENDING.value,
        )
        assert await repo.increment_retry(job.id, error_message="timeout") == 1
        assert await repo.increment_retry(job.id, error_message="timeout") == 2

    async def test_mark_failed(self, db_session, audit) -> None:
        repo = CrawlRepository(db_session)
        job = await repo.create(
            audit_id=audit.id,
            url=audit.target_url,
            method=CrawlMethod.SCRAPY.value,
            status=CrawlStatus.RUNNING.value,
        )
        await repo.mark_failed(job.id, error_message="boom")
        failed = await repo.get_by_id(job.id)
        assert failed.status == CrawlStatus.FAILED.value
        assert failed.error_message == "boom"

    async def test_list_stale_running(self, db_session, audit) -> None:
        repo = CrawlRepository(db_session)
        job = await repo.create(
            audit_id=audit.id,
            url=audit.target_url,
            method=CrawlMethod.SCRAPY.value,
            status=CrawlStatus.RUNNING.value,
        )
        recent = datetime.now(tz=UTC) - timedelta(minutes=5)
        assert await repo.list_stale_running(older_than=recent) == []

        cutoff = datetime.now(tz=UTC) + timedelta(minutes=1)
        assert [row.id for row in await repo.list_stale_running(older_than=cutoff)] == [job.id]

    async def test_list_for_audit_returns_newest_first_with_stable_ordering(
        self, db_session, audit
    ) -> None:
        repo = CrawlRepository(db_session)
        now = datetime.now(tz=UTC)
        oldest = await repo.create(
            audit_id=audit.id,
            url="https://93.184.216.34/a",
            method=CrawlMethod.SCRAPY.value,
            status=CrawlStatus.PENDING.value,
        )
        newest = await repo.create(
            audit_id=audit.id,
            url="https://93.184.216.34/b",
            method=CrawlMethod.SCRAPY.value,
            status=CrawlStatus.PENDING.value,
        )
        # Rows created in one transaction share `created_at` (transaction time),
        # so the timestamps are set explicitly here.
        await repo.update_fields(oldest.id, created_at=now - timedelta(minutes=5))
        await repo.update_fields(newest.id, created_at=now)

        rows, total = await repo.list_for_audit(audit.id)
        assert total == 2
        assert rows[0].id == newest.id
        assert rows[-1].id == oldest.id

        # Ordering is stable across identical calls (pagination safety).
        again, _ = await repo.list_for_audit(audit.id)
        assert [row.id for row in again] == [row.id for row in rows]


class TestChunkRepository:
    async def test_store_embeddings_round_trip(self, db_session, audit) -> None:
        repo = ChunkRepository(db_session)
        created = await repo.bulk_insert(
            [
                {
                    "audit_id": audit.id,
                    "content": "citation share benchmark",
                    "chunk_index": 0,
                    "token_count": 3,
                    "char_count": 23,
                },
                {
                    "audit_id": audit.id,
                    "content": "pineapple protocol queue",
                    "chunk_index": 1,
                    "token_count": 3,
                    "char_count": 22,
                },
            ]
        )
        assert created == 2
        chunks, total = await repo.list_for_audit(audit.id)
        assert total == 2
        vector = [1.0] + [0.0] * 1535
        assert await repo.store_embeddings([(chunks[0].id, vector)]) == 1
        assert await repo.count_embedded_for_audit(audit.id) == 1
        assert await repo.count_for_audit(audit.id) == 2

    async def test_next_index(self, db_session, audit) -> None:
        repo = ChunkRepository(db_session)
        assert await repo.next_index(audit.id) == 0
        await repo.bulk_insert(
            [
                {
                    "audit_id": audit.id,
                    "content": "one",
                    "chunk_index": 0,
                    "token_count": 1,
                    "char_count": 3,
                }
            ]
        )
        assert await repo.next_index(audit.id) == 1

    async def test_delete_for_audit(self, db_session, audit) -> None:
        repo = ChunkRepository(db_session)
        await repo.bulk_insert(
            [
                {
                    "audit_id": audit.id,
                    "content": "one",
                    "chunk_index": 0,
                    "token_count": 1,
                    "char_count": 3,
                }
            ]
        )
        assert await repo.delete_for_audit(audit.id) == 1
        assert await repo.count_for_audit(audit.id) == 0

    async def test_count_scoped_by_project(self, db_session, project, audit) -> None:
        repo = ChunkRepository(db_session)
        await repo.bulk_insert(
            [
                {
                    "audit_id": audit.id,
                    "content": "scoped",
                    "chunk_index": 0,
                    "token_count": 1,
                    "char_count": 6,
                }
            ]
        )
        assert await repo.count_scoped(project_id=project.id) == 1
        assert await repo.count_scoped(audit_id=audit.id) == 1
        assert await repo.count_scoped(audit_id=uuid.uuid4()) == 0


class TestBaseRepository:
    async def test_upsert_inserts_then_updates(self, db_session) -> None:
        user = UserFactory(email="upsert@example.com")
        db_session.add(user)
        await db_session.flush()

        repo = UserRepository(db_session)
        row = await repo.upsert(
            values={
                "email": "upsert@example.com",
                "supabase_uid": "uid-upsert",
                "full_name": "Before",
                "plan_tier": PlanTier.FREE.value,
            },
            index_elements=["email"],
        )
        updated = await repo.upsert(
            values={
                "email": "upsert@example.com",
                "supabase_uid": "uid-upsert",
                "full_name": "After",
                "plan_tier": PlanTier.FREE.value,
            },
            index_elements=["email"],
            update_columns=["full_name"],
        )
        assert row.id == updated.id
        assert updated.full_name == "After"

    async def test_delete_where_removes_matches(self, db_session, user) -> None:
        repo = ProjectRepository(db_session)
        for index in range(3):
            db_session.add(
                ProjectFactory(user_id=user.id, domain_url=f"https://93.184.216.{index + 20}")
            )
        await db_session.flush()
        removed = await repo.delete_where(user_id=user.id)
        assert removed == 3
