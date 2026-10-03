"""Audit — one scored analysis of a target URL."""

from __future__ import annotations

import uuid
from enum import StrEnum

from sqlalchemy import CheckConstraint, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class AuditStatus(StrEnum):
    """Audit lifecycle states."""

    QUEUED = "queued"
    CRAWLING = "crawling"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


AUDIT_STATUS_VALUES: tuple[str, ...] = tuple(status.value for status in AuditStatus)

#: PCS sub-scores, all normalised to 0..1.
SCORE_FIELDS: tuple[str, ...] = (
    "technical_readiness_score",
    "semantic_alignment_score",
    "evidentiary_density_score",
    "machine_readability_score",
    "pcs_score",
)


class Audit(Base, UUIDMixin, TimestampMixin):
    """Crawl + scoring result for a single URL.

    ``raw_html`` holds the sanitised source for reprocessing; ``clean_markdown``
    holds the boilerplate-free text that chunks are derived from.
    """

    __tablename__ = "audits"
    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'crawling', 'analyzing', 'completed', 'failed')",
            name="status_valid",
        ),
        CheckConstraint(
            "pcs_score IS NULL OR (pcs_score >= 0 AND pcs_score <= 1)",
            name="pcs_score_range",
        ),
        Index("ix_audits_project_created", "project_id", "created_at"),
        Index("ix_audits_project_status", "project_id", "status"),
        Index("ix_audits_target_url", "target_url"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    domain_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("domains.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        default=AuditStatus.QUEUED.value,
        server_default=AuditStatus.QUEUED.value,
        nullable=False,
    )

    # --- Scores (computed after analysis, 0..1) ------------------------------
    technical_readiness_score: Mapped[float | None] = mapped_column(Float)  # T(u)
    semantic_alignment_score: Mapped[float | None] = mapped_column(Float)  # S(u,q)
    evidentiary_density_score: Mapped[float | None] = mapped_column(Float)  # E(u)
    machine_readability_score: Mapped[float | None] = mapped_column(Float)  # M(u)
    pcs_score: Mapped[float | None] = mapped_column(Float)  # composite

    # --- Raw crawl data ------------------------------------------------------
    raw_html: Mapped[str | None] = mapped_column(Text)
    clean_markdown: Mapped[str | None] = mapped_column(Text)
    word_count: Mapped[int | None] = mapped_column(Integer)
    json_ld_data: Mapped[dict | list | None] = mapped_column(JSONB)
    #: Breakdown of how each sub-score was derived (kept for explainability).
    score_breakdown: Mapped[dict | None] = mapped_column(JSONB)

    error_message: Mapped[str | None] = mapped_column(Text)

    project = relationship("Project", back_populates="audits", lazy="raise")
    domain = relationship("Domain", back_populates="audits", lazy="raise")
    crawl_jobs = relationship(
        "CrawlJob",
        back_populates="audit",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )
    chunks = relationship(
        "Chunk",
        back_populates="audit",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )
    simulation_runs = relationship(
        "SimulationRun",
        back_populates="audit",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )


__all__ = ["AUDIT_STATUS_VALUES", "SCORE_FIELDS", "Audit", "AuditStatus"]
