"""Chunk (retrieval unit) schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

SearchMode = Literal["semantic", "full_text", "hybrid"]


class ChunkCreate(BaseModel):
    """Internal payload used by the crawl pipeline (never client supplied)."""

    content: str = Field(..., min_length=1)
    chunk_index: int = Field(..., ge=0)
    token_count: int = Field(..., ge=0)
    char_count: int | None = Field(default=None, ge=0)
    heading_path: str | None = Field(default=None, max_length=512)
    xpath_location: str | None = Field(default=None, max_length=1024)


class ChunkResponse(BaseModel):
    """Chunk projection. Embeddings are never serialised over the wire."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    audit_id: UUID
    content: str
    chunk_index: int
    token_count: int
    char_count: int | None = None
    heading_path: str | None = None
    xpath_location: str | None = None
    has_embedding: bool = False
    created_at: datetime


class ChunkSearchRequest(BaseModel):
    """Retrieval query used by semantic-alignment scoring and the API."""

    query: str = Field(..., min_length=1, max_length=2000)
    mode: SearchMode = "hybrid"
    limit: int = Field(default=10, ge=1, le=50)
    similarity_threshold: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Minimum cosine similarity for semantic hits"
    )
    audit_id: UUID | None = Field(default=None, description="Restrict the search to a single audit")
    project_id: UUID | None = Field(
        default=None, description="Restrict the search to every audit of a project"
    )


class ChunkSearchResult(BaseModel):
    """One scored retrieval hit."""

    chunk: ChunkResponse
    score: float = Field(description="Cosine similarity (semantic) or ts_rank (full text)")
    source: str = Field(description="vector | full_text | hybrid")


class ChunkSearchResponse(BaseModel):
    """Search results plus corpus statistics for the UI."""

    query: str
    mode: SearchMode
    results: list[ChunkSearchResult]
    total: int = 0
    searched_chunks: int = 0


class ChunkListResponse(BaseModel):
    """Paginated chunk list for one audit."""

    items: list[ChunkResponse]
    total: int
    skip: int
    limit: int
    has_more: bool = False


__all__ = [
    "ChunkCreate",
    "ChunkListResponse",
    "ChunkResponse",
    "ChunkSearchRequest",
    "ChunkSearchResponse",
    "ChunkSearchResult",
    "SearchMode",
]
