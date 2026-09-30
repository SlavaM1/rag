from __future__ import annotations

from typing import Protocol


class Reranker(Protocol):
    def rerank(self, query: str, chunks: list[dict[str, object]]) -> list[dict[str, object]]:
        """Return candidates ordered by local cross-encoder relevance."""


class CrossEncoderReranker:
    """Lazy singleton-style cross-encoder; no CUDA dependency is required."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self._model = None

    def rerank(self, query: str, chunks: list[dict[str, object]]) -> list[dict[str, object]]:
        if not chunks:
            return []
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.model_name, device="cpu")
        scores = self._model.predict([(query, str(chunk["text"])) for chunk in chunks], show_progress_bar=False)
        scored = []
        for candidate, score in zip(chunks, scores):
            candidate["rerank_score"] = float(score)
            scored.append(candidate)
        scored.sort(key=lambda item: float(item["rerank_score"]), reverse=True)
        for rank, candidate in enumerate(scored, start=1):
            candidate["final_rank"] = rank
        return scored
