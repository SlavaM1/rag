from __future__ import annotations

import asyncio
from dataclasses import dataclass
from enum import Enum
from time import perf_counter

from .chat_repository import ChatRepository
from .config import Settings
from .context_builder import ContextBuilder
from .llm import LLMProvider, LLMResponse
from .query_rewriter import QueryRewriter
from .relevance_filter import RelevanceFilter
from .reranker import CrossEncoderReranker, Reranker
from .search_service import SearchService


class ChatMode(str, Enum):
    WITHOUT_RAG = "without_rag"
    WITH_RAG = "with_rag"


class RetrievalMode(str, Enum):
    BASELINE = "baseline"
    ENHANCED = "enhanced"


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

NO_RELEVANT_CONTEXT_PROMPT = """В базе знаний не найдено достаточно релевантной информации для уверенного ответа.
Сообщи это пользователю. Не отвечай знаниями модели и не придумывай источники."""


@dataclass(frozen=True)
class ChatResult:
    answer: str
    model: str
    mode: ChatMode
    retrieval_mode: RetrievalMode | None
    sources: list[dict[str, object]]
    usage: dict[str, int | None]
    strategy: str
    top_k: int
    original_question: str
    rewritten_query: str | None
    retrieval: dict[str, object] | None
    timings: dict[str, float]


class RAGService:
    def __init__(
        self,
        settings: Settings,
        search_service: SearchService,
        llm_provider: LLMProvider,
        chat_repository: ChatRepository,
        context_builder: ContextBuilder | None = None,
        query_rewriter: QueryRewriter | None = None,
        relevance_filter: RelevanceFilter | None = None,
        reranker: Reranker | None = None,
    ) -> None:
        self.settings = settings
        self.search_service = search_service
        self.llm_provider = llm_provider
        self.chat_repository = chat_repository
        self.context_builder = context_builder or ContextBuilder()
        self.query_rewriter = query_rewriter or QueryRewriter(llm_provider, settings.query_rewrite_model)
        self.relevance_filter = relevance_filter or RelevanceFilter()
        self.reranker = reranker or CrossEncoderReranker(settings.rerank_model)

    async def ask(
        self,
        question: str,
        mode: ChatMode,
        model: DeepSeekModel,
        top_k: int = 5,
        strategy: str = "structural",
        chat_id: int | None = None,
        retrieval_mode: RetrievalMode = RetrievalMode.ENHANCED,
        candidate_top_k: int | None = None,
        final_top_k: int | None = None,
    ) -> tuple[int, ChatResult]:
        if chat_id is None:
            chat_id = int(self.chat_repository.create_chat(self._title(question))["id"])
        history = self.chat_repository.recent_messages(chat_id, self.settings.chat_history_messages)
        self.chat_repository.add_user_message(chat_id, question)
        result = await self.generate(
            question, mode, model, top_k, strategy, history, retrieval_mode, candidate_top_k, final_top_k
        )
        self.chat_repository.add_assistant_message(
            chat_id, result.answer, result.mode.value, result.model, result.usage, result.sources,
            result.retrieval_mode.value if result.retrieval_mode else None, result.original_question,
            result.rewritten_query, result.retrieval,
        )
        return chat_id, result

    async def generate(
        self,
        question: str,
        mode: ChatMode,
        model: DeepSeekModel,
        top_k: int = 5,
        strategy: str = "structural",
        history: list[dict[str, str]] | None = None,
        retrieval_mode: RetrievalMode = RetrievalMode.ENHANCED,
        candidate_top_k: int | None = None,
        final_top_k: int | None = None,
    ) -> ChatResult:
        started = perf_counter()
        timings: dict[str, float] = {}
        sources: list[dict[str, object]] = []
        rewritten_query: str | None = None
        retrieval: dict[str, object] | None = None
        effective_final_top_k = final_top_k or top_k
        if mode == ChatMode.WITH_RAG:
            if retrieval_mode == RetrievalMode.BASELINE:
                sources, retrieval = await self._baseline(question, strategy, effective_final_top_k, timings)
            else:
                sources, rewritten_query, retrieval = await self._enhanced(
                    question, strategy, candidate_top_k or self.settings.candidate_top_k, effective_final_top_k, timings
                )
            system_prompt = self._rag_prompt(sources)
        else:
            retrieval_mode = None
            system_prompt = WITHOUT_RAG_PROMPT

        generation_started = perf_counter()
        messages = [{"role": "system", "content": system_prompt}, *(history or []), {"role": "user", "content": question}]
        response = await self.llm_provider.generate(messages, model.value)
        timings["generation_ms"] = self._milliseconds(generation_started)
        timings["total_ms"] = self._milliseconds(started)
        return self._result(
            response, mode, retrieval_mode, sources, strategy, effective_final_top_k, question,
            rewritten_query, retrieval, timings,
        )

    async def compare(
        self, question: str, model: DeepSeekModel, top_k: int = 5, strategy: str = "structural"
    ) -> tuple[ChatResult, ChatResult]:
        without_rag = await self.generate(question, ChatMode.WITHOUT_RAG, model, top_k, strategy)
        with_rag = await self.generate(question, ChatMode.WITH_RAG, model, top_k, strategy, retrieval_mode=RetrievalMode.BASELINE)
        return without_rag, with_rag

    async def compare_retrieval(
        self, question: str, model: DeepSeekModel, candidate_top_k: int, final_top_k: int, strategy: str = "structural"
    ) -> tuple[ChatResult, ChatResult]:
        baseline = await self.generate(
            question, ChatMode.WITH_RAG, model, final_top_k, strategy, retrieval_mode=RetrievalMode.BASELINE
        )
        enhanced = await self.generate(
            question, ChatMode.WITH_RAG, model, final_top_k, strategy,
            retrieval_mode=RetrievalMode.ENHANCED, candidate_top_k=candidate_top_k, final_top_k=final_top_k,
        )
        return baseline, enhanced

    async def _baseline(
        self, question: str, strategy: str, top_k: int, timings: dict[str, float]
    ) -> tuple[list[dict[str, object]], dict[str, object]]:
        started = perf_counter()
        matches = await asyncio.to_thread(self.search_service.search, question, strategy, top_k)
        timings["retrieval_ms"] = self._milliseconds(started)
        sources = [self._source(number, match, final_rank=number) for number, match in enumerate(matches, start=1)]
        return sources, {
            "candidate_top_k": top_k, "candidates_found": len(matches), "similarity_threshold": None,
            "after_filter": len(matches), "final_top_k": top_k, "final_count": len(sources),
            "candidates": [self._candidate_debug(match) for match in matches],
        }

    async def _enhanced(
        self, question: str, strategy: str, candidate_top_k: int, final_top_k: int, timings: dict[str, float]
    ) -> tuple[list[dict[str, object]], str, dict[str, object]]:
        rewritten_query = question
        if self.settings.query_rewrite_enabled:
            rewrite_started = perf_counter()
            rewritten_query = await self.query_rewriter.rewrite(question)
            timings["rewrite_ms"] = self._milliseconds(rewrite_started)

        retrieval_started = perf_counter()
        candidates = await asyncio.to_thread(self.search_service.search, rewritten_query, strategy, candidate_top_k)
        timings["retrieval_ms"] = self._milliseconds(retrieval_started)
        for rank, candidate in enumerate(candidates, start=1):
            candidate["original_rank"] = rank
            candidate["similarity_score"] = float(candidate.get("similarity_score", candidate["score"]))

        filtered = candidates
        if self.settings.filter_enabled:
            filtered = self.relevance_filter.filter(candidates, self.settings.similarity_threshold)
        else:
            for candidate in filtered:
                candidate["passed_threshold"] = True

        reranked = filtered
        if self.settings.rerank_enabled and filtered:
            rerank_started = perf_counter()
            reranked = await asyncio.to_thread(self.reranker.rerank, rewritten_query, filtered)
            timings["rerank_ms"] = self._milliseconds(rerank_started)
        else:
            for rank, candidate in enumerate(reranked, start=1):
                candidate["final_rank"] = rank
        final = reranked[:final_top_k]
        sources = [self._source(number, match, final_rank=number) for number, match in enumerate(final, start=1)]
        return sources, rewritten_query, {
            "candidate_top_k": candidate_top_k,
            "candidates_found": len(candidates),
            "similarity_threshold": self.settings.similarity_threshold if self.settings.filter_enabled else None,
            "after_filter": len(filtered),
            "final_top_k": final_top_k,
            "final_count": len(sources),
            "candidates": [self._candidate_debug(candidate) for candidate in candidates],
        }

    def _rag_prompt(self, sources: list[dict[str, object]]) -> str:
        if not sources:
            return f"{WITH_RAG_PROMPT}\n\n{NO_RELEVANT_CONTEXT_PROMPT}"
        return f"{WITH_RAG_PROMPT}\n\nCONTEXT\n\n{self.context_builder.build(sources)}"

    @staticmethod
    def _title(question: str) -> str:
        return question.strip().replace("\n", " ")[:80] or "New chat"

    @staticmethod
    def _milliseconds(started: float) -> float:
        return round((perf_counter() - started) * 1000, 2)

    @staticmethod
    def _source(number: int, match: dict[str, object], final_rank: int) -> dict[str, object]:
        metadata = match["metadata"]
        assert isinstance(metadata, dict)
        similarity_score = float(match.get("similarity_score", match["score"]))
        return {
            "number": number, "rank": number, "score": similarity_score, "similarity_score": similarity_score,
            "rerank_score": match.get("rerank_score"), "original_rank": match.get("original_rank", number),
            "final_rank": final_rank, "passed_threshold": match.get("passed_threshold"),
            "chunk_id": match["chunk_id"], "file": metadata.get("file", ""), "section": metadata.get("section", ""),
            "section_path": metadata.get("section_path", ""), "text": match["text"],
        }

    @staticmethod
    def _candidate_debug(candidate: dict[str, object]) -> dict[str, object]:
        metadata = candidate["metadata"]
        assert isinstance(metadata, dict)
        return {
            "chunk_id": candidate["chunk_id"],
            "file": metadata.get("file", ""),
            "section": metadata.get("section", ""),
            "similarity_score": candidate.get("similarity_score", candidate["score"]),
            "original_rank": candidate.get("original_rank"),
            "passed_threshold": candidate.get("passed_threshold"),
            "rerank_score": candidate.get("rerank_score"),
            "final_rank": candidate.get("final_rank"),
        }

    @staticmethod
    def _result(
        response: LLMResponse, mode: ChatMode, retrieval_mode: RetrievalMode | None, sources: list[dict[str, object]],
        strategy: str, top_k: int, original_question: str, rewritten_query: str | None,
        retrieval: dict[str, object] | None, timings: dict[str, float],
    ) -> ChatResult:
        return ChatResult(
            answer=response.content, model=response.model, mode=mode, retrieval_mode=retrieval_mode, sources=sources,
            usage={"prompt_tokens": response.prompt_tokens, "completion_tokens": response.completion_tokens, "total_tokens": response.total_tokens},
            strategy=strategy, top_k=top_k, original_question=original_question, rewritten_query=rewritten_query,
            retrieval=retrieval, timings=timings,
        )
