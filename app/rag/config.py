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
    deepseek_api_key: str | None
    deepseek_base_url: str
    deepseek_default_model: str
    deepseek_available_models: tuple[str, ...]
    deepseek_temperature: float
    deepseek_max_tokens: int
    deepseek_timeout_seconds: float
    chat_history_messages: int
    chat_database_path: Path
    query_rewrite_enabled: bool = True
    query_rewrite_model: str = "deepseek-flash"
    candidate_top_k: int = 15
    final_top_k: int = 5
    similarity_threshold: float = 0.4
    filter_enabled: bool = True
    rerank_enabled: bool = True
    rerank_model: str = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"

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
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY") or None,
            deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").rstrip("/"),
            deepseek_default_model=os.getenv("DEEPSEEK_DEFAULT_MODEL", "deepseek-flash"),
            deepseek_available_models=tuple(
                model.strip()
                for model in os.getenv(
                    "DEEPSEEK_AVAILABLE_MODELS", "deepseek-flash,deepseek-v4-pro"
                ).split(",")
                if model.strip()
            ),
            deepseek_temperature=float(os.getenv("DEEPSEEK_TEMPERATURE", "0.2")),
            deepseek_max_tokens=int(os.getenv("DEEPSEEK_MAX_TOKENS", "1024")),
            deepseek_timeout_seconds=float(os.getenv("DEEPSEEK_TIMEOUT_SECONDS", "45")),
            chat_history_messages=int(os.getenv("CHAT_HISTORY_MESSAGES", "10")),
            chat_database_path=PROJECT_ROOT / os.getenv("RAG_CHAT_DB_PATH", "data/rag.db"),
            query_rewrite_enabled=_env_bool("RAG_QUERY_REWRITE_ENABLED", True),
            query_rewrite_model=os.getenv("RAG_QUERY_REWRITE_MODEL", "deepseek-flash"),
            candidate_top_k=int(os.getenv("RAG_CANDIDATE_TOP_K", "15")),
            final_top_k=int(os.getenv("RAG_FINAL_TOP_K", "5")),
            similarity_threshold=float(os.getenv("RAG_SIMILARITY_THRESHOLD", "0.4")),
            filter_enabled=_env_bool("RAG_FILTER_ENABLED", True),
            rerank_enabled=_env_bool("RAG_RERANK_ENABLED", True),
            rerank_model=os.getenv("RAG_RERANK_MODEL", "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"),
        )

    def index_path(self, strategy: str) -> Path:
        return self.data_path / strategy


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    return default if value is None else value.strip().lower() in {"1", "true", "yes", "on"}
