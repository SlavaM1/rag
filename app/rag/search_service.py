from __future__ import annotations

from time import perf_counter

from .config import Settings
from .embeddings import EmbeddingProvider, SentenceTransformerEmbeddingProvider
from .vector_store import VectorStore


class SearchService:
    def __init__(self, settings: Settings, embedding_provider: EmbeddingProvider | None = None) -> None:
        self.settings = settings
        self.embedding_provider = embedding_provider or SentenceTransformerEmbeddingProvider(settings.embedding_model)
        self._stores: dict[str, VectorStore] = {}

    def search(self, query: str, strategy: str = "structural", top_k: int | None = None) -> list[dict[str, object]]:
        results, _ = self.search_with_timings(query, strategy, top_k)
        return results

    def search_with_timings(
        self, query: str, strategy: str = "structural", top_k: int | None = None
    ) -> tuple[list[dict[str, object]], dict[str, float]]:
        if strategy not in {"fixed", "structural"}:
            raise ValueError("strategy must be fixed or structural")
        top_k = top_k or self.settings.default_top_k
        if top_k < 1 or top_k > self.settings.max_top_k:
            raise ValueError(f"top_k must be between 1 and {self.settings.max_top_k}")
        store = self._stores.get(strategy)
        if store is None:
            store = VectorStore.load(self.settings.index_path(strategy))
            self._stores[strategy] = store
        embedding_started = perf_counter()
        query_embedding = self.embedding_provider.embed_query(query)
        embedding_ms = round((perf_counter() - embedding_started) * 1000, 2)
        faiss_started = perf_counter()
        matches = store.search(query_embedding, top_k)
        faiss_ms = round((perf_counter() - faiss_started) * 1000, 2)
        results = [
            {
                "score": round(score, 4),
                "similarity_score": round(score, 4),
                "original_rank": rank,
                "passed_threshold": None,
                "rerank_score": None,
                "final_rank": None,
                "chunk_id": chunk.chunk_id,
                "text": chunk.text,
                "metadata": chunk.metadata.to_dict(),
            }
            for rank, (score, chunk) in enumerate(matches, start=1)
        ]
        return results, {"embedding_ms": embedding_ms, "faiss_ms": faiss_ms}
