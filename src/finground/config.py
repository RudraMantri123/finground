"""Central configuration: paths, model names, and environment loading.

Everything reads from here so that swapping models or relocating data is a
one-line change rather than a codebase-wide edit. Values come from environment
variables (loaded from a local ``.env`` if present) with sensible defaults.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the repo root if present. Never fail if it is absent.
_REPO_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_REPO_ROOT / ".env")


def _env(key: str, default: str) -> str:
    val = os.environ.get(key)
    return val if val else default


@dataclass(frozen=True)
class Paths:
    """Filesystem layout. All paths are absolute and derived from the repo root."""

    root: Path = _REPO_ROOT
    data: Path = _REPO_ROOT / "data"
    filings: Path = _REPO_ROOT / "data" / "filings"
    chunks: Path = _REPO_ROOT / "data" / "chunks.jsonl"
    indexes: Path = _REPO_ROOT / "indexes"
    bm25_index: Path = _REPO_ROOT / "indexes" / "bm25.pkl"
    dense_index: Path = _REPO_ROOT / "indexes" / "dense.faiss"
    dense_meta: Path = _REPO_ROOT / "indexes" / "dense_meta.json"
    results: Path = _REPO_ROOT / "results"
    human_labels: Path = _REPO_ROOT / "results" / "human_labels"
    llm_cache: Path = _REPO_ROOT / "llm_cache"

    def ensure(self) -> None:
        """Create directories that are safe to create on demand."""
        for p in (self.data, self.filings, self.indexes, self.results, self.llm_cache):
            p.mkdir(parents=True, exist_ok=True)


@dataclass(frozen=True)
class Models:
    """Model identifiers. Answer/judge use ``provider:model`` form (see llm.py)."""

    embed: str = field(default_factory=lambda: _env("FINGROUND_EMBED_MODEL", "BAAI/bge-base-en-v1.5"))
    reranker: str = field(
        default_factory=lambda: _env(
            "FINGROUND_RERANKER_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
        )
    )
    answer: str = field(default_factory=lambda: _env("FINGROUND_ANSWER_MODEL", "openai:gpt-4o-mini"))
    judge: str = field(default_factory=lambda: _env("FINGROUND_JUDGE_MODEL", "openai:gpt-4o"))


@dataclass(frozen=True)
class Retrieval:
    """Chunking + retrieval hyperparameters."""

    chunk_tokens: int = 500
    chunk_overlap_tokens: int = 75
    top_k: int = 8
    rrf_k: int = 60  # RRF smoothing constant
    # Score below which the answerer is told evidence is weak (drives refusal).
    min_evidence_score: float = 0.015


@dataclass(frozen=True)
class Config:
    paths: Paths = field(default_factory=Paths)
    models: Models = field(default_factory=Models)
    retrieval: Retrieval = field(default_factory=Retrieval)

    @property
    def sec_user_agent(self) -> str:
        return _env(
            "SEC_EDGAR_USER_AGENT",
            "FinGround research contact example@example.com",
        )

    @property
    def ollama_base_url(self) -> str:
        return _env("OLLAMA_BASE_URL", "http://localhost:11434")


# Singleton used throughout the codebase.
CONFIG = Config()
