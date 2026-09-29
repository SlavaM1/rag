from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class Heading:
    text: str
    level: int
    start_char: int


@dataclass(frozen=True)
class MarkdownSection:
    heading: str
    heading_level: int
    section_path: str
    text: str
    start_char: int
    end_char: int


@dataclass(frozen=True)
class Document:
    document_id: str
    source: str
    file: str
    raw_text: str
    text: str
    front_matter: dict[str, object]
    title: str
    h1: str
    headings: list[Heading]
    sections: list[MarkdownSection]
    code_blocks: list[str]


@dataclass(frozen=True)
class ChunkMetadata:
    source: str
    file: str
    title: str
    section: str
    section_path: str
    chunk_id: str
    chunk_index: int
    chunk_strategy: str
    document_id: str
    heading_level: int | None
    char_count: int
    word_count: int
    start_char: int
    end_char: int

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    text: str
    metadata: ChunkMetadata
