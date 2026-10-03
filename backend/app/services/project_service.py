"""Project business logic (tenant-scoped CRUD + validation)."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError
from app.core.logging_config import get_logger
from app.core.security import check_ssrf_async, validate_domain
from app.models.project import Project
from app.repositories.project_repo import ProjectRepository, ProjectStats

logger = get_logger(__name__)


class ProjectService:
    """All project use-cases; routes and tasks call into this class."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ProjectRepository(session)

    async def create_project(
        self,
        user_id: uuid.UUID,
        name: str,
        domain_url: str,
        description: str | None = None,
    ) -> Project:
        """Validate a domain and create the project for ``user_id``.

        The URL is normalised to its origin and SSRF-checked *before* anything is
        persisted, so users cannot register internal infrastructure as a target.
        """
        origin = validate_domain(domain_url)
        await check_ssrf_async(origin)

        existing = await self.repo.get_by_domain_for_user(origin, user_id)
        if existing is not None:
            raise ConflictError(f"A project for {origin} already exists")

        project = await self.repo.create(
            user_id=user_id,
            name=name.strip(),
            domain_url=origin,
            description=description.strip() if description else None,
        )
        logger.info(
            "project.created", project_id=str(project.id), user_id=str(user_id), domain=origin
        )
        return project

    async def list_user_projects(
        self,
        user_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 20,
        is_active: bool | None = None,
        search: str | None = None,
    ) -> tuple[list[Project], int]:
        """Paginated projects owned by the caller."""
        return await self.repo.list_for_user(
            user_id, skip=skip, limit=limit, is_active=is_active, search=search
        )

    async def get_user_project(self, project_id: uuid.UUID, user_id: uuid.UUID) -> Project:
        """Fetch a project, enforcing ownership (404 vs 403 semantics)."""
        project = await self.repo.get_by_id(project_id)
        if project is None:
            raise NotFoundError("Project", str(project_id))
        if project.user_id != user_id:
            logger.warning(
                "project.tenant_violation",
                project_id=str(project_id),
                owner_id=str(project.user_id),
                requester_id=str(user_id),
            )
            raise ForbiddenError("Not authorized to access this project")
        return project

    async def get_project_detail(
        self, project_id: uuid.UUID, user_id: uuid.UUID
    ) -> tuple[Project, ProjectStats]:
        """Project plus dashboard counters."""
        project = await self.get_user_project(project_id, user_id)
        stats = await self.repo.stats(project.id)
        return project, stats

    async def update_project(
        self, project_id: uuid.UUID, user_id: uuid.UUID, **changes: object
    ) -> Project:
        """Patch a project; re-validates the domain when it changes."""
        project = await self.get_user_project(project_id, user_id)

        if (new_domain := changes.get("domain_url")) is not None:
            origin = validate_domain(str(new_domain))
            await check_ssrf_async(origin)
            if origin != project.domain_url:
                clash = await self.repo.get_by_domain_for_user(origin, user_id)
                if clash is not None and clash.id != project.id:
                    raise ConflictError(f"A project for {origin} already exists")
            changes["domain_url"] = origin

        if (name := changes.get("name")) is not None:
            changes["name"] = str(name).strip()
        if (description := changes.get("description")) is not None:
            changes["description"] = str(description).strip() or None

        updated = await self.repo.update(project.id, **changes)
        if updated is None:  # pragma: no cover - row disappeared mid-request
            raise NotFoundError("Project", str(project_id))
        logger.info("project.updated", project_id=str(project_id), fields=sorted(changes))
        return updated

    async def delete_project(self, project_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Delete a project and everything cascading from it."""
        project = await self.get_user_project(project_id, user_id)
        await self.repo.delete(project.id)
        logger.info("project.deleted", project_id=str(project_id), user_id=str(user_id))

    async def get_or_create_default(
        self, user_id: uuid.UUID, domain_url: str, *, name: str | None = None
    ) -> Project:
        """Resolve a project for a URL, creating one when necessary.

        Used by the ad-hoc ``POST /audits`` flow where the client supplies only a
        project id; keeps project creation idempotent.
        """
        origin = validate_domain(domain_url)
        existing = await self.repo.get_by_domain_for_user(origin, user_id)
        if existing is not None:
            return existing
        return await self.create_project(
            user_id=user_id,
            name=name or origin.replace("https://", "").replace("http://", ""),
            domain_url=origin,
        )


__all__ = ["ProjectService"]
