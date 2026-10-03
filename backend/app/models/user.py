"""User account (shadow row mirroring a Supabase Auth identity)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, CheckConstraint, DateTime, Integer, String, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class PlanTier(StrEnum):
    """Billing tiers; credit allowances live in ``Settings.PLAN_CREDIT_LIMITS``."""

    FREE = "free"
    PRO = "pro"
    AGENCY = "agency"
    ENTERPRISE = "enterprise"


PLAN_TIER_VALUES: tuple[str, ...] = tuple(tier.value for tier in PlanTier)


class User(Base, UUIDMixin, TimestampMixin):
    """A tenant of the platform.

    Supabase owns credentials; this row owns authorisation data (plan, credits)
    and every foreign key used for tenant isolation.
    """

    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "plan_tier IN ('free', 'pro', 'agency', 'enterprise')",
            name="plan_tier_valid",
        ),
        CheckConstraint("monthly_credits_used >= 0", name="credits_used_non_negative"),
        CheckConstraint("monthly_credits_limit >= 0", name="credits_limit_non_negative"),
    )

    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(200))
    supabase_uid: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    plan_tier: Mapped[str] = mapped_column(
        String(32), default=PlanTier.FREE.value, server_default=PlanTier.FREE.value, nullable=False
    )
    monthly_credits_used: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    monthly_credits_limit: Mapped[int] = mapped_column(
        Integer, default=10, server_default="10", nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=true(), nullable=False
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    projects = relationship(
        "Project",
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        lazy="raise",
    )


__all__ = ["PLAN_TIER_VALUES", "PlanTier", "User"]
