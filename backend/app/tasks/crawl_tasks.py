"""Crawl tasks.

Every task follows the same shape:

``run_x_async(...)``  pure async implementation, uses :func:`task_session`
``run_x``             Celery entry point: ``asyncio.run`` around the async body

``dispatch_crawl_job`` is the single dispatch helper used by the service layer.
When ``TASK_ALWAYS_EAGER`` is enabled (tests, local dev without Redis) the job
runs inline **on the caller's session**, which keeps the whole request in one
transaction instead of deadlocking on uncommitted rows.
"""

from __future__ import annotations

import asyncio
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import anyio
from celery import Task

from app.config import get_settings
from app.core.database import task_session
from app.core.logging_config import configure_logging, get_logger
from app.tasks.celery_app import celery_app

logger = get_logger(__name__)
settings = get_settings()

#: Queues consumed by the default worker.
CRAWL_QUEUE = "xgeo.crawl"


async def run_crawl_job_async(job_id: str) -> dict[str, Any]:
    """Execute a crawl job in a self-contained session (own engine + loop)."""
    from app.services.crawl_service import CrawlService

    async with task_session() as session:
        service = CrawlService(session)
        outcome = await service.run_job(uuid.UUID(str(job_id)))
        return outcome.as_dict()


@celery_app.task(
    bind=True,
    name="app.tasks.crawl_tasks.run_crawl_job",
    max_retries=settings.TASK_MAX_RETRIES,
    acks_late=True,
)
def run_crawl_job(self: Task, job_id: str) -> dict[str, Any]:
    """Crawl one URL (fetch → clean → chunk → score)."""
    configure_logging(settings, force=True)
    outcome = asyncio.run(run_crawl_job_async(job_id))

    if outcome.get("should_retry") and self.request.retries < self.max_retries:
        countdown = 2 ** (self.request.retries + 1)  # 2s, 4s, 8s...
        logger.warning(
            "task.crawl_retry",
            job_id=job_id,
            attempt=self.request.retries + 1,
            countdown=countdown,
        )
        raise self.retry(countdown=countdown, exc=RuntimeError(str(outcome.get("error"))))
    return outcome


async def dispatch_crawl_job(job_id: uuid.UUID, *, session: Any | None = None) -> str:
    """Queue (or inline-execute) a crawl job; returns a task id or ``eager:<status>``."""
    if settings.TASK_ALWAYS_EAGER or celery_app.conf.task_always_eager:
        if session is not None:
            from app.services.crawl_service import CrawlService

            outcome = await CrawlService(session).run_job(job_id)
            return f"eager:{outcome.status}"
        eager_result = await run_crawl_job_async(str(job_id))
        return f"eager:{eager_result.get('status')}"

    # `.delay()` blocks on the broker connection: keep it off the event loop.
    async_result = await anyio.to_thread.run_sync(
        lambda: run_crawl_job.apply_async(args=[str(job_id)], queue=CRAWL_QUEUE)
    )
    logger.info("task.crawl_dispatched", job_id=str(job_id), task_id=async_result.id)
    return str(async_result.id)


async def recover_stale_jobs_async(*, max_age_seconds: int = 1800) -> dict[str, Any]:
    """Fail crawl jobs whose worker died, and unstick their audits."""
    from sqlalchemy import select, update

    from app.models.audit import Audit, AuditStatus
    from app.models.crawl import CrawlJob, CrawlStatus

    cutoff = datetime.now(tz=UTC) - timedelta(seconds=max_age_seconds)
    async with task_session() as session:
        stale_jobs = list(
            (
                await session.execute(
                    select(CrawlJob).where(
                        CrawlJob.status == CrawlStatus.RUNNING.value, CrawlJob.updated_at < cutoff
                    )
                )
            )
            .scalars()
            .all()
        )
        for job in stale_jobs:
            await session.execute(
                update(CrawlJob)
                .where(CrawlJob.id == job.id)
                .values(
                    status=CrawlStatus.FAILED.value,
                    error_message=f"Worker lost (no update for {max_age_seconds}s)",
                    finished_at=datetime.now(tz=UTC),
                )
            )
            await session.execute(
                update(Audit)
                .where(Audit.id == job.audit_id, Audit.status == AuditStatus.CRAWLING.value)
                .values(
                    status=AuditStatus.FAILED.value,
                    error_message="Crawl worker stopped responding",
                )
            )
    if stale_jobs:
        logger.warning("task.stale_jobs_recovered", count=len(stale_jobs))
    return {"recovered": len(stale_jobs), "cutoff": cutoff.isoformat()}


@celery_app.task(name="app.tasks.crawl_tasks.recover_stale_jobs")
def recover_stale_jobs(max_age_seconds: int = 1800) -> dict[str, Any]:
    """Beat task: requeue/fail jobs abandoned by a crashed worker."""
    return asyncio.run(recover_stale_jobs_async(max_age_seconds=max_age_seconds))


async def cleanup_orphan_chunks_async(*, max_age_seconds: int = 86400) -> dict[str, Any]:
    """Delete chunks whose audit no longer exists (belt and braces for FK drift)."""
    from sqlalchemy import delete, select

    from app.models.audit import Audit
    from app.models.chunk import Chunk

    # Only touch chunks older than the grace window: a chunk inserted seconds
    # ago may belong to a transaction that has not committed yet.
    cutoff = datetime.now(tz=UTC) - timedelta(seconds=max_age_seconds)
    async with task_session() as session:
        orphan_query = (
            select(Chunk.id)
            .outerjoin(Audit, Audit.id == Chunk.audit_id)
            .where(Audit.id.is_(None), Chunk.created_at < cutoff)
        )
        orphan_ids = list((await session.execute(orphan_query.limit(5000))).scalars().all())
        if orphan_ids:
            await session.execute(delete(Chunk).where(Chunk.id.in_(orphan_ids)))
    if orphan_ids:
        logger.warning("task.orphan_chunks_deleted", count=len(orphan_ids))
    return {"deleted": len(orphan_ids)}


@celery_app.task(name="app.tasks.crawl_tasks.cleanup_orphan_chunks")
def cleanup_orphan_chunks() -> dict[str, Any]:
    """Beat task: drop chunks that lost their audit row."""
    return asyncio.run(cleanup_orphan_chunks_async())


__all__ = [
    "CRAWL_QUEUE",
    "cleanup_orphan_chunks",
    "dispatch_crawl_job",
    "recover_stale_jobs",
    "run_crawl_job",
    "run_crawl_job_async",
]
