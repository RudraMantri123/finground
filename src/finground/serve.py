"""FastAPI service exposing the cited-answering pipeline.

    POST /query {question, model?, top_k?} -> {answer, citations[], abstained, ...}
    GET  /dashboard -> observability report over traces/ + results/

Also serves the static demo page at ``/``. Every /query is traced (see
``tracing.py``); the trace id is returned in the ``X-Trace-Id`` header so a
user-reported bad answer can be looked up in the dashboard.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from . import tracing
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
    model = req.model or CONFIG.models.answer
    with tracing.trace("query", source="api", question=req.question, model=model) as tr:
        headers = {"X-Trace-Id": tr.trace_id} if tr is not None else None
        try:
            ans = answer_question(req.question, model=req.model, top_k=req.top_k)
        except FileNotFoundError as exc:
            tracing.record_error(exc)
            return JSONResponse(status_code=503, content={"error": str(exc)}, headers=headers)
        except LLMUnavailable as exc:
            tracing.record_error(exc)
            return JSONResponse(
                status_code=503,
                content={
                    "error": f"LLM provider unavailable: {exc}. Set a key or pick another model."
                },
                headers=headers,
            )
        tracing.record_answer(ans)
        return JSONResponse(content=ans.to_json(), headers=headers)


@app.get("/dashboard")
def dashboard() -> HTMLResponse:
    """Observability report, rebuilt from traces/ and results/ on each request."""
    from .dashboard import build_dashboard

    return HTMLResponse(build_dashboard())


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(_DEMO_DIR / "index.html"))


def demo_path() -> Path:
    return _DEMO_DIR / "index.html"
