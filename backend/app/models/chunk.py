"""Chunk — an embeddable passage of cleaned page content (pgvector + tsvector)."""

from __future__ import annotations

import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    Computed,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

#: Embedding width. Must stay in sync with ``Settings.EMBEDDING_DIMENSIONS``;
#: changing it is a schema change and therefore requires a migration.
EMBEDDING_DIMENSIONS = 1536


class Chunk(Base, UUIDMixin, TimestampMixin):
    """A retrieval unit.

    ``embedding`` powers vector similarity search, ``search_vector`` powers
    BM25-style full-text ranking. Together they enable hybrid retrieval (RRF)
    for semantic-alignment scoring and Phase 3 citation simulation.
    """

    __tablename__ = "chunks"
    __table_args__ = (
        UniqueConstraint("audit_id", "chunk_index", name="audit_chunk_index"),
        Index(
            "ix_chunks_embedding",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index("ix_chunks_search", "search_vector", postgresql_using="gin"),
        Index(
            "ix_chunks_content_trgm",
            "content",
            postgresql_using="gin",
            postgresql_ops={"content": "gin_trgm_ops"},
        ),
        Index("ix_chunks_audit_index", "audit_id", "chunk_index"),
    )

    audit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("audits.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    content: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    char_count: Mapped[int | None] = mapped_column(Integer)
    xpath_location: Mapped[str | None] = mapped_column(String(1024))
    #: Cheap "is this chunk embedded?" flag: lets list/search endpoints
    #: defer the 1536-float vector column without a lazy load per row.
    is_embedded: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    #: Heading trail, e.g. "Pricing > Enterprise", used to ground citations.
    heading_path: Mapped[str | None] = mapped_column(String(512))

    # Vector embedding of `content` (nullable until the embedding worker runs).
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMBEDDING_DIMENSIONS), nullable=True
    )

    # Generated BM25-ish full-text vector; maintained by PostgreSQL itself.
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR,
        Computed("to_tsvector('english', content)", persisted=True),
        nullable=True,
    )

    audit = relationship("Audit", back_populates="chunks", lazy="raise")


__all__ = ["EMBEDDING_DIMENSIONS", "Chunk"]
