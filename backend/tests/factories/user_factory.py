"""User factory."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import factory

from app.models.user import PlanTier, User
from tests.factories import unique_email


class UserFactory(factory.Factory):
    """Build an (unpersisted) :class:`~app.models.user.User`."""

    class Meta:
        model = User

    id = factory.LazyFunction(uuid.uuid4)
    email = factory.LazyFunction(unique_email)
    full_name = factory.Faker("name")
    supabase_uid = factory.LazyFunction(lambda: f"supabase-{uuid.uuid4()}")
    plan_tier = PlanTier.FREE.value
    monthly_credits_used = 0
    monthly_credits_limit = 10
    is_active = True
    created_at = factory.LazyFunction(lambda: datetime.now(tz=UTC))
    updated_at = factory.LazyFunction(lambda: datetime.now(tz=UTC))


__all__ = ["UserFactory"]
