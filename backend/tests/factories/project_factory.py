"""Project factory."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import factory

from app.models.project import Project
from tests.factories import unique_domain


class ProjectFactory(factory.Factory):
    """Build an (unpersisted) :class:`~app.models.project.Project`.

    ``user_id`` must be supplied by the caller unless a ``user`` instance is
    passed as ``user_id=user.id``.
    """

    class Meta:
        model = Project

    id = factory.LazyFunction(uuid.uuid4)
    user_id = factory.LazyFunction(uuid.uuid4)
    name = factory.Faker("company")
    domain_url = factory.LazyFunction(unique_domain)
    description = factory.Faker("sentence")
    is_active = True
    created_at = factory.LazyFunction(lambda: datetime.now(tz=UTC))
    updated_at = factory.LazyFunction(lambda: datetime.now(tz=UTC))


__all__ = ["ProjectFactory"]
