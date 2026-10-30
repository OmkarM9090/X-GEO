"""PCS scoring rubric: technical, evidentiary, machine readability, composite."""

from __future__ import annotations

import pytest

from app.config import get_settings
from app.services.audit_service import (
    BOILERPLATE_RATIO_CEILING,
    GOOD_RESPONSE_TIME_MS,
    LONG_PARAGRAPH_WORDS,
    MACHINE_WEIGHTS,
    TECHNICAL_WEIGHTS,
    ScoringInput,
    build_scoring_input,
    compute_evidentiary_density,
    compute_machine_readability,
    compute_pcs,
    compute_technical_readiness,
)

EVIDENCE_RICH = """
# Citation share benchmark

According to a 2024 study of 1,200 answers, 78% of cited passages contained
numbers, dates or named sources — an increase of 17 percentage points over 2023.

## Methodology

The team measured 41% more citations when pages included a results table with
12 metrics. "Evidence density is the strongest single predictor," said the lead
researcher from Example University.

| Metric | 2023 | 2024 |
| --- | --- | --- |
| Citations | 63% | 78% |
| Words | 120 | 140 |
"""


def perfect_input(**overrides: object) -> ScoringInput:
    """A page that passes every technical and readability check."""
    values: dict[str, object] = {
        "target_url": "https://example.com/guide",
        "markdown": "# Title\n\nShort paragraph about generative engines in 2024.",
        "word_count": 900,
        "has_json_ld": True,
        "has_canonical": True,
        "has_meta_description": True,
        "heading_structure_valid": True,
        "has_sitemap": True,
        "has_lang": True,
        "has_viewport": True,
        "response_time_ms": 450,
        "boilerplate_ratio": 0.05,
        "has_lists": True,
        "has_tables": True,
        "avg_paragraph_words": 35.0,
        "semantic_html_score": 0.9,
        "external_link_count": 3,
    }
    values.update(overrides)
    return ScoringInput(**values)  # type: ignore[arg-type]


class TestTechnicalReadiness:
    def test_perfect_page_scores_one(self) -> None:
        score, breakdown = compute_technical_readiness(perfect_input())
        assert score == pytest.approx(1.0)
        assert breakdown["failed"] == []

    def test_bare_http_page_scores_zero(self) -> None:
        score, breakdown = compute_technical_readiness(
            ScoringInput(
                target_url="http://example.com",
                markdown="text",
                word_count=1,
                response_time_ms=None,
            )
        )
        assert score == pytest.approx(0.0)
        assert "https" in breakdown["failed"]

    def test_weights_sum_to_one(self) -> None:
        assert sum(TECHNICAL_WEIGHTS.values()) == pytest.approx(1.0)

    def test_response_time_boundary(self) -> None:
        fast, _ = compute_technical_readiness(perfect_input(response_time_ms=GOOD_RESPONSE_TIME_MS))
        slow, _ = compute_technical_readiness(
            perfect_input(response_time_ms=GOOD_RESPONSE_TIME_MS + 1)
        )
        assert fast > slow

    def test_each_flag_contributes_its_weight(self) -> None:
        full, _ = compute_technical_readiness(perfect_input())
        without_json_ld, _ = compute_technical_readiness(perfect_input(has_json_ld=False))
        assert full - without_json_ld == pytest.approx(TECHNICAL_WEIGHTS["json_ld"])

    def test_score_is_bounded(self) -> None:
        score, _ = compute_technical_readiness(perfect_input())
        assert 0.0 <= score <= 1.0


class TestEvidentiaryDensity:
    def test_empty_document_scores_zero(self) -> None:
        score, breakdown = compute_evidentiary_density("")
        assert score == 0.0
        assert breakdown["reason"] == "empty_document"

    def test_evidence_rich_markdown_scores_high(self) -> None:
        score, breakdown = compute_evidentiary_density(EVIDENCE_RICH)
        assert score > 0.6
        assert breakdown["counts"]["percentages"] >= 3
        assert breakdown["counts"]["numbers"] >= 4

    def test_plain_prose_scores_low(self) -> None:
        prose = (
            "Generative engines are changing how people discover information online. "
            "Many teams are unsure how to react to these changes and what to do next. "
        ) * 5
        rich, _ = compute_evidentiary_density(EVIDENCE_RICH)
        plain, _ = compute_evidentiary_density(prose)
        assert plain < rich
        assert plain < 0.25

    def test_more_evidence_never_lowers_the_score(self) -> None:
        base, _ = compute_evidentiary_density("The sample grew by 12 percent in 2024.")
        more, _ = compute_evidentiary_density(
            "The sample grew by 12 percent in 2024, according to a study of 500 teams."
        )
        assert more >= base

    def test_densities_are_per_hundred_words(self) -> None:
        _, breakdown = compute_evidentiary_density("word " * 100 + " 42% 2024")
        assert breakdown["counts"]["percentages"] == 1
        # ~100 words, so one percentage is ~1 per 100 words.
        assert breakdown["per_100_words"]["percentages"] == pytest.approx(1.0, abs=0.05)


class TestMachineReadability:
    def test_well_structured_page_scores_high(self) -> None:
        score, breakdown = compute_machine_readability(perfect_input())
        assert score > 0.8
        assert breakdown["components"]["headings"] == 1.0
        assert breakdown["components"]["tables"] == 1.0

    def test_heading_requires_actual_markdown_heading(self) -> None:
        _, breakdown = compute_machine_readability(
            perfect_input(markdown="No headings here at all.", heading_structure_valid=True)
        )
        assert breakdown["components"]["headings"] == 0.0

    def test_long_paragraphs_penalised(self) -> None:
        short, _ = compute_machine_readability(perfect_input(avg_paragraph_words=20.0))
        long, _ = compute_machine_readability(
            perfect_input(avg_paragraph_words=LONG_PARAGRAPH_WORDS * 2)
        )
        assert long < short

    def test_boilerplate_penalised_up_to_the_ceiling(self) -> None:
        clean, _ = compute_machine_readability(perfect_input(boilerplate_ratio=0.0))
        dirty, _ = compute_machine_readability(
            perfect_input(boilerplate_ratio=BOILERPLATE_RATIO_CEILING)
        )
        assert dirty < clean

    def test_weights_sum_to_one(self) -> None:
        assert sum(MACHINE_WEIGHTS.values()) == pytest.approx(1.0)

    def test_missing_metadata_defaults_are_conservative(self) -> None:
        score, _ = compute_machine_readability(
            ScoringInput(target_url="https://example.com", markdown="text", word_count=10)
        )
        assert score < 0.35


class TestCompositePcs:
    WEIGHTS = get_settings().PCS_WEIGHTS

    def test_weighted_average(self) -> None:
        score, breakdown = compute_pcs(
            technical=1.0,
            semantic=0.5,
            evidentiary=0.5,
            machine=0.8,
            weights=self.WEIGHTS,
        )
        expected = (
            1.0 * self.WEIGHTS["technical"]
            + 0.5 * self.WEIGHTS["semantic"]
            + 0.5 * self.WEIGHTS["evidentiary"]
            + 0.8 * self.WEIGHTS["machine_readability"]
        )
        assert score == pytest.approx(expected)
        assert breakdown["missing"] == []

    def test_missing_semantic_is_renormalised(self) -> None:
        score, breakdown = compute_pcs(
            technical=1.0, semantic=None, evidentiary=1.0, machine=1.0, weights=self.WEIGHTS
        )
        assert score == pytest.approx(1.0)
        assert breakdown["missing"] == ["semantic"]
        assert breakdown["effective_weight"] == pytest.approx(1.0 - self.WEIGHTS["semantic"])

    def test_single_component_returns_its_own_value(self) -> None:
        score, _ = compute_pcs(
            technical=0.42, semantic=None, evidentiary=None, machine=None, weights=self.WEIGHTS
        )
        assert score == pytest.approx(0.42)

    def test_no_components_returns_none(self) -> None:
        score, breakdown = compute_pcs(
            technical=None, semantic=None, evidentiary=None, machine=None, weights=self.WEIGHTS
        )
        assert score is None
        assert breakdown["reason"] == "no_components"

    def test_missing_semantic_does_not_penalise(self) -> None:
        """No tracked prompts means no semantic score — never a zero penalty."""
        with_semantic, _ = compute_pcs(
            technical=0.8, semantic=0.8, evidentiary=0.8, machine=0.8, weights=self.WEIGHTS
        )
        without_semantic, _ = compute_pcs(
            technical=0.8, semantic=None, evidentiary=0.8, machine=0.8, weights=self.WEIGHTS
        )
        assert without_semantic == pytest.approx(0.8)
        assert with_semantic == pytest.approx(0.8)


class TestScoringInputAdapter:
    def test_builds_from_mapping(self) -> None:
        data = build_scoring_input(
            {"has_json_ld": True, "boilerplate_ratio": 0.1, "has_tables": True},
            markdown="# H",
            word_count=10,
            target_url="https://example.com",
            response_time_ms=120,
        )
        assert data.has_json_ld is True
        assert data.has_tables is True
        assert data.boilerplate_ratio == pytest.approx(0.1)
        assert data.response_time_ms == 120

    def test_builds_from_object(self) -> None:
        class Metadata:
            has_canonical = True
            has_lists = True
            external_link_count = 2
            boilerplate_ratio = 0.3

        data = build_scoring_input(
            Metadata(), markdown="text", word_count=5, target_url="https://example.com"
        )
        assert data.has_canonical is True
        assert data.has_lists is True
        assert data.external_link_count == 2

    def test_missing_attributes_use_defaults(self) -> None:
        data = build_scoring_input(
            None, markdown="", word_count=0, target_url="https://example.com"
        )
        assert data.has_json_ld is False
        assert data.boilerplate_ratio == pytest.approx(1.0)
        assert data.avg_paragraph_words == pytest.approx(0.0)

    def test_invalid_numeric_attribute_falls_back(self) -> None:
        data = build_scoring_input(
            {"boilerplate_ratio": "not-a-number"},
            markdown="",
            word_count=0,
            target_url="https://example.com",
        )
        assert data.boilerplate_ratio == pytest.approx(1.0)
