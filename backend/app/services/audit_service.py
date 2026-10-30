"""Audit business logic: creation, retrieval and PCS scoring.

Scoring model
-------------
Four explainable sub-scores, all normalised to ``0..1``:

======================  ==========================================================
Term                    Meaning
======================  ==========================================================
``T(u)`` technical       crawlability/technical-readiness rubric (canonical, JSON-LD,
                        meta description, heading tree, sitemap, HTTPS, lang,
                        viewport, response time)
``S(u,q)`` semantic      mean best-chunk cosine similarity between tracked queries
                        and the page (retrieval based)
``E(u)`` evidentiary     density of verifiable facts (numbers, statistics, dates,
                        units, external citations, quotations)
``M(u)`` machine         structure a retrieval engine can parse (headings, lists,
                        tables, paragraph length, boilerplate ratio, JSON-LD)
======================  ==========================================================

``PCS`` is the weighted sum of the available sub-scores, re-normalised over the
components that could be computed (so a project without tracked prompts is not
punished). Weights come from ``Settings.PCS_WEIGHTS``.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.exceptions import ForbiddenError, InvalidInputError, NotFoundError, QuotaExceededError
from app.core.logging_config import get_logger
from app.core.security import check_ssrf_async, validate_url
from app.models.audit import Audit, AuditStatus
from app.models.crawl import CrawlJob, CrawlMethod, CrawlStatus
from app.models.domain import DomainCrawlStatus
from app.repositories.audit_repo import AuditRepository
from app.repositories.chunk_repo import ChunkRepository
from app.repositories.crawl_repo import CrawlRepository
from app.repositories.project_repo import ProjectRepository
from app.repositories.user_repo import UserRepository
from app.schemas.audit import AuditCreate
from app.services.project_service import ProjectService

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Regexes used by the evidentiary-density scorer (compiled once)
# ---------------------------------------------------------------------------
_NUMBER_RE = re.compile(r"\b\d[\d,.]*\b")
# The symbol form (`41%`) is not word-bounded, so `\b` only applies to the
# spelled-out variants; otherwise `63% of pages` would never be counted.
_PERCENT_RE = re.compile(r"\b\d[\d,.]*\s?(?:%|percent\b|percentage points?\b)", re.IGNORECASE)
_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")
_DATE_RE = re.compile(
    r"\b(?:\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{2,4}"
    r"|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2},?\s+\d{2,4})\b",
    re.IGNORECASE,
)
_UNIT_RE = re.compile(
    r"\b\d[\d,.]*\s?(?:kg|g|mg|km|m|cm|mm|mi|ft|in|lb|oz|ml|l|gb|mb|kb|tb|ms|s|min|h|hr|hours?|days?|weeks?|months?|years?|usd|eur|gbp|\$|€|£)\b",
    re.IGNORECASE,
)
_CITATION_RE = re.compile(r"\[[^\]]+\]\((?!#)[^)]+\)")
_QUOTE_RE = re.compile(r"(?:\u201c[^\u201d]{15,}\u201d|\"[^\"]{15,}\")")
_EXTERNAL_LINK_RE = re.compile(r"\]\((https?://[^)]+)\)")

# ---------------------------------------------------------------------------
# Technical readiness rubric (weights sum to 1.0)
# ---------------------------------------------------------------------------
TECHNICAL_WEIGHTS: dict[str, float] = {
    "https": 0.10,
    "canonical": 0.12,
    "meta_description": 0.12,
    "json_ld": 0.18,
    "heading_structure": 0.15,
    "sitemap": 0.08,
    "language": 0.07,
    "viewport": 0.08,
    "response_time": 0.10,
}

# ---------------------------------------------------------------------------
# Evidentiary density targets (per 100 words) and weights (sum to 1.0)
# ---------------------------------------------------------------------------
EVIDENTIARY_TARGETS: dict[str, float] = {
    "numbers": 4.0,
    "percentages": 0.6,
    "dates": 0.8,
    "units": 0.8,
    "citations": 1.2,
    "quotes": 0.3,
}
EVIDENTIARY_WEIGHTS: dict[str, float] = {
    "numbers": 0.22,
    "percentages": 0.16,
    "dates": 0.14,
    "units": 0.10,
    "citations": 0.22,
    "quotes": 0.16,
}

# ---------------------------------------------------------------------------
# Machine readability weights (sum to 1.0)
# ---------------------------------------------------------------------------
MACHINE_WEIGHTS: dict[str, float] = {
    "headings": 0.20,
    "lists": 0.15,
    "tables": 0.10,
    "paragraph_length": 0.15,
    "boilerplate": 0.15,
    "semantic_html": 0.10,
    "structured_data": 0.15,
}

LONG_PARAGRAPH_WORDS = 120
BOILERPLATE_RATIO_CEILING = 0.35
GOOD_RESPONSE_TIME_MS = 2000
SLOW_RESPONSE_TIME_MS = 6000


@dataclass(slots=True)
class ScoringInput:
    """Everything the scorers need, decoupled from the crawler's own types."""

    target_url: str
    markdown: str
    word_count: int
    has_json_ld: bool = False
    has_canonical: bool = False
    has_meta_description: bool = False
    heading_structure_valid: bool = False
    has_sitemap: bool = False
    has_lang: bool = False
    has_viewport: bool = False
    response_time_ms: int | None = None
    boilerplate_ratio: float | None = None
    has_lists: bool = False
    has_tables: bool = False
    avg_paragraph_words: float = 0.0
    semantic_html_score: float = 0.0
    external_link_count: int = 0


@dataclass(frozen=True, slots=True)
class ScoreResult:
    """Computed scores plus the explanation persisted with the audit."""

    technical_readiness: float | None
    semantic_alignment: float | None
    evidentiary_density: float | None
    machine_readability: float | None
    pcs: float | None
    breakdown: dict[str, Any] = field(default_factory=dict)

    def as_columns(self) -> dict[str, float | None]:
        return {
            "technical_readiness": self.technical_readiness,
            "semantic_alignment": self.semantic_alignment,
            "evidentiary_density": self.evidentiary_density,
            "machine_readability": self.machine_readability,
            "pcs": self.pcs,
        }


@dataclass(slots=True)
class AuditDetail:
    """Audit plus the related rows the detail endpoint needs."""

    audit: Audit
    crawl_jobs: list[CrawlJob]
    chunk_count: int
    embedded_chunk_count: int


def _clamp(value: float | None) -> float | None:
    if value is None:
        return None
    return max(0.0, min(1.0, float(value)))


def _per_100_words(count: int, word_count: int) -> float:
    if word_count <= 0:
        return 0.0
    return count * 100.0 / word_count


def _saturate(value: float, target: float) -> float:
    """Map ``value`` onto 0..1, reaching 1.0 at ``target``."""
    if target <= 0:
        return 0.0
    return max(0.0, min(1.0, value / target))


def build_scoring_input(
    metadata: Any,
    *,
    markdown: str,
    word_count: int,
    target_url: str,
    response_time_ms: int | None = None,
) -> ScoringInput:
    """Adapter from crawler metadata (object or mapping) to :class:`ScoringInput`."""

    def flag(name: str, default: bool = False) -> bool:
        if isinstance(metadata, dict):
            return bool(metadata.get(name, default))
        return bool(getattr(metadata, name, default))

    def number(name: str, default: float = 0.0) -> float:
        if isinstance(metadata, dict):
            value = metadata.get(name, default)
        else:
            value = getattr(metadata, name, default)
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    return ScoringInput(
        target_url=target_url,
        markdown=markdown,
        word_count=word_count,
        has_json_ld=flag("has_json_ld"),
        has_canonical=flag("has_canonical"),
        has_meta_description=flag("has_meta_description"),
        heading_structure_valid=flag("heading_structure_valid"),
        has_sitemap=flag("has_sitemap"),
        has_lang=flag("has_lang"),
        has_viewport=flag("has_viewport"),
        response_time_ms=response_time_ms,
        boilerplate_ratio=number("boilerplate_ratio", 1.0),
        has_lists=flag("has_lists"),
        has_tables=flag("has_tables"),
        avg_paragraph_words=number("avg_paragraph_words"),
        semantic_html_score=number("semantic_html_score"),
        external_link_count=int(number("external_link_count")),
    )


def compute_technical_readiness(data: ScoringInput) -> tuple[float, dict[str, Any]]:
    """Score crawlability/machine-consumability of the page (``T(u)``)."""
    checks: dict[str, bool] = {
        "https": data.target_url.startswith("https://"),
        "canonical": data.has_canonical,
        "meta_description": data.has_meta_description,
        "json_ld": data.has_json_ld,
        "heading_structure": data.heading_structure_valid,
        "sitemap": data.has_sitemap,
        "language": data.has_lang,
        "viewport": data.has_viewport,
        "response_time": (
            data.response_time_ms is not None and data.response_time_ms <= GOOD_RESPONSE_TIME_MS
        ),
    }
    score = sum(TECHNICAL_WEIGHTS[name] for name, passed in checks.items() if passed)
    breakdown = {
        "checks": checks,
        "passed": sorted(name for name, passed in checks.items() if passed),
        "failed": sorted(name for name, passed in checks.items() if not passed),
        "weights": TECHNICAL_WEIGHTS,
    }
    return _clamp(score) or 0.0, breakdown


def compute_evidentiary_density(
    markdown: str, *, word_count: int | None = None
) -> tuple[float, dict[str, Any]]:
    """Score density of verifiable facts (``E(u)``)."""
    text = markdown or ""
    words = word_count if word_count is not None else len(text.split())
    if words <= 0:
        return 0.0, {"reason": "empty_document", "counts": {}}

    counts = {
        "numbers": len(_NUMBER_RE.findall(text)),
        "percentages": len(_PERCENT_RE.findall(text)),
        "dates": len(_YEAR_RE.findall(text)) + len(_DATE_RE.findall(text)),
        "units": len(_UNIT_RE.findall(text)),
        "citations": len(_CITATION_RE.findall(text)),
        "quotes": len(_QUOTE_RE.findall(text)),
    }
    densities = {name: _per_100_words(count, words) for name, count in counts.items()}
    components = {
        name: _saturate(densities[name], EVIDENTIARY_TARGETS[name]) for name in EVIDENTIARY_TARGETS
    }
    score = sum(EVIDENTIARY_WEIGHTS[name] * components[name] for name in EVIDENTIARY_WEIGHTS)
    breakdown = {
        "counts": counts,
        "per_100_words": {name: round(value, 3) for name, value in densities.items()},
        "targets": EVIDENTIARY_TARGETS,
        "components": {name: round(value, 3) for name, value in components.items()},
    }
    return _clamp(score) or 0.0, breakdown


def compute_machine_readability(data: ScoringInput) -> tuple[float, dict[str, Any]]:
    """Score how easily a retrieval engine can parse the content (``M(u)``)."""
    markdown = data.markdown or ""
    boilerplate_ratio = data.boilerplate_ratio if data.boilerplate_ratio is not None else 1.0
    components = {
        "headings": (
            1.0 if data.heading_structure_valid and re.search(r"^#{1,6}\s", markdown, re.M) else 0.0
        ),
        "lists": 1.0 if data.has_lists else 0.0,
        "tables": 1.0 if data.has_tables else 0.0,
        "paragraph_length": _saturate(
            max(0.0, (LONG_PARAGRAPH_WORDS - data.avg_paragraph_words) / LONG_PARAGRAPH_WORDS), 0.6
        ),
        "boilerplate": 1.0 - _saturate(boilerplate_ratio, BOILERPLATE_RATIO_CEILING),
        "semantic_html": _saturate(data.semantic_html_score, 0.6),
        "structured_data": 1.0 if data.has_json_ld else 0.0,
    }
    score = sum(MACHINE_WEIGHTS[name] * value for name, value in components.items())
    breakdown = {
        "components": {name: round(value, 3) for name, value in components.items()},
        "boilerplate_ratio": round(boilerplate_ratio, 3),
        "avg_paragraph_words": round(data.avg_paragraph_words, 1),
    }
    return _clamp(score) or 0.0, breakdown


def compute_pcs(
    *,
    technical: float | None,
    semantic: float | None,
    evidentiary: float | None,
    machine: float | None,
    weights: dict[str, float],
) -> tuple[float | None, dict[str, Any]]:
    """Weighted composite, re-normalised over the available sub-scores."""
    available = {
        "technical": technical,
        "semantic": semantic,
        "evidentiary": evidentiary,
        "machine_readability": machine,
    }
    present = {name: value for name, value in available.items() if value is not None}
    if not present:
        return None, {"reason": "no_components"}

    total_weight = sum(weights[name] for name in present)
    if total_weight <= 0:  # pragma: no cover - guarded by settings validation
        return None, {"reason": "no_weights"}
    composite = sum(weights[name] * value for name, value in present.items()) / total_weight
    breakdown = {
        "weights": weights,
        "components": {name: round(value, 4) for name, value in present.items()},
        "missing": sorted(set(available) - set(present)),
        "effective_weight": round(total_weight, 4),
    }
    return _clamp(composite), breakdown


class AuditService:
    """Audit use-cases."""

    def __init__(self, session: AsyncSession, *, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.audits = AuditRepository(session)
        self.crawls = CrawlRepository(session)
        self.chunks = ChunkRepository(session)
        self.projects = ProjectRepository(session)
        self.users = UserRepository(session)

    # -- creation ------------------------------------------------------------
    def _assert_within_project(self, project_domain_url: str, target_url: str) -> None:
        """Only allow auditing the project's own site (no open proxy)."""
        from urllib.parse import urlparse

        project_host = (urlparse(project_domain_url).hostname or "").lower()
        target_host = (urlparse(target_url).hostname or "").lower()
        if not project_host or not target_host:
            raise InvalidInputError("Both the project domain and the target URL need a host")
        if target_host != project_host and not target_host.endswith(f".{project_host}"):
            raise InvalidInputError(
                f"Target host {target_host!r} does not belong to project domain {project_host!r}"
            )

    async def create_audit(self, user_id: uuid.UUID, data: AuditCreate) -> Audit:
        """Validate the target, consume a credit, persist the audit and queue it."""
        project = await ProjectService(self.session).get_user_project(data.project_id, user_id)

        target_url = validate_url(data.target_url)
        self._assert_within_project(project.domain_url, target_url)
        await check_ssrf_async(target_url)

        if not await self.users.consume_credits(user_id, 1):
            raise QuotaExceededError("Monthly audit credit limit reached for your plan")

        domain = await self.audits.get_or_create_domain(
            project_id=project.id, url=self._origin_of(target_url)
        )
        audit = await self.audits.create(
            project_id=project.id,
            domain_id=domain.id,
            target_url=target_url,
            status=AuditStatus.QUEUED.value,
        )
        if data.tracked_prompts:
            created = await self.audits.upsert_prompts(project.id, data.tracked_prompts)
            logger.info("audit.prompts_registered", project_id=str(project.id), created=created)

        job = await self.crawls.create(
            audit_id=audit.id,
            url=target_url,
            method=CrawlMethod.SCRAPY.value,
            status=CrawlStatus.PENDING.value,
        )
        logger.info(
            "audit.created",
            audit_id=str(audit.id),
            project_id=str(project.id),
            target_url=target_url,
        )

        if data.run_async:
            from app.tasks.crawl_tasks import dispatch_crawl_job

            await dispatch_crawl_job(job.id)
        return audit

    @staticmethod
    def _origin_of(url: str) -> str:
        from urllib.parse import urlparse

        parsed = urlparse(url)
        host = parsed.hostname or ""
        if parsed.port and parsed.port not in (80, 443):
            host = f"{host}:{parsed.port}"
        return f"{parsed.scheme}://{host}"

    # -- reads ---------------------------------------------------------------
    async def get_audit_for_user(self, audit_id: uuid.UUID, user_id: uuid.UUID) -> Audit:
        """Fetch an audit, enforcing tenant ownership."""
        audit = await self.audits.get_for_user(audit_id, user_id)
        if audit is None:
            # Distinguish "does not exist" (404) from "belongs to another tenant"
            # (403) so that the logs record cross-tenant access attempts.
            exists = await self.audits.get_by_id(audit_id)
            if exists is None:
                raise NotFoundError("Audit", str(audit_id))
            logger.warning(
                "audit.tenant_violation",
                audit_id=str(audit_id),
                project_id=str(exists.project_id),
                requester_id=str(user_id),
            )
            raise ForbiddenError("Not authorized to access this audit")
        return audit

    async def get_audit_detail(self, audit_id: uuid.UUID, user_id: uuid.UUID) -> AuditDetail:
        """Audit + crawl history + chunk statistics."""
        audit = await self.get_audit_for_user(audit_id, user_id)
        jobs = await self.audits.list_jobs(audit.id)
        return AuditDetail(
            audit=audit,
            crawl_jobs=jobs,
            chunk_count=await self.chunks.count_for_audit(audit.id),
            embedded_chunk_count=await self.chunks.count_embedded_for_audit(audit.id),
        )

    async def list_audits(
        self,
        user_id: uuid.UUID,
        *,
        project_id: uuid.UUID | None = None,
        status: str | None = None,
        skip: int = 0,
        limit: int = 20,
    ) -> tuple[list[Audit], int]:
        """Paginated audits, scoped to one project or the caller's whole account."""
        if project_id is not None:
            await ProjectService(self.session).get_user_project(project_id, user_id)
            return await self.audits.list_for_project(
                project_id, skip=skip, limit=limit, status=status
            )
        return await self.audits.list_for_user(user_id, skip=skip, limit=limit, status=status)

    async def delete_audit(self, audit_id: uuid.UUID, user_id: uuid.UUID) -> None:
        """Delete an audit and its cascading rows."""
        audit = await self.get_audit_for_user(audit_id, user_id)
        await self.audits.delete(audit.id)
        logger.info("audit.deleted", audit_id=str(audit_id), user_id=str(user_id))

    # -- scoring -------------------------------------------------------------
    async def score_audit(
        self,
        audit_id: uuid.UUID,
        *,
        data: ScoringInput,
        metadata: Any = None,
    ) -> ScoreResult:
        """Compute and persist every sub-score plus the explainability breakdown."""
        from app.services.chunk_service import ChunkService

        technical, technical_breakdown = compute_technical_readiness(data)
        evidentiary, evidentiary_breakdown = compute_evidentiary_density(
            data.markdown, word_count=data.word_count
        )
        machine, machine_breakdown = compute_machine_readability(data)
        semantic = await ChunkService(self.session, settings=self.settings).alignment_score(
            audit_id, await self._tracked_queries(audit_id)
        )
        pcs, pcs_breakdown = compute_pcs(
            technical=technical,
            semantic=semantic,
            evidentiary=evidentiary,
            machine=machine,
            weights=self.settings.PCS_WEIGHTS,
        )

        breakdown = {
            "computed_at": datetime.now(tz=UTC).isoformat(),
            "page": {
                "url": getattr(metadata, "url", data.target_url),
                "title": getattr(metadata, "title", None),
                "meta_description": getattr(metadata, "meta_description", None),
                "canonical_url": getattr(metadata, "canonical_url", None),
                "lang": getattr(metadata, "lang", None),
                "json_ld_types": list(getattr(metadata, "json_ld_types", ()) or ()),
                "heading_count": len(getattr(metadata, "headings", ()) or ()),
            },
            "technical": technical_breakdown,
            "semantic": {
                "score": round(semantic, 4) if semantic is not None else None,
                "queries": len(await self._tracked_queries(audit_id)),
                "method": "max cosine similarity per tracked query, averaged",
            },
            "evidentiary": evidentiary_breakdown,
            "machine_readability": machine_breakdown,
            "pcs": pcs_breakdown,
            "notes": (
                None if self.settings.embeddings_enabled else "deterministic dev embeddings in use"
            ),
        }

        result = ScoreResult(
            technical_readiness=technical,
            semantic_alignment=semantic,
            evidentiary_density=evidentiary,
            machine_readability=machine,
            pcs=pcs,
            breakdown=breakdown,
        )
        await self.audits.save_scores(
            audit_id,
            technical_readiness_score=result.technical_readiness,
            semantic_alignment_score=result.semantic_alignment,
            evidentiary_density_score=result.evidentiary_density,
            machine_readability_score=result.machine_readability,
            pcs_score=result.pcs,
            score_breakdown=result.breakdown,
        )
        logger.info(
            "audit.scored",
            audit_id=str(audit_id),
            pcs=round(pcs, 4) if pcs is not None else None,
        )
        return result

    async def _tracked_queries(self, audit_id: uuid.UUID) -> list[str]:
        audit = await self.audits.get_by_id(audit_id)
        if audit is None:
            return []
        return await self.audits.list_prompt_texts(audit.project_id)

    async def mark_completed(self, audit_id: uuid.UUID) -> None:
        """Move an audit to its terminal success state."""
        await self.audits.set_status(audit_id, AuditStatus.COMPLETED.value, error_message=None)

    async def mark_failed(self, audit_id: uuid.UUID, reason: str) -> None:
        """Move an audit to its terminal failure state."""
        await self.audits.set_status(
            audit_id, AuditStatus.FAILED.value, error_message=reason[:2000]
        )

    async def update_domain_signals(self, domain_id: uuid.UUID, **signals: Any) -> None:
        """Cache technical signals on the domain row."""
        await self.audits.update_domain_signals(domain_id, **signals)

    async def mark_domain_crawling(self, domain_id: uuid.UUID) -> None:
        await self.audits.update_domain_signals(
            domain_id, crawl_status=DomainCrawlStatus.CRAWLING.value
        )


__all__ = [
    "AuditDetail",
    "AuditService",
    "EVIDENTIARY_TARGETS",
    "EVIDENTIARY_WEIGHTS",
    "MACHINE_WEIGHTS",
    "ScoreResult",
    "ScoringInput",
    "TECHNICAL_WEIGHTS",
    "build_scoring_input",
    "compute_evidentiary_density",
    "compute_machine_readability",
    "compute_pcs",
    "compute_technical_readiness",
]
