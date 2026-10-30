"""Chunking, embedding and retrieval business logic.

Responsibilities
----------------
* split cleaned markdown into token-bounded, heading-aware chunks with overlap;
* attach embeddings (OpenAI when configured, a deterministic hashing embedder
  otherwise so the pipeline and tests always work offline);
* store chunks with pgvector + tsvector and expose hybrid (RRF) retrieval used
  by semantic-alignment scoring and, later, citation simulation.
"""

from __future__ import annotations

import hashlib
import math
import re
import uuid
from dataclasses import dataclass

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.core.exceptions import ExternalServiceError, InvalidInputError
from app.core.logging_config import get_logger
from app.models.chunk import Chunk
from app.repositories.chunk_repo import ChunkRepository
from app.schemas.chunk import (
    ChunkResponse,
    ChunkSearchRequest,
    ChunkSearchResponse,
    ChunkSearchResult,
)

logger = get_logger(__name__)

#: OpenAI embeddings endpoint.
OPENAI_EMBEDDINGS_URL = "https://api.openai.com/v1/embeddings"
#: Max inputs per embeddings request (OpenAI allows 2048; keep batches small).
EMBEDDING_BATCH_SIZE = 64
#: RRF constant from Cormack et al. (2009).
RRF_K = 60

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")
_CODE_FENCE_RE = re.compile(r"^\s*(```|~~~)")
_TOKEN_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True, slots=True)
class ChunkDraft:
    """A chunk that has not been persisted yet."""

    content: str
    chunk_index: int
    token_count: int
    char_count: int
    heading_path: str | None = None

    def as_row(self, audit_id: uuid.UUID) -> dict[str, object]:
        return {
            "audit_id": audit_id,
            "content": self.content,
            "chunk_index": self.chunk_index,
            "token_count": self.token_count,
            "char_count": self.char_count,
            "heading_path": self.heading_path,
        }


@dataclass(frozen=True, slots=True)
class IngestResult:
    """Outcome of chunking + embedding a document."""

    chunks_created: int
    chunks_embedded: int
    skipped: int = 0


@dataclass(slots=True)
class _Section:
    """A heading-delimited block of markdown."""

    heading_path: str | None
    text: str


def estimate_tokens(text: str) -> int:
    """Estimate tokens from whitespace-delimited words (~1.3 tokens/word).

    Deliberately dependency free: exact tokenisation would require tiktoken,
    which we do not need for sizing decisions (target is a size *band*, not an
    exact count). The estimate is stable and monotonic.
    """
    words = len(text.split())
    if words == 0:
        return 0
    return max(1, int(round(words * 1.3)))


def _flush_section(sections: list[_Section], lines: list[str], heading_path: str | None) -> None:
    text = "\n".join(lines).strip()
    if text:
        sections.append(_Section(heading_path=heading_path, text=text))
    lines.clear()


def split_sections(markdown: str) -> list[_Section]:
    """Split markdown into heading-delimited sections (code fences respected)."""
    sections: list[_Section] = []
    heading_stack: list[str] = []
    current_heading: str | None = None
    lines: list[str] = []
    in_fence = False

    for line in markdown.splitlines():
        if _CODE_FENCE_RE.match(line):
            in_fence = not in_fence
            lines.append(line)
            continue
        match = None if in_fence else _HEADING_RE.match(line.strip())
        if match:
            _flush_section(sections, lines, current_heading)
            level = len(match.group(1))
            title = match.group(2).strip()
            heading_stack = heading_stack[: level - 1]
            heading_stack.append(title)
            current_heading = " > ".join(heading_stack)
            lines.append(line.strip())
            continue
        lines.append(line)

    _flush_section(sections, lines, current_heading)
    return sections


def _split_paragraphs(text: str) -> list[str]:
    """Split a section into paragraph-ish blocks without breaking code fences."""
    blocks: list[str] = []
    buffer: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if _CODE_FENCE_RE.match(line):
            in_fence = not in_fence
            buffer.append(line)
            continue
        if not in_fence and not line.strip():
            chunk = "\n".join(buffer).strip()
            if chunk:
                blocks.append(chunk)
            buffer = []
            continue
        buffer.append(line)
    tail = "\n".join(buffer).strip()
    if tail:
        blocks.append(tail)
    return blocks


def _split_oversized(block: str, max_tokens: int) -> list[str]:
    """Split a block larger than the budget: sentences first, words as a fallback."""
    sentences = [part.strip() for part in _SENTENCE_SPLIT_RE.split(block) if part.strip()]
    if len(sentences) <= 1:
        sentences = [part.strip() for part in block.split("\n") if part.strip()] or [block]

    pieces: list[str] = []
    current: list[str] = []
    for sentence in sentences:
        candidate = " ".join([*current, sentence])
        if current and estimate_tokens(candidate) > max_tokens:
            pieces.append(" ".join(current))
            current = [sentence]
        else:
            current.append(sentence)
        # A single sentence can still exceed the budget -> hard word split.
        if estimate_tokens(" ".join(current)) > max_tokens:
            words = " ".join(current).split()
            step = max(1, int(max_tokens / 1.3))
            for start in range(0, len(words), step):
                pieces.append(" ".join(words[start : start + step]))
            current = []
    if current:
        pieces.append(" ".join(current))
    return [piece for piece in pieces if piece.strip()]


def _tail_overlap(text: str, overlap_tokens: int) -> str:
    """Return the trailing words of ``text`` worth ``overlap_tokens``."""
    if overlap_tokens <= 0:
        return ""
    words = text.split()
    take = max(1, int(overlap_tokens / 1.3))
    return " ".join(words[-take:])


def chunk_markdown(
    markdown: str,
    *,
    chunk_size_tokens: int | None = None,
    overlap_tokens: int | None = None,
    min_tokens: int | None = None,
    max_chunks: int = 2000,
) -> list[ChunkDraft]:
    """Split cleaned markdown into overlapping, heading-aware chunks.

    Purely functional — this is the unit under test in ``tests/unit/test_chunking.py``.
    """
    settings = get_settings()
    chunk_size = settings.CHUNK_SIZE_TOKENS if chunk_size_tokens is None else chunk_size_tokens
    overlap = settings.CHUNK_OVERLAP_TOKENS if overlap_tokens is None else overlap_tokens
    min_size = settings.CHUNK_MIN_TOKENS if min_tokens is None else min_tokens

    if chunk_size <= 0:
        raise InvalidInputError("chunk_size_tokens must be positive")
    if overlap < 0:
        raise InvalidInputError("overlap_tokens must not be negative")
    if overlap >= chunk_size:
        raise InvalidInputError("overlap_tokens must be smaller than chunk_size_tokens")
    if min_size < 0:
        raise InvalidInputError("min_tokens must not be negative")
    if max_chunks <= 0:
        raise InvalidInputError("max_chunks must be positive")

    markdown = (markdown or "").strip()
    if not markdown:
        return []

    drafts: list[ChunkDraft] = []
    index = 0
    previous_tail = ""

    for section in split_sections(markdown):
        paragraphs: list[str] = []
        for block in _split_paragraphs(section.text):
            if estimate_tokens(block) > chunk_size:
                paragraphs.extend(_split_oversized(block, chunk_size))
            else:
                paragraphs.append(block)

        buffer: list[str] = []
        buffer_tokens = 0

        def flush(section: _Section = section) -> None:
            nonlocal buffer, buffer_tokens, index, previous_tail
            if not buffer:
                return
            body = "\n\n".join(buffer).strip()
            prefix = _tail_overlap(previous_tail, overlap) if previous_tail else ""
            content = f"{prefix}\n\n{body}".strip() if prefix else body
            tokens = estimate_tokens(content)
            if tokens < min_size and drafts:
                # Too small to be useful as its own retrieval unit: append to the
                # previous chunk instead of emitting noise.
                previous = drafts[-1]
                merged = f"{previous.content}\n\n{body}".strip()
                drafts[-1] = ChunkDraft(
                    content=merged,
                    chunk_index=previous.chunk_index,
                    token_count=estimate_tokens(merged),
                    char_count=len(merged),
                    heading_path=previous.heading_path,
                )
                previous_tail = merged
            else:
                drafts.append(
                    ChunkDraft(
                        content=content,
                        chunk_index=index,
                        token_count=tokens,
                        char_count=len(content),
                        heading_path=section.heading_path,
                    )
                )
                index += 1
                previous_tail = body
            buffer = []
            buffer_tokens = 0

        for paragraph in paragraphs:
            paragraph_tokens = estimate_tokens(paragraph)
            if buffer and buffer_tokens + paragraph_tokens > chunk_size:
                flush()
            buffer.append(paragraph)
            buffer_tokens += paragraph_tokens
            if buffer_tokens >= chunk_size:
                flush()
        flush()

        if len(drafts) >= max_chunks:
            logger.warning("chunk.truncated", max_chunks=max_chunks)
            break

    return drafts[:max_chunks]


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------
def deterministic_embedding(text: str, dimensions: int = 1536) -> list[float]:
    """Hash-based bag-of-words embedding (offline/development fallback).

    Dimension-correct, deterministic and L2-normalised, so cosine similarity
    behaves sensibly (identical token sets score 1.0). It is *not* a semantic
    model: production deployments must configure ``OPENAI_API_KEY``.
    """
    vector = [0.0] * dimensions
    for token in _TOKEN_RE.findall(text.lower()):
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


class ChunkService:
    """Chunking, embedding, ingestion and retrieval."""

    def __init__(self, session: AsyncSession, *, settings: Settings | None = None) -> None:
        self.session = session
        self.settings = settings or get_settings()
        self.repo = ChunkRepository(session)

    # -- ingestion -----------------------------------------------------------
    async def ingest_markdown(
        self,
        audit_id: uuid.UUID,
        markdown: str,
        *,
        replace: bool = True,
        embed: bool = True,
    ) -> IngestResult:
        """Chunk a document, persist the chunks and (optionally) embed them."""
        if replace:
            await self.repo.delete_for_audit(audit_id)

        drafts = chunk_markdown(
            markdown,
            chunk_size_tokens=self.settings.CHUNK_SIZE_TOKENS,
            overlap_tokens=self.settings.CHUNK_OVERLAP_TOKENS,
            min_tokens=self.settings.CHUNK_MIN_TOKENS,
        )
        if not drafts:
            return IngestResult(chunks_created=0, chunks_embedded=0)

        await self.repo.bulk_insert([draft.as_row(audit_id) for draft in drafts])
        embedded = 0
        if embed:
            embedded = await self.embed_audit_chunks(audit_id)

        logger.info("chunk.ingested", audit_id=str(audit_id), chunks=len(drafts), embedded=embedded)
        return IngestResult(chunks_created=len(drafts), chunks_embedded=embedded)

    async def embed_audit_chunks(self, audit_id: uuid.UUID) -> int:
        """Embed every chunk of an audit that does not have a vector yet."""
        # `is_embedded` avoids loading the (deferred) 1536-float vector column.
        chunks, _total = await self.repo.list_for_audit(audit_id, limit=10_000)
        pending = [chunk for chunk in chunks if not chunk.is_embedded]
        if not pending:
            return 0
        vectors = await self.embed_texts([chunk.content for chunk in pending])
        return await self.repo.store_embeddings(
            [(chunk.id, vector) for chunk, vector in zip(pending, vectors, strict=True)]
        )

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts, using OpenAI when configured."""
        if not texts:
            return []
        if not self.settings.embeddings_enabled:
            logger.debug("embedding.fallback_deterministic", count=len(texts))
            return [
                deterministic_embedding(text, self.settings.EMBEDDING_DIMENSIONS) for text in texts
            ]
        return await self._embed_with_openai(texts)

    async def _embed_with_openai(self, texts: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        headers = {
            "Authorization": f"Bearer {self.settings.OPENAI_API_KEY}",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=self.settings.OPENAI_TIMEOUT_SECONDS) as client:
            for start in range(0, len(texts), EMBEDDING_BATCH_SIZE):
                batch = texts[start : start + EMBEDDING_BATCH_SIZE]
                try:
                    response = await client.post(
                        OPENAI_EMBEDDINGS_URL,
                        headers=headers,
                        json={
                            "model": self.settings.OPENAI_EMBEDDING_MODEL,
                            "input": batch,
                            "dimensions": self.settings.EMBEDDING_DIMENSIONS,
                            "encoding_format": "float",
                        },
                    )
                    response.raise_for_status()
                except httpx.HTTPStatusError as exc:
                    detail = exc.response.text[:200]
                    raise ExternalServiceError(
                        "OpenAI", f"embeddings failed ({exc.response.status_code}): {detail}"
                    ) from exc
                except httpx.HTTPError as exc:
                    raise ExternalServiceError(
                        "OpenAI", f"embeddings request failed: {exc}"
                    ) from exc

                payload = response.json()
                ordered = sorted(payload["data"], key=lambda item: item["index"])
                vectors.extend([list(item["embedding"]) for item in ordered])
        return vectors

    async def embed_query(self, query: str) -> list[float]:
        """Embed a single query string."""
        vectors = await self.embed_texts([query])
        return vectors[0]

    # -- retrieval -----------------------------------------------------------
    @staticmethod
    def to_response(chunk: Chunk) -> ChunkResponse:
        """Project a chunk row into its API representation."""
        return ChunkResponse(
            id=chunk.id,
            audit_id=chunk.audit_id,
            content=chunk.content,
            chunk_index=chunk.chunk_index,
            token_count=chunk.token_count,
            char_count=chunk.char_count,
            heading_path=chunk.heading_path,
            xpath_location=chunk.xpath_location,
            has_embedding=chunk.is_embedded,
            created_at=chunk.created_at,
        )

    @staticmethod
    def _fuse_rrf(
        vector_hits: list[tuple[Chunk, float]],
        text_hits: list[tuple[Chunk, float]],
        *,
        k: int = RRF_K,
    ) -> list[tuple[Chunk, float, str]]:
        """Reciprocal Rank Fusion of the semantic and lexical rankings."""
        scores: dict[uuid.UUID, float] = {}
        chunks: dict[uuid.UUID, Chunk] = {}
        for ranking in (vector_hits, text_hits):
            for rank, (chunk, _score) in enumerate(ranking, start=1):
                chunks[chunk.id] = chunk
                scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (k + rank)
        ordered = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        best = ordered[0][1] if ordered else 1.0
        return [(chunks[chunk_id], score / best, "hybrid") for chunk_id, score in ordered]

    async def search(self, request: ChunkSearchRequest) -> ChunkSearchResponse:
        """Run semantic, full-text or hybrid retrieval."""
        scope = {"audit_id": request.audit_id, "project_id": request.project_id}
        chunks_total = await self.repo.count_scoped(**scope)

        vector_hits: list[tuple[Chunk, float]] = []
        text_hits: list[tuple[Chunk, float]] = []
        results: list[tuple[Chunk, float, str]] = []

        if request.mode in {"semantic", "hybrid"}:
            embedding = await self.embed_query(request.query)
            vector_hits = await self.repo.similarity_search(
                embedding,
                limit=request.limit,
                similarity_threshold=request.similarity_threshold,
                **scope,
            )
        if request.mode in {"full_text", "hybrid"}:
            text_hits = await self.repo.full_text_search(
                request.query, limit=request.limit, **scope
            )

        if request.mode == "semantic":
            results = [(chunk, score, "vector") for chunk, score in vector_hits]
        elif request.mode == "full_text":
            results = [(chunk, score, "full_text") for chunk, score in text_hits]
        else:
            results = self._fuse_rrf(vector_hits, text_hits)

        return ChunkSearchResponse(
            query=request.query,
            mode=request.mode,
            results=[
                ChunkSearchResult(
                    chunk=self.to_response(chunk), score=round(score, 6), source=source
                )
                for chunk, score, source in results[: request.limit]
            ],
            total=len(results),
            searched_chunks=chunks_total,
        )

    async def alignment_score(self, audit_id: uuid.UUID, queries: list[str]) -> float | None:
        """Mean best-chunk cosine similarity between tracked queries and the page.

        This is the ``S(u, q)`` term of the PCS score. Returns ``None`` when the
        audit has no chunks or no queries to align against.
        """
        cleaned = [query.strip() for query in queries if query and query.strip()]
        if not cleaned:
            return None
        if await self.repo.count_embedded_for_audit(audit_id) == 0:
            return None

        scores: list[float] = []
        embeddings = await self.embed_texts(cleaned)
        for embedding in embeddings:
            hits = await self.repo.similarity_search(embedding, audit_id=audit_id, limit=5)
            if hits:
                scores.append(max(0.0, min(1.0, max(similarity for _chunk, similarity in hits))))
        if not scores:
            return None
        return sum(scores) / len(scores)


__all__ = [
    "ChunkDraft",
    "ChunkService",
    "IngestResult",
    "chunk_markdown",
    "deterministic_embedding",
    "estimate_tokens",
    "split_sections",
]
