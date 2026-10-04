from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path


def post_json(url: str, payload: dict[str, object]) -> dict[str, object]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.load(response)


def quote_is_valid(quote: dict[str, object], sources: list[dict[str, object]]) -> bool:
    source = next(
        (item for item in sources if item.get("number") == quote.get("source_number")),
        None,
    )
    return bool(
        source
        and quote.get("chunk_id") == source.get("chunk_id")
        and isinstance(quote.get("quote"), str)
        and quote["quote"] in str(source.get("text", ""))
    )


def cell(value: object, limit: int = 180) -> str:
    text = " ".join(str(value).split()).replace("|", "\\|")
    return text if len(text) <= limit else f"{text[:limit - 3]}..."


def evaluate(base_url: str, dataset_path: Path) -> tuple[list[dict[str, object]], dict[str, int]]:
    dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
    rows: list[dict[str, object]] = []
    metrics = {"answered": 0, "with_sources": 0, "with_quotes": 0, "quotes": 0, "valid_quotes": 0}
    for item in dataset:
        try:
            result = post_json(
                f"{base_url.rstrip('/')}/api/chat",
                {
                    "question": item["question"],
                    "mode": "with_rag",
                    "retrieval_mode": "enhanced",
                    "model": "deepseek-flash",
                    "strategy": "structural",
                    "candidate_top_k": 15,
                    "final_top_k": 5,
                },
            )
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            rows.append({"item": item, "error": str(exc)})
            continue

        sources = result.get("sources") if isinstance(result.get("sources"), list) else []
        quotes = result.get("quotes") if isinstance(result.get("quotes"), list) else []
        valid = [quote_is_valid(quote, sources) for quote in quotes]
        if result.get("status") == "answered":
            metrics["answered"] += 1
            metrics["with_sources"] += int(bool(sources))
            metrics["with_quotes"] += int(bool(quotes))
        metrics["quotes"] += len(quotes)
        metrics["valid_quotes"] += sum(valid)
        rows.append({"item": item, "result": result, "quotes_valid": all(valid) and bool(valid)})
    return rows, metrics


def write_report(rows: list[dict[str, object]], metrics: dict[str, int], output: Path) -> None:
    lines = [
        "# Day 24 Grounding Evaluation",
        "",
        "Deterministic checks validate source presence, quote presence, source numbers, chunk IDs, and exact quote substrings. Semantic support remains a manual review item.",
        "",
        "| # | Question | Answer | Sources present | Quotes present | Quotes valid | Meaning supported |",
        "|---|---|---|---|---|---|---|",
    ]
    for index, row in enumerate(rows, start=1):
        item = row["item"]
        if "error" in row:
            lines.append(f"| {index} | {cell(item['question'])} | ERROR: {cell(row['error'])} | no | no | no | TODO/manual |")
            continue
        result = row["result"]
        sources = result.get("sources") or []
        quotes = result.get("quotes") or []
        lines.append(
            f"| {index} | {cell(item['question'])} | {cell(result.get('answer', ''))} | "
            f"{'yes' if sources else 'no'} | {'yes' if quotes else 'no'} | "
            f"{'yes' if row['quotes_valid'] else 'no'} | TODO/manual |"
        )
    answered = metrics["answered"]
    lines.extend(
        [
            "",
            "## Metrics",
            "",
            f"- Questions tested: {len(rows)}",
            f"- Answered RAG requests: {answered}",
            f"- Sources coverage: {metrics['with_sources']}/{answered}",
            f"- Quotes coverage: {metrics['with_quotes']}/{answered}",
            f"- Quote validation: {metrics['valid_quotes']}/{metrics['quotes']}",
            "- Semantic quote check: TODO/manual",
            "",
        ]
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Day 24 grounded RAG responses")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--dataset", type=Path, default=Path("evaluation/day24_questions.json"))
    parser.add_argument("--output", type=Path, default=Path("evaluation/day24_results.md"))
    arguments = parser.parse_args()
    evaluated_rows, evaluated_metrics = evaluate(arguments.base_url, arguments.dataset)
    write_report(evaluated_rows, evaluated_metrics, arguments.output)
    print(arguments.output)
