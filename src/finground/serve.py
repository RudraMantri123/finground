"""FastAPI service exposing the cited-answering pipeline.

    POST /query {question, model?, top_k?} -> {answer, citations[], abstained, ...}

Also serves the static demo page at ``/``.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel, Field

from .answer import answer_question
from .config import CONFIG
from .llm import LLMUnavailable, available_providers

app = FastAPI(title="FinGround", version="0.1.0")

_DEMO_DIR = CONFIG.paths.root / "demo"


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3)
    model: str | None = None
    top_k: int | None = Field(default=None, ge=1, le=20)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "providers": sorted(available_providers()),
        "default_model": CONFIG.models.answer,
        "indexes_present": CONFIG.paths.bm25_index.exists() and CONFIG.paths.dense_index.exists(),
    }


@app.post("/query")
def query(req: QueryRequest) -> JSONResponse:
    try:
        ans = answer_question(req.question, model=req.model, top_k=req.top_k)
    except FileNotFoundError as exc:
        return JSONResponse(status_code=503, content={"error": str(exc)})
    except LLMUnavailable as exc:
        return JSONResponse(
            status_code=503,
            content={"error": f"LLM provider unavailable: {exc}. Set a key or pick another model."},
        )
    return JSONResponse(content=ans.to_json())


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(_DEMO_DIR / "index.html"))


def demo_path() -> Path:
    return _DEMO_DIR / "index.html"
