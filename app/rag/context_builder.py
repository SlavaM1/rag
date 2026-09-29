from __future__ import annotations


class ContextBuilder:
    def build(self, sources: list[dict[str, object]]) -> str:
        """Build a numbered context whose labels match the response sources."""
        parts: list[str] = []
        for source in sources:
            parts.append(
                "\n".join(
                    [
                        f"[SOURCE {source['number']}]",
                        f"File: {source['file']}",
                        f"Section: {source['section']}",
                        f"Section path: {source['section_path']}",
                        f"Chunk ID: {source['chunk_id']}",
                        f"Similarity: {source['score']:.4f}",
                        "Content:",
                        str(source["text"]),
                    ]
                )
            )
        return "\n\n".join(parts)
