import asyncio
import json

import httpx
from fastapi.testclient import TestClient

from app.main import create_app
from app.rag.chat_repository import ChatRepository
from app.rag.config import Settings
from app.rag.llm import LLMResponse, OllamaProvider
from app.rag.rag_service import RAGService


class StubSearchService:
    def __init__(self):
        self.calls = []

    def search(self, query, strategy, top_k):
        self.calls.append((query, strategy, top_k))
        return [{
            "score": 0.9,
            "chunk_id": "chunk-1",
            "text": "exact local source text",
            "metadata": {
                "source": "docs/rag/example.md",
                "file": "example.md",
                "section": "Local",
                "section_path": "Example > Local",
            },
        }]


class FakeReranker:
    def rerank(self, query, chunks):
        for rank, chunk in enumerate(chunks, start=1):
            chunk["rerank_score"] = 1.0
            chunk["final_rank"] = rank
        return chunks


class PipelineProvider:
    def __init__(self):
        self.calls = []
        self.temperature = 0.2
        self.max_tokens = 1024

    async def generate(
        self, messages, model, json_mode=False, temperature=None, max_tokens=None
    ):
        self.calls.append({
            "messages": messages,
            "model": model,
            "json_mode": json_mode,
            "temperature": temperature,
            "max_tokens": max_tokens,
        })
        prompt = messages[0]["content"]
        if "структурированную память задачи" in prompt:
            content = json.dumps({
                "goal": None,
                "clarifications": [],
                "constraints": [],
                "terms": {},
                "decisions": [],
                "open_questions": [],
            })
        elif "semantic retrieval" in prompt:
            content = "Weather MCP local retrieval"
        elif "CONTEXT" in prompt:
            content = json.dumps({
                "answer": "Local grounded answer [1]",
                "citations": [{"source_number": 1, "quote": "exact local source text"}],
            })
        else:
            content = "Local answer"
        return LLMResponse(content, model, 10, 5, 15, "stop", "ollama")


class RecordingFactory:
    def __init__(self, provider, expected_provider="ollama"):
        self.provider = provider
        self.expected_provider = expected_provider
        self.created = []

    def create(self, provider_name):
        self.created.append(provider_name)
        if provider_name != self.expected_provider:
            raise AssertionError(f"Unexpected provider: {provider_name}")
        return self.provider


def make_settings(tmp_path):
    return Settings(
        tmp_path / "docs", tmp_path / "data", "fake", 100, 10, 200, 20, 5, 20, 1000,
        None, "https://api.deepseek.com", "deepseek-flash", ("deepseek-flash", "deepseek-v4-pro"),
        0.2, 100, 10.0, 10, tmp_path / "rag.db",
    )


def integration_client(tmp_path):
    settings = make_settings(tmp_path)
    search = StubSearchService()
    repository = ChatRepository(settings.chat_database_path)
    service = RAGService(
        settings,
        search,
        None,
        repository,
        reranker=FakeReranker(),
        provider_factory=lambda name: (_ for _ in ()).throw(AssertionError(name)),
    )
    provider = PipelineProvider()
    factory = RecordingFactory(provider)
    client = TestClient(create_app(search, service, repository, factory))
    return client, search, repository, provider, factory


def test_ollama_normalizes_usage_durations_and_rates(tmp_path):
    settings = make_settings(tmp_path)
    captured = {}

    def handler(request):
        captured.update(json.loads(request.content))
        return httpx.Response(200, json={
            "model": "qwen3:8b",
            "created_at": "2026-10-07T10:00:00Z",
            "message": {"role": "assistant", "content": " answer "},
            "done": True,
            "done_reason": "stop",
            "total_duration": 2_000_000_000,
            "load_duration": 100_000_000,
            "prompt_eval_count": 20,
            "prompt_eval_duration": 500_000_000,
            "eval_count": 10,
            "eval_duration": 250_000_000,
        })

    provider = OllamaProvider(settings, httpx.MockTransport(handler))
    response = asyncio.run(provider.generate(
        [{"role": "user", "content": "hello"}], "qwen3:8b", json_mode=True
    ))

    assert captured["stream"] is False
    assert captured["think"] is False
    assert captured["format"] == "json"
    assert response.content == "answer"
    assert (response.prompt_tokens, response.completion_tokens, response.total_tokens) == (20, 10, 30)
    assert response.metrics == {
        "prompt_eval_count": 20,
        "eval_count": 10,
        "input_tokens": 20,
        "output_tokens": 10,
        "total_tokens": 30,
        "total_duration_ms": 2000.0,
        "load_duration_ms": 100.0,
        "prompt_eval_duration_ms": 500.0,
        "eval_duration_ms": 250.0,
        "prompt_tokens_per_second": 40.0,
        "generation_tokens_per_second": 40.0,
    }
    assert response.provider_metrics["done"] is True


def test_integration_ollama_rag_off_skips_retrieval_and_forwards_history(tmp_path):
    client, search, repository, provider, factory = integration_client(tmp_path)

    response = client.post("/api/integration/chat", json={
        "request_id": "local-off",
        "question": "Continue",
        "messages": [
            {"role": "user", "content": "First"},
            {"role": "assistant", "content": "Second"},
        ],
        "provider": "ollama",
        "model": "qwen3:8b",
        "rag_enabled": False,
    })

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "answered"
    assert body["sources"] == []
    assert search.calls == []
    assert factory.created == ["ollama"]
    assert repository.list_chats() == []
    final_messages = provider.calls[-1]["messages"]
    assert [(item["role"], item["content"]) for item in final_messages[1:]] == [
        ("user", "First"),
        ("assistant", "Second"),
        ("user", "Continue"),
    ]
    assert body["metrics"]["history_messages_count"] == 2
    assert body["metrics"]["token_usage"] == {
        "input_tokens": 20,
        "output_tokens": 10,
        "total_tokens": 30,
    }


def test_integration_rag_on_uses_selected_provider_for_all_llm_stages(tmp_path):
    client, search, repository, provider, factory = integration_client(tmp_path)

    response = client.post("/api/integration/chat", json={
        "request_id": "local-on",
        "question": "How does it work?",
        "messages": [{"role": "user", "content": "Ask about Weather MCP"}],
        "provider": "ollama",
        "model": "qwen3:8b",
        "rag_enabled": True,
        "candidate_top_k": 3,
        "final_top_k": 1,
    })

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "answered"
    assert body["sources"][0]["original_rank"] == 1
    assert body["sources"][0]["final_rank"] == 1
    assert search.calls == [("Weather MCP local retrieval", "structural", 3)]
    assert factory.created == ["ollama"]
    assert repository.list_chats() == []
    assert len(provider.calls) == 3
    assert {call["model"] for call in provider.calls} == {"qwen3:8b"}
    assert body["metrics"]["rag_context_chunks"] == 1
    assert body["metrics"]["retrieval_counts"]["candidates_found"] == 1


def test_legacy_enhanced_chat_uses_deepseek_provider_for_query_rewrite(tmp_path):
    settings = make_settings(tmp_path)
    search = StubSearchService()
    repository = ChatRepository(settings.chat_database_path)
    provider = PipelineProvider()
    factory = RecordingFactory(provider, expected_provider="deepseek")
    service = RAGService(
        settings,
        search,
        None,
        repository,
        reranker=FakeReranker(),
        provider_factory=factory.create,
    )
    client = TestClient(create_app(search, service, repository, factory))

    response = client.post("/api/chat", json={
        "question": "How does it work?",
        "mode": "with_rag",
        "model": "deepseek-flash",
        "retrieval_mode": "enhanced",
        "candidate_top_k": 3,
        "final_top_k": 1,
    })

    assert response.status_code == 200
    assert factory.created == ["deepseek"]
    assert search.calls == [("Weather MCP local retrieval", "structural", 3)]


def test_integration_accepts_complete_history_larger_than_one_hundred_messages(tmp_path):
    client, search, _repository, _provider, factory = integration_client(tmp_path)
    messages = [
        {"role": "user" if index % 2 == 0 else "assistant", "content": f"message {index}"}
        for index in range(102)
    ]

    response = client.post("/api/integration/chat", json={
        "request_id": "long-history",
        "question": "Continue",
        "messages": messages,
        "provider": "ollama",
        "model": "qwen3:8b",
        "rag_enabled": False,
    })

    assert response.status_code == 200
    assert response.json()["metrics"]["history_messages_count"] == 102
    assert search.calls == []
    assert factory.created == ["ollama"]
