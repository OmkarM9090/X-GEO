"""Markdown chunking, token estimation and offline embeddings."""

from __future__ import annotations

import math

import pytest

from app.core.exceptions import InvalidInputError
from app.services.chunk_service import (
    ChunkService,
    chunk_markdown,
    deterministic_embedding,
    estimate_tokens,
    split_sections,
)

MARKDOWN = """# Pricing

Our starter plan costs $29 per month and includes 5 projects.
Enterprise pricing is custom and includes SSO, audit logs and a 99.9% SLA.

## Feature comparison

| Feature | Starter | Enterprise |
| --- | --- | --- |
| Projects | 5 | Unlimited |
| Support | Email | 24/7 |

## Frequently asked questions

What is included in the free tier? The free tier includes one project and
ten audits per month, which is enough for evaluation.

```python
# code fences must never be split mid-block
def price():
    return 29
```

### Cancellation

You can cancel at any time from the billing page; access continues until the
end of the billing period.
"""


class TestEstimateTokens:
    def test_empty_text(self) -> None:
        assert estimate_tokens("") == 0

    def test_monotonic_in_word_count(self) -> None:
        short = estimate_tokens("one two three")
        long = estimate_tokens(" ".join(["word"] * 300))
        assert short < long

    def test_approximates_words_times_1_3(self) -> None:
        assert estimate_tokens(" ".join(["word"] * 100)) == 130


class TestSplitSections:
    def test_tracks_heading_paths(self) -> None:
        sections = split_sections(MARKDOWN)
        paths = [section.heading_path for section in sections]
        assert "Pricing" in paths[0]
        assert any(path and path.startswith("Pricing > Feature comparison") for path in paths)

    def test_each_section_contains_its_heading(self) -> None:
        sections = split_sections(MARKDOWN)
        assert sections[0].text.startswith("# Pricing")

    def test_document_without_headings_is_one_section(self) -> None:
        sections = split_sections("Just a paragraph.\n\nAnd another one.")
        assert len(sections) == 1
        assert sections[0].heading_path is None


class TestChunkMarkdown:
    def test_empty_input_produces_no_chunks(self) -> None:
        assert chunk_markdown("") == []
        assert chunk_markdown("   \n\n  ") == []

    def test_small_document_is_a_single_chunk(self) -> None:
        drafts = chunk_markdown("A short sentence about GEO.", min_tokens=1)
        assert len(drafts) == 1
        assert drafts[0].chunk_index == 0
        assert drafts[0].token_count > 0

    def test_respects_token_budget(self) -> None:
        paragraphs = "\n\n".join(f"Paragraph {index} " + "word " * 60 for index in range(12))
        drafts = chunk_markdown(paragraphs, chunk_size_tokens=120, overlap_tokens=10, min_tokens=5)
        assert len(drafts) > 1
        assert all(draft.token_count <= 200 for draft in drafts)

    def test_chunk_indexes_are_sequential(self) -> None:
        paragraphs = "\n\n".join("word " * 80 for _ in range(6))
        drafts = chunk_markdown(paragraphs, chunk_size_tokens=100, overlap_tokens=10, min_tokens=5)
        assert [draft.chunk_index for draft in drafts] == list(range(len(drafts)))

    def test_overlap_repeats_previous_context(self) -> None:
        first = "alpha " * 60
        second = "beta " * 60
        drafts = chunk_markdown(
            f"{first}\n\n{second}", chunk_size_tokens=100, overlap_tokens=30, min_tokens=5
        )
        assert len(drafts) >= 2
        assert "alpha" in drafts[1].content  # tail of the previous chunk is carried over

    def test_headings_are_recorded_on_chunks(self) -> None:
        drafts = chunk_markdown(MARKDOWN, chunk_size_tokens=60, overlap_tokens=10, min_tokens=5)
        heading_paths = [draft.heading_path for draft in drafts if draft.heading_path]
        assert heading_paths
        assert any("Pricing" in path for path in heading_paths)

    def test_tiny_trailing_fragment_is_merged(self) -> None:
        body = "word " * 60
        drafts = chunk_markdown(
            f"{body}\n\ntiny tail", chunk_size_tokens=100, overlap_tokens=10, min_tokens=20
        )
        assert "tiny tail" in drafts[-1].content

    def test_oversized_single_paragraph_is_split(self) -> None:
        huge = "sentence about generative engines. " * 200
        drafts = chunk_markdown(huge, chunk_size_tokens=100, overlap_tokens=0, min_tokens=5)
        assert len(drafts) > 1
        assert all(draft.token_count <= 140 for draft in drafts)

    def test_code_fences_are_preserved(self) -> None:
        drafts = chunk_markdown(MARKDOWN, chunk_size_tokens=64, overlap_tokens=8, min_tokens=5)
        joined = "\n".join(draft.content for draft in drafts)
        assert "def price()" in joined

    def test_rejects_invalid_configuration(self) -> None:
        with pytest.raises(InvalidInputError):
            chunk_markdown("text", chunk_size_tokens=0)
        with pytest.raises(InvalidInputError):
            chunk_markdown("text", chunk_size_tokens=50, overlap_tokens=50)

    def test_max_chunks_cap(self) -> None:
        paragraphs = "\n\n".join("word " * 60 for _ in range(50))
        drafts = chunk_markdown(
            paragraphs, chunk_size_tokens=60, overlap_tokens=0, min_tokens=5, max_chunks=3
        )
        assert len(drafts) == 3

    def test_char_count_matches_content(self) -> None:
        drafts = chunk_markdown(MARKDOWN, chunk_size_tokens=80, min_tokens=5)
        for draft in drafts:
            assert draft.char_count == len(draft.content)


class TestDeterministicEmbedding:
    def test_is_unit_length(self) -> None:
        vector = deterministic_embedding("generative engine optimization", dimensions=64)
        norm = math.sqrt(sum(value * value for value in vector))
        assert pytest.approx(norm, abs=1e-6) == 1.0

    def test_dimension_matches_request(self) -> None:
        assert len(deterministic_embedding("text", dimensions=128)) == 128

    def test_is_deterministic(self) -> None:
        assert deterministic_embedding("same text") == deterministic_embedding("same text")

    def test_empty_text_yields_zero_vector(self) -> None:
        assert set(deterministic_embedding("")) == {0.0}

    def test_identical_text_scores_one(self) -> None:
        left = deterministic_embedding("citation share benchmark")
        right = deterministic_embedding("citation share benchmark")
        assert pytest.approx(sum(a * b for a, b in zip(left, right, strict=False)), abs=1e-6) == 1.0


class TestChunkServiceHelpers:
    def test_to_response_projection(self) -> None:
        class _Row:
            id = "11111111-1111-1111-1111-111111111111"
            audit_id = "22222222-2222-2222-2222-222222222222"
            content = "hello"
            chunk_index = 0
            token_count = 2
            char_count = 5
            heading_path = "Pricing"
            xpath_location = None
            embedding = None
            is_embedded = False
            created_at = __import__("datetime").datetime(
                2024, 1, 1, tzinfo=__import__("datetime").timezone.utc
            )

        response = ChunkService.to_response(_Row())  # type: ignore[arg-type]
        assert response.has_embedding is False
        assert response.heading_path == "Pricing"

    def test_rrf_fusion_ranks_agreement_first(self) -> None:
        class _Chunk:
            def __init__(self, identifier: str) -> None:
                self.id = identifier

        shared, only_vector, only_text = _Chunk("shared"), _Chunk("vector"), _Chunk("text")
        fused = ChunkService._fuse_rrf(
            [(only_vector, 0.9), (shared, 0.8)],
            [(shared, 7.0), (only_text, 3.0)],
        )
        assert fused[0][0] is shared
        assert all(0.0 <= score <= 1.0 for _chunk, score, _source in fused)
