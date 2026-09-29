from __future__ import annotations

import re
from pathlib import Path

import yaml

from .models import Document, Heading, MarkdownSection


FRONT_MATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", re.DOTALL)
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^\w]+", "-", value, flags=re.UNICODE)
    return value.strip("-") or "document"


class MarkdownLoader:
    """Loads only Markdown documents below the configured knowledge directory."""

    def __init__(self, documents_path: Path, project_root: Path) -> None:
        self.documents_path = documents_path
        self.project_root = project_root

    def load_all(self) -> list[Document]:
        return [self.load(path) for path in sorted(self.documents_path.rglob("*.md"))]

    def load(self, path: Path) -> Document:
        raw_text = path.read_text(encoding="utf-8")
        front_matter, text = self._split_front_matter(raw_text)
        headings, sections, code_blocks = self._parse_markdown(text)
        h1 = next((heading.text for heading in headings if heading.level == 1), "")
        title = str(front_matter.get("title") or h1 or path.stem)
        source = path.relative_to(self.project_root).as_posix()
        return Document(
            document_id=slugify(path.stem),
            source=source,
            file=path.name,
            raw_text=raw_text,
            text=text,
            front_matter=front_matter,
            title=title,
            h1=h1,
            headings=headings,
            sections=sections,
            code_blocks=code_blocks,
        )

    @staticmethod
    def _split_front_matter(raw_text: str) -> tuple[dict[str, object], str]:
        match = FRONT_MATTER_RE.match(raw_text)
        if not match:
            return {}, raw_text
        parsed = yaml.safe_load(match.group(1)) or {}
        if not isinstance(parsed, dict):
            raise ValueError("Markdown front matter must be a YAML mapping")
        return parsed, raw_text[match.end() :]

    @staticmethod
    def _parse_markdown(text: str) -> tuple[list[Heading], list[MarkdownSection], list[str]]:
        headings: list[Heading] = []
        code_blocks: list[str] = []
        in_fence = False
        fence_marker = ""
        fence_start = 0
        offset = 0
        for line in text.splitlines(keepends=True):
            fence_match = FENCE_RE.match(line)
            if fence_match:
                marker = fence_match.group(1)
                if not in_fence:
                    in_fence = True
                    fence_marker = marker
                    fence_start = offset
                elif marker == fence_marker:
                    code_blocks.append(text[fence_start : offset + len(line)])
                    in_fence = False
                    fence_marker = ""
            elif not in_fence:
                match = HEADING_RE.match(line.rstrip("\r\n"))
                if match:
                    headings.append(Heading(match.group(2).strip(), len(match.group(1)), offset))
            offset += len(line)

        sections: list[MarkdownSection] = []
        hierarchy: list[tuple[int, str]] = []
        for index, heading in enumerate(headings):
            hierarchy = [item for item in hierarchy if item[0] < heading.level]
            hierarchy.append((heading.level, heading.text))
            end_char = headings[index + 1].start_char if index + 1 < len(headings) else len(text)
            sections.append(
                MarkdownSection(
                    heading=heading.text,
                    heading_level=heading.level,
                    section_path=" > ".join(item[1] for item in hierarchy),
                    text=text[heading.start_char:end_char].strip(),
                    start_char=heading.start_char,
                    end_char=end_char,
                )
            )
        if not sections and text.strip():
            sections.append(MarkdownSection(title := "Document", 1, title, text.strip(), 0, len(text)))
        return headings, sections, code_blocks
