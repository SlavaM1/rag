from __future__ import annotations

import logging
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from time import perf_counter
from typing import Callable

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from app.rag.config import Settings
from app.rag.chat_repository import ChatNotFoundError, ChatRepository
from app.rag.llm import (
    LLMProvider,
    LLMProviderFactory,
    MeasuredLLMProvider,
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMError,
    LLMInvalidResponseError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMUnavailableError,
    LLMUnavailableModelError,
)
from app.rag.rag_service import ChatMode, DeepSeekModel, RAGService, RetrievalMode
from app.rag.search_service import SearchService


logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)


class ProviderName(str, Enum):
    OLLAMA = "ollama"
    DEEPSEEK = "deepseek"


class IntegrationMessage(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=20_000)

    @field_validator("content")
    @classmethod
    def content_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message content must not be blank")
        return value


class IntegrationChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=20_000)
    messages: list[IntegrationMessage] = Field(default_factory=list)
    provider: ProviderName
    model: str | None = Field(default=None, min_length=1, max_length=200)
    rag_enabled: bool = True
    retrieval_mode: RetrievalMode = RetrievalMode.ENHANCED
    strategy: str = Field(default="structural", pattern="^(fixed|structural)$")
    candidate_top_k: int = Field(default=15, ge=1, le=20)
    final_top_k: int = Field(default=5, ge=1, le=20)
    request_id: str = Field(min_length=1, max_length=200)
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_output_tokens: int | None = Field(default=None, ge=1, le=32_768)

    @field_validator("question", "request_id")
    @classmethod
    def value_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be blank")
        return value

    @field_validator("model")
    @classmethod
    def model_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("model must not be blank")
        return value


class SearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    strategy: str = Field(default="structural", pattern="^(fixed|structural)$")
    top_k: int = Field(default=5, ge=1, le=20)

    @field_validator("query")
    @classmethod
    def query_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("query must not be blank")
        return value


class ChatRequest(BaseModel):
    chat_id: int | None = Field(default=None, ge=1)
    question: str = Field(min_length=1, max_length=1000)
    mode: ChatMode = ChatMode.WITH_RAG
    model: DeepSeekModel = DeepSeekModel.FLASH
    strategy: str = Field(default="structural", pattern="^(fixed|structural)$")
    top_k: int = Field(default=5, ge=1, le=20)
    retrieval_mode: RetrievalMode = RetrievalMode.ENHANCED
    candidate_top_k: int | None = Field(default=None, ge=1, le=20)
    final_top_k: int | None = Field(default=None, ge=1, le=20)

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("question must not be blank")
        return value


class CompareRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    model: DeepSeekModel = DeepSeekModel.FLASH
    strategy: str = Field(default="structural", pattern="^(fixed|structural)$")
    top_k: int = Field(default=5, ge=1, le=20)

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("question must not be blank")
        return value


class CompareRetrievalRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    model: DeepSeekModel = DeepSeekModel.FLASH
    strategy: str = Field(default="structural", pattern="^(fixed|structural)$")
    candidate_top_k: int = Field(default=15, ge=1, le=20)
    final_top_k: int = Field(default=5, ge=1, le=20)

    @field_validator("question")
    @classmethod
    def question_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("question must not be blank")
        return value


class CreateChatRequest(BaseModel):
    title: str = Field(default="New chat", min_length=1, max_length=80)

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title must not be blank")
        return value


def _result_payload(result: object) -> dict[str, object]:
    return {
        "status": result.status.value,
        "mode": result.mode.value,
        "retrieval_mode": result.retrieval_mode.value if result.retrieval_mode else None,
        "model": result.model,
        "answer": result.answer,
        "sources": result.sources,
        "quotes": result.quotes,
        "usage": result.usage,
        "strategy": result.strategy,
        "top_k": result.top_k,
        "original_question": result.original_question,
        "rewritten_query": result.rewritten_query,
        "retrieval": result.retrieval,
        "timings": result.timings,
        "task_state": result.task_state,
    }


def _raise_llm_error(exc: LLMError) -> None:
    status = _llm_http_status(exc)
    raise HTTPException(status_code=status, detail=str(exc)) from exc


def _llm_http_status(exc: LLMError) -> int:
    status = 502
    if isinstance(exc, LLMConfigurationError):
        status = 503
    elif isinstance(exc, LLMAuthenticationError):
        status = 502
    elif isinstance(exc, LLMRateLimitError):
        status = 429
    elif isinstance(exc, LLMTimeoutError):
        status = 504
    elif isinstance(exc, (LLMUnavailableModelError, LLMUnavailableError, LLMInvalidResponseError)):
        status = 502
    return status


def create_app(
    search_service: SearchService | None = None,
    rag_service: RAGService | None = None,
    chat_repository: ChatRepository | None = None,
    provider_factory: LLMProviderFactory | Callable[[str], LLMProvider] | None = None,
) -> FastAPI:
    settings = Settings.from_env()
    app = FastAPI(title="RAG Chat", version="4.0.0")
    app.state.search_service = search_service or SearchService(settings)
    app.state.chat_repository = chat_repository or ChatRepository(settings.chat_database_path)
    app.state.provider_factory = provider_factory or LLMProviderFactory(settings)
    create_provider = (
        app.state.provider_factory.create
        if hasattr(app.state.provider_factory, "create")
        else app.state.provider_factory
    )
    app.state.rag_service = rag_service or RAGService(
        settings,
        app.state.search_service,
        None,
        app.state.chat_repository,
        provider_factory=create_provider,
    )
    static_path = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=static_path), name="static")

    @app.get("/", include_in_schema=False)
    def root() -> FileResponse:
        return FileResponse(static_path / "index.html")

    @app.get("/health")
    async def health() -> dict[str, object]:
        reranker = getattr(app.state.rag_service, "reranker", None)
        indexes = {
            strategy: all(
                (settings.index_path(strategy) / filename).is_file()
                for filename in ("index.faiss", "metadata.json")
            )
            for strategy in ("fixed", "structural")
        }
        ollama_status = "unavailable"
        try:
            async with httpx.AsyncClient(timeout=settings.ollama_health_timeout_seconds) as client:
                response = await client.get(f"{settings.ollama_base_url}/api/tags")
                if response.is_success:
                    ollama_status = "available"
        except httpx.HTTPError:
            pass
        return {
            "status": "ok",
            "backend_ready": True,
            "local_retrieval_ready": all(indexes.values()),
            "indexes": indexes,
            "ollama_status": ollama_status,
            "ollama_available": ollama_status == "available",
            "deepseek_configured": bool(settings.deepseek_api_key),
            "embedding_model_loaded": bool(getattr(getattr(app.state.search_service, "embedding_provider", None), "_model", None)),
            "reranker_loaded": bool(getattr(reranker, "_model", None)),
        }

    @app.post("/api/search")
    def search(request: SearchRequest) -> dict[str, object]:
        try:
            results = app.state.search_service.search(request.query, request.strategy, request.top_k)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"query": request.query, "strategy": request.strategy, "results": results}

    @app.post("/api/chat")
    async def chat(request: ChatRequest) -> dict[str, object]:
        try:
            if request.candidate_top_k and request.final_top_k and request.final_top_k > request.candidate_top_k:
                raise ValueError("final_top_k must not exceed candidate_top_k")
            chat_id, result = await app.state.rag_service.ask(
                request.question,
                request.mode,
                request.model,
                request.top_k,
                request.strategy,
                request.chat_id,
                request.retrieval_mode,
                request.candidate_top_k,
                request.final_top_k,
            )
            return {"chat_id": chat_id, **_result_payload(result)}
        except ChatNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except LLMError as exc:
            _raise_llm_error(exc)

    @app.post("/api/integration/chat")
    async def integration_chat(request: IntegrationChatRequest) -> object:
        request_started_at = datetime.now(timezone.utc).isoformat()
        started = perf_counter()
        provider_name = request.provider.value
        model = request.model or (
            settings.ollama_default_model
            if request.provider == ProviderName.OLLAMA
            else settings.deepseek_default_model
        )
        history = [message.model_dump() for message in request.messages]
        logger.info(
            "integration_chat_start request_id=%s provider=%s model=%s rag_enabled=%s "
            "retrieval_mode=%s history_count=%s",
            request.request_id,
            provider_name,
            model,
            request.rag_enabled,
            request.retrieval_mode.value,
            len(history),
        )
        measured: MeasuredLLMProvider | None = None
        selected: LLMProvider | None = None
        try:
            if request.final_top_k > request.candidate_top_k:
                raise ValueError("final_top_k must not exceed candidate_top_k")
            if request.provider == ProviderName.DEEPSEEK and model not in settings.deepseek_available_models:
                raise ValueError("model is not in DEEPSEEK_AVAILABLE_MODELS")
            selected = create_provider(provider_name)
            measured = MeasuredLLMProvider(selected)
            result = await app.state.rag_service.generate_integration(
                request.question,
                history,
                measured,
                model,
                request.rag_enabled,
                request.strategy,
                request.retrieval_mode,
                request.candidate_top_k,
                request.final_top_k,
                request.temperature,
                request.max_output_tokens,
            )
            metrics = _integration_metrics(
                request,
                result,
                measured,
                request_started_at,
                round((perf_counter() - started) * 1000, 2),
                selected,
            )
            logger.info(
                "integration_chat_complete request_id=%s provider=%s model=%s status=%s "
                "sources_count=%s quotes_count=%s total_ms=%s llm_ms=%s",
                request.request_id,
                provider_name,
                result.model,
                result.status.value,
                len(result.sources),
                len(result.quotes),
                metrics["total_latency_ms"],
                metrics["llm_latency_ms"],
            )
            response_candidate_top_k = metrics.get("candidate_top_k")
            response_final_top_k = metrics.get("final_top_k")
            return {
                "request_id": request.request_id,
                "status": result.status.value,
                "answer": result.answer,
                "provider": provider_name,
                "model": result.model,
                "rag_enabled": request.rag_enabled,
                "retrieval_mode": request.retrieval_mode.value if request.rag_enabled else None,
                "strategy": request.strategy,
                "candidate_top_k": response_candidate_top_k,
                "final_top_k": response_final_top_k,
                "sources": result.sources,
                "quotes": result.quotes,
                "metrics": metrics,
            }
        except ValueError as exc:
            status_code = 422
            error_type = type(exc).__name__
            detail = str(exc)
        except (FileNotFoundError, LLMError) as exc:
            status_code = 503 if isinstance(exc, FileNotFoundError) else _llm_http_status(exc)
            error_type = type(exc).__name__
            detail = str(exc)
        except Exception as exc:
            status_code = 500
            error_type = type(exc).__name__
            detail = "RAG pipeline failed"
            logger.exception(
                "integration_chat_unhandled request_id=%s provider=%s model=%s",
                request.request_id,
                provider_name,
                model,
            )

        total_ms = round((perf_counter() - started) * 1000, 2)
        llm_metrics = measured.metrics() if measured else _empty_llm_metrics()
        logger.info(
            "integration_chat_error request_id=%s provider=%s model=%s http_status=%s error_type=%s total_ms=%s",
            request.request_id,
            provider_name,
            model,
            status_code,
            error_type,
            total_ms,
        )
        return JSONResponse(
            status_code=status_code,
            content={
                "request_id": request.request_id,
                "status": "error",
                "answer": "",
                "provider": provider_name,
                "model": model,
                "rag_enabled": request.rag_enabled,
                "retrieval_mode": request.retrieval_mode.value if request.rag_enabled else None,
                "strategy": request.strategy,
                "candidate_top_k": request.candidate_top_k,
                "final_top_k": request.final_top_k,
                "sources": [],
                "quotes": [],
                "error": detail,
                "metrics": {
                    "request_started_at": request_started_at,
                    "success": False,
                    "http_status": status_code,
                    "error_type": error_type,
                    "total_latency_ms": total_ms,
                    "provider": provider_name,
                    "model": model,
                    "request_id": request.request_id,
                    "rag_enabled": request.rag_enabled,
                    "retrieval_mode": request.retrieval_mode.value if request.rag_enabled else None,
                    "strategy": request.strategy,
                    "history_messages_count": len(history),
                    "history_chars": sum(len(message["content"]) for message in history),
                    "rag_context_chars": None,
                    "rag_context_chunks": None,
                    "retrieved_chunks_count": 0 if not request.rag_enabled else None,
                    "source_count": 0,
                    "quote_count": 0,
                    "tokens_per_second": llm_metrics["generation_tokens_per_second"],
                    "query_rewrite_ms": None,
                    "embedding_ms": None,
                    "faiss_search_ms": None,
                    "filter_ms": None,
                    "rerank_ms": None,
                    "context_build_ms": None,
                    "retrieval_total_ms": None,
                    "candidate_top_k": request.candidate_top_k,
                    "candidate_count": None,
                    "filtered_count": None,
                    "final_top_k": request.final_top_k,
                    "final_chunk_count": None,
                    "best_similarity": None,
                    "similarity_threshold": None,
                    "rerank_enabled": None,
                    **llm_metrics,
                    "token_usage": {
                        "input_tokens": llm_metrics["input_tokens"],
                        "output_tokens": llm_metrics["output_tokens"],
                        "total_tokens": llm_metrics["total_tokens"],
                    },
                    "token_rates": {
                        "prompt_tokens_per_second": llm_metrics["prompt_tokens_per_second"],
                        "generation_tokens_per_second": llm_metrics["generation_tokens_per_second"],
                    },
                    "retrieval_timings": {
                        name: None
                        for name in (
                            "task_state_update_ms", "rewrite_ms", "embedding_ms", "faiss_ms",
                            "retrieval_ms", "filter_ms", "rerank_ms", "context_ms",
                            "retrieval_total_ms", "generation_ms",
                        )
                    },
                    "retrieval_counts": {
                        "candidates_found": None,
                        "after_filter": None,
                        "final_count": None,
                    },
                    "retrieval_settings": {
                        "mode": request.retrieval_mode.value if request.rag_enabled else None,
                        "strategy": request.strategy,
                        "candidate_top_k": request.candidate_top_k,
                        "final_top_k": request.final_top_k,
                        "best_similarity": None,
                        "similarity_threshold": None,
                        "min_context_similarity": None,
                        "rerank_enabled": None,
                    },
                    "generation_settings": {
                        "temperature": request.temperature if request.temperature is not None else getattr(selected, "temperature", None),
                        "max_output_tokens": request.max_output_tokens if request.max_output_tokens is not None else getattr(selected, "max_tokens", None),
                    },
                },
            },
        )

    @app.post("/api/compare")
    async def compare(request: CompareRequest) -> dict[str, object]:
        try:
            without_rag, with_rag = await app.state.rag_service.compare(
                request.question, request.model, request.top_k, request.strategy
            )
            return {
                "question": request.question,
                "model": request.model.value,
                "without_rag": _result_payload(without_rag),
                "with_rag": _result_payload(with_rag),
            }
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except LLMError as exc:
            _raise_llm_error(exc)

    @app.post("/api/compare-retrieval")
    async def compare_retrieval(request: CompareRetrievalRequest) -> dict[str, object]:
        try:
            if request.final_top_k > request.candidate_top_k:
                raise ValueError("final_top_k must not exceed candidate_top_k")
            baseline, enhanced = await app.state.rag_service.compare_retrieval(
                request.question, request.model, request.candidate_top_k, request.final_top_k, request.strategy
            )
            return {
                "question": request.question,
                "model": request.model.value,
                "baseline": _result_payload(baseline),
                "enhanced": _result_payload(enhanced),
            }
        except (FileNotFoundError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except LLMError as exc:
            _raise_llm_error(exc)

    @app.post("/api/chats")
    def create_chat(request: CreateChatRequest) -> dict[str, object]:
        return app.state.chat_repository.create_chat(request.title)

    @app.get("/api/chats")
    def list_chats() -> dict[str, object]:
        return {"chats": app.state.chat_repository.list_chats()}

    @app.get("/api/chats/{chat_id}")
    def get_chat(chat_id: int) -> dict[str, object]:
        try:
            return app.state.chat_repository.get_chat(chat_id)
        except ChatNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    @app.delete("/api/chats/{chat_id}")
    def delete_chat(chat_id: int) -> dict[str, bool]:
        try:
            app.state.chat_repository.delete_chat(chat_id)
        except ChatNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"deleted": True}

    return app


def _integration_metrics(
    request: IntegrationChatRequest,
    result: object,
    measured: MeasuredLLMProvider,
    request_started_at: str,
    total_latency_ms: float,
    selected_provider: object,
) -> dict[str, object]:
    llm_metrics = measured.metrics()
    retrieval = result.retrieval or {}
    effective_candidate_top_k = retrieval.get("candidate_top_k", request.candidate_top_k)
    effective_final_top_k = retrieval.get("final_top_k", request.final_top_k)
    timing_names = (
        "task_state_update_ms",
        "rewrite_ms",
        "embedding_ms",
        "faiss_ms",
        "retrieval_ms",
        "filter_ms",
        "rerank_ms",
        "context_ms",
        "retrieval_total_ms",
        "generation_ms",
    )
    retrieval_timings = {name: result.timings.get(name) for name in timing_names}
    generation_temperature = (
        request.temperature
        if request.temperature is not None
        else getattr(selected_provider, "temperature", None)
    )
    generation_max_tokens = (
        request.max_output_tokens
        if request.max_output_tokens is not None
        else getattr(selected_provider, "max_tokens", None)
    )
    return {
        "request_started_at": request_started_at,
        "success": True,
        "http_status": 200,
        "error_type": None,
        "provider": request.provider.value,
        "model": result.model,
        "request_id": request.request_id,
        "rag_enabled": request.rag_enabled,
        "retrieval_mode": request.retrieval_mode.value if request.rag_enabled else None,
        "strategy": request.strategy,
        "total_latency_ms": total_latency_ms,
        "history_messages_count": len(request.messages),
        "history_chars": sum(len(message.content) for message in request.messages),
        "rag_context_chars": retrieval.get("context_chars", 0),
        "rag_context_chunks": retrieval.get("context_chunks", 0),
        "retrieved_chunks_count": retrieval.get("context_chunks", 0),
        "source_count": len(result.sources),
        "quote_count": len(result.quotes),
        **llm_metrics,
        "tokens_per_second": llm_metrics["generation_tokens_per_second"],
        "query_rewrite_ms": result.timings.get("rewrite_ms"),
        "embedding_ms": result.timings.get("embedding_ms"),
        "faiss_search_ms": result.timings.get("faiss_ms"),
        "filter_ms": result.timings.get("filter_ms"),
        "rerank_ms": result.timings.get("rerank_ms"),
        "context_build_ms": result.timings.get("context_ms"),
        "retrieval_total_ms": result.timings.get("retrieval_total_ms"),
        "candidate_top_k": effective_candidate_top_k,
        "candidate_count": retrieval.get("candidate_count"),
        "filtered_count": retrieval.get("after_filter"),
        "final_top_k": effective_final_top_k,
        "final_chunk_count": retrieval.get("final_count"),
        "best_similarity": retrieval.get("best_similarity"),
        "similarity_threshold": retrieval.get("similarity_threshold"),
        "rerank_enabled": retrieval.get("rerank_enabled"),
        "token_usage": {
            "input_tokens": llm_metrics["input_tokens"],
            "output_tokens": llm_metrics["output_tokens"],
            "total_tokens": llm_metrics["total_tokens"],
        },
        "token_rates": {
            "prompt_tokens_per_second": llm_metrics["prompt_tokens_per_second"],
            "generation_tokens_per_second": llm_metrics["generation_tokens_per_second"],
        },
        "retrieval_timings": retrieval_timings,
        "retrieval_counts": {
            "candidates_found": retrieval.get("candidates_found"),
            "candidate_count": retrieval.get("candidate_count"),
            "after_filter": retrieval.get("after_filter"),
            "filtered_count": retrieval.get("after_filter"),
            "final_count": retrieval.get("final_count"),
            "final_chunk_count": retrieval.get("final_count"),
        },
        "retrieval_settings": {
            "mode": request.retrieval_mode.value if request.rag_enabled else None,
            "strategy": request.strategy,
            "candidate_top_k": effective_candidate_top_k,
            "final_top_k": effective_final_top_k,
            "best_similarity": retrieval.get("best_similarity"),
            "similarity_threshold": retrieval.get("similarity_threshold"),
            "min_context_similarity": retrieval.get("min_context_similarity"),
            "rerank_enabled": retrieval.get("rerank_enabled"),
        },
        "generation_settings": {
            "temperature": generation_temperature,
            "max_output_tokens": generation_max_tokens,
        },
    }


def _empty_llm_metrics() -> dict[str, object]:
    return {
        "llm_latency_ms": 0.0,
        "total_prompt_chars": 0,
        "input_tokens": None,
        "output_tokens": None,
        "total_tokens": None,
        "prompt_tokens_per_second": None,
        "generation_tokens_per_second": None,
        "provider_specific": {"calls": []},
    }


app = create_app()
