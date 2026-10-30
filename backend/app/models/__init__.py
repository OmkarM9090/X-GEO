"""SQLAlchemy models.

Importing this package registers every table on ``Base.metadata`` — Alembic's
autogenerate and ``create_all`` both depend on it, so *always* import from here
(never from the individual modules) outside of the model package itself.
"""

from app.models.audit import AUDIT_STATUS_VALUES, SCORE_FIELDS, Audit, AuditStatus
from app.models.base import NAMING_CONVENTION, Base, TimestampMixin, UUIDMixin
from app.models.chunk import EMBEDDING_DIMENSIONS, Chunk
from app.models.citation_log import CitationLog
from app.models.crawl import (
    CRAWL_METHOD_VALUES,
    CRAWL_STATUS_VALUES,
    CrawlJob,
    CrawlMethod,
    CrawlStatus,
)
from app.models.domain import DOMAIN_CRAWL_STATUS_VALUES, Domain, DomainCrawlStatus
from app.models.project import Project
from app.models.simulation_run import (
    NLI_LABEL_VALUES,
    SIMULATION_OUTCOME_VALUES,
    NliLabel,
    SimulationOutcome,
    SimulationRun,
)
from app.models.tracked_prompt import PROMPT_CATEGORY_VALUES, PromptCategory, TrackedPrompt
from app.models.user import PLAN_TIER_VALUES, PlanTier, User

__all__ = [
    "AUDIT_STATUS_VALUES",
    "Audit",
    "AuditStatus",
    "Base",
    "CRAWL_METHOD_VALUES",
    "CRAWL_STATUS_VALUES",
    "Chunk",
    "CitationLog",
    "CrawlJob",
    "CrawlMethod",
    "CrawlStatus",
    "DOMAIN_CRAWL_STATUS_VALUES",
    "Domain",
    "DomainCrawlStatus",
    "EMBEDDING_DIMENSIONS",
    "NAMING_CONVENTION",
    "NLI_LABEL_VALUES",
    "NliLabel",
    "PLAN_TIER_VALUES",
    "PROMPT_CATEGORY_VALUES",
    "PlanTier",
    "Project",
    "PromptCategory",
    "SCORE_FIELDS",
    "SIMULATION_OUTCOME_VALUES",
    "SimulationOutcome",
    "SimulationRun",
    "TimestampMixin",
    "TrackedPrompt",
    "UUIDMixin",
    "User",
]
