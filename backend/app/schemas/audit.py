"""Audit request/response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Page


class AuditCreate(BaseModel):
    """Payload for ``POST /audits``.

    Either point at an existing project (``project_id``) or let the API resolve
    the project from a ``project_id`` + ``target_url`` pair.
    """

    project_id: UUID
    target_url: str = Field(..., min_length=5, max_length=2048)
    tracked_prompts: list[str] = Field(
        default_factory=list,
        max_length=25,
        description="Optional queries to track; created idempotently per project.",
    )
    run_async: bool = Field(
        default=True,
        description="Queue the crawl on Celery. When false the audit is stored in 'queued' state only.",
    )


class AuditScores(BaseModel):
    """The four PCS sub-scores plus the composite index (all 0..1)."""

    technical_readiness: float | None = None
    semantic_alignment: float | None = None
    evidentiary_density: float | None = None
    machine_readability: float | None = None
    pcs: float | None = None


class AuditResponse(BaseModel):
    """Audit projection."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    domain_id: UUID
    target_url: str
    status: str
    technical_readiness_score: float | None = None
    semantic_alignment_score: float | None = None
    evidentiary_density_score: float | None = None
    machine_readability_score: float | None = None
    pcs_score: float | None = None
    word_count: int | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class CrawlJobSummary(BaseModel):
    """Compact crawl-job view embedded in audit details."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    url: str
    method: str
    status: str
    http_status_code: int | None = None
    response_time_ms: int | None = None
    is_spa_detected: bool
    playwright_fallback_used: bool
    error_message: str | None = None
    retry_count: int
    created_at: datetime


class AuditDetailResponse(AuditResponse):
    """Audit plus crawl history, chunk stats and the score explanation."""

    json_ld_data: dict | list | None = None
    score_breakdown: dict | None = None
    chunk_count: int = 0
    embedded_chunk_count: int = 0
    crawl_jobs: list[CrawlJobSummary] = Field(default_factory=list)


class AuditListResponse(Page[AuditResponse]):
    """Paginated audit list."""


class AuditScoreBreakdownResponse(BaseModel):
    """Explainability payload for a completed audit."""

    audit_id: UUID
    scores: AuditScores
    weights: dict[str, float]
    breakdown: dict | None = None


__all__ = [
    "AuditCreate",
    "AuditDetailResponse",
    "AuditListResponse",
    "AuditResponse",
    "AuditScoreBreakdownResponse",
    "AuditScores",
    "CrawlJobSummary",
]
