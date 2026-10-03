"""TrackedPrompt — a user query monitored across generative engines."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    true,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class PromptCategory(StrEnum):
    """Funnel stage a prompt belongs to."""

    INFORMATIONAL = "informational"
    CONSIDERATION = "consideration"
    TRANSACTIONAL = "transactional"
    NAVIGATIONAL = "navigational"


PROMPT_CATEGORY_VALUES: tuple[str, ...] = tuple(category.value for category in PromptCategory)


class TrackedPrompt(Base, UUIDMixin, TimestampMixin):
    """A natural-language query the customer cares about being cited for."""

    __tablename__ = "tracked_prompts"
    __table_args__ = (
        UniqueConstraint("project_id", "query_text", name="project_query"),
        CheckConstraint(
            "category IN ('informational', 'consideration', 'transactional', 'navigational')",
            name="category_valid",
        ),
        Index("ix_tracked_prompts_project_active", "project_id", "is_active"),
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(
        String(32),
        default=PromptCategory.INFORMATIONAL.value,
        server_default=PromptCategory.INFORMATIONAL.value,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False
    )
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    project = relationship("Project", back_populates="tracked_prompts", lazy="raise")
    simulation_runs = relationship(
        "SimulationRun",
        back_populates="prompt",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )


__all__ = ["PROMPT_CATEGORY_VALUES", "PromptCategory", "TrackedPrompt"]
