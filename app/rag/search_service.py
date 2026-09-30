from __future__ import annotations

from .config import Settings
from .embeddings import EmbeddingProvider, SentenceTransformerEmbeddingProvider
from .vector_store import VectorStore


class SearchService:
    def __init__(self, settings: Settings, embedding_provider: EmbeddingProvider | None = None) -> None:
        self.settings = settings
        self.embedding_provider = embedding_provider or SentenceTransformerEmbeddingProvider(settings.embedding_model)
        self._stores: dict[str, VectorStore] = {}

    def search(self, query: str, strategy: str = "structural", top_k: int | None = None) -> list[dict[str, object]]:
        if strategy not in {"fixed", "structural"}:
            raise ValueError("strategy must be fixed or structural")
        top_k = top_k or self.settings.default_top_k
        if top_k < 1 or top_k > self.settings.max_top_k:
            raise ValueError(f"top_k must be between 1 and {self.settings.max_top_k}")
        store = self._stores.get(strategy)
        if store is None:
            store = VectorStore.load(self.settings.index_path(strategy))
            self._stores[strategy] = store
        matches = store.search(self.embedding_provider.embed_query(query), top_k)
        return [
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
