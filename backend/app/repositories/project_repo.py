"""Data access for :class:`~app.models.project.Project`."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import Audit
from app.models.domain import Domain
from app.models.project import Project
from app.models.tracked_prompt import TrackedPrompt
from app.repositories.base import BaseRepository


@dataclass(frozen=True, slots=True)
class ProjectStats:
    """Aggregate counters shown on the project detail screen."""

    audit_count: int
    domain_count: int
    tracked_prompt_count: int
    latest_pcs_score: float | None


class ProjectRepository(BaseRepository[Project]):
    """Queries scoped to the ``projects`` table (always tenant filtered)."""

    default_ordering = ("created_at",)

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Project, session)

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        skip: int = 0,
        limit: int = 20,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> tuple[list[Project], int]:
        """Paginated projects owned by ``user_id``."""
        filters = [Project.user_id == user_id]
        if is_active is not None:
            filters.append(Project.is_active.is_(is_active))
        if search:
            filters.append(Project.name.ilike(f"%{search.strip()}%"))

        items_query = (
            select(Project)
            .where(*filters)
            .order_by(Project.created_at.desc(), Project.id)
            .offset(skip)
            .limit(limit)
        )
        count_query = select(func.count()).select_from(Project).where(*filters)

        items = list((await self.session.execute(items_query)).scalars().all())
        total = int((await self.session.execute(count_query)).scalar_one())
        return items, total

    async def get_for_user(self, project_id: UUID, user_id: UUID) -> Project | None:
        """Fetch a project only when it belongs to ``user_id`` (tenant isolation)."""
        query = select(Project).where(Project.id == project_id, Project.user_id == user_id).limit(1)
        return (await self.session.execute(query)).scalar_one_or_none()

    async def get_by_domain_for_user(self, domain_url: str, user_id: UUID) -> Project | None:
        """Find a project by its canonical domain URL."""
        query = (
            select(Project)
            .where(Project.user_id == user_id, Project.domain_url == domain_url)
            .limit(1)
        )
        return (await self.session.execute(query)).scalar_one_or_none()

    async def stats(self, project_id: UUID) -> ProjectStats:
        """Counters + latest PCS score for a project in a single round-trip."""
        latest_pcs = (
            select(Audit.pcs_score)
            .where(Audit.project_id == project_id, Audit.pcs_score.is_not(None))
            .order_by(Audit.created_at.desc())
            .limit(1)
            .scalar_subquery()
        )
        query = select(
            select(func.count())
            .select_from(Audit)
            .where(Audit.project_id == project_id)
            .scalar_subquery(),
            select(func.count())
            .select_from(Domain)
            .where(Domain.project_id == project_id)
            .scalar_subquery(),
            select(func.count())
            .select_from(TrackedPrompt)
            .where(TrackedPrompt.project_id == project_id)
            .scalar_subquery(),
            latest_pcs,
        )
        audit_count, domain_count, prompt_count, pcs = (await self.session.execute(query)).one()
        return ProjectStats(
            audit_count=int(audit_count or 0),
            domain_count=int(domain_count or 0),
            tracked_prompt_count=int(prompt_count or 0),
            latest_pcs_score=float(pcs) if pcs is not None else None,
        )

    async def set_active(self, project_id: UUID, is_active: bool) -> None:
        """Activate/deactivate a project."""
        await self.update_fields(project_id, is_active=is_active)


__all__ = ["ProjectRepository", "ProjectStats"]
