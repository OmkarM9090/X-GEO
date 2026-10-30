"""Audit routes: create, read, score breakdown, chunk retrieval and search."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query, Response, status

from app.api.deps import CurrentUser, DbSession, PaginationDep
from app.config import get_settings
from app.schemas.audit import (
    AuditCreate,
    AuditDetailResponse,
    AuditListResponse,
    AuditResponse,
    AuditScoreBreakdownResponse,
    AuditScores,
    CrawlJobSummary,
)
from app.schemas.chunk import ChunkListResponse, ChunkSearchRequest, ChunkSearchResponse
from app.schemas.common import ErrorResponse
from app.services.audit_service import AuditService
from app.services.chunk_service import ChunkService

router = APIRouter()

ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Not authenticated"},
    402: {"model": ErrorResponse, "description": "Monthly credit limit reached"},
    403: {"model": ErrorResponse, "description": "Audit belongs to another user"},
    404: {"model": ErrorResponse, "description": "Audit not found"},
    422: {"model": ErrorResponse, "description": "Target URL is invalid or blocked (SSRF)"},
}


@router.post(
    "",
    response_model=AuditResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an audit",
    responses=ERROR_RESPONSES,
)
async def create_audit(data: AuditCreate, user: CurrentUser, db: DbSession) -> AuditResponse:
    """Queue an audit for a URL belonging to one of the caller's projects.

    The URL must be inside the project's domain, must pass SSRF validation and
    consumes one monthly credit.
    """
    audit = await AuditService(db).create_audit(user.id, data)
    return AuditResponse.model_validate(audit)


@router.get("", response_model=AuditListResponse, summary="List audits")
async def list_audits(
    user: CurrentUser,
    db: DbSession,
    pagination: PaginationDep,
    project_id: UUID | None = Query(default=None, description="Restrict to one project"),
    audit_status: str | None = Query(
        default=None, alias="status", description="queued|crawling|analyzing|completed|failed"
    ),
) -> AuditListResponse:
    """Paginated audits for the caller (optionally filtered by project/status)."""
    items, total = await AuditService(db).list_audits(
        user.id,
        project_id=project_id,
        status=audit_status,
        skip=pagination.skip,
        limit=pagination.limit,
    )
    return AuditListResponse.create(
        [AuditResponse.model_validate(audit) for audit in items],
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
    )


@router.get(
    "/{audit_id}",
    response_model=AuditDetailResponse,
    summary="Get an audit",
    responses=ERROR_RESPONSES,
)
async def get_audit(audit_id: UUID, user: CurrentUser, db: DbSession) -> AuditDetailResponse:
    """Audit detail: scores, crawl history and chunk statistics."""
    detail = await AuditService(db).get_audit_detail(audit_id, user.id)
    base = AuditResponse.model_validate(detail.audit)
    return AuditDetailResponse(
        **base.model_dump(),
        json_ld_data=detail.audit.json_ld_data,
        score_breakdown=detail.audit.score_breakdown,
        chunk_count=detail.chunk_count,
        embedded_chunk_count=detail.embedded_chunk_count,
        crawl_jobs=[CrawlJobSummary.model_validate(job) for job in detail.crawl_jobs[:20]],
    )


@router.delete(
    "/{audit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an audit",
    responses=ERROR_RESPONSES,
)
async def delete_audit(audit_id: UUID, user: CurrentUser, db: DbSession) -> Response:
    """Delete an audit (cascades to crawl jobs, chunks and simulations)."""
    await AuditService(db).delete_audit(audit_id, user.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{audit_id}/scores",
    response_model=AuditScoreBreakdownResponse,
    summary="Score breakdown",
    responses=ERROR_RESPONSES,
)
async def get_audit_scores(
    audit_id: UUID, user: CurrentUser, db: DbSession
) -> AuditScoreBreakdownResponse:
    """Explainability payload: how each PCS sub-score was derived."""
    audit = await AuditService(db).get_audit_for_user(audit_id, user.id)
    return AuditScoreBreakdownResponse(
        audit_id=audit.id,
        scores=AuditScores(
            technical_readiness=audit.technical_readiness_score,
            semantic_alignment=audit.semantic_alignment_score,
            evidentiary_density=audit.evidentiary_density_score,
            machine_readability=audit.machine_readability_score,
            pcs=audit.pcs_score,
        ),
        weights=get_settings().PCS_WEIGHTS,
        breakdown=audit.score_breakdown,
    )


@router.get(
    "/{audit_id}/chunks",
    response_model=ChunkListResponse,
    summary="List embedded chunks",
    responses=ERROR_RESPONSES,
)
async def list_audit_chunks(
    audit_id: UUID, user: CurrentUser, db: DbSession, pagination: PaginationDep
) -> ChunkListResponse:
    """Chunks generated from a crawled page, in document order."""
    audit = await AuditService(db).get_audit_for_user(audit_id, user.id)
    service = ChunkService(db)
    chunks, total = await service.repo.list_for_audit(
        audit.id, skip=pagination.skip, limit=pagination.limit
    )
    return ChunkListResponse(
        items=[service.to_response(chunk) for chunk in chunks],
        total=total,
        skip=pagination.skip,
        limit=pagination.limit,
        has_more=(pagination.skip + len(chunks)) < total,
    )


@router.post(
    "/{audit_id}/search",
    response_model=ChunkSearchResponse,
    summary="Search a page's chunks",
    description=(
        "Hybrid retrieval over one audit: pgvector cosine similarity, PostgreSQL "
        "full-text ranking, or reciprocal-rank fusion of both."
    ),
    responses=ERROR_RESPONSES,
)
async def search_audit_chunks(
    audit_id: UUID, data: ChunkSearchRequest, user: CurrentUser, db: DbSession
) -> ChunkSearchResponse:
    """Retrieve the passages of an audit most relevant to a query."""
    audit = await AuditService(db).get_audit_for_user(audit_id, user.id)
    scoped = data.model_copy(update={"audit_id": audit.id, "project_id": None})
    return await ChunkService(db).search(scoped)


__all__ = ["router"]
