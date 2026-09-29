import asyncio

from app.rag.chat_repository import ChatRepository
from app.rag.config import Settings
from app.rag.llm import LLMResponse
from app.rag.rag_service import ChatMode, DeepSeekModel, RAGService


class StubSearchService:
    def __init__(self):
        self.calls = []

    def search(self, query, strategy, top_k):
        self.calls.append((query, strategy, top_k))
        return [{
            "score": 0.91,
            "chunk_id": "weather-1",
            "text": "Weather MCP exposes current weather.",
            "metadata": {"file": "08-weather-mcp.md", "section": "Назначение", "section_path": "Weather MCP > Назначение"},
        }]


class FakeLLMProvider:
    def __init__(self):
        self.calls = []

    async def generate(self, messages, model):
        self.calls.append((messages, model))
        return LLMResponse("Fake answer", model, 11, 7, 18, "stop")


def make_settings(tmp_path):
    return Settings(
        tmp_path / "docs", tmp_path / "data", "fake", 100, 10, 200, 20, 5, 20, 1000,
        None, "https://api.deepseek.com", "deepseek-flash", ("deepseek-flash", "deepseek-v4-pro"),
        0.2, 100, 10.0, 10, tmp_path / "rag.db",
    )


def make_service(tmp_path):
    settings = make_settings(tmp_path)
    search = StubSearchService()
    provider = FakeLLMProvider()
    repository = ChatRepository(settings.chat_database_path)
    return RAGService(settings, search, provider, repository), search, provider, repository


def test_without_rag_does_not_retrieve(tmp_path):
    service, search, provider, _ = make_service(tmp_path)

    result = asyncio.run(service.generate("What is Weather MCP?", ChatMode.WITHOUT_RAG, DeepSeekModel.FLASH))

    assert search.calls == []
    assert result.sources == []
    assert provider.calls[0][1] == "deepseek-flash"
    assert "CONTEXT" not in provider.calls[0][0][0]["content"]


def test_with_rag_retrieves_and_includes_structured_context(tmp_path):
    service, search, provider, _ = make_service(tmp_path)

    result = asyncio.run(service.generate("What is Weather MCP?", ChatMode.WITH_RAG, DeepSeekModel.FLASH, 3, "structural"))

    assert search.calls == [("What is Weather MCP?", "structural", 3)]
    assert result.sources[0]["file"] == "08-weather-mcp.md"
    prompt = provider.calls[0][0][0]["content"]
    assert "[SOURCE 1]" in prompt
    assert "weather-1" in prompt


def test_compare_uses_the_same_model_for_both_branches(tmp_path):
    service, search, provider, _ = make_service(tmp_path)

    without_rag, with_rag = asyncio.run(service.compare("Weather?", DeepSeekModel.PRO, 2, "fixed"))

    assert [call[1] for call in provider.calls] == ["deepseek-v4-pro", "deepseek-v4-pro"]
    assert without_rag.mode == ChatMode.WITHOUT_RAG
    assert with_rag.mode == ChatMode.WITH_RAG
    assert search.calls == [("Weather?", "fixed", 2)]


def test_chat_history_and_sources_persist_in_sqlite(tmp_path):
    service, _, _, repository = make_service(tmp_path)

    chat_id, result = asyncio.run(service.ask("Weather?", ChatMode.WITH_RAG, DeepSeekModel.FLASH))
    stored = ChatRepository(repository.database_path).get_chat(chat_id)

    assert stored["title"] == "Weather?"
    assert [message["role"] for message in stored["messages"]] == ["user", "assistant"]
    assistant = stored["messages"][1]
    assert assistant["model"] == "deepseek-flash"
    assert assistant["usage"]["total_tokens"] == 18
    assert assistant["sources"][0]["chunk_id"] == result.sources[0]["chunk_id"]
