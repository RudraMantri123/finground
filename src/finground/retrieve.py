"""Hybrid retrieval: BM25 + dense (FAISS), fused with Reciprocal Rank Fusion.

Returns top-k chunks with their component scores and full provenance. The dense
cosine similarity is surfaced so the answerer can gate refusals on evidence
strength.
"""

from __future__ import annotations

import json
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import faiss
import numpy as np

from .config import CONFIG
from .index import embed_queries, tokenize


@dataclass
class RetrievedChunk:
    """A retrieved chunk with fusion + component scores and its provenance."""

    label: str  # per-query citation label, e.g. "C1"
    chunk_id: str
    doc_id: str
    company: str
    ticker: str
    section: str
    filing_type: str
    filing_date: str
    text: str
    rrf_score: float
    dense_score: float  # cosine similarity in [-1, 1]; ~[0,1] in practice
    bm25_score: float
    span: tuple[int, int] = (0, 0)

    def provenance(self) -> str:
        """Human-readable source citation string."""
        return f"{self.ticker} {self.filing_type} ({self.filing_date}) — {self.section}"


@dataclass
class _Indexes:
    bm25: Any  # rank_bm25.BM25Okapi (untyped third-party)
    bm25_chunks: list[dict]
    faiss_index: faiss.Index
    dense_chunks: list[dict]
    model_name: str


_CACHE: _Indexes | None = None


def load_indexes(force: bool = False) -> _Indexes:
    """Load both indexes from disk (cached per process)."""
    global _CACHE
    if _CACHE is not None and not force:
        return _CACHE

    bm25_path: Path = CONFIG.paths.bm25_index
    if not bm25_path.exists():
        raise FileNotFoundError(
            f"BM25 index not found at {bm25_path}. Run `make ingest && make index` first."
        )
    with open(bm25_path, "rb") as fh:
        bm25_blob = pickle.load(fh)

    faiss_index = faiss.read_index(str(CONFIG.paths.dense_index))
    with open(CONFIG.paths.dense_meta, encoding="utf-8") as fh:
        dense_meta = json.load(fh)

    _CACHE = _Indexes(
        bm25=bm25_blob["bm25"],
        bm25_chunks=bm25_blob["chunks"],
        faiss_index=faiss_index,
        dense_chunks=dense_meta["chunks"],
        model_name=dense_meta["model"],
    )
    return _CACHE


def _rrf_ranks(ordered_ids: list[str], rrf_k: int) -> dict[str, float]:
    """Reciprocal-rank contribution for one ranker's ordered id list."""
    return {cid: 1.0 / (rrf_k + rank) for rank, cid in enumerate(ordered_ids, start=1)}


def retrieve(
    query: str,
    *,
    top_k: int | None = None,
    pool: int | None = None,
) -> list[RetrievedChunk]:
    """Hybrid retrieve for ``query``. Returns up to ``top_k`` fused chunks.

    BM25 and dense retrievers each produce a ranked candidate pool; the two
    rankings are combined with Reciprocal Rank Fusion (RRF). Component scores
    (bm25, dense cosine) are attached to each result for transparency and for
    the answerer's evidence gate.
    """
    idx = load_indexes()
    top_k = top_k or CONFIG.retrieval.top_k
    pool = pool or CONFIG.retrieval.candidate_pool
    chunks = idx.bm25_chunks  # bm25 and dense share the same chunk ordering
    n = len(chunks)
    if n == 0:
        return []
    pool = min(pool, n)

    # --- BM25 ranking ---
    q_tokens = tokenize(query)
    bm25_scores = np.asarray(idx.bm25.get_scores(q_tokens), dtype="float32")
    bm25_top = np.argsort(-bm25_scores)[:pool]
    bm25_ids = [chunks[i]["chunk_id"] for i in bm25_top]
    bm25_score_by_id = {chunks[i]["chunk_id"]: float(bm25_scores[i]) for i in bm25_top}

    # --- Dense ranking ---
    q_vec = embed_queries([query], model_name=idx.model_name)
    sims, dense_top = idx.faiss_index.search(q_vec, pool)
    sims = sims[0]
    dense_top = dense_top[0]
    dense_ids = [chunks[i]["chunk_id"] for i in dense_top if i >= 0]
    dense_score_by_id = {
        chunks[i]["chunk_id"]: float(s) for i, s in zip(dense_top, sims, strict=True) if i >= 0
    }

    # --- RRF fusion ---
    rrf_k = CONFIG.retrieval.rrf_k
    fused: dict[str, float] = {}
    for contrib in (_rrf_ranks(bm25_ids, rrf_k), _rrf_ranks(dense_ids, rrf_k)):
        for cid, s in contrib.items():
            fused[cid] = fused.get(cid, 0.0) + s

    by_id = {c["chunk_id"]: c for c in chunks}
    ranked_ids = sorted(fused, key=lambda cid: fused[cid], reverse=True)[:top_k]

    results: list[RetrievedChunk] = []
    for i, cid in enumerate(ranked_ids, start=1):
        c = by_id[cid]
        results.append(
            RetrievedChunk(
                label=f"C{i}",
                chunk_id=c["chunk_id"],
                doc_id=c["doc_id"],
                company=c["company"],
                ticker=c["ticker"],
                section=c["section"],
                filing_type=c["filing_type"],
                filing_date=c["filing_date"],
                text=c["text"],
                rrf_score=fused[cid],
                dense_score=dense_score_by_id.get(cid, 0.0),
                bm25_score=bm25_score_by_id.get(cid, 0.0),
                span=tuple(c.get("span", (0, 0))),
            )
        )
    return results


def best_dense_sim(results: list[RetrievedChunk]) -> float:
    """Strongest dense cosine similarity among results (evidence strength)."""
    return max((r.dense_score for r in results), default=0.0)
