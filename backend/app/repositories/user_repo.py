"""Data access for :class:`~app.models.user.User`."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.user import PlanTier, User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """Queries scoped to the ``users`` table."""

    default_ordering = ("created_at",)

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> User | None:
        """Look a user up by (case-insensitive) e-mail address."""
        query = select(User).where(func.lower(User.email) == email.strip().lower()).limit(1)
        return (await self.session.execute(query)).scalar_one_or_none()

    async def get_by_supabase_uid(self, supabase_uid: str) -> User | None:
        """Look a user up by their Supabase identity."""
        query = select(User).where(User.supabase_uid == str(supabase_uid)).limit(1)
        return (await self.session.execute(query)).scalar_one_or_none()

    async def create_from_identity(
        self,
        *,
        supabase_uid: str,
        email: str,
        full_name: str | None = None,
        plan_tier: str = PlanTier.FREE.value,
        monthly_credits_limit: int | None = None,
    ) -> User:
        """Create the local shadow row for a Supabase identity."""
        settings = get_settings()
        return await self.create(
            supabase_uid=str(supabase_uid),
            email=email.strip().lower(),
            full_name=full_name,
            plan_tier=plan_tier,
            monthly_credits_limit=(
                monthly_credits_limit
                if monthly_credits_limit is not None
                else settings.plan_credit_limit(plan_tier)
            ),
        )

    async def set_last_seen(self, user_id: UUID, *, when: datetime | None = None) -> None:
        """Record activity (used by JIT provisioning on authenticated requests)."""
        await self.session.execute(
            update(User).where(User.id == user_id).values(last_seen_at=when or datetime.now(tz=UTC))
        )

    async def sync_profile(
        self, user: User, *, email: str | None = None, full_name: str | None = None
    ) -> User:
        """Refresh locally cached profile fields from the identity provider."""
        changed = False
        if email and user.email != email.lower():
            user.email = email.lower()
            changed = True
        if full_name and user.full_name != full_name:
            user.full_name = full_name
            changed = True
        if changed:
            await self.session.flush()
        return user

    async def credits_remaining(self, user_id: UUID) -> int:
        """Remaining monthly credits for a user (never negative)."""
        query = select(User.monthly_credits_limit - User.monthly_credits_used).where(
            User.id == user_id
        )
        value = (await self.session.execute(query)).scalar_one_or_none()
        return max(0, int(value)) if value is not None else 0

    async def consume_credits(self, user_id: UUID, amount: int = 1) -> bool:
        """Atomically consume credits; returns False when the quota is exhausted.

        The ``UPDATE ... WHERE used + amount <= limit`` guard makes this safe
        under concurrency (no read-modify-write race).
        """
        if amount <= 0:
            return True
        result = await self.session.execute(
            update(User)
            .where(
                User.id == user_id, User.monthly_credits_used + amount <= User.monthly_credits_limit
            )
            .values(monthly_credits_used=User.monthly_credits_used + amount)
            .returning(User.id)
        )
        await self.session.flush()
        return result.scalar_one_or_none() is not None

    async def set_plan(
        self, user_id: UUID, plan_tier: str, *, credits_limit: int | None = None
    ) -> None:
        """Change a user's plan and (optionally) its allowance."""
        settings = get_settings()
        values: dict[str, Any] = {"plan_tier": plan_tier}
        values["monthly_credits_limit"] = (
            credits_limit if credits_limit is not None else settings.plan_credit_limit(plan_tier)
        )
        await self.session.execute(update(User).where(User.id == user_id).values(**values))

    async def list_active(self, *, skip: int = 0, limit: int = 100) -> list[User]:
        """Active users page (admin/reporting helper)."""
        query = (
            select(User)
            .where(User.is_active.is_(True))
            .order_by(User.created_at)
            .offset(skip)
            .limit(limit)
        )
        return list((await self.session.execute(query)).scalars().all())


__all__ = ["UserRepository"]
