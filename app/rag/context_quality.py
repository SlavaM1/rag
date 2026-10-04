from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ContextQuality:
    sufficient: bool
    best_similarity: float | None
    threshold: float
    chunks_count: int

    @property
    def status(self) -> str:
        return "sufficient" if self.sufficient else "insufficient"


class ContextQualityChecker:
    """Decide whether retrieved chunks are strong enough to permit generation."""

    def __init__(self, min_similarity: float) -> None:
        self.min_similarity = min_similarity

    def check(
        self,
        sources: list[dict[str, object]],
        candidates: list[dict[str, object]] | None = None,
    ) -> ContextQuality:
        score_items = sources or candidates or []
        scores = [float(source["similarity_score"]) for source in score_items]
        best_similarity = max(scores) if scores else None
        return ContextQuality(
            sufficient=bool(sources) and best_similarity is not None and best_similarity >= self.min_similarity,
            best_similarity=best_similarity,
            threshold=self.min_similarity,
            chunks_count=len(sources),
        )
