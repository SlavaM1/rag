from __future__ import annotations

from dataclasses import asdict

from .chunking import FixedSizeChunker, FixedSizeNoOverlapChunker, StructuralMarkdownChunker
from .config import Settings
from .embeddings import EmbeddingProvider, SentenceTransformerEmbeddingProvider
from .loader import MarkdownLoader
from .models import Chunk, Document
from .vector_store import VectorStore


def chunk_statistics(chunks: list[Chunk]) -> dict[str, int | float]:
    sizes = [len(chunk.text) for chunk in chunks]
    return {
        "chunks": len(chunks),
        "average_chars": round(sum(sizes) / len(sizes), 2) if sizes else 0,
        "min_chars": min(sizes) if sizes else 0,
        "max_chars": max(sizes) if sizes else 0,
    }


def corpus_statistics(documents: list[Document]) -> dict[str, int]:
    return {"documents": len(documents), "words": sum(len(document.raw_text.split()) for document in documents)}


def build_indexes(settings: Settings | None = None, provider: EmbeddingProvider | None = None) -> dict[str, object]:
    settings = settings or Settings.from_env()
    loader = MarkdownLoader(settings.documents_path, settings.documents_path.parents[1])
    documents = loader.load_all()
    if not documents:
        raise FileNotFoundError(f"No Markdown documents found in {settings.documents_path}")
    provider = provider or SentenceTransformerEmbeddingProvider(settings.embedding_model)
    strategies = {
        "fixed": FixedSizeChunker(settings.fixed_chunk_size, settings.fixed_chunk_overlap),
        "fixed_no_overlap": FixedSizeNoOverlapChunker(settings.fixed_chunk_size),
        "structural": StructuralMarkdownChunker(settings.structural_max_chunk_size, settings.structural_overlap),
    }
    result: dict[str, object] = {"corpus": corpus_statistics(documents), "strategies": {}}
    for name, chunker in strategies.items():
        chunks = [chunk for document in documents for chunk in chunker.chunk(document)]
        store = VectorStore()
        store.add(chunks, provider.embed_documents([chunk.text for chunk in chunks]))
        store.save(settings.index_path(name))
        result["strategies"][name] = chunk_statistics(chunks)  # type: ignore[index]
    return result


def _print_stats(result: dict[str, object]) -> None:
    corpus = result["corpus"]
    print(f"Documents: {corpus['documents']}")  # type: ignore[index]
    print(f"Words: {corpus['words']}")  # type: ignore[index]
    for name in ("fixed", "structural"):
        stats = result["strategies"][name]  # type: ignore[index]
        print(f"\n{name.upper()}")
        print(f"Chunks: {stats['chunks']}")
        print(f"Average chars: {stats['average_chars']}")
        print(f"Min chars: {stats['min_chars']}")
        print(f"Max chars: {stats['max_chars']}")


if __name__ == "__main__":
    _print_stats(build_indexes())
