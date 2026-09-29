from fastapi.testclient import TestClient

from app.main import create_app


class StubSearchService:
    def search(self, query, strategy, top_k):
        return [{"score": 0.9, "chunk_id": "chunk", "text": "text", "metadata": {"file": "example.md"}}]


def test_health_and_search_api():
    client = TestClient(create_app(StubSearchService()))

    assert client.get("/health").json() == {"status": "ok"}
    response = client.post("/api/search", json={"query": "weather", "strategy": "fixed", "top_k": 1})
    assert response.status_code == 200
    assert response.json()["results"][0]["chunk_id"] == "chunk"


def test_search_api_validates_request():
    client = TestClient(create_app(StubSearchService()))

    assert client.post("/api/search", json={"query": "   "}).status_code == 422
    assert client.post("/api/search", json={"query": "weather", "strategy": "invalid"}).status_code == 422
    assert client.post("/api/search", json={"query": "weather", "top_k": 0}).status_code == 422
