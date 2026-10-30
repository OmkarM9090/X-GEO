"""SimulationRun — one Monte-Carlo sample of a prompt against an engine.

Phase 3 populates this table; the schema ships now so migrations, retrieval and
API contracts are stable ahead of the simulation worker.
"""

from __future__ import annotations

import uuid
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    false,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class SimulationOutcome(StrEnum):
    """Terminal state of a simulation run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


SIMULATION_OUTCOME_VALUES: tuple[str, ...] = tuple(outcome.value for outcome in SimulationOutcome)


class NliLabel(StrEnum):
    """Natural-language-inference verdict for a citation (Phase 4)."""

    ENTAILMENT = "entailment"
    CONTRADICTION = "contradiction"
    NEUTRAL = "neutral"


NLI_LABEL_VALUES: tuple[str, ...] = tuple(label.value for label in NliLabel)


class SimulationRun(Base, UUIDMixin, TimestampMixin):
    """A single stochastic sample: (audit, prompt, temperature, run_index)."""

    __tablename__ = "simulation_runs"
    __table_args__ = (
        UniqueConstraint(
            "audit_id", "prompt_id", "temperature", "run_index", name="audit_prompt_temp_run"
        ),
        CheckConstraint("temperature >= 0 AND temperature <= 2", name="temperature_range"),
        CheckConstraint("run_index >= 1", name="run_index_positive"),
        CheckConstraint(
            "status IN ('pending', 'running', 'completed', 'failed')", name="status_valid"
        ),
        CheckConstraint(
            "nli_label IS NULL OR nli_label IN ('entailment', 'contradiction', 'neutral')",
            name="nli_label_valid",
        ),
        Index("ix_simulation_runs_audit_prompt", "audit_id", "prompt_id"),
        Index("ix_simulation_runs_cited", "target_url_cited"),
    )

    audit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    prompt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tracked_prompts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    engine: Mapped[str] = mapped_column(
        String(32), default="chatgpt", server_default="chatgpt", nullable=False
    )
    model_name: Mapped[str | None] = mapped_column(String(120))
    temperature: Mapped[float] = mapped_column(Float, nullable=False)
    run_index: Mapped[int] = mapped_column(Integer, nullable=False)  # 1..N (N=10 by default)
    status: Mapped[str] = mapped_column(
        String(32),
        default=SimulationOutcome.PENDING.value,
        server_default=SimulationOutcome.PENDING.value,
        nullable=False,
    )

    generated_response: Mapped[str | None] = mapped_column(Text)
    cited_urls: Mapped[list | None] = mapped_column(JSONB)
    target_url_cited: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=false(), nullable=False
    )

    # --- NLI verification (Phase 4) -----------------------------------------
    nli_entailment_score: Mapped[float | None] = mapped_column(Float)
    nli_label: Mapped[str | None] = mapped_column(String(32))

    error_message: Mapped[str | None] = mapped_column(Text)

    audit = relationship("Audit", back_populates="simulation_runs", lazy="raise")
    prompt = relationship("TrackedPrompt", back_populates="simulation_runs", lazy="raise")
    citations = relationship(
        "CitationLog",
        back_populates="simulation_run",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )


__all__ = [
    "NLI_LABEL_VALUES",
    "SIMULATION_OUTCOME_VALUES",
    "NliLabel",
    "SimulationOutcome",
    "SimulationRun",
]
