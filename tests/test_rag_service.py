import json
import asyncio
from dataclasses import replace

from app.rag.chat_repository import ChatRepository
from app.rag.config import Settings
from app.rag.context_quality import ContextQualityChecker
from app.rag.llm import LLMResponse
from app.rag.rag_service import AnswerStatus, ChatMode, DeepSeekModel, RAGService, RetrievalMode
from app.rag.task_state import TaskState, TaskStateUpdate


class StubSearchService:
    def __init__(self):
        self.calls = []

    def search(self, query, strategy, top_k):
        self.calls.append((query, strategy, top_k))
        return [{
            "score": 0.91,
            "chunk_id": "weather-1",
            "text": "Weather MCP exposes current weather.",
            "metadata": {"source": "docs/rag/08-weather-mcp.md", "file": "08-weather-mcp.md", "section": "Назначение", "section_path": "Weather MCP > Назначение"},
        }]


class FakeLLMProvider:
    def __init__(self):
        self.calls = []

    async def generate(self, messages, model, json_mode=False):
        self.calls.append((messages, model))
        content = "Fake answer"
        if "CONTEXT" in messages[0]["content"]:
            content = json.dumps({
                "answer": "Weather MCP exposes current weather [1].",
                "citations": [{"source_number": 1, "quote": "Weather MCP exposes current weather."}],
            })
        return LLMResponse(content, model, 11, 7, 18, "stop")


class FakeRewriter:
    def __init__(self, rewritten="Weather MCP forecast"):
        self.rewritten = rewritten
        self.calls = []

    async def rewrite(self, question, conversational_context=None):
        self.calls.append((question, conversational_context))
        return self.rewritten


class RepairingLLMProvider:
    def __init__(self):
        self.calls = []

    async def generate(self, messages, model, json_mode=False):
        self.calls.append((messages, model))
        quote = "Invented quote" if len(self.calls) == 1 else "Weather MCP exposes current weather."
        return LLMResponse(json.dumps({
            "answer": "Weather MCP exposes current weather [1].",
            "citations": [{"source_number": 1, "quote": quote}],
        }), model, 5, 5, 10, "stop")


class FakeReranker:
    def __init__(self):
        self.calls = []

    def rerank(self, query, chunks):
        self.calls.append((query, chunks))
        for rank, chunk in enumerate(reversed(chunks), start=1):
            chunk["rerank_score"] = float(rank)
            chunk["final_rank"] = rank
        return list(reversed(chunks))


class FakeTaskStateUpdater:
    def __init__(self, state=None):
        self.state = state
        self.calls = []

    async def update(self, current, user_message, recent_history):
        self.calls.append((current, user_message, recent_history))
        state = self.state or current
        return TaskStateUpdate(state, state != current)


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
    updater = FakeTaskStateUpdater()
    return RAGService(
        settings, search, provider, repository, query_rewriter=rewriter, reranker=reranker,
        task_state_updater=updater,
    ), search, provider, repository


def test_without_rag_does_not_retrieve(tmp_path):
    service, search, provider, _ = make_service(tmp_path)

    result = asyncio.run(service.generate("What is Weather MCP?", ChatMode.WITHOUT_RAG, DeepSeekModel.FLASH))

    assert search.calls == []
    assert result.sources == []
    assert result.quotes == []
    assert result.status == AnswerStatus.ANSWERED
    assert provider.calls[0][1] == "deepseek-flash"
    assert "CONTEXT" not in provider.calls[0][0][0]["content"]


def test_with_rag_retrieves_and_includes_structured_context(tmp_path):
    service, search, provider, _ = make_service(tmp_path)

    result = asyncio.run(service.generate("What is Weather MCP?", ChatMode.WITH_RAG, DeepSeekModel.FLASH, 3, "structural", retrieval_mode=RetrievalMode.BASELINE))

    assert search.calls == [("What is Weather MCP?", "structural", 3)]
    assert service.query_rewriter.calls == []
    assert service.reranker.calls == []
    assert result.sources[0]["file"] == "08-weather-mcp.md"
    assert result.sources[0]["source"] == "docs/rag/08-weather-mcp.md"
    assert result.quotes[0]["quote"] == "Weather MCP exposes current weather."
    assert result.status == AnswerStatus.ANSWERED
    prompt = provider.calls[0][0][0]["content"]
    assert "[SOURCE 1]" in prompt
    assert "weather-1" in prompt
    assert "только на основании CONTEXT" in prompt
    assert "Не придумывай источники и цитаты" in prompt
    assert "source_number" in prompt


def test_enhanced_rewrites_retrieves_filters_reranks_and_answers_original_question(tmp_path):
    service, search, provider, _ = make_service(tmp_path)

    result = asyncio.run(service.generate(
        "А weather как прогноз получает?", ChatMode.WITH_RAG, DeepSeekModel.FLASH,
        strategy="structural", retrieval_mode=RetrievalMode.ENHANCED, candidate_top_k=3, final_top_k=1,
    ))

    assert search.calls == [("Weather MCP forecast", "structural", 3)]
    assert result.rewritten_query == "Weather MCP forecast"
    assert service.query_rewriter.calls[0][0] == "А weather как прогноз получает?"
    assert "CURRENT QUESTION" in service.query_rewriter.calls[0][1]
    assert result.retrieval["candidates_found"] == 1
    assert provider.calls[-1][0][-1]["content"] == "А weather как прогноз получает?"
    assert result.sources[0]["rerank_score"] == 1.0


def test_enhanced_all_filtered_returns_controlled_response_without_answer_generation(tmp_path):
    service, search, provider, _ = make_service(tmp_path)
    service.settings = replace(service.settings, similarity_threshold=0.95)

    result = asyncio.run(service.generate(
        "Weather?", ChatMode.WITH_RAG, DeepSeekModel.FLASH, retrieval_mode=RetrievalMode.ENHANCED
    ))

    assert search.calls == [("Weather MCP forecast", "structural", 15)]
    assert result.sources == []
    assert result.quotes == []
    assert result.status == AnswerStatus.INSUFFICIENT_CONTEXT
    assert result.retrieval["after_filter"] == 0
    assert result.retrieval["context_status"] == "insufficient"
    assert "Уточните" in result.answer
    assert provider.calls == []


def test_invalid_quote_gets_one_controlled_repair_attempt(tmp_path):
    service, _, _, _ = make_service(tmp_path)
    provider = RepairingLLMProvider()
    service.llm_provider = provider

    result = asyncio.run(service.generate(
        "Weather?", ChatMode.WITH_RAG, DeepSeekModel.FLASH, retrieval_mode=RetrievalMode.BASELINE
    ))

    assert len(provider.calls) == 2
    assert result.quotes[0]["quote"] == "Weather MCP exposes current weather."
    assert result.usage["total_tokens"] == 20


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
    assert assistant["status"] == "answered"
    assert assistant["quotes"] == result.quotes
    assert assistant["retrieval_mode"] == "enhanced"
    assert assistant["rewritten_query"] == "Weather MCP forecast"
    assert stored["task_state"] == TaskState().model_dump(mode="json")


def test_retrieval_runs_for_every_conversational_rag_turn(tmp_path):
    service, search, _, _ = make_service(tmp_path)

    chat_id, _ = asyncio.run(service.ask("Weather?", ChatMode.WITH_RAG, DeepSeekModel.FLASH))
    asyncio.run(service.ask("А где он хранится?", ChatMode.WITH_RAG, DeepSeekModel.FLASH, chat_id=chat_id))

    assert len(search.calls) == 2
    assert len(service.query_rewriter.calls) == 2


def test_task_state_constraint_is_used_after_it_leaves_recent_history(tmp_path):
    service, _, provider, _ = make_service(tmp_path)
    state = TaskState(
        goal="Понять scheduler storage",
        constraints=["рассматривать только backend"],
        terms={"scheduler": "APScheduler"},
    )

    result = asyncio.run(service.generate(
        "А где он хранится?", ChatMode.WITH_RAG, DeepSeekModel.FLASH,
        history=[{"role": "user", "content": "Поздний вопрос без старого ограничения"}],
        task_state=state,
    ))

    rewrite_context = service.query_rewriter.calls[0][1]
    assert "рассматривать только backend" in rewrite_context
    assert "scheduler = APScheduler" in rewrite_context
    assert "Task State describes user goals" in provider.calls[-1][0][0]["content"]
    assert result.retrieval["constraints_used"] == ["рассматривать только backend"]


def test_task_state_does_not_bypass_weak_context_guard(tmp_path):
    service, _, provider, _ = make_service(tmp_path)
    service.context_quality_checker = ContextQualityChecker(0.95)

    result = asyncio.run(service.generate(
        "В какой таблице?", ChatMode.WITH_RAG, DeepSeekModel.FLASH,
        task_state=TaskState(goal="Проверить PostgreSQL", decisions=["Пользователь предполагает PostgreSQL"]),
    ))

    assert result.status == AnswerStatus.INSUFFICIENT_CONTEXT
    assert result.sources == []
    assert result.quotes == []
    assert provider.calls == []
