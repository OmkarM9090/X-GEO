"""Data access for :class:`~app.models.crawl.CrawlJob`."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.crawl import CrawlJob, CrawlStatus
from app.repositories.base import BaseRepository


class CrawlRepository(BaseRepository[CrawlJob]):
    """Queries scoped to the ``crawl_jobs`` table."""

    default_ordering = ("created_at",)

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(CrawlJob, session)

    async def latest_for_audit(self, audit_id: UUID) -> CrawlJob | None:
        """Most recent crawl attempt for an audit."""
        query = (
            select(CrawlJob)
            .where(CrawlJob.audit_id == audit_id)
            # `created_at` defaults to the transaction timestamp, so rows created
            # in one transaction share it: the id tie-break keeps pages stable.
            .order_by(CrawlJob.created_at.desc(), CrawlJob.id.desc())
            .limit(1)
        )
        return (await self.session.execute(query)).scalar_one_or_none()

    async def list_for_audit(
        self, audit_id: UUID, *, skip: int = 0, limit: int = 20
    ) -> tuple[list[CrawlJob], int]:
        """Paginated crawl history for an audit."""
        items_query = (
            select(CrawlJob)
            .where(CrawlJob.audit_id == audit_id)
            .order_by(CrawlJob.created_at.desc(), CrawlJob.id)
            .offset(skip)
            .limit(limit)
        )
        count_query = (
            select(func.count()).select_from(CrawlJob).where(CrawlJob.audit_id == audit_id)
        )
        items = list((await self.session.execute(items_query)).scalars().all())
        total = int((await self.session.execute(count_query)).scalar_one())
        return items, total

    async def list_for_user(
        self, user_id: UUID, *, skip: int = 0, limit: int = 20, status: str | None = None
    ) -> tuple[list[CrawlJob], int]:
        """Crawl jobs across every audit of a user's projects."""
        from app.models.audit import Audit
        from app.models.project import Project

        filters = [Project.user_id == user_id]
        if status:
            filters.append(CrawlJob.status == status)

        items_query = (
            select(CrawlJob)
            .join(Audit, Audit.id == CrawlJob.audit_id)
            .join(Project, Project.id == Audit.project_id)
            .where(*filters)
            .order_by(CrawlJob.created_at.desc(), CrawlJob.id)
            .offset(skip)
            .limit(limit)
        )
        count_query = (
            select(func.count())
            .select_from(CrawlJob)
            .join(Audit, Audit.id == CrawlJob.audit_id)
            .join(Project, Project.id == Audit.project_id)
            .where(*filters)
        )
        items = list((await self.session.execute(items_query)).scalars().all())
        total = int((await self.session.execute(count_query)).scalar_one())
        return items, total

    async def mark_running(self, job_id: UUID, *, method: str | None = None) -> CrawlJob | None:
        """Atomically claim a pending job for execution.

        Returns ``None`` when the job was already claimed or finished.
        """
        values: dict[str, Any] = {
            "status": CrawlStatus.RUNNING.value,
            "started_at": datetime.now(tz=UTC),
            "error_message": None,
        }
        if method:
            values["method"] = method
        result = await self.session.execute(
            update(CrawlJob)
            .where(CrawlJob.id == job_id, CrawlJob.status == CrawlStatus.PENDING.value)
            .values(**values)
            .returning(CrawlJob.id)
        )
        await self.session.flush()
        if result.scalar_one_or_none() is None:
            return None
        return await self.get_by_id(job_id)

    async def mark_completed(
        self,
        job_id: UUID,
        *,
        http_status_code: int | None = None,
        content_type: str | None = None,
        response_time_ms: int | None = None,
        response_size_bytes: int | None = None,
        is_spa_detected: bool = False,
        playwright_fallback_used: bool = False,
        robots_txt_allowed: bool | None = None,
        method: str | None = None,
    ) -> None:
        """Record a successful fetch."""
        values: dict[str, Any] = {
            "status": CrawlStatus.COMPLETED.value,
            "finished_at": datetime.now(tz=UTC),
            "http_status_code": http_status_code,
            "content_type": content_type,
            "response_time_ms": response_time_ms,
            "response_size_bytes": response_size_bytes,
            "is_spa_detected": is_spa_detected,
            "playwright_fallback_used": playwright_fallback_used,
            "error_message": None,
        }
        if robots_txt_allowed is not None:
            values["robots_txt_allowed"] = robots_txt_allowed
        if method:
            values["method"] = method
        await self.update_fields(job_id, **values)

    async def mark_failed(
        self,
        job_id: UUID,
        *,
        error_message: str,
        http_status_code: int | None = None,
        response_time_ms: int | None = None,
        is_spa_detected: bool = False,
        playwright_fallback_used: bool = False,
        robots_txt_allowed: bool | None = None,
        method: str | None = None,
    ) -> None:
        """Record a failed fetch."""
        values: dict[str, Any] = {
            "status": CrawlStatus.FAILED.value,
            "finished_at": datetime.now(tz=UTC),
            "error_message": error_message[:2000],
            "http_status_code": http_status_code,
            "response_time_ms": response_time_ms,
            "is_spa_detected": is_spa_detected,
            "playwright_fallback_used": playwright_fallback_used,
        }
        if robots_txt_allowed is not None:
            values["robots_txt_allowed"] = robots_txt_allowed
        if method:
            values["method"] = method
        await self.update_fields(job_id, **values)

    async def increment_retry(self, job_id: UUID, *, error_message: str | None = None) -> int:
        """Bump the retry counter and return the new value."""
        result = await self.session.execute(
            update(CrawlJob)
            .where(CrawlJob.id == job_id)
            .values(
                retry_count=CrawlJob.retry_count + 1,
                error_message=error_message,
                updated_at=datetime.now(tz=UTC),
            )
            .returning(CrawlJob.retry_count)
        )
        await self.session.flush()
        return int(result.scalar_one_or_none() or 0)

    async def list_stale_running(self, *, older_than: datetime) -> list[CrawlJob]:
        """Jobs stuck in ``running`` (worker crash recovery)."""
        query = select(CrawlJob).where(
            CrawlJob.status == CrawlStatus.RUNNING.value, CrawlJob.updated_at < older_than
        )
        return list((await self.session.execute(query)).scalars().all())

    async def count_by_status(self, audit_id: UUID) -> dict[str, int]:
        """Crawl job counts grouped by status for an audit."""
        query = (
            select(CrawlJob.status, func.count())
            .where(CrawlJob.audit_id == audit_id)
            .group_by(CrawlJob.status)
        )
        rows = await self.session.execute(query)
        return {status: int(count) for status, count in rows.all()}


__all__ = ["CrawlRepository"]
