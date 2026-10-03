"""Crawl routes: trigger a crawl, inspect job status, list jobs."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession, PaginationDep
from app.schemas.common import ErrorResponse
from app.schemas.crawl import (
    CrawlJobResponse,
    CrawlListResponse,
    CrawlStatusResponse,
    CrawlTriggerRequest,
)
from app.services.crawl_service import CrawlService

router = APIRouter()

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Not authenticated"},
    404: {"model": ErrorResponse, "description": "Audit or crawl job not found"},
    422: {"model": ErrorResponse, "description": "Invalid target URL"},
}


@router.post(
    "/trigger",
    response_model=CrawlJobResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger a crawl",
    responses=ERROR_RESPONSES,
)
async def trigger_crawl(
    data: CrawlTriggerRequest, user: CurrentUser, db: DbSession
) -> CrawlJobResponse:
    """Queue a crawl for an existing audit or for a URL inside a project."""
    job = await CrawlService(db).trigger_crawl(user.id, data)
    return CrawlJobResponse.model_validate(job)


@router.get("", response_model=CrawlListResponse, summary="List crawl jobs")
async def list_crawls(
    user: CurrentUser,
    db: DbSession,
    pagination: PaginationDep,
    crawl_status: str | None = Query(
        default=None, alias="status", description="pending|running|completed|failed|cancelled"
    ),
) -> CrawlListResponse:
    """Paginated crawl jobs across the caller's projects."""
    items, total = await CrawlService(db).list_jobs(
        user.id, skip=pagination.skip, limit=pagination.limit, status=crawl_status
    )
    return CrawlListResponse.create(
        [CrawlJobResponse.model_validate(job) for job in items],
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )


@router.get(
    "/{job_id}/status",
    response_model=CrawlStatusResponse,
    summary="Crawl job status",
    responses=ERROR_RESPONSES,
)
async def get_crawl_status(job_id: UUID, user: CurrentUser, db: DbSession) -> CrawlStatusResponse:
    """Poll progress of a crawl job (and the audit it belongs to)."""
    return await CrawlService(db).get_job_status(job_id, user.id)


__all__ = ["router"]
