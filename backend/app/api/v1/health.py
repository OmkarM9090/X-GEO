"""Health, database and readiness probes."""

from __future__ import annotations

import time
from datetime import UTC, datetime

from fastapi import APIRouter, Response, status

from app.api.deps import DbSession, SettingsDep
from app.core.database import check_database_health
from app.schemas.health import DatabaseHealthResponse, HealthResponse

router = APIRouter()

#: Process start time, used for the ``uptime_seconds`` field.
STARTED_AT = time.monotonic()


def _uptime_seconds() -> float:
    return round(time.monotonic() - STARTED_AT, 3)


@router.get(
    "",
    response_model=HealthResponse,
    summary="Liveness probe",
    description="Returns 200 as soon as the process is serving traffic. Does not touch the database.",
)
async def health_check(settings: SettingsDep) -> HealthResponse:
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        timestamp=datetime.now(tz=UTC),
        uptime_seconds=_uptime_seconds(),
        environment=settings.ENVIRONMENT,
        details={"service": settings.APP_NAME},
    )


@router.get(
    "/db",
    response_model=DatabaseHealthResponse,
    summary="Database probe",
    description="Checks connectivity, reports the PostgreSQL version and whether pgvector is installed.",
)
async def db_health_check(db: DbSession, settings: SettingsDep) -> DatabaseHealthResponse:
    health = await check_database_health(db)
    details = dict(health.details)
    if health.error:
        details["error"] = health.error[:500]
    return DatabaseHealthResponse(
        status="healthy" if health.healthy else "unhealthy",
        version=settings.APP_VERSION,
        timestamp=datetime.now(tz=UTC),
        uptime_seconds=_uptime_seconds(),
        environment=settings.ENVIRONMENT,
        details=details,
        latency_ms=health.latency_ms,
        pgvector_version=health.pgvector_version,
    )


@router.get(
    "/ready",
    response_model=HealthResponse,
    summary="Readiness probe",
    description="Returns 503 until the database (and pgvector) are reachable — use for k8s `readinessProbe`.",
    responses={503: {"description": "Dependencies are not ready"}},
)
async def readiness_check(
    db: DbSession, settings: SettingsDep, response: Response
) -> HealthResponse:
    health = await check_database_health(db)
    # NOTE: FastAPI injects a Response whose `status_code` is None (not 200), so
    # readiness must be tracked explicitly instead of compared against 200.
    ready = health.healthy and bool(health.pgvector_version)
    if not ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    details = dict(health.details)
    if health.pgvector_version:
        details["pgvector"] = health.pgvector_version
    if health.error:
        details["error"] = health.error[:500]
    return HealthResponse(
        status="healthy" if ready else "unhealthy",
        version=settings.APP_VERSION,
        timestamp=datetime.now(tz=UTC),
        uptime_seconds=_uptime_seconds(),
        environment=settings.ENVIRONMENT,
        details=details,
    )


__all__ = ["router"]
