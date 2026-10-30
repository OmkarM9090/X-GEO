"""Data access for :class:`~app.models.audit.Audit`."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.audit import Audit, AuditStatus
from app.models.crawl import CrawlJob
from app.models.domain import Domain
from app.models.project import Project
from app.repositories.base import BaseRepository


class AuditRepository(BaseRepository[Audit]):
    """Queries scoped to the ``audits`` table."""

    default_ordering = ("created_at",)

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Audit, session)

    async def get_for_user(self, audit_id: UUID, user_id: UUID) -> Audit | None:
        """Fetch an audit only when its project belongs to ``user_id``."""
        query = (
            select(Audit)
            .join(Project, Project.id == Audit.project_id)
            .where(Audit.id == audit_id, Project.user_id == user_id)
            .limit(1)
        )
        return (await self.session.execute(query)).scalar_one_or_none()

    async def get_with_jobs(self, audit_id: UUID) -> Audit | None:
        """Fetch an audit with its crawl jobs eagerly loaded (async-safe)."""
        query = (
            select(Audit)
            .where(Audit.id == audit_id)
            .options(selectinload(Audit.crawl_jobs))
            .limit(1)
        )
        return (await self.session.execute(query)).scalar_one_or_none()

    async def list_for_project(
        self,
        project_id: UUID,
        *,
        skip: int = 0,
        limit: int = 20,
        status: str | None = None,
    ) -> tuple[list[Audit], int]:
        """Paginated audits of one project, newest first."""
        filters = [Audit.project_id == project_id]
        if status:
            filters.append(Audit.status == status)

        items_query = (
            select(Audit)
            .where(*filters)
            .order_by(Audit.created_at.desc(), Audit.id)
            .offset(skip)
            .limit(limit)
        )
        count_query = select(func.count()).select_from(Audit).where(*filters)
        items = list((await self.session.execute(items_query)).scalars().all())
        total = int((await self.session.execute(count_query)).scalar_one())
        return items, total

    async def list_for_user(
        self, user_id: UUID, *, skip: int = 0, limit: int = 20, status: str | None = None
    ) -> tuple[list[Audit], int]:
        """Paginated audits across every project owned by ``user_id``."""
        filters = [Project.user_id == user_id]
        if status:
            filters.append(Audit.status == status)

        items_query = (
            select(Audit)
            .join(Project, Project.id == Audit.project_id)
            .where(*filters)
            .order_by(Audit.created_at.desc(), Audit.id)
            .offset(skip)
            .limit(limit)
        )
        count_query = (
            select(func.count())
            .select_from(Audit)
            .join(Project, Project.id == Audit.project_id)
            .where(*filters)
        )
        items = list((await self.session.execute(items_query)).scalars().all())
        total = int((await self.session.execute(count_query)).scalar_one())
        return items, total

    async def latest_for_domain(self, domain_id: UUID) -> Audit | None:
        """Most recent audit performed for a domain."""
        query = (
            select(Audit)
            .where(Audit.domain_id == domain_id)
            .order_by(Audit.created_at.desc())
            .limit(1)
        )
        return (await self.session.execute(query)).scalar_one_or_none()

    async def claim_for_processing(self, audit_id: UUID) -> Audit | None:
        """Atomically move a queued audit to ``crawling``.

        Returns ``None`` when another worker already claimed it, which makes the
        pipeline safe to retry (idempotent task execution).
        """
        result = await self.session.execute(
            update(Audit)
            .where(
                Audit.id == audit_id,
                Audit.status.in_([AuditStatus.QUEUED.value, AuditStatus.CRAWLING.value]),
            )
            .values(status=AuditStatus.CRAWLING.value, updated_at=datetime.now(tz=UTC))
            .returning(Audit.id)
        )
        await self.session.flush()
        if result.scalar_one_or_none() is None:
            return None
        return await self.get_by_id(audit_id)

    async def set_status(
        self, audit_id: UUID, status: str, *, error_message: str | None = None
    ) -> None:
        """Update lifecycle status (and optionally the failure reason)."""
        values: dict[str, Any] = {"status": status}
        if error_message is not None or status != AuditStatus.FAILED.value:
            values["error_message"] = error_message
        await self.update_fields(audit_id, **values)

    async def save_scores(
        self,
        audit_id: UUID,
        *,
        technical_readiness_score: float | None = None,
        semantic_alignment_score: float | None = None,
        evidentiary_density_score: float | None = None,
        machine_readability_score: float | None = None,
        pcs_score: float | None = None,
        score_breakdown: dict[str, Any] | None = None,
    ) -> None:
        """Persist the computed PCS scores."""
        values: dict[str, Any] = {
            "technical_readiness_score": technical_readiness_score,
            "semantic_alignment_score": semantic_alignment_score,
            "evidentiary_density_score": evidentiary_density_score,
            "machine_readability_score": machine_readability_score,
            "pcs_score": pcs_score,
        }
        if score_breakdown is not None:
            values["score_breakdown"] = score_breakdown
        await self.update_fields(audit_id, **values)

    async def save_crawl_artifact(
        self,
        audit_id: UUID,
        *,
        raw_html: str | None = None,
        clean_markdown: str | None = None,
        word_count: int | None = None,
        json_ld_data: dict | list | None = None,
    ) -> None:
        """Persist the crawl artefacts used by later phases."""
        await self.update_fields(
            audit_id,
            raw_html=raw_html,
            clean_markdown=clean_markdown,
            word_count=word_count,
            json_ld_data=json_ld_data,
        )

    async def project_average_pcs(self, project_id: UUID) -> float | None:
        """Mean PCS across completed audits of a project."""
        query = select(func.avg(Audit.pcs_score)).where(
            Audit.project_id == project_id, Audit.pcs_score.is_not(None)
        )
        value = (await self.session.execute(query)).scalar_one_or_none()
        return float(value) if value is not None else None

    async def count_by_status(self, project_id: UUID) -> dict[str, int]:
        """Audit counts grouped by status."""
        query = (
            select(Audit.status, func.count())
            .where(Audit.project_id == project_id)
            .group_by(Audit.status)
        )
        rows = await self.session.execute(query)
        return {status: int(count) for status, count in rows.all()}

    async def list_stale(
        self, *, older_than: datetime, statuses: tuple[str, ...] = (AuditStatus.CRAWLING.value,)
    ) -> list[Audit]:
        """Audits stuck in a transient state (watchdog/beat task)."""
        query = select(Audit).where(Audit.status.in_(statuses), Audit.updated_at < older_than)
        return list((await self.session.execute(query)).scalars().all())

    async def list_jobs(self, audit_id: UUID) -> list[CrawlJob]:
        """Crawl jobs belonging to an audit, newest first."""
        query = (
            select(CrawlJob)
            .where(CrawlJob.audit_id == audit_id)
            .order_by(CrawlJob.created_at.desc())
        )
        return list((await self.session.execute(query)).scalars().all())

    # -- domains (child rows of a project, consumed by the audit flow) -------
    async def get_domain(self, project_id: UUID, url: str) -> Domain | None:
        """Look up a domain row by project + normalised URL."""
        query = select(Domain).where(Domain.project_id == project_id, Domain.url == url).limit(1)
        return (await self.session.execute(query)).scalar_one_or_none()

    async def get_or_create_domain(
        self, *, project_id: UUID, url: str, sitemap_url: str | None = None
    ) -> Domain:
        """Return the domain row for ``url``, creating it on first audit."""
        existing = await self.get_domain(project_id, url)
        if existing is not None:
            return existing
        try:
            domain = Domain(project_id=project_id, url=url, sitemap_url=sitemap_url)
            self.session.add(domain)
            await self.session.flush()
            await self.session.refresh(domain)
            return domain
        except IntegrityError:
            # Lost a race with a concurrent audit creation - re-read the winner.
            await self.session.rollback()
            winner = await self.get_domain(project_id, url)
            if winner is None:  # pragma: no cover - defensive
                raise
            return winner

    async def update_domain_signals(
        self,
        domain_id: UUID,
        *,
        crawl_status: str | None = None,
        last_crawled_at: datetime | None = None,
        sitemap_url: str | None = None,
        robots_txt: str | None = None,
        **flags: Any,
    ) -> None:
        """Persist the technical-audit cache for a domain."""
        values: dict[str, Any] = {}
        for key, value in flags.items():
            if value is not None:
                values[key] = value
        if crawl_status is not None:
            values["crawl_status"] = crawl_status
        if last_crawled_at is not None:
            values["last_crawled_at"] = last_crawled_at
        if sitemap_url is not None:
            values["sitemap_url"] = sitemap_url
        if robots_txt is not None:
            values["robots_txt"] = robots_txt
        if values:
            await self.session.execute(
                update(Domain).where(Domain.id == domain_id).values(**values)
            )
            await self.session.flush()

    async def list_domains(self, project_id: UUID) -> list[Domain]:
        """All domains of a project."""
        query = select(Domain).where(Domain.project_id == project_id).order_by(Domain.url)
        return list((await self.session.execute(query)).scalars().all())

    async def upsert_prompts(self, project_id: UUID, queries: list[str]) -> int:
        """Insert tracked prompts idempotently; returns how many were new."""
        from app.models.tracked_prompt import PromptCategory, TrackedPrompt

        unique = {query.strip() for query in queries if query and query.strip()}
        if not unique:
            return 0
        rows = [
            {
                "project_id": project_id,
                "query_text": query,
                "category": PromptCategory.INFORMATIONAL.value,
            }
            for query in sorted(unique)
        ]
        statement = (
            pg_insert(TrackedPrompt)
            .values(rows)
            .on_conflict_do_nothing(index_elements=["project_id", "query_text"])
        )
        result = await self.session.execute(statement)
        await self.session.flush()
        return int(result.rowcount or 0)

    async def list_prompt_texts(self, project_id: UUID, *, active_only: bool = True) -> list[str]:
        """Active tracked query strings for a project."""
        from app.models.tracked_prompt import TrackedPrompt

        query = select(TrackedPrompt.query_text).where(TrackedPrompt.project_id == project_id)
        if active_only:
            query = query.where(TrackedPrompt.is_active.is_(True))
        return list((await self.session.execute(query)).scalars().all())


__all__ = ["AuditRepository"]
