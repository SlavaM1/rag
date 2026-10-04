from __future__ import annotations

import json
from dataclasses import dataclass


class GroundingValidationError(ValueError):
    pass


@dataclass(frozen=True)
class GroundedAnswer:
    answer: str
    sources: list[dict[str, object]]
    quotes: list[dict[str, object]]


class GroundingValidator:
    """Validate model citations only against chunks already selected by retrieval."""

    def validate(self, content: str, sources: list[dict[str, object]]) -> GroundedAnswer:
        payload = self._json_payload(content)
        answer = payload.get("answer")
        citations = payload.get("citations")
        if not isinstance(answer, str) or not answer.strip():
            raise GroundingValidationError("grounded response has no answer")
        if not isinstance(citations, list) or not citations:
            raise GroundingValidationError("grounded response has no citations")

        source_by_number = {int(source["number"]): source for source in sources}
        for source in sources:
            if not source.get("source") or not source.get("chunk_id"):
                raise GroundingValidationError("retrieved source has incomplete backend metadata")
            if not source.get("section") and not source.get("section_path"):
                raise GroundingValidationError("retrieved source has no section metadata")
        quotes: list[dict[str, object]] = []
        cited_numbers: set[int] = set()
        seen_quotes: set[tuple[int, str]] = set()
        for citation in citations:
            if not isinstance(citation, dict):
                raise GroundingValidationError("citation must be an object")
            source_number = citation.get("source_number")
            quote = citation.get("quote")
            if isinstance(source_number, bool) or not isinstance(source_number, int):
                raise GroundingValidationError("citation source_number must be an integer")
            source = source_by_number.get(source_number)
            if source is None:
                raise GroundingValidationError("citation references an unknown source")
            if not isinstance(quote, str) or not quote.strip():
                raise GroundingValidationError("citation has no quote")
            quote = quote.strip()
            if len(quote) > 600:
                raise GroundingValidationError("citation quote is too long")
            if quote not in str(source["text"]):
                raise GroundingValidationError("citation quote is not present in its source chunk")
            if f"[{source_number}]" not in answer:
                raise GroundingValidationError("answer does not reference a cited source")

            cited_numbers.add(source_number)
            key = (source_number, quote)
            if key in seen_quotes:
                continue
            seen_quotes.add(key)
            quotes.append(
                {
                    "quote": quote,
                    "source_number": source_number,
                    "source": source["source"],
                    "file": source["file"],
                    "section": source["section"],
                    "section_path": source["section_path"],
                    "chunk_id": source["chunk_id"],
                }
            )

        used_sources = [source for source in sources if int(source["number"]) in cited_numbers]
        if not used_sources or not quotes:
            raise GroundingValidationError("grounded response has no validated evidence")
        return GroundedAnswer(answer.strip(), used_sources, quotes)

    @staticmethod
    def _json_payload(content: str) -> dict[str, object]:
        value = content.strip()
        if value.startswith("```"):
            lines = value.splitlines()
            if len(lines) >= 3 and lines[-1].strip() == "```":
                value = "\n".join(lines[1:-1])
        try:
            payload = json.loads(value)
        except json.JSONDecodeError as exc:
            raise GroundingValidationError("grounded response is not valid JSON") from exc
        if not isinstance(payload, dict):
            raise GroundingValidationError("grounded response must be a JSON object")
        return payload
