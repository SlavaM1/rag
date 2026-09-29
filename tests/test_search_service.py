from app.rag.config import Settings
from app.rag.search_service import SearchService
from app.rag.vector_store import VectorStore

from .conftest import FakeEmbeddingProvider, make_chunk


def test_search_service_uses_both_strategies_and_metadata(tmp_path):
    settings = Settings(tmp_path / "docs", tmp_path / "data", "fake", 100, 10, 200, 20, 5, 20, 1000)
    for strategy, vector in (("fixed", [1.0, 0.0, 1.0]), ("structural", [0.0, 1.0, 1.0])):
        store = VectorStore()
        store.add([make_chunk(strategy, f"{strategy} weather", strategy)], [vector])
        store.save(settings.index_path(strategy))
    service = SearchService(settings, FakeEmbeddingProvider())

    fixed = service.search("weather", "fixed", 1)
    structural = service.search("weather", "structural", 1)

    assert fixed[0]["chunk_id"] == "fixed"
    assert structural[0]["metadata"]["chunk_strategy"] == "structural"
    assert structural[0]["metadata"]["section_path"] == "Example > Section"
