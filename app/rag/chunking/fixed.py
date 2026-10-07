from __future__ import annotations

from .base import Chunker, make_metadata
from ..models import Chunk, Document


class FixedSizeChunker(Chunker):
    strategy = "fixed"

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 150) -> None:
        if chunk_size <= 0 or chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be non-negative and less than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, document: Document) -> list[Chunk]:
        text = document.text
        chunks: list[Chunk] = []
        start = 0
        index = 0
        while start < len(text):
            while start < len(text) and text[start].isspace():
                start += 1
            if start >= len(text):
                break
            limit = min(start + self.chunk_size, len(text))
            end = limit
            if limit < len(text):
                boundary = text.rfind(" ", start + 1, limit + 1)
                newline = text.rfind("\n", start + 1, limit + 1)
                boundary = max(boundary, newline)
                if boundary > start:
                    end = boundary
            part = text[start:end].strip()
            if part:
                chunk_id = f"{document.document_id}_{self.strategy}_{index:04d}"
                metadata = make_metadata(
                    document,
                    chunk_id=chunk_id,
                    chunk_index=index,
                    strategy=self.strategy,
                    text=part,
                    section=document.h1 or document.title,
                    section_path=document.h1 or document.title,
                    heading_level=1 if document.h1 else None,
                    start_char=start,
                    end_char=end,
                )
                chunks.append(Chunk(chunk_id, part, metadata))
                index += 1
            if end >= len(text):
                break
            start = max(end - self.chunk_overlap, start + 1)
        return chunks


class FixedSizeNoOverlapChunker(FixedSizeChunker):
    strategy = "fixed_no_overlap"

    def __init__(self, chunk_size: int = 1000) -> None:
        super().__init__(chunk_size=chunk_size, chunk_overlap=0)
