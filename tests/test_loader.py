from app.rag.loader import MarkdownLoader


def test_loader_extracts_front_matter_headings_and_fences(tmp_path):
    docs = tmp_path / "docs" / "rag"
    docs.mkdir(parents=True)
    path = docs / "guide.md"
    path.write_text("---\ntitle: Guide\nproject: test\n---\n# Main\nIntro\n\n## Child\n```python\nprint('ok')\n```\n", encoding="utf-8")

    document = MarkdownLoader(docs, tmp_path).load(path)

    assert document.front_matter == {"title": "Guide", "project": "test"}
    assert document.h1 == "Main"
    assert document.title == "Guide"
    assert [heading.text for heading in document.headings] == ["Main", "Child"]
    assert document.sections[1].section_path == "Main > Child"
    assert "print('ok')" in document.code_blocks[0]
    assert document.source == "docs/rag/guide.md"
