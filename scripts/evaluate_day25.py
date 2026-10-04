from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request
from pathlib import Path


def request_json(url: str, payload: dict[str, object] | None = None) -> dict[str, object]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"} if data else {},
        method="POST" if data else "GET",
    )
    with urllib.request.urlopen(request, timeout=180) as response:
        return json.load(response)


def quote_is_valid(quote: dict[str, object], sources: list[dict[str, object]]) -> bool:
    source = next((item for item in sources if item.get("number") == quote.get("source_number")), None)
    return bool(
        source
        and quote.get("chunk_id") == source.get("chunk_id")
        and isinstance(quote.get("quote"), str)
        and quote["quote"] in str(source.get("text", ""))
    )


def contains(value: object, expected: str) -> bool:
    return expected.casefold() in str(value or "").casefold()


def state_matches(state: dict[str, object], turn: dict[str, object]) -> bool:
    if expected := turn.get("expected_goal_contains"):
        if not contains(state.get("goal"), str(expected)):
            return False
    if expected := turn.get("expected_constraint_contains"):
        if not any(contains(item, str(expected)) for item in state.get("constraints", [])):
            return False
    if expected := turn.get("expected_term"):
        terms = state.get("terms") or {}
        if not isinstance(terms, dict):
            return False
        for key, value in expected.items():
            if not contains(terms.get(key), value):
                return False
    return True


def final_state_matches(state: dict[str, object], expected: dict[str, object]) -> dict[str, bool]:
    goal = all(contains(state.get("goal"), item) for item in expected.get("goal_contains", []))
    constraints = all(
        any(contains(value, item) for value in state.get("constraints", []))
        for item in expected.get("constraints_contain", [])
    )
    terms = state.get("terms") or {}
    terms_ok = isinstance(terms, dict) and all(contains(terms.get(key), value) for key, value in expected.get("terms", {}).items())
    return {"goal_preserved": goal, "constraints_preserved": constraints, "terms_preserved": terms_ok}


def evaluate(base_url: str, dataset_path: Path) -> list[dict[str, object]]:
    scenarios = json.loads(dataset_path.read_text(encoding="utf-8"))
    results: list[dict[str, object]] = []
    for scenario in scenarios:
        chat_id = None
        turns: list[dict[str, object]] = []
        for turn in scenario["turns"]:
            try:
                response = request_json(
                    f"{base_url.rstrip('/')}/api/chat",
                    {
                        "chat_id": chat_id,
                        "question": turn["message"],
                        "mode": "with_rag",
                        "retrieval_mode": "enhanced",
                        "model": "deepseek-flash",
                        "strategy": "structural",
                        "candidate_top_k": 15,
                        "final_top_k": 3,
                    },
                )
                chat_id = response["chat_id"]
                sources = response.get("sources") if isinstance(response.get("sources"), list) else []
                quotes = response.get("quotes") if isinstance(response.get("quotes"), list) else []
                state = response.get("task_state") if isinstance(response.get("task_state"), dict) else {}
                turns.append(
                    {
                        "response": response,
                        "state_expected": state_matches(state, turn),
                        "sources": bool(sources),
                        "quotes": bool(quotes),
                        "quotes_valid": bool(quotes) and all(quote_is_valid(quote, sources) for quote in quotes),
                        "retrieval": bool((response.get("retrieval") or {}).get("retrieval_performed")),
                    }
                )
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, KeyError) as exc:
                # An HTTP response from /api/chat is produced after this WITH RAG turn reached
                # retrieval; provider/grounding failures can happen later during generation.
                turns.append({"error": str(exc), "retrieval": isinstance(exc, urllib.error.HTTPError)})
                continue

        persisted = request_json(f"{base_url.rstrip('/')}/api/chats/{chat_id}") if chat_id else {}
        final_state = persisted.get("task_state") if isinstance(persisted.get("task_state"), dict) else {}
        checks = final_state_matches(final_state, scenario["final_expectations"])
        answered = [turn for turn in turns if turn.get("response", {}).get("status") == "answered"]
        source_sets = {
            tuple(source.get("chunk_id") for source in turn["response"].get("sources", []))
            for turn in answered
        }
        results.append(
            {
                "scenario": scenario,
                "chat_id": chat_id,
                "turns": turns,
                "final_state": final_state,
                "checks": checks,
                "answered": len(answered),
                "with_sources": sum(turn["sources"] for turn in answered),
                "with_quotes": sum(turn["quotes"] for turn in answered),
                "valid_quotes": sum(turn["quotes_valid"] for turn in answered),
                "retrieval_turns": sum(turn.get("retrieval", False) for turn in turns),
                "state_expectations": sum(turn.get("state_expected", False) for turn in turns),
                "source_sets": len(source_sets),
                "persisted": bool(persisted.get("messages")) and persisted.get("task_state") == final_state,
            }
        )
    return results


def write_report(results: list[dict[str, object]], output: Path) -> None:
    lines = [
        "# Day 25 Long Conversation Evaluation",
        "",
        "Deterministic checks only: persisted task-state fields, retrieval metadata, source/quote presence, and exact quote substrings. Answer semantics remain a manual review item.",
    ]
    for index, result in enumerate(results, start=1):
        scenario = result["scenario"]
        checks = result["checks"]
        messages = len(scenario["turns"])
        lines.extend(
            [
                "",
                f"## Scenario {index}: {scenario['title']}",
                "",
                f"- Chat ID: {result['chat_id']}",
                f"- Messages: {messages}",
                f"- Goal preserved: {'yes' if checks['goal_preserved'] else 'no'}",
                f"- Constraints preserved: {'yes' if checks['constraints_preserved'] else 'no'}",
                f"- Terms preserved: {'yes' if checks['terms_preserved'] else 'no'}",
                f"- Per-turn state expectations: {result['state_expectations']}/{messages}",
                f"- Retrieval performed: {result['retrieval_turns']}/{messages}",
                f"- API/provider errors: {sum('error' in turn for turn in result['turns'])}/{messages}",
                f"- Answered: {result['answered']}/{messages}",
                f"- Answers with sources: {result['with_sources']}/{result['answered']}",
                f"- Answers with quotes: {result['with_quotes']}/{result['answered']}",
                f"- Answers with valid quotes: {result['valid_quotes']}/{result['answered']}",
                f"- Distinct final source sets: {result['source_sets']}",
                f"- Messages and task state persisted: {'yes' if result['persisted'] else 'no'}",
                "- Final Task State:",
                "",
                "```json",
                json.dumps(result["final_state"], ensure_ascii=False, indent=2),
                "```",
            ]
        )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate Day 25 conversational RAG scenarios")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--dataset", type=Path, default=Path("evaluation/day25_scenarios.json"))
    parser.add_argument("--output", type=Path, default=Path("evaluation/day25_results.md"))
    arguments = parser.parse_args()
    evaluated = evaluate(arguments.base_url, arguments.dataset)
    write_report(evaluated, arguments.output)
    print(arguments.output)
