from app.rag.chunking.fixed import FixedSizeChunker
from app.rag.chunking.structural import StructuralMarkdownChunker
from app.rag.loader import MarkdownLoader


def _document(tmp_path, body: str):
    docs = tmp_path / "docs" / "rag"
    docs.mkdir(parents=True)
    path = docs / "sample.md"
    path.write_text("---\ntitle: Sample\n---\n" + body, encoding="utf-8")
    return MarkdownLoader(docs, tmp_path).load(path)


def test_fixed_chunks_are_stable_nonempty_and_keep_metadata(tmp_path):
    document = _document(tmp_path, "# Sample\n" + ("alpha beta gamma " * 30))
    chunker = FixedSizeChunker(chunk_size=80, chunk_overlap=15)
    first = chunker.chunk(document)
    second = chunker.chunk(document)

    assert [chunk.chunk_id for chunk in first] == [chunk.chunk_id for chunk in second]
    assert all(chunk.text and len(chunk.text) <= 80 for chunk in first)
    assert first[0].metadata.chunk_strategy == "fixed"
    assert first[0].metadata.source == "docs/rag/sample.md"
    assert first[0].text[-10:].split()[-1] in first[1].text


def test_structural_chunks_keep_heading_hierarchy_and_fence(tmp_path):
    document = _document(tmp_path, "# Root\nIntro\n## Tools\n### get_weather\n```python\nrun()\n```\nDetails\n")
    chunks = StructuralMarkdownChunker(max_chunk_size=500, chunk_overlap=20).chunk(document)
    weather = next(chunk for chunk in chunks if chunk.metadata.section == "get_weather")

    assert weather.metadata.section_path == "Root > Tools > get_weather"
    assert "```python" in weather.text
    assert weather.metadata.heading_level == 3


def test_structural_splits_large_sections_with_overlap(tmp_path):
    document = _document(tmp_path, "# Root\n## Large\n" + ("long content words " * 100))
    chunks = StructuralMarkdownChunker(max_chunk_size=140, chunk_overlap=25).chunk(document)
    large = [chunk for chunk in chunks if chunk.metadata.section == "Large"]

    assert len(large) > 1
    assert all(chunk.metadata.char_count <= 140 for chunk in large)
    assert all(chunk.metadata.section_path == "Root > Large" for chunk in large)
