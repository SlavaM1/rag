from app.rag.vector_store import VectorStore

from .conftest import make_chunk


def test_vector_store_add_save_load_and_search(tmp_path):
    store = VectorStore()
    chunks = [make_chunk("weather", "weather data"), make_chunk("database", "database data")]
    store.add(chunks, [[1.0, 0.0], [0.0, 1.0]])
    store.save(tmp_path)

    loaded = VectorStore.load(tmp_path)
    results = loaded.search([0.9, 0.1], top_k=1)

    assert loaded.index.ntotal == 2
    assert results[0][1].chunk_id == "weather"
    assert results[0][1].metadata.file == "example.md"
