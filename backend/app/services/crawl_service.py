"""Crawl orchestration: fetch → extract → clean → chunk → embed → score.

The service is transport agnostic: it drives a :class:`~app.crawler.fetchers.BaseFetcher`
(Scrapy by default, Playwright for SPAs, httpx as a last resort) and owns every
state transition of the audit and crawl-job records.

It is invoked from the Celery task (``app.tasks.crawl_tasks``) and, in tests or
when ``TASK_ALWAYS_EAGER=true``, directly from the request that created the audit.
"""

from __future__ import annotations

import dataclasses
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.exceptions import NotFoundError
from app.core.logging_config import get_logger
from app.core.security import sanitize_crawled_content
from app.models.audit import Audit, AuditStatus
from app.models.crawl import CrawlJob, CrawlMethod, CrawlStatus
from app.repositories.audit_repo import AuditRepository
from app.repositories.crawl_repo import CrawlRepository
from app.schemas.crawl import CrawlJobResponse, CrawlStatusResponse, CrawlTriggerRequest
from app.services.audit_service import AuditService, build_scoring_input
from app.services.chunk_service import ChunkService
from app.services.project_service import ProjectService

logger = get_logger(__name__)

#: Upper bound on the sanitised HTML stored on an audit row (~1 MB of text).
MAX_STORED_HTML_CHARS = 1_000_000

#: Coarse progress values surfaced to the UI.
_PROGRESS = {
    AuditStatus.QUEUED.value: 0.05,
    AuditStatus.CRAWLING.value: 0.35,
    AuditStatus.ANALYZING.value: 0.75,
    AuditStatus.COMPLETED.value: 1.0,
    AuditStatus.FAILED.value: 1.0,
}


@dataclass(slots=True)
class CrawlOutcome:
    """Result of one crawl-job execution."""

    job_id: uuid.UUID
    status: str
    claimed: bool = True
    chunks_created: int = 0
    word_count: int = 0
    pcs_score: float | None = None
    error: str | None = None
    should_retry: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "job_id": str(self.job_id),
            "status": self.status,
            "claimed": self.claimed,
            "chunks_created": self.chunks_created,
            "word_count": self.word_count,
            "pcs_score": self.pcs_score,
            "error": self.error,
            "should_retry": self.should_retry,
        }


class CrawlService:
    """Drives the crawl pipeline for a single audit."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        fetcher: Any | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.fetcher = fetcher
        self.crawls = CrawlRepository(session)
        self.audits = AuditRepository(session)
        self.audit_service = AuditService(session, settings=self.settings)
        self.chunks = ChunkService(session, settings=self.settings)

    # -- public API ----------------------------------------------------------
    async def trigger_crawl(
        self,
        user_id: uuid.UUID,
        request: CrawlTriggerRequest,
        *,
        dispatch: bool = True,
    ) -> CrawlJob:
        """Create (or reuse) an audit target and queue a crawl job for it."""
        if request.audit_id is not None:
            audit = await self.audit_service.get_audit_for_user(request.audit_id, user_id)
        else:
            assert request.project_id and request.url  # guaranteed by the schema
            project = await ProjectService(self.session).get_user_project(
                request.project_id, user_id
            )
            from app.schemas.audit import AuditCreate

            audit = await self.audit_service.create_audit(
                user_id,
                AuditCreate(project_id=project.id, target_url=request.url, run_async=False),
            )

        method = (
            CrawlMethod.PLAYWRIGHT.value if request.force_playwright else CrawlMethod.SCRAPY.value
        )
        job = await self.crawls.create(
            audit_id=audit.id,
            url=audit.target_url,
            method=method,
            status=CrawlStatus.PENDING.value,
        )
        logger.info("crawl.queued", job_id=str(job.id), audit_id=str(audit.id), url=job.url)
        if dispatch:
            from app.tasks.crawl_tasks import dispatch_crawl_job

            await dispatch_crawl_job(job.id)
        return job

    async def run_job(self, job_id: uuid.UUID) -> CrawlOutcome:
        """Execute one crawl job end to end.

        Safe to call twice: only the worker that atomically claims the job
        (``pending`` → ``running``) performs any work.
        """
        job = await self.crawls.mark_running(job_id)
        if job is None:
            existing = await self.crawls.get_by_id(job_id)
            logger.info(
                "crawl.not_claimed",
                job_id=str(job_id),
                status=existing.status if existing else "missing",
            )
            return CrawlOutcome(
                job_id=job_id, status=existing.status if existing else "missing", claimed=False
            )

        audit = await self.audits.get_by_id(job.audit_id)
        if audit is None:  # pragma: no cover - FK makes this unreachable
            await self.crawls.mark_failed(job.id, error_message="Audit no longer exists")
            return CrawlOutcome(
                job_id=job.id, status=CrawlStatus.FAILED.value, error="audit_missing"
            )

        await self.audits.set_status(audit.id, AuditStatus.CRAWLING.value)
        await self.audits.update_domain_signals(
            audit.domain_id, crawl_status="crawling", last_crawled_at=datetime.now(tz=UTC)
        )

        try:
            return await self._execute(job, audit)
        except Exception as exc:
            return await self._handle_failure(job, audit, exc)

    async def get_job_status(self, job_id: uuid.UUID, user_id: uuid.UUID) -> CrawlStatusResponse:
        """Status envelope for polling clients."""
        job = await self.crawls.get_by_id(job_id)
        if job is None:
            raise NotFoundError("Crawl job", str(job_id))
        # Tenant check through the audit -> project -> user chain.
        audit = await self.audit_service.get_audit_for_user(job.audit_id, user_id)
        return CrawlStatusResponse(
            job=CrawlJobResponse.model_validate(job),
            audit_status=audit.status,
            audit_progress=_PROGRESS.get(audit.status, 0.0),
            is_terminal=job.status
            in {CrawlStatus.COMPLETED.value, CrawlStatus.FAILED.value, CrawlStatus.CANCELLED.value},
        )

    async def list_jobs(
        self,
        user_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 20,
        status: str | None = None,
    ) -> tuple[list[CrawlJob], int]:
        """Paginated crawl jobs across the caller's projects."""
        return await self.crawls.list_for_user(user_id, skip=skip, limit=limit, status=status)

    # -- pipeline ------------------------------------------------------------
    async def _execute(self, job: CrawlJob, audit: Audit) -> CrawlOutcome:
        from app.crawler.fetchers import get_fetcher
        from app.crawler.pipelines.cleaner import html_to_markdown
        from app.crawler.pipelines.extractor import extract_metadata

        fetcher = self.fetcher or get_fetcher(settings=self.settings)
        force_playwright = job.method == CrawlMethod.PLAYWRIGHT.value

        fetched = await fetcher.fetch(job.url, force_playwright=force_playwright)

        # 1. Structured metadata (title, JSON-LD, headings, links, hreflang...).
        metadata = extract_metadata(fetched.html, base_url=fetched.final_url or fetched.url)

        # 2. Boilerplate stripping + markdown conversion (also sanitises content).
        cleaned = html_to_markdown(fetched.html, base_url=fetched.final_url or fetched.url)
        word_count = cleaned.word_count

        # 3. Persist crawl artefacts on the audit.
        stored_html = sanitize_crawled_content(fetched.html)[:MAX_STORED_HTML_CHARS]
        await self.audits.save_crawl_artifact(
            audit.id,
            raw_html=stored_html,
            clean_markdown=cleaned.markdown,
            word_count=word_count,
            json_ld_data=metadata.json_ld_data,
        )

        # 4. Cache the domain-level technical signals.
        await self.audits.update_domain_signals(
            audit.domain_id,
            crawl_status="completed",
            last_crawled_at=datetime.now(tz=UTC),
            has_json_ld=metadata.has_json_ld,
            has_sitemap=fetched.sitemap_url is not None or metadata.has_sitemap,
            heading_structure_valid=metadata.heading_structure_valid,
            meta_description_present=metadata.has_meta_description,
            canonical_set=metadata.has_canonical,
            robots_txt_allows_crawl=fetched.robots_allowed,
            robots_txt=(fetched.robots_txt or None),
            sitemap_url=fetched.sitemap_url,
        )

        await self.audits.set_status(audit.id, AuditStatus.ANALYZING.value)

        # 5. Chunk + embed the cleaned content for retrieval.
        ingest = await self.chunks.ingest_markdown(audit.id, cleaned.markdown)

        # 6. Score with the four PCS components.
        scoring_input = build_scoring_input(
            metadata,
            markdown=cleaned.markdown,
            word_count=word_count,
            target_url=job.url,
            response_time_ms=fetched.response_time_ms,
        )
        scoring_input = dataclasses.replace(
            scoring_input,
            boilerplate_ratio=cleaned.boilerplate_ratio,
            has_lists=cleaned.has_lists,
            has_tables=cleaned.has_tables,
            avg_paragraph_words=cleaned.avg_paragraph_words,
            external_link_count=cleaned.external_link_count,
            has_sitemap=fetched.sitemap_url is not None or metadata.has_sitemap,
        )
        scores = await self.audit_service.score_audit(
            audit.id, data=scoring_input, metadata=metadata
        )

        # 7. Close out the job + audit.
        await self.crawls.mark_completed(
            job.id,
            http_status_code=fetched.status_code,
            robots_txt_allowed=fetched.robots_allowed,
            content_type=fetched.content_type,
            response_time_ms=fetched.response_time_ms,
            response_size_bytes=fetched.size_bytes,
            is_spa_detected=fetched.is_spa_detected,
            playwright_fallback_used=fetched.playwright_fallback_used,
            method=fetched.method,
        )
        await self.audit_service.mark_completed(audit.id)

        logger.info(
            "crawl.completed",
            job_id=str(job.id),
            audit_id=str(audit.id),
            method=fetched.method,
            status_code=fetched.status_code,
            chunks=ingest.chunks_created,
            word_count=word_count,
        )
        return CrawlOutcome(
            job_id=job.id,
            status=CrawlStatus.COMPLETED.value,
            chunks_created=ingest.chunks_created,
            word_count=word_count,
            pcs_score=scores.pcs,
        )

    async def _handle_failure(self, job: CrawlJob, audit: Audit, exc: Exception) -> CrawlOutcome:
        """Record the failure, decide whether a retry is still allowed."""
        error = f"{type(exc).__name__}: {exc}"
        retry_count = await self.crawls.increment_retry(job.id, error_message=error)
        can_retry = retry_count < self.settings.CRAWLER_MAX_RETRIES

        from app.crawler.utils import RobotsDisallowedError

        # A robots.txt refusal is not a transport problem: record the verdict so
        # the UI can distinguish "we were not allowed" from "the site failed".
        robots_allowed = False if isinstance(exc, RobotsDisallowedError) else None
        await self.crawls.mark_failed(
            job.id, error_message=error, robots_txt_allowed=robots_allowed
        )
        await self.audits.update_domain_signals(audit.domain_id, crawl_status="failed")

        if can_retry:
            # Re-queue the same job so the Celery retry can claim it again.
            await self.crawls.update_fields(job.id, status=CrawlStatus.PENDING.value)
        else:
            await self.audit_service.mark_failed(audit.id, error)

        logger.warning(
            "crawl.failed",
            job_id=str(job.id),
            audit_id=str(audit.id),
            url=job.url,
            retry_count=retry_count,
            will_retry=can_retry,
            error=error,
        )
        return CrawlOutcome(
            job_id=job.id,
            status=CrawlStatus.FAILED.value,
            error=error,
            should_retry=can_retry,
        )


__all__ = ["CrawlOutcome", "CrawlService"]
