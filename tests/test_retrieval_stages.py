from app.rag.relevance_filter import RelevanceFilter


def test_similarity_filter_keeps_boundary_and_marks_rejected_candidates():
    candidates = [
        {"similarity_score": 0.36},
        {"similarity_score": 0.35},
        {"similarity_score": 0.34},
    ]
    filtered = RelevanceFilter().filter(candidates, 0.35)
    assert filtered == candidates[:2]
    assert [candidate["passed_threshold"] for candidate in candidates] == [True, True, False]


def test_similarity_filter_all_removed():
    candidates = [{"similarity_score": 0.2}]
    assert RelevanceFilter().filter(candidates, 0.35) == []
    assert candidates[0]["passed_threshold"] is False
