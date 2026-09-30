from __future__ import annotations


class RelevanceFilter:
    def filter(self, candidates: list[dict[str, object]], threshold: float) -> list[dict[str, object]]:
        filtered: list[dict[str, object]] = []
        for candidate in candidates:
            passed = float(candidate["similarity_score"]) >= threshold
            candidate["passed_threshold"] = passed
            if passed:
                filtered.append(candidate)
        return filtered
