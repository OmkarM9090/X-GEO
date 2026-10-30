"""Health/readiness response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

HealthState = Literal["healthy", "degraded", "unhealthy"]


class HealthResponse(BaseModel):
    """Liveness/readiness payload for ``GET /health`` and ``GET /health/db``."""

    status: HealthState
    version: str
    timestamp: datetime
    uptime_seconds: float | None = None
    environment: str | None = None
    details: dict[str, str] = Field(default_factory=dict)


class DatabaseHealthResponse(HealthResponse):
    """Database probe payload including pgvector availability."""

    latency_ms: float | None = None
    pgvector_version: str | None = None


__all__ = ["DatabaseHealthResponse", "HealthResponse", "HealthState"]
