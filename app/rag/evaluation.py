from __future__ import annotations

import json
from pathlib import Path

from .config import PROJECT_ROOT, Settings
from .indexer import chunk_statistics, corpus_statistics
from .loader import MarkdownLoader
from .search_service import SearchService


def _hit(results: list[dict[str, object]], expected_files: set[str], limit: int) -> bool:
    return any(str(result["metadata"]["file"]) in expected_files for result in results[:limit])  # type: ignore[index]


def compare(settings: Settings | None = None) -> dict[str, object]:
    settings = settings or Settings.from_env()
    dataset_path = PROJECT_ROOT / "evaluation" / "dataset.json"
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    service = SearchService(settings)
    reports: list[dict[str, object]] = []
    metrics = {strategy: {1: 0, 3: 0, 5: 0} for strategy in ("fixed", "structural")}
    for item in dataset:
        expected_files = set(item["expected_files"])
        entry: dict[str, object] = {"query": item["query"], "expected_files": item["expected_files"], "results": {}}
        for strategy in ("fixed", "structural"):
            results = service.search(item["query"], strategy, 5)
            entry["results"][strategy] = results  # type: ignore[index]
            for limit in (1, 3, 5):
                metrics[strategy][limit] += int(_hit(results, expected_files, limit))
        reports.append(entry)
    count = len(dataset)
    return {
        "dataset": dataset,
        "reports": reports,
        "metrics": {strategy: {limit: round(value / count, 3) for limit, value in values.items()} for strategy, values in metrics.items()},
    }


def write_report(result: dict[str, object], settings: Settings | None = None) -> Path:
    settings = settings or Settings.from_env()
    loader = MarkdownLoader(settings.documents_path, settings.documents_path.parents[1])
    documents = loader.load_all()
    from .chunking import FixedSizeChunker, StructuralMarkdownChunker

    fixed_chunks = [chunk for document in documents for chunk in FixedSizeChunker(settings.fixed_chunk_size, settings.fixed_chunk_overlap).chunk(document)]
    structural_chunks = [chunk for document in documents for chunk in StructuralMarkdownChunker(settings.structural_max_chunk_size, settings.structural_overlap).chunk(document)]
    corpus = corpus_statistics(documents)
    fixed_stats = chunk_statistics(fixed_chunks)
    structural_stats = chunk_statistics(structural_chunks)
    metrics = result["metrics"]
    lines = [
        "# Chunking Strategy Comparison",
        "",
        "## Dataset",
        "",
        f"Documents: {corpus['documents']}",
        f"Words: {corpus['words']}",
        f"Queries: {len(result['dataset'])}",
        "",
        "## Fixed Size",
        "",
        f"chunk_size: {settings.fixed_chunk_size}",
        f"overlap: {settings.fixed_chunk_overlap}",
        f"chunks: {fixed_stats['chunks']}",
        f"average size: {fixed_stats['average_chars']}",
        f"min size: {fixed_stats['min_chars']}",
        f"max size: {fixed_stats['max_chars']}",
        "",
        "## Structural",
        "",
        f"max_chunk_size: {settings.structural_max_chunk_size}",
        f"overlap: {settings.structural_overlap}",
        f"chunks: {structural_stats['chunks']}",
        f"average size: {structural_stats['average_chars']}",
        f"min size: {structural_stats['min_chars']}",
        f"max size: {structural_stats['max_chars']}",
        "",
        "## Evaluation",
        "",
        "| Metric | Fixed | Structural |",
        "|---|---:|---:|",
        f"| Hit@1 | {metrics['fixed'][1]:.3f} | {metrics['structural'][1]:.3f} |",
        f"| Hit@3 | {metrics['fixed'][3]:.3f} | {metrics['structural'][3]:.3f} |",
        f"| Hit@5 | {metrics['fixed'][5]:.3f} | {metrics['structural'][5]:.3f} |",
        "",
        "## Queries",
        "",
    ]
    for number, report in enumerate(result["reports"], start=1):
        lines.extend([f"### Query {number}", "", str(report["query"]), "", f"Expected files: {', '.join(report['expected_files'])}", ""])
        for strategy in ("fixed", "structural"):
            lines.extend([f"{strategy.title()} results:", ""])
            for rank, search_result in enumerate(report["results"][strategy], start=1):
                metadata = search_result["metadata"]
                lines.append(f"{rank}. {metadata['file']} | {metadata['section_path']} | score {search_result['score']}")
            lines.append("")
    lines.extend(
        [
            "## Observations",
            "",
            "Scores and Hit@K values above are generated from the recorded document-level relevance set. Results can differ after changing the embedding model, chunk parameters, or documentation corpus.",
        ]
    )
    output = settings.data_path / "comparison.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output
