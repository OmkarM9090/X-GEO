"""factory-boy factories and small persistence helpers.

The helpers are defined *before* the factory imports so the factory modules can
import them from this package without a circular import at module load time.
"""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession


def unique_email(prefix: str = "user") -> str:
    """Collision-free e-mail address."""
    return f"{prefix}-{uuid.uuid4().hex[:12]}@example.com"


def unique_domain() -> str:
    """Collision-free public-looking domain (never resolved by the factories)."""
    return f"https://{uuid.uuid4().hex[:10]}.example.com"


async def persist(session: AsyncSession, instance: Any) -> Any:
    """Add + flush + refresh an unpersisted factory instance."""
    session.add(instance)
    await session.flush()
    await session.refresh(instance)
    return instance


from tests.factories.project_factory import ProjectFactory  # noqa: E402
from tests.factories.user_factory import UserFactory  # noqa: E402

__all__ = ["ProjectFactory", "UserFactory", "persist", "unique_domain", "unique_email"]
