from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from app.rag.config import Settings
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


def create_app(search_service: SearchService | None = None) -> FastAPI:
    settings = Settings.from_env()
    app = FastAPI(title="Local RAG Search", version="1.0.0")
    app.state.search_service = search_service or SearchService(settings)
    static_path = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=static_path), name="static")

    @app.get("/", include_in_schema=False)
    def root() -> FileResponse:
        return FileResponse(static_path / "index.html")

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/search")
    def search(request: SearchRequest) -> dict[str, object]:
        try:
            results = app.state.search_service.search(request.query, request.strategy, request.top_k)
        except FileNotFoundError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"query": request.query, "strategy": request.strategy, "results": results}

    return app


app = create_app()
