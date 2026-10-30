"""Data access for :class:`~app.models.chunk.Chunk`.

Holds the pgvector similarity search and the ``tsvector`` full-text search used
by semantic-alignment scoring and hybrid retrieval.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from app.models.audit import Audit
from app.models.chunk import Chunk
from app.repositories.base import BaseRepository

#: Weight applied to the tsvector fields when ranking full-text hits.
FULL_TEXT_CONFIG = "english"


class ChunkRepository(BaseRepository[Chunk]):
    """Queries scoped to the ``chunks`` table."""

    default_ordering = ("chunk_index",)

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Chunk, session)

    # -- reads ---------------------------------------------------------------
    async def list_for_audit(
        self, audit_id: UUID, *, skip: int = 0, limit: int = 100, include_embeddings: bool = False
    ) -> tuple[list[Chunk], int]:
        """Paginated chunks of an audit, in document order.

        The 1536-float ``embedding`` column is deferred unless
        ``include_embeddings=True``; use ``Chunk.is_embedded`` for the
        "is it embedded?" flag instead of touching the vector.
        """
        items_query = (
            select(Chunk)
            .where(Chunk.audit_id == audit_id)
            .order_by(Chunk.chunk_index)
            .offset(skip)
            .limit(limit)
        )
        if not include_embeddings:
            items_query = items_query.options(defer(Chunk.embedding))
        count_query = select(func.count()).select_from(Chunk).where(Chunk.audit_id == audit_id)
        items = list((await self.session.execute(items_query)).scalars().all())
        total = int((await self.session.execute(count_query)).scalar_one())
        return items, total

    async def count_for_audit(self, audit_id: UUID) -> int:
        """Number of chunks belonging to an audit."""
        return await self.count(audit_id=audit_id)

    async def count_embedded_for_audit(self, audit_id: UUID) -> int:
        """Number of chunks with a stored embedding."""
        query = (
            select(func.count())
            .select_from(Chunk)
            .where(Chunk.audit_id == audit_id, Chunk.is_embedded.is_(True))
        )
        return int((await self.session.execute(query)).scalar_one())

    async def iter_audit_content(self, audit_id: UUID, *, limit: int = 1000) -> list[str]:
        """Chunk texts of an audit (used for scoring and citation grounding)."""
        query = (
            select(Chunk.content)
            .where(Chunk.audit_id == audit_id)
            .order_by(Chunk.chunk_index)
            .limit(limit)
        )
        return list((await self.session.execute(query)).scalars().all())

    # -- vector / full-text search -------------------------------------------
    def _scope_query(self, audit_id: UUID | None, project_id: UUID | None) -> Any:
        query = select(Chunk)
        if project_id is not None:
            query = query.join(Audit, Audit.id == Chunk.audit_id).where(
                Audit.project_id == project_id
            )
        if audit_id is not None:
            query = query.where(Chunk.audit_id == audit_id)
        return query

    async def similarity_search(
        self,
        embedding: Sequence[float],
        *,
        audit_id: UUID | None = None,
        project_id: UUID | None = None,
        limit: int = 10,
        similarity_threshold: float = 0.0,
    ) -> list[tuple[Chunk, float]]:
        """Cosine-similarity search over stored embeddings (pgvector).

        Returns ``(chunk, similarity)`` tuples ordered by descending similarity.
        """
        distance = Chunk.embedding.cosine_distance(list(embedding))
        similarity = (1.0 - distance).label("similarity")
        query = self._scope_query(audit_id, project_id).add_columns(similarity)
        query = query.where(Chunk.is_embedded.is_(True))
        if similarity_threshold > 0:
            query = query.where(distance <= (1.0 - similarity_threshold))
        query = query.order_by(distance).limit(limit)
        rows = await self.session.execute(query)
        return [(row[0], float(row[1])) for row in rows.all()]

    async def full_text_search(
        self,
        query_text: str,
        *,
        audit_id: UUID | None = None,
        project_id: UUID | None = None,
        limit: int = 10,
    ) -> list[tuple[Chunk, float]]:
        """BM25-style ranking with PostgreSQL ``ts_rank_cd`` over the generated tsvector."""
        tsquery = func.websearch_to_tsquery(FULL_TEXT_CONFIG, query_text)
        rank = func.ts_rank_cd(Chunk.search_vector, tsquery).label("rank")
        query = self._scope_query(audit_id, project_id).add_columns(rank)
        query = query.where(Chunk.search_vector.op("@@")(tsquery))
        query = query.order_by(rank.desc()).limit(limit)
        rows = await self.session.execute(query)
        return [(row[0], float(row[1])) for row in rows.all()]

    async def count_scoped(
        self, *, audit_id: UUID | None = None, project_id: UUID | None = None
    ) -> int:
        """Number of chunks in the search scope."""
        query = select(func.count()).select_from(Chunk)
        if project_id is not None:
            query = query.join(Audit, Audit.id == Chunk.audit_id).where(
                Audit.project_id == project_id
            )
        if audit_id is not None:
            query = query.where(Chunk.audit_id == audit_id)
        return int((await self.session.execute(query)).scalar_one())

    # -- writes --------------------------------------------------------------
    async def bulk_insert(self, rows: Iterable[dict[str, Any]]) -> int:
        """Insert many chunks in one round-trip; returns the inserted count."""
        return await self.create_many(rows)

    async def store_embeddings(self, items: Iterable[tuple[UUID, Sequence[float]]]) -> int:
        """Attach embeddings to existing chunks (bulk update by primary key)."""
        payload = [
            {"id": chunk_id, "embedding": list(vector), "is_embedded": True}
            for chunk_id, vector in items
        ]
        if not payload:
            return 0
        from sqlalchemy import update as sa_update

        await self.session.execute(sa_update(Chunk), payload)
        await self.session.flush()
        return len(payload)

    async def delete_for_audit(self, audit_id: UUID) -> int:
        """Remove every chunk of an audit (idempotent re-ingestion)."""
        return await self.delete_where(audit_id=audit_id)

    async def next_index(self, audit_id: UUID) -> int:
        """Next free ``chunk_index`` for an audit."""
        query = select(func.coalesce(func.max(Chunk.chunk_index), -1) + 1).where(
            Chunk.audit_id == audit_id
        )
        return int((await self.session.execute(query)).scalar_one())


__all__ = ["FULL_TEXT_CONFIG", "ChunkRepository"]
