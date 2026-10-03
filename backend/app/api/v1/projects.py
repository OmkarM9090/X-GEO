"""Project CRUD routes (tenant scoped)."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from app.api.deps import CurrentUser, DbSession, PaginationDep
from app.schemas.common import ErrorResponse
from app.schemas.project import (
    ProjectCreate,
    ProjectDetailResponse,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)
from app.services.project_service import ProjectService

router = APIRouter()

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Not authenticated"},
    403: {"model": ErrorResponse, "description": "Not authorized for this project"},
    404: {"model": ErrorResponse, "description": "Project not found"},
    409: {"model": ErrorResponse, "description": "A project for this domain already exists"},
}


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project",
    responses=ERROR_RESPONSES,
)
async def create_project(data: ProjectCreate, user: CurrentUser, db: DbSession) -> ProjectResponse:
    """Register a domain the caller wants to optimise (URL is SSRF-validated)."""
    project = await ProjectService(db).create_project(
        user_id=user.id,
        name=data.name,
        domain_url=data.domain_url,
        description=data.description,
    )
    return ProjectResponse.model_validate(project)


@router.get("", response_model=ProjectListResponse, summary="List projects")
async def list_projects(
    user: CurrentUser,
    db: DbSession,
    pagination: PaginationDep,
    is_active: bool | None = Query(default=None, description="Filter by activation state"),
    search: str | None = Query(default=None, max_length=200, description="Substring match on name"),
) -> ProjectListResponse:
    """Paginated projects owned by the caller."""
    items, total = await ProjectService(db).list_user_projects(
        user_id=user.id,
        skip=pagination.skip,
        limit=pagination.limit,
        is_active=is_active,
        search=search,
    )
    return ProjectListResponse.create(
        [ProjectResponse.model_validate(project) for project in items],
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )


@router.get(
    "/{project_id}",
    response_model=ProjectDetailResponse,
    summary="Get a project",
    responses=ERROR_RESPONSES,
)
async def get_project(project_id: UUID, user: CurrentUser, db: DbSession) -> ProjectDetailResponse:
    """Project details plus dashboard counters."""
    project, stats = await ProjectService(db).get_project_detail(project_id, user.id)
    return ProjectDetailResponse(
        **ProjectResponse.model_validate(project).model_dump(),
        audit_count=stats.audit_count,
        domain_count=stats.domain_count,
        tracked_prompt_count=stats.tracked_prompt_count,
        latest_pcs_score=stats.latest_pcs_score,
    )


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update a project",
    responses=ERROR_RESPONSES,
)
async def update_project(
    project_id: UUID, data: ProjectUpdate, user: CurrentUser, db: DbSession
) -> ProjectResponse:
    """Partially update a project; ``domain_url`` is re-validated when present."""
    project = await ProjectService(db).update_project(
        project_id=project_id,
        user_id=user.id,
        **data.model_dump(exclude_unset=True),
    )
    return ProjectResponse.model_validate(project)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a project",
    responses=ERROR_RESPONSES,
)
async def delete_project(project_id: UUID, user: CurrentUser, db: DbSession) -> Response:
    """Delete a project and every audit, chunk and prompt cascading from it."""
    await ProjectService(db).delete_project(project_id, user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
