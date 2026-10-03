"""Crawl request/response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.common import Page


class CrawlTriggerRequest(BaseModel):
    """Payload for ``POST /crawls/trigger``.

    Two shapes are accepted:

    * ``{"audit_id": "..."}``  — re-crawl an existing audit.
    * ``{"project_id": "...", "url": "https://..."}`` — target ad-hoc.
    """

    audit_id: UUID | None = None
    project_id: UUID | None = None
    url: str | None = Field(default=None, max_length=2048)
    force_playwright: bool = False
    max_pages: int | None = Field(default=None, ge=1, le=500)

    @model_validator(mode="after")
    def _require_target(self) -> CrawlTriggerRequest:
        if self.audit_id is None and not (self.project_id and self.url):
            raise ValueError("Provide either 'audit_id' or both 'project_id' and 'url'")
        if self.project_id and self.url and self.audit_id:
            raise ValueError("Provide either 'audit_id' or 'project_id' + 'url', not both")
        return self


class CrawlJobResponse(BaseModel):
    """Crawl job projection."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    audit_id: UUID
    url: str
    method: str
    status: str
    http_status_code: int | None = None
    content_type: str | None = None
    response_time_ms: int | None = None
    response_size_bytes: int | None = None
    is_spa_detected: bool
    playwright_fallback_used: bool
    robots_txt_allowed: bool
    error_message: str | None = None
    retry_count: int
    started_at: datetime | None = None
    finished_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class CrawlStatusResponse(BaseModel):
    """Status envelope for ``GET /crawls/{id}/status``."""

    job: CrawlJobResponse
    audit_status: str | None = None
    audit_progress: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Coarse-grained progress for the UI"
    )
    is_terminal: bool = False


class CrawlListResponse(Page[CrawlJobResponse]):
    """Paginated crawl-job list."""


__all__ = [
    "CrawlJobResponse",
    "CrawlListResponse",
    "CrawlStatusResponse",
    "CrawlTriggerRequest",
]
