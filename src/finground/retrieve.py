"""Hybrid retrieval: BM25 + dense (FAISS), fused with Reciprocal Rank Fusion.

Returns top-k chunks with their component scores and full provenance. The dense
cosine similarity is surfaced so the answerer can gate refusals on evidence
strength.
"""

from __future__ import annotations

import json
import pickle
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import faiss
import numpy as np

from .config import CONFIG
from .index import embed_passages, embed_queries, make_bm25, make_faiss, tokenize


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

# Which rankers feed the fusion step. "hybrid" is the production setting; the
# single-ranker modes exist so ablations reuse this exact code path (company
# filter, reranker, cut-off) instead of re-implementing retrieval.
RetrievalMode = Literal["hybrid", "bm25", "dense"]
RETRIEVAL_MODES: tuple[str, ...] = ("hybrid", "bm25", "dense")


def indexes_from_chunks(chunks: list[dict], *, model_name: str | None = None) -> _Indexes:
    """Build both indexes in memory over ``chunks`` (no files written).

    Used for small, committed evaluation corpora: embedding a few hundred
    chunks is cheaper and more reproducible than shipping binary index files.
    """
    model_name = model_name or CONFIG.models.embed
    vecs = embed_passages([c["text"] for c in chunks], model_name=model_name)
    return _Indexes(
        bm25=make_bm25(chunks),
        bm25_chunks=chunks,
        faiss_index=make_faiss(vecs),
        dense_chunks=chunks,
        model_name=model_name,
    )


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


# ---------------------------------------------------------------------------
# Company detection (query -> tickers present in the corpus)
# ---------------------------------------------------------------------------

# Extra aliases that the first-word-of-company-name heuristic can't derive.
_COMPANY_ALIASES = {"google": "GOOGL", "aws": "AMZN", "coke": "KO"}


def _company_terms(chunks: list[dict]) -> dict[str, str]:
    """Build {lowercase term -> ticker} from the indexed chunks themselves."""
    terms: dict[str, str] = dict(_COMPANY_ALIASES)
    for c in chunks:
        ticker = c.get("ticker", "")
        name = c.get("company", "")
        if not ticker:
            continue
        terms[ticker.lower()] = ticker
        # First meaningful word of the company name ("Apple Inc." -> "apple").
        words = [w for w in re.findall(r"[a-z0-9-]+", name.lower()) if w != "the"]
        if words:
            terms[words[0]] = ticker
    return terms


def detect_tickers(query: str, chunks: list[dict]) -> set[str]:
    """Tickers of corpus companies explicitly mentioned in the query."""
    q = query.lower()
    q_tokens = set(re.findall(r"[a-z0-9-]+", q))
    found: set[str] = set()
    for term, ticker in _company_terms(chunks).items():
        if term in q_tokens:
            found.add(ticker)
    return found


# ---------------------------------------------------------------------------
# Cross-encoder reranking
# ---------------------------------------------------------------------------

_RERANKER = None
_RERANKER_FAILED = False  # set when the model can't be loaded (e.g. no network)


def _load_reranker():
    """Load the cross-encoder once; return None (and warn once) on failure.

    Reranking is a precision boost, not a correctness requirement — if the
    model cannot be downloaded (offline / blocked network), retrieval proceeds
    with the RRF ordering instead of crashing the pipeline.
    """
    global _RERANKER, _RERANKER_FAILED
    if _RERANKER is None and not _RERANKER_FAILED:
        try:
            from sentence_transformers import CrossEncoder

            _RERANKER = CrossEncoder(CONFIG.models.reranker)
        except Exception as exc:  # noqa: BLE001 — degrade gracefully
            _RERANKER_FAILED = True
            print(
                f"[retrieve] reranker unavailable ({exc.__class__.__name__}); "
                f"continuing with RRF order only."
            )
    return _RERANKER


def reranker_available() -> bool:
    """Whether the cross-encoder loaded (tries once).

    Serving degrades silently without it, but an evaluation must not: a
    "reranked" score measured on the RRF fallback would be mislabelled.
    """
    return _load_reranker() is not None


def rerank(query: str, candidates: list[dict]) -> list[tuple[dict, float]]:
    """Score (query, chunk) pairs with the cross-encoder; highest first.

    Falls back to the incoming order (scores of 0.0) when the model is
    unavailable, keeping retrieval deterministic and non-fatal offline.
    """
    model = _load_reranker()
    if model is None:
        return [(c, 0.0) for c in candidates]
    scores = model.predict([(query, c["text"]) for c in candidates])
    order = sorted(zip(candidates, scores, strict=True), key=lambda t: -float(t[1]))
    return [(c, float(s)) for c, s in order]


def retrieve(
    query: str,
    *,
    top_k: int | None = None,
    pool: int | None = None,
    mode: RetrievalMode = "hybrid",
    use_reranker: bool | None = None,
    indexes: _Indexes | None = None,
) -> list[RetrievedChunk]:
    """Hybrid retrieve for ``query``. Returns up to ``top_k`` fused chunks.

    BM25 and dense retrievers each produce a ranked candidate pool; the two
    rankings are combined with Reciprocal Rank Fusion (RRF). Component scores
    (bm25, dense cosine) are attached to each result for transparency and for
    the answerer's evidence gate.

    ``mode`` restricts fusion to one ranker (RRF over a single list preserves
    that list's order), ``use_reranker`` overrides the config toggle, and
    ``indexes`` swaps in an alternative corpus; all three exist for retrieval
    ablations and default to the production behaviour.
    """
    if mode not in RETRIEVAL_MODES:
        raise ValueError(f"unknown retrieval mode {mode!r}; expected one of {RETRIEVAL_MODES}")
    if use_reranker is None:
        use_reranker = CONFIG.retrieval.use_reranker
    idx = indexes if indexes is not None else load_indexes()
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
    rankings = {"hybrid": (bm25_ids, dense_ids), "bm25": (bm25_ids,), "dense": (dense_ids,)}[mode]
    fused: dict[str, float] = {}
    for contrib in (_rrf_ranks(ids, rrf_k) for ids in rankings):
        for cid, s in contrib.items():
            fused[cid] = fused.get(cid, 0.0) + s

    by_id = {c["chunk_id"]: c for c in chunks}
    ranked_ids = sorted(fused, key=lambda cid: fused[cid], reverse=True)

    # --- Company filter ---
    # If the query names corpus companies, prefer their chunks so an Apple
    # question is not answered with (and cited to) another filer's text.
    # Fill back with the remainder only if the filtered set is too small.
    if CONFIG.retrieval.company_filter:
        wanted = detect_tickers(query, chunks)
        if wanted:
            matching = [cid for cid in ranked_ids if by_id[cid]["ticker"] in wanted]
            if len(matching) >= top_k:
                ranked_ids = matching
            else:
                rest = [cid for cid in ranked_ids if by_id[cid]["ticker"] not in wanted]
                ranked_ids = matching + rest

    # --- Cross-encoder reranking ---
    # Rerank the fused head with a cross-encoder for precision, then cut to k.
    if use_reranker:
        head = ranked_ids[: max(CONFIG.retrieval.rerank_pool, top_k)]
        reranked = rerank(query, [by_id[cid] for cid in head])
        ranked_ids = [c["chunk_id"] for c, _s in reranked]

    ranked_ids = ranked_ids[:top_k]

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
