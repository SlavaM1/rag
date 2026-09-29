from __future__ import annotations

import re
from abc import ABC, abstractmethod

from ..models import Chunk, ChunkMetadata, Document


def make_metadata(
    document: Document,
    *,
    chunk_id: str,
    chunk_index: int,
    strategy: str,
    text: str,
    section: str,
    section_path: str,
    heading_level: int | None,
    start_char: int,
    end_char: int,
) -> ChunkMetadata:
    return ChunkMetadata(
        source=document.source,
        file=document.file,
        title=document.title,
        section=section,
        section_path=section_path,
        chunk_id=chunk_id,
        chunk_index=chunk_index,
        chunk_strategy=strategy,
        document_id=document.document_id,
        heading_level=heading_level,
        char_count=len(text),
        word_count=len(re.findall(r"\S+", text)),
        start_char=start_char,
        end_char=end_char,
    )


class Chunker(ABC):
    strategy: str

    @abstractmethod
    def chunk(self, document: Document) -> list[Chunk]:
        raise NotImplementedError
