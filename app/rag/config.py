from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    documents_path: Path
    data_path: Path
    embedding_model: str
    fixed_chunk_size: int
    fixed_chunk_overlap: int
    structural_max_chunk_size: int
    structural_overlap: int
    default_top_k: int
    max_top_k: int
    max_query_length: int

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            documents_path=PROJECT_ROOT / os.getenv("RAG_DOCUMENTS_PATH", "docs/rag"),
            data_path=PROJECT_ROOT / os.getenv("RAG_DATA_PATH", "data/rag"),
            embedding_model=os.getenv(
                "RAG_EMBEDDING_MODEL",
                "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
            ),
            fixed_chunk_size=int(os.getenv("RAG_FIXED_CHUNK_SIZE", "1000")),
            fixed_chunk_overlap=int(os.getenv("RAG_FIXED_CHUNK_OVERLAP", "150")),
            structural_max_chunk_size=int(os.getenv("RAG_STRUCTURAL_MAX_CHUNK_SIZE", "1500")),
            structural_overlap=int(os.getenv("RAG_STRUCTURAL_OVERLAP", "150")),
            default_top_k=int(os.getenv("RAG_DEFAULT_TOP_K", "5")),
            max_top_k=int(os.getenv("RAG_MAX_TOP_K", "20")),
            max_query_length=int(os.getenv("RAG_MAX_QUERY_LENGTH", "1000")),
        )

    def index_path(self, strategy: str) -> Path:
        return self.data_path / strategy
