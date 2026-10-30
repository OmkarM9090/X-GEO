"""Async SQLAlchemy engine, session factories and health probes.

Two engine flavours exist on purpose:

* the **process engine** (:data:`engine`) used by the API: pooled, long-lived,
  created once at import time;
* :func:`task_session` for Celery workers: a throwaway ``NullPool`` engine bound
  to the event loop created by ``asyncio.run()`` inside the task. Reusing the
  pooled engine across worker tasks raises "attached to a different loop"
  errors, so tasks must never touch the process engine.
"""

from __future__ import annotations

import contextlib
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.config import get_settings
from app.models.base import Base

logger = structlog.get_logger(__name__)

settings = get_settings()

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_timeout=settings.DATABASE_POOL_TIMEOUT_SECONDS,
    pool_recycle=settings.DATABASE_POOL_RECYCLE_SECONDS,
    pool_pre_ping=True,
    echo=settings.DATABASE_ECHO,
)

async_session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency yielding a transactional session.

    Commits when the request handler succeeds, rolls back on any exception.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


@contextlib.asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Session for scripts/CLI usage: commits on success, always closes."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def create_task_engine(url: str | None = None) -> AsyncEngine:
    """Build a short-lived engine suitable for Celery tasks and one-off scripts."""
    return create_async_engine(
        url or settings.DATABASE_URL,
        poolclass=NullPool,
        echo=settings.DATABASE_ECHO,
    )


@contextlib.asynccontextmanager
async def task_session(url: str | None = None) -> AsyncIterator[AsyncSession]:
    """Self-contained session for background tasks (own engine, own loop)."""
    task_engine = create_task_engine(url)
    factory = async_sessionmaker(
        task_engine, class_=AsyncSession, expire_on_commit=False, autoflush=False
    )
    try:
        async with factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    finally:
        await task_engine.dispose()


async def init_models(target_engine: AsyncEngine | None = None) -> None:
    """Create every table declared on ``Base.metadata`` (development only)."""
    target = target_engine or engine
    async with target.begin() as connection:
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await connection.run_sync(Base.metadata.create_all)


async def drop_models(target_engine: AsyncEngine | None = None) -> None:
    """Drop every table declared on ``Base.metadata`` (tests/scripts only)."""
    target = target_engine or engine
    async with target.begin() as connection:
        await connection.run_sync(Base.metadata.drop_all)


async def dispose_engine() -> None:
    """Close the pooled engine (application shutdown)."""
    await engine.dispose()


@dataclass(slots=True)
class DatabaseHealth:
    """Result of a database readiness probe."""

    healthy: bool
    latency_ms: float
    database_version: str | None = None
    pgvector_version: str | None = None
    error: str | None = None
    details: dict[str, str] = field(default_factory=dict)


async def check_database_health(session: AsyncSession) -> DatabaseHealth:
    """Probe connectivity, server version and the pgvector extension."""
    started = time.perf_counter()
    try:
        version = (await session.execute(text("SELECT version()"))).scalar_one()
        pgvector = (
            await session.execute(
                text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
            )
        ).scalar_one_or_none()
    except Exception as exc:
        return DatabaseHealth(
            healthy=False,
            latency_ms=round((time.perf_counter() - started) * 1000, 2),
            error=str(exc),
        )

    latency_ms = round((time.perf_counter() - started) * 1000, 2)
    details: dict[str, str] = {}
    if not pgvector:
        details["pgvector"] = "not installed"
    return DatabaseHealth(
        healthy=True,
        latency_ms=latency_ms,
        database_version=str(version) if version else None,
        pgvector_version=str(pgvector) if pgvector else None,
        details=details,
    )
