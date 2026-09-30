from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from app.rag.config import Settings
from app.rag.chat_repository import ChatNotFoundError, ChatRepository
from app.rag.llm import (
    DeepSeekProvider,
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
        "mode": result.mode.value,
        "retrieval_mode": result.retrieval_mode.value if result.retrieval_mode else None,
        "model": result.model,
        "answer": result.answer,
        "sources": result.sources,
        "usage": result.usage,
        "strategy": result.strategy,
        "top_k": result.top_k,
        "original_question": result.original_question,
        "rewritten_query": result.rewritten_query,
        "retrieval": result.retrieval,
        "timings": result.timings,
    }


def _raise_llm_error(exc: LLMError) -> None:
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
    raise HTTPException(status_code=status, detail=str(exc)) from exc


def create_app(
    search_service: SearchService | None = None,
    rag_service: RAGService | None = None,
    chat_repository: ChatRepository | None = None,
) -> FastAPI:
    settings = Settings.from_env()
    app = FastAPI(title="RAG Chat", version="2.0.0")
    app.state.search_service = search_service or SearchService(settings)
    app.state.chat_repository = chat_repository or ChatRepository(settings.chat_database_path)
    app.state.rag_service = rag_service or RAGService(
        settings,
        app.state.search_service,
        DeepSeekProvider(settings),
        app.state.chat_repository,
    )
    static_path = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=static_path), name="static")

    @app.get("/", include_in_schema=False)
    def root() -> FileResponse:
        return FileResponse(static_path / "index.html")

    @app.get("/health")
    def health() -> dict[str, object]:
        reranker = getattr(app.state.rag_service, "reranker", None)
        return {
            "status": "ok",
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


app = create_app()
