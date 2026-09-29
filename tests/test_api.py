from fastapi.testclient import TestClient

from app.main import create_app
from app.rag.chat_repository import ChatRepository
from app.rag.config import Settings
from app.rag.llm import LLMResponse
from app.rag.rag_service import RAGService


class StubSearchService:
    def search(self, query, strategy, top_k):
        return [{"score": 0.9, "chunk_id": "chunk", "text": "text", "metadata": {"file": "example.md"}}]


class FakeLLMProvider:
    async def generate(self, messages, model):
        return LLMResponse("Generated answer", model, 10, 5, 15, "stop")


def chat_client(tmp_path):
    settings = Settings(
        tmp_path / "docs", tmp_path / "data", "fake", 100, 10, 200, 20, 5, 20, 1000,
        None, "https://api.deepseek.com", "deepseek-flash", ("deepseek-flash", "deepseek-v4-pro"),
        0.2, 100, 10.0, 10, tmp_path / "rag.db",
    )
    repository = ChatRepository(settings.chat_database_path)
    rag_service = RAGService(settings, StubSearchService(), FakeLLMProvider(), repository)
    return TestClient(create_app(rag_service.search_service, rag_service, repository))


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


def test_chat_compare_and_history_apis(tmp_path):
    client = chat_client(tmp_path)
    response = client.post("/api/chat", json={"question": "Weather?", "mode": "with_rag", "model": "deepseek-flash"})

    assert response.status_code == 200
    chat_id = response.json()["chat_id"]
    assert response.json()["sources"][0]["chunk_id"] == "chunk"
    history = client.get(f"/api/chats/{chat_id}")
    assert [message["role"] for message in history.json()["messages"]] == ["user", "assistant"]
    comparison = client.post("/api/compare", json={"question": "Weather?", "model": "deepseek-v4-pro"})
    assert comparison.status_code == 200
    assert comparison.json()["without_rag"]["model"] == comparison.json()["with_rag"]["model"]
    assert client.delete(f"/api/chats/{chat_id}").json() == {"deleted": True}


def test_chat_api_rejects_unknown_model(tmp_path):
    client = chat_client(tmp_path)

    assert client.post("/api/chat", json={"question": "Weather?", "model": "gpt-whatever"}).status_code == 422
