"""Declarative base, naming conventions and shared column mixins.

Models are *pure* SQLAlchemy: no business rules, no I/O, no service imports.
Every behavioural concern lives in the service layer.

Notes
-----
* ``lazy="raise"`` is used for all relationships. Accessing an unloaded
  relationship in async code raises ``MissingGreenlet`` at runtime, so failing
  loudly forces repositories to declare their eager-loading strategy
  (``selectinload``/``joinedload``) explicitly.
* ``passive_deletes=True`` pairs with ``ON DELETE CASCADE`` foreign keys so the
  database performs cascaded deletes instead of the ORM loading children.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

#: Deterministic constraint names keep Alembic autogenerate diffs stable.
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base for every ORM model."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        identifier = getattr(self, "id", None)
        return f"<{type(self).__name__} id={identifier}>"

    __str__ = __repr__


class UUIDMixin:
    """Adds a UUID primary key generated application-side."""

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


class TimestampMixin:
    """Adds timezone-aware ``created_at`` / ``updated_at`` timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


__all__ = ["NAMING_CONVENTION", "Base", "TimestampMixin", "UUIDMixin"]
