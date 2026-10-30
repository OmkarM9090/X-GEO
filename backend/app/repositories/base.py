"""Generic async CRUD repository.

Every SQL statement in the application lives in the repository layer; services
never build queries and routes never touch the session. Subclasses bound the
generic to a concrete model and add domain-specific queries::

    class ProjectRepository(BaseRepository[Project]):
        def __init__(self, session: AsyncSession) -> None:
            super().__init__(Project, session)
"""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Sequence
from typing import Any, Generic, TypeVar, cast

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, insert, select
from sqlalchemy import update as sa_update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import ColumnElement

from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)

#: Ordering applied when a repository does not declare its own.
DEFAULT_ORDERING: tuple[str, ...] = ("created_at", "id")


class BaseRepository(Generic[ModelType]):
    """Reusable CRUD operations for a single SQLAlchemy model."""

    #: Column names used by :meth:`get_all` when no explicit ordering is given.
    default_ordering: tuple[str, ...] = DEFAULT_ORDERING

    def __init__(self, model: type[ModelType], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    @property
    def _id_column(self) -> Any:
        """Primary-key column of ``model``.

        ``ModelType`` is a bare ``TypeVar``, so mypy cannot know that every
        mapped class exposes ``id``; this accessor keeps the base class honest.
        """
        return cast(Any, self.model).id

    # -- reads ---------------------------------------------------------------
    async def get_by_id(self, id: uuid.UUID) -> ModelType | None:
        """Fetch one row by primary key."""
        return await self.session.get(self.model, id)

    async def get_by_id_for_update(self, id: uuid.UUID) -> ModelType | None:
        """Fetch one row and lock it (``SELECT ... FOR UPDATE``)."""
        result = await self.session.execute(
            select(self.model).where(self._id_column == id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_one(self, **filters: Any) -> ModelType | None:
        """Fetch the first row matching ``filters``."""
        query = self._apply_filters(select(self.model), filters)
        result = await self.session.execute(query.limit(1))
        return result.scalar_one_or_none()

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 50,
        order_by: Sequence[str | ColumnElement[Any]] | None = None,
        **filters: Any,
    ) -> Sequence[ModelType]:
        """Fetch a page of rows matching ``filters``."""
        query = self._apply_filters(select(self.model), filters)
        query = self._apply_ordering(query, order_by).offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def list_by_ids(self, ids: Iterable[uuid.UUID]) -> Sequence[ModelType]:
        """Fetch every row whose primary key is in ``ids``."""
        id_list = list(ids)
        if not id_list:
            return []
        result = await self.session.execute(select(self.model).where(self._id_column.in_(id_list)))
        return result.scalars().all()

    async def count(self, **filters: Any) -> int:
        """Count rows matching ``filters``."""
        query = self._apply_filters(select(func.count()).select_from(self.model), filters)
        return int((await self.session.execute(query)).scalar_one())

    async def exists(self, **filters: Any) -> bool:
        """Cheap existence check."""
        query = self._apply_filters(select(self._id_column), filters).limit(1)
        return (await self.session.execute(query)).scalar_one_or_none() is not None

    async def paginate(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
        order_by: Sequence[str] | None = None,
        **filters: Any,
    ) -> tuple[Sequence[ModelType], int]:
        """Return ``(items, total)`` for a list endpoint."""
        items = await self.get_all(skip=skip, limit=limit, order_by=order_by, **filters)
        total = await self.count(**filters)
        return items, total

    # -- writes --------------------------------------------------------------
    async def create(self, **kwargs: Any) -> ModelType:
        """Insert one row and return the refreshed instance."""
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def create_many(self, rows: Iterable[dict[str, Any]]) -> int:
        """Bulk insert rows, returning the number of inserted rows."""
        payload = list(rows)
        if not payload:
            return 0
        await self.session.execute(insert(self.model), payload)
        await self.session.flush()
        return len(payload)

    async def update(self, id: uuid.UUID, **kwargs: Any) -> ModelType | None:
        """Patch one row by primary key; returns ``None`` when it does not exist."""
        instance = await self.get_by_id(id)
        if instance is None:
            return None
        for key, value in kwargs.items():
            if not hasattr(instance, key):
                raise ValueError(f"{type(self.model).__name__} has no attribute '{key}'")
            setattr(instance, key, value)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def update_fields(self, id: uuid.UUID, **values: Any) -> int:
        """Single-statement UPDATE (no ORM round-trip); returns affected rows."""
        if not values:
            return 0
        result = await self.session.execute(
            sa_update(self.model).where(self._id_column == id).values(**values)
        )
        await self.session.flush()
        return int(result.rowcount or 0)

    async def upsert(
        self,
        *,
        index_elements: Sequence[str],
        values: dict[str, Any],
        update_columns: Sequence[str] | None = None,
    ) -> ModelType | None:
        """Insert-or-update in one statement (PostgreSQL ``ON CONFLICT``)."""
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        stmt = pg_insert(self.model).values(**values)
        update_map = {
            column: getattr(stmt.excluded, column)
            for column in (update_columns or [key for key in values if key not in index_elements])
        }
        if update_map:
            stmt = stmt.on_conflict_do_update(index_elements=list(index_elements), set_=update_map)
        else:
            stmt = stmt.on_conflict_do_nothing(index_elements=list(index_elements))
        await self.session.execute(stmt)
        await self.session.flush()
        # `populate_existing` so the returned instance reflects the UPDATE even
        # when the row was already loaded in this session's identity map.
        filters = {key: values[key] for key in index_elements}
        query = self._apply_filters(select(self.model), filters).execution_options(
            populate_existing=True
        )
        return (await self.session.execute(query)).scalars().first()

    async def commit(self) -> None:
        """Commit the current transaction (callers usually rely on ``get_db``)."""
        await self.session.commit()

    async def delete(self, id: uuid.UUID) -> bool:
        """Delete one row by primary key."""
        instance = await self.get_by_id(id)
        if instance is None:
            return False
        await self.session.delete(instance)
        await self.session.flush()
        return True

    async def delete_where(self, **filters: Any) -> int:
        """Bulk delete by filters; returns the number of deleted rows."""
        query = self._apply_filters(sa_delete(self.model), filters)
        result = await self.session.execute(query)
        await self.session.flush()
        return int(result.rowcount or 0)

    # -- helpers -------------------------------------------------------------
    def _resolve_columns(self, filters: dict[str, Any]) -> dict[str, Any]:
        for key in filters:
            if not hasattr(self.model, key):
                raise ValueError(
                    f"{self.model.__name__} has no attribute '{key}' used as a query filter"
                )
        return {key: value for key, value in filters.items() if value is not None}

    def _apply_filters(self, query: Any, filters: dict[str, Any]) -> Any:
        for key, value in self._resolve_columns(filters).items():
            query = query.where(getattr(self.model, key) == value)
        return query

    def _apply_ordering(
        self, query: Any, order_by: Sequence[str | ColumnElement[Any]] | None
    ) -> Any:
        columns: list[Any] = []
        for item in order_by if order_by is not None else self.default_ordering:
            if isinstance(item, str):
                if not hasattr(self.model, item):
                    raise ValueError(f"{self.model.__name__} has no attribute '{item}' to order by")
                columns.append(getattr(self.model, item))
            else:
                columns.append(item)
        # Deterministic tie-breaker keeps pagination stable.
        if columns:
            id_column = getattr(self.model, "id", None)
            if id_column is not None:
                columns.append(id_column)
        return query.order_by(*columns) if columns else query

    @staticmethod
    def is_integrity_error(exc: Exception, *, constraint: str | None = None) -> bool:
        """True when ``exc`` is a unique/foreign-key violation."""
        if not isinstance(exc, IntegrityError):
            return False
        if constraint is None:
            return True
        return constraint in str(exc.orig)


__all__ = ["DEFAULT_ORDERING", "BaseRepository", "ModelType"]
