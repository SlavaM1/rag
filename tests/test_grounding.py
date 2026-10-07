import json

import pytest

from app.rag.context_quality import ContextQualityChecker
from app.rag.grounding import GroundingValidationError, GroundingValidator


def source(number=1, score=0.8):
    return {
        "number": number,
        "source": "docs/rag/example.md",
        "file": "example.md",
        "section": "Section",
        "section_path": "Example > Section",
        "chunk_id": "example-1",
        "similarity_score": score,
        "text": "Weather MCP exposes current weather and forecasts.",
    }


def test_valid_quote_is_accepted_and_enriched_from_backend_source():
    content = json.dumps({
        "answer": "Weather MCP exposes current weather [1].",
        "citations": [{"source_number": 1, "quote": "Weather MCP exposes current weather"}],
    })

    result = GroundingValidator().validate(content, [source()])

    assert result.quotes[0]["source"] == "docs/rag/example.md"
    assert result.quotes[0]["chunk_id"] == "example-1"
    assert result.sources[0]["number"] == 1


def test_quote_not_present_in_retrieved_chunk_is_rejected():
    content = json.dumps({
        "answer": "Invented claim [1].",
        "citations": [{"source_number": 1, "quote": "Invented quote"}],
    })

    with pytest.raises(GroundingValidationError, match="not present"):
        GroundingValidator().validate(content, [source()])


def test_quote_markdown_and_whitespace_are_restored_to_exact_source_text():
    retrieved = source()
    retrieved["text"] = "Flow:\n`get_weather_forecast`   calls wttr.in"
    content = json.dumps({
        "answer": "Forecast uses the weather tool [1].",
        "citations": [{"source_number": 1, "quote": "get_weather_forecast calls wttr.in"}],
    })

    result = GroundingValidator().validate(content, [retrieved])

    assert result.quotes[0]["quote"] == "`get_weather_forecast`   calls wttr.in"


def test_missing_citation_marker_is_added_after_evidence_validation():
    content = json.dumps({
        "answer": "Weather MCP exposes current weather.",
        "citations": [{"source_number": 1, "quote": "Weather MCP exposes current weather"}],
    })

    result = GroundingValidator().validate(content, [source()])

    assert result.answer.endswith("[1]")


def test_uncited_source_markers_are_removed_from_answer():
    content = json.dumps({
        "answer": "Weather MCP exposes current weather [2].",
        "citations": [{"source_number": 1, "quote": "Weather MCP exposes current weather"}],
    })

    result = GroundingValidator().validate(content, [source()])

    assert "[2]" not in result.answer
    assert result.answer.endswith("[1]")


def test_context_quality_requires_a_chunk_above_configured_threshold():
    checker = ContextQualityChecker(0.5)

    assert checker.check([source(score=0.5)]).sufficient is True
    assert checker.check([source(score=0.49)]).sufficient is False
    assert checker.check([]).sufficient is False
