import asyncio
from dataclasses import replace

from app.rag.chat_repository import ChatRepository
from app.rag.config import Settings
from app.rag.llm import LLMResponse
from app.rag.rag_service import ChatMode, DeepSeekModel, RAGService, RetrievalMode


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


class FakeRewriter:
    def __init__(self, rewritten="Weather MCP forecast"):
        self.rewritten = rewritten
        self.calls = []

    async def rewrite(self, question):
        self.calls.append(question)
        return self.rewritten


class FakeReranker:
    def __init__(self):
        self.calls = []

    def rerank(self, query, chunks):
        self.calls.append((query, chunks))
        for rank, chunk in enumerate(reversed(chunks), start=1):
            chunk["rerank_score"] = float(rank)
            chunk["final_rank"] = rank
        return list(reversed(chunks))


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
    rewriter, reranker = FakeRewriter(), FakeReranker()
    return RAGService(settings, search, provider, repository, query_rewriter=rewriter, reranker=reranker), search, provider, repository


def test_without_rag_does_not_retrieve(tmp_path):
    service, search, provider, _ = make_service(tmp_path)

    result = asyncio.run(service.generate("What is Weather MCP?", ChatMode.WITHOUT_RAG, DeepSeekModel.FLASH))

    assert search.calls == []
    assert result.sources == []
    assert provider.calls[0][1] == "deepseek-flash"
    assert "CONTEXT" not in provider.calls[0][0][0]["content"]


def test_with_rag_retrieves_and_includes_structured_context(tmp_path):
    service, search, provider, _ = make_service(tmp_path)

    result = asyncio.run(service.generate("What is Weather MCP?", ChatMode.WITH_RAG, DeepSeekModel.FLASH, 3, "structural", retrieval_mode=RetrievalMode.BASELINE))

    assert search.calls == [("What is Weather MCP?", "structural", 3)]
    assert service.query_rewriter.calls == []
    assert service.reranker.calls == []
    assert result.sources[0]["file"] == "08-weather-mcp.md"
    prompt = provider.calls[0][0][0]["content"]
    assert "[SOURCE 1]" in prompt
    assert "weather-1" in prompt


def test_enhanced_rewrites_retrieves_filters_reranks_and_answers_original_question(tmp_path):
    service, search, provider, _ = make_service(tmp_path)

    result = asyncio.run(service.generate(
        "А weather как прогноз получает?", ChatMode.WITH_RAG, DeepSeekModel.FLASH,
        strategy="structural", retrieval_mode=RetrievalMode.ENHANCED, candidate_top_k=3, final_top_k=1,
    ))

    assert search.calls == [("Weather MCP forecast", "structural", 3)]
    assert result.rewritten_query == "Weather MCP forecast"
    assert result.retrieval["candidates_found"] == 1
    assert provider.calls[-1][0][-1]["content"] == "А weather как прогноз получает?"
    assert result.sources[0]["rerank_score"] == 1.0


def test_enhanced_all_filtered_gives_llm_an_explicit_no_context_instruction(tmp_path):
    service, search, provider, _ = make_service(tmp_path)
    service.settings = replace(service.settings, similarity_threshold=0.95)

    result = asyncio.run(service.generate(
        "Weather?", ChatMode.WITH_RAG, DeepSeekModel.FLASH, retrieval_mode=RetrievalMode.ENHANCED
    ))

    assert search.calls == [("Weather MCP forecast", "structural", 15)]
    assert result.sources == []
    assert result.retrieval["after_filter"] == 0
    assert "не найдено достаточно релевантной" in provider.calls[-1][0][0]["content"]


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
    assert assistant["retrieval_mode"] == "enhanced"
    assert assistant["rewritten_query"] == "Weather MCP forecast"
