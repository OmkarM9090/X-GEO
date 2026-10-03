"""CitationLog — a single cited URL inside one simulated engine response.

Phase 3 populates this table; the schema ships now so the PWC (position-weighted
citation) scoring from Aggarwal et al. can be computed without further
migrations.
"""

from __future__ import annotations

import uuid

from sqlalchemy import (
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class CitationLog(Base, UUIDMixin, TimestampMixin):
    """One citation: which URL, in which position, inside which sentence."""

    __tablename__ = "citation_logs"
    __table_args__ = (
        UniqueConstraint("simulation_run_id", "citation_position", name="run_position"),
        CheckConstraint("citation_position >= 1", name="citation_position_positive"),
        CheckConstraint("word_count IS NULL OR word_count >= 0", name="word_count_non_negative"),
        CheckConstraint(
            "position_weight IS NULL OR (position_weight >= 0 AND position_weight <= 1)",
            name="position_weight_range",
        ),
        Index("ix_citation_logs_cited_url", "cited_url"),
        Index("ix_citation_logs_run", "simulation_run_id", "citation_position"),
    )

    simulation_run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("simulation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    cited_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    citation_position: Mapped[int] = mapped_column(Integer, nullable=False)
    sentence_text: Mapped[str | None] = mapped_column(Text)
    word_count: Mapped[int | None] = mapped_column(Integer)
    #: True when the citation belongs to the audited domain.
    is_target_url: Mapped[bool] = mapped_column(
        default=False, server_default="false", nullable=False
    )

    # --- PWC scoring (Aggarwal position-weighted citation formula) -----------
    position_weight: Mapped[float | None] = mapped_column(Float)
    imp_pwc: Mapped[float | None] = mapped_column(Float)

    simulation_run = relationship("SimulationRun", back_populates="citations", lazy="raise")


__all__ = ["CitationLog"]
