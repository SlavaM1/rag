from __future__ import annotations

from app.rag.models import Chunk, ChunkMetadata


class FakeEmbeddingProvider:
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._vector(text)

    @staticmethod
    def _vector(text: str) -> list[float]:
        text = text.lower()
        return [float("weather" in text or "погода" in text), float("database" in text or "база" in text), 1.0]


def make_chunk(chunk_id: str, text: str, strategy: str = "structural") -> Chunk:
    metadata = ChunkMetadata(
        source="docs/rag/example.md",
        file="example.md",
        title="Example",
        section="Section",
        section_path="Example > Section",
        chunk_id=chunk_id,
        chunk_index=0,
        chunk_strategy=strategy,
        document_id="example",
        heading_level=2,
        char_count=len(text),
        word_count=len(text.split()),
        start_char=0,
        end_char=len(text),
    )
    return Chunk(chunk_id, text, metadata)
