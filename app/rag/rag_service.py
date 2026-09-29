from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum

from .chat_repository import ChatRepository
from .config import Settings
from .context_builder import ContextBuilder
from .llm import LLMProvider, LLMResponse
from .search_service import SearchService


class ChatMode(str, Enum):
    WITHOUT_RAG = "without_rag"
    WITH_RAG = "with_rag"


class DeepSeekModel(str, Enum):
    FLASH = "deepseek-flash"
    PRO = "deepseek-v4-pro"


WITHOUT_RAG_PROMPT = """Ответь на вопрос пользователя максимально точно и понятно.
Если не знаешь специфическую информацию, не выдумывай её.
Отвечай на языке вопроса пользователя."""

WITH_RAG_PROMPT = """Ты отвечаешь на вопрос пользователя на основании предоставленного контекста базы знаний.
Используй факты из CONTEXT. Не выдумывай детали, которых нет в контексте.
Если информации недостаточно, прямо скажи, что предоставленных источников недостаточно.
При использовании фактов указывай ссылки вида [1], [2] и так далее, соответствующие SOURCE.
Отвечай на языке вопроса пользователя."""


@dataclass(frozen=True)
class ChatResult:
    answer: str
    model: str
    mode: ChatMode
    sources: list[dict[str, object]]
    usage: dict[str, int | None]
    strategy: str
    top_k: int


class RAGService:
    def __init__(
        self,
        settings: Settings,
        search_service: SearchService,
        llm_provider: LLMProvider,
        chat_repository: ChatRepository,
        context_builder: ContextBuilder | None = None,
    ) -> None:
        self.settings = settings
        self.search_service = search_service
        self.llm_provider = llm_provider
        self.chat_repository = chat_repository
        self.context_builder = context_builder or ContextBuilder()

    async def ask(
        self,
        question: str,
        mode: ChatMode,
        model: DeepSeekModel,
        top_k: int = 5,
        strategy: str = "structural",
        chat_id: int | None = None,
    ) -> tuple[int, ChatResult]:
        if chat_id is None:
            chat_id = int(self.chat_repository.create_chat(self._title(question))["id"])
        history = self.chat_repository.recent_messages(chat_id, self.settings.chat_history_messages)
        self.chat_repository.add_user_message(chat_id, question)
        result = await self.generate(question, mode, model, top_k, strategy, history)
        self.chat_repository.add_assistant_message(chat_id, result.answer, result.mode.value, result.model, result.usage, result.sources)
        return chat_id, result

    async def generate(
        self,
        question: str,
        mode: ChatMode,
        model: DeepSeekModel,
        top_k: int = 5,
        strategy: str = "structural",
        history: list[dict[str, str]] | None = None,
    ) -> ChatResult:
        sources: list[dict[str, object]] = []
        if mode == ChatMode.WITH_RAG:
            # SentenceTransformer can load/download on the first query; do not block health checks.
            matches = await asyncio.to_thread(self.search_service.search, question, strategy, top_k)
            sources = [self._source(number, match) for number, match in enumerate(matches, start=1)]
            system_prompt = f"{WITH_RAG_PROMPT}\n\nCONTEXT\n\n{self.context_builder.build(sources)}"
        else:
            system_prompt = WITHOUT_RAG_PROMPT

        messages = [{"role": "system", "content": system_prompt}, *(history or []), {"role": "user", "content": question}]
        response = await self.llm_provider.generate(messages, model.value)
        return self._result(response, mode, sources, strategy, top_k)

    async def compare(
        self, question: str, model: DeepSeekModel, top_k: int = 5, strategy: str = "structural"
    ) -> tuple[ChatResult, ChatResult]:
        without_rag = await self.generate(question, ChatMode.WITHOUT_RAG, model, top_k, strategy)
        with_rag = await self.generate(question, ChatMode.WITH_RAG, model, top_k, strategy)
        return without_rag, with_rag

    @staticmethod
    def _title(question: str) -> str:
        return question.strip().replace("\n", " ")[:80] or "New chat"

    @staticmethod
    def _source(number: int, match: dict[str, object]) -> dict[str, object]:
        metadata = match["metadata"]
        assert isinstance(metadata, dict)
        return {
            "number": number,
            "score": match["score"],
            "chunk_id": match["chunk_id"],
            "file": metadata.get("file", ""),
            "section": metadata.get("section", ""),
            "section_path": metadata.get("section_path", ""),
            "text": match["text"],
        }

    @staticmethod
    def _result(
        response: LLMResponse,
        mode: ChatMode,
        sources: list[dict[str, object]],
        strategy: str,
        top_k: int,
    ) -> ChatResult:
        return ChatResult(
            answer=response.content,
            model=response.model,
            mode=mode,
            sources=sources,
            usage={
                "prompt_tokens": response.prompt_tokens,
                "completion_tokens": response.completion_tokens,
                "total_tokens": response.total_tokens,
            },
            strategy=strategy,
            top_k=top_k,
        )
