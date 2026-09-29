from __future__ import annotations

import json
from pathlib import Path

import faiss
import numpy as np

from .models import Chunk, ChunkMetadata


class VectorStore:
    """FAISS inner-product index with an explicit vector-id to chunk mapping."""

    def __init__(self, dimension: int | None = None) -> None:
        self.dimension = dimension
        self.index = faiss.IndexFlatIP(dimension) if dimension else None
        self.chunks: list[Chunk] = []

    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        if len(chunks) != len(embeddings):
            raise ValueError("Each chunk needs exactly one embedding")
        if not chunks:
            return
        vectors = np.asarray(embeddings, dtype=np.float32)
        if vectors.ndim != 2 or vectors.shape[0] != len(chunks):
            raise ValueError("Embeddings must be a non-empty two-dimensional matrix")
        if self.index is None:
            self.dimension = int(vectors.shape[1])
            self.index = faiss.IndexFlatIP(self.dimension)
        if vectors.shape[1] != self.dimension:
            raise ValueError("Embedding dimensions do not match the index")
        faiss.normalize_L2(vectors)
        self.index.add(vectors)
        self.chunks.extend(chunks)

    def search(self, query_embedding: list[float], top_k: int) -> list[tuple[float, Chunk]]:
        if self.index is None or self.index.ntotal == 0:
            return []
        vector = np.asarray([query_embedding], dtype=np.float32)
        if vector.shape[1] != self.dimension:
            raise ValueError("Query embedding dimension does not match the index")
        faiss.normalize_L2(vector)
        scores, ids = self.index.search(vector, min(top_k, self.index.ntotal))
        return [(float(score), self.chunks[int(vector_id)]) for score, vector_id in zip(scores[0], ids[0]) if vector_id >= 0]

    def save(self, directory: Path) -> None:
        if self.index is None:
            raise ValueError("Cannot save an empty vector store")
        directory.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(directory / "index.faiss"))
        records = [
            {"vector_id": vector_id, "chunk_id": chunk.chunk_id, "text": chunk.text, "metadata": chunk.metadata.to_dict()}
            for vector_id, chunk in enumerate(self.chunks)
        ]
        (directory / "metadata.json").write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, directory: Path) -> "VectorStore":
        index_path = directory / "index.faiss"
        metadata_path = directory / "metadata.json"
        if not index_path.exists() or not metadata_path.exists():
            raise FileNotFoundError(f"Index is missing in {directory}; run python scripts/build_index.py")
        index = faiss.read_index(str(index_path))
        records = json.loads(metadata_path.read_text(encoding="utf-8"))
        if index.ntotal != len(records):
            raise ValueError("FAISS vector count and metadata count differ")
        store = cls(index.d)
        store.index = index
        store.chunks = [
            Chunk(record["chunk_id"], record["text"], ChunkMetadata(**record["metadata"])) for record in records
        ]
        return store
