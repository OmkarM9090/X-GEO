"""Project request/response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Page


class ProjectCreate(BaseModel):
    """Payload for ``POST /projects``."""

    name: str = Field(..., min_length=1, max_length=200)
    domain_url: str = Field(..., min_length=5, max_length=500)
    description: str | None = Field(default=None, max_length=1000)


class ProjectUpdate(BaseModel):
    """Payload for ``PATCH /projects/{id}`` (partial)."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    domain_url: str | None = Field(default=None, min_length=5, max_length=500)
    description: str | None = Field(default=None, max_length=1000)
    is_active: bool | None = None


class ProjectResponse(BaseModel):
    """Project projection."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    domain_url: str
    description: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProjectDetailResponse(ProjectResponse):
    """Project plus aggregate counters used by the dashboard."""

    audit_count: int = 0
    domain_count: int = 0
    tracked_prompt_count: int = 0
    latest_pcs_score: float | None = None


class ProjectListResponse(Page[ProjectResponse]):
    """Paginated project list."""


__all__ = [
    "ProjectCreate",
    "ProjectDetailResponse",
    "ProjectListResponse",
    "ProjectResponse",
    "ProjectUpdate",
]
