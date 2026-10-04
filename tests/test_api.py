import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.rag.chat_repository import ChatRepository
from app.rag.config import Settings
from app.rag.llm import LLMResponse
from app.rag.rag_service import RAGService


class StubSearchService:
    def __init__(self, score=0.9):
        self.score = score

    def search(self, query, strategy, top_k):
        return [{"score": self.score, "chunk_id": "chunk", "text": "exact source text", "metadata": {
            "source": "docs/rag/example.md", "file": "example.md", "section": "Section",
            "section_path": "Example > Section",
        }}]


class FakeLLMProvider:
    def __init__(self):
        self.calls = []

    async def generate(self, messages, model):
        self.calls.append((messages, model))
        content = "Generated answer"
        if "CONTEXT" in messages[0]["content"]:
            content = json.dumps({
                "answer": "Generated answer [1]",
                "citations": [{"source_number": 1, "quote": "exact source text"}],
            })
        return LLMResponse(content, model, 10, 5, 15, "stop")


class FakeRewriter:
    async def rewrite(self, question):
        return question


class FakeReranker:
    def rerank(self, query, chunks):
        for rank, chunk in enumerate(chunks, start=1):
            chunk["rerank_score"] = float(rank)
            chunk["final_rank"] = rank
        return chunks


def chat_client(tmp_path, score=0.9):
    settings = Settings(
        tmp_path / "docs", tmp_path / "data", "fake", 100, 10, 200, 20, 5, 20, 1000,
        None, "https://api.deepseek.com", "deepseek-flash", ("deepseek-flash", "deepseek-v4-pro"),
        0.2, 100, 10.0, 10, tmp_path / "rag.db",
    )
    repository = ChatRepository(settings.chat_database_path)
    rag_service = RAGService(settings, StubSearchService(score), FakeLLMProvider(), repository, query_rewriter=FakeRewriter(), reranker=FakeReranker())
    return TestClient(create_app(rag_service.search_service, rag_service, repository))


def test_health_and_search_api():
    client = TestClient(create_app(StubSearchService()))

    assert client.get("/health").json()["status"] == "ok"
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
    assert response.json()["status"] == "answered"
    assert response.json()["sources"][0]["chunk_id"] == "chunk"
    assert response.json()["sources"][0]["source"] == "docs/rag/example.md"
    assert response.json()["quotes"][0]["quote"] == "exact source text"
    history = client.get(f"/api/chats/{chat_id}")
    assert [message["role"] for message in history.json()["messages"]] == ["user", "assistant"]
    comparison = client.post("/api/compare", json={"question": "Weather?", "model": "deepseek-v4-pro"})
    assert comparison.status_code == 200
    assert comparison.json()["without_rag"]["model"] == comparison.json()["with_rag"]["model"]
    enhanced = client.post("/api/chat", json={"question": "Weather?", "retrieval_mode": "enhanced", "candidate_top_k": 3, "final_top_k": 1})
    assert enhanced.status_code == 200
    assert enhanced.json()["retrieval_mode"] == "enhanced"
    retrieval_comparison = client.post("/api/compare-retrieval", json={"question": "Weather?", "candidate_top_k": 3, "final_top_k": 1})
    assert retrieval_comparison.status_code == 200
    assert retrieval_comparison.json()["baseline"]["retrieval_mode"] == "baseline"
    assert client.post("/api/compare-retrieval", json={"question": "Weather?", "candidate_top_k": 1, "final_top_k": 2}).status_code == 422
    assert client.delete(f"/api/chats/{chat_id}").json() == {"deleted": True}


def test_chat_api_returns_insufficient_context_as_a_normal_result(tmp_path):
    client = chat_client(tmp_path, score=0.3)

    response = client.post("/api/chat", json={"question": "Toyota?", "mode": "with_rag"})

    assert response.status_code == 200
    assert response.json()["status"] == "insufficient_context"
    assert response.json()["sources"] == []
    assert response.json()["quotes"] == []
    assert "Уточните" in response.json()["answer"]
    assert client.app.state.rag_service.llm_provider.calls == []


def test_chat_api_rejects_unknown_model(tmp_path):
    client = chat_client(tmp_path)

    assert client.post("/api/chat", json={"question": "Weather?", "model": "gpt-whatever"}).status_code == 422
