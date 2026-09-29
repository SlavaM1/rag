from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError


class SentenceTransformerEmbeddingProvider(EmbeddingProvider):
    """Lazy adapter so the rest of the application is model-independent."""

    def __init__(self, model_name: str, batch_size: int = 32) -> None:
        self.model_name = model_name
        self.batch_size = batch_size
        self._model = None

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self.model.encode(texts, batch_size=self.batch_size, show_progress_bar=False)
        return vectors.tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.model.encode([text], show_progress_bar=False)[0].tolist()
