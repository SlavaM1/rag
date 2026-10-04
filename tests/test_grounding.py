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


def test_context_quality_requires_a_chunk_above_configured_threshold():
    checker = ContextQualityChecker(0.5)

    assert checker.check([source(score=0.5)]).sufficient is True
    assert checker.check([source(score=0.49)]).sufficient is False
    assert checker.check([]).sufficient is False
