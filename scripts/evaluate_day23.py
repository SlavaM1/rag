from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from statistics import mean
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.rag.config import PROJECT_ROOT, Settings
from app.rag.llm import DeepSeekProvider
from app.rag.query_rewriter import QueryRewriter
from app.rag.relevance_filter import RelevanceFilter
from app.rag.reranker import CrossEncoderReranker
from app.rag.search_service import SearchService


def _hit(results: list[dict[str, object]], expected: set[str], limit: int) -> bool:
    return any(str(item["metadata"]["file"]) in expected for item in results[:limit])  # type: ignore[index]


async def evaluate(settings: Settings) -> dict[str, object]:
    dataset = json.loads((PROJECT_ROOT / "evaluation" / "day23_questions.json").read_text(encoding="utf-8"))
    search = SearchService(settings)
    rewriter = QueryRewriter(DeepSeekProvider(settings), settings.query_rewrite_model)
    reranker = CrossEncoderReranker(settings.rerank_model)
    relevance_filter = RelevanceFilter()
    baseline_hits = {limit: 0 for limit in (1, 3, 5)}
    enhanced_hits = {limit: 0 for limit in (1, 3, 5)}
    threshold_stats = {threshold: {"kept": [], "empty": 0, "expected_retained": 0} for threshold in (0.2, 0.3, 0.4, 0.45, 0.5)}
    reports: list[dict[str, object]] = []
    for item in dataset:
        question = item["question"]
        expected = set(item["expected_sources"])
        baseline_started = perf_counter()
        baseline = await asyncio.to_thread(search.search, question, "structural", settings.final_top_k)
        baseline_ms = round((perf_counter() - baseline_started) * 1000, 2)
        for limit in baseline_hits:
            baseline_hits[limit] += int(_hit(baseline, expected, limit))

        rewrite_started = perf_counter()
        rewritten = await rewriter.rewrite(question) if settings.query_rewrite_enabled else question
        rewrite_ms = round((perf_counter() - rewrite_started) * 1000, 2)
        retrieval_started = perf_counter()
        candidates = await asyncio.to_thread(search.search, rewritten, "structural", settings.candidate_top_k)
        retrieval_ms = round((perf_counter() - retrieval_started) * 1000, 2)
        for threshold, values in threshold_stats.items():
            surviving = [candidate for candidate in candidates if float(candidate["similarity_score"]) >= threshold]
            values["kept"].append(len(surviving))
            values["empty"] += int(not surviving)
            values["expected_retained"] += int(_hit(surviving, expected, len(surviving)))
        filtered = relevance_filter.filter(candidates, settings.similarity_threshold) if settings.filter_enabled else candidates
        for candidate in filtered:
            candidate["passed_threshold"] = True
        rerank_started = perf_counter()
        reranked = await asyncio.to_thread(reranker.rerank, rewritten, filtered) if settings.rerank_enabled else filtered
        rerank_ms = round((perf_counter() - rerank_started) * 1000, 2) if filtered and settings.rerank_enabled else 0.0
        final = reranked[:settings.final_top_k]
        for limit in enhanced_hits:
            enhanced_hits[limit] += int(_hit(final, expected, limit))
        reports.append({
            "item": item, "rewritten": rewritten, "baseline": baseline, "enhanced": final,
            "candidate_count": len(candidates), "filtered_count": len(filtered), "final_count": len(final),
            "top1_changed": bool(final and candidates and final[0]["chunk_id"] != candidates[0]["chunk_id"]),
            "ordering_changed": [item["chunk_id"] for item in filtered] != [item["chunk_id"] for item in reranked],
            "timings": {"baseline_retrieval_ms": baseline_ms, "rewrite_ms": rewrite_ms, "retrieval_ms": retrieval_ms, "rerank_ms": rerank_ms},
        })
    count = len(reports)
    return {"reports": reports, "count": count, "threshold_stats": threshold_stats, "metrics": {
        "baseline": {limit: baseline_hits[limit] / count for limit in baseline_hits},
        "enhanced": {limit: enhanced_hits[limit] / count for limit in enhanced_hits},
        "avg_candidates": mean(item["candidate_count"] for item in reports),
        "avg_filtered": mean(item["filtered_count"] for item in reports),
        "avg_final": mean(item["final_count"] for item in reports),
        "top1_changed": sum(item["top1_changed"] for item in reports) / count,
        "ordering_changed": sum(item["ordering_changed"] for item in reports) / count,
        "baseline_retrieval_ms": mean(item["timings"]["baseline_retrieval_ms"] for item in reports),
        "rewrite_ms": mean(item["timings"]["rewrite_ms"] for item in reports),
        "rerank_ms": mean(item["timings"]["rerank_ms"] for item in reports),
        "enhanced_retrieval_ms": mean(item["timings"]["retrieval_ms"] for item in reports),
    }}


def write_report(result: dict[str, object], settings: Settings) -> Path:
    metrics = result["metrics"]
    lines = [
        "# Day 23 Retrieval Comparison", "", "## Configuration", "",
        f"Embedding model: `{settings.embedding_model}`", f"Reranker: `{settings.rerank_model}` (local CPU)",
        f"Similarity threshold: `{settings.similarity_threshold}`", f"Candidate Top-K: `{settings.candidate_top_k}`",
        f"Final Top-K: `{settings.final_top_k}`", "", "## Metrics", "",
        "| Metric | Baseline | Enhanced |", "|---|---:|---:|",
        f"| Hit@1 | {metrics['baseline'][1]:.3f} | {metrics['enhanced'][1]:.3f} |",
        f"| Hit@3 | {metrics['baseline'][3]:.3f} | {metrics['enhanced'][3]:.3f} |",
        f"| Hit@5 | {metrics['baseline'][5]:.3f} | {metrics['enhanced'][5]:.3f} |", "",
        "## Pipeline Metrics", "",
        f"Average candidates retrieved: {metrics['avg_candidates']:.2f}", f"Average chunks after threshold: {metrics['avg_filtered']:.2f}",
        f"Average final chunks: {metrics['avg_final']:.2f}", f"Queries where reranking changed Top-1: {metrics['top1_changed']:.1%}",
        f"Queries where reranking changed ordering: {metrics['ordering_changed']:.1%}",
        f"Average baseline retrieval time: {metrics['baseline_retrieval_ms']:.2f} ms", f"Average rewrite time: {metrics['rewrite_ms']:.2f} ms",
        f"Average rerank time: {metrics['rerank_ms']:.2f} ms", f"Average enhanced FAISS retrieval time: {metrics['enhanced_retrieval_ms']:.2f} ms", "",
        "## Threshold Tuning", "", "| Threshold | Average kept | Empty queries | Expected source retained |", "|---|---:|---:|---:|",
    ]
    for threshold, values in result["threshold_stats"].items():
        lines.append(f"| {threshold:.2f} | {mean(values['kept']):.2f} | {values['empty'] / result['count']:.1%} | {values['expected_retained'] / result['count']:.1%} |")
    lines.extend(["", "The configured threshold is selected from this small corpus-specific sweep by balancing retained expected sources against weak candidates; it must be revisited after changing the corpus, chunking, or embedding model.", "", "## Questions", ""])
    for report in result["reports"]:
        item = report["item"]
        lines.extend([f"### {item['id']}", "", f"Original query: {item['question']}", "", f"Rewritten query: {report['rewritten']}", "", f"Expected sources: {', '.join(item['expected_sources'])}", "", "Baseline retrieval:"])
        lines.extend([f"{rank}. {result['metadata']['file']} | {result['metadata'].get('section_path', '')} | score {result['score']:.4f}" for rank, result in enumerate(report["baseline"], 1)])
        lines.extend(["", "Enhanced retrieval:"])
        lines.extend([f"{rank}. {result['metadata']['file']} | {result['metadata'].get('section_path', '')} | similarity {result['similarity_score']:.4f} | rerank {result.get('rerank_score')} | FAISS rank {result.get('original_rank')}" for rank, result in enumerate(report["enhanced"], 1)])
        lines.append("")
    lines.extend(["## Observations", "", "Metrics are generated from document-level expected sources. Enhanced is not declared superior by configuration: inspect the measured metrics and per-question ordering above. The threshold is a score cutoff for this normalized embedding/index pipeline, not a probability."])
    output = settings.data_path / "day23_comparison.md"
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return output


if __name__ == "__main__":
    configuration = Settings.from_env()
    print(write_report(asyncio.run(evaluate(configuration)), configuration))
