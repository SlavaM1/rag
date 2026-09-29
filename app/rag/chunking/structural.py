from __future__ import annotations

import re

from .base import Chunker, make_metadata
from ..loader import slugify
from ..models import Chunk, Document, MarkdownSection


class StructuralMarkdownChunker(Chunker):
    strategy = "structural"

    def __init__(self, max_chunk_size: int = 1500, chunk_overlap: int = 150) -> None:
        if max_chunk_size <= 0 or chunk_overlap < 0 or chunk_overlap >= max_chunk_size:
            raise ValueError("chunk_overlap must be non-negative and less than max_chunk_size")
        self.max_chunk_size = max_chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk(self, document: Document) -> list[Chunk]:
        chunks: list[Chunk] = []
        global_index = 0
        for section in document.sections:
            for part_number, (text, start, end) in enumerate(self._split_section(section)):
                if not text:
                    continue
                section_slug = slugify(section.heading)
                chunk_id = f"{document.document_id}_structural_{section_slug}_{global_index:04d}"
                metadata = make_metadata(
                    document,
                    chunk_id=chunk_id,
                    chunk_index=global_index,
                    strategy=self.strategy,
                    text=text,
                    section=section.heading,
                    section_path=section.section_path,
                    heading_level=section.heading_level,
                    start_char=start,
                    end_char=end,
                )
                chunks.append(Chunk(chunk_id, text, metadata))
                global_index += 1
        return chunks

    def _split_section(self, section: MarkdownSection) -> list[tuple[str, int, int]]:
        if len(section.text) <= self.max_chunk_size:
            return [(section.text, section.start_char, section.end_char)]
        parts: list[tuple[str, int, int]] = []
        text = section.text
        start = 0
        while start < len(text):
            while start < len(text) and text[start].isspace():
                start += 1
            if start >= len(text):
                break
            limit = min(start + self.max_chunk_size, len(text))
            end = limit
            if limit < len(text):
                candidates = [text.rfind("\n\n", start + 1, limit + 1), text.rfind("\n", start + 1, limit + 1)]
                candidates.append(text.rfind(" ", start + 1, limit + 1))
                boundary = max(candidates)
                if boundary > start:
                    end = boundary
            part = text[start:end].strip()
            if part:
                parts.append((part, section.start_char + start, section.start_char + end))
            if end >= len(text):
                break
            start = max(end - self.chunk_overlap, start + 1)
        return parts
