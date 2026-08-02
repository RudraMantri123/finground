"""Unit tests for hybrid retrieval + provenance.

These build a tiny in-memory index and stub the query embedder, so they run
without network access or the embedding model download.
"""

from __future__ import annotations

import faiss
import numpy as np
import pytest
from rank_bm25 import BM25Okapi

import finground.retrieve as R
from finground.index import tokenize
from finground.retrieve import RetrievedChunk, best_dense_sim, retrieve


def _chunk(cid, ticker, company, section, text):
    return {
        "chunk_id": cid,
        "doc_id": f"{ticker}-10-K-acc",
        "company": company,
        "ticker": ticker,
        "cik": "0000000000",
        "filing_type": "10-K",
        "filing_date": "2024-01-01",
        "section": section,
        "span": [0, len(text)],
        "text": text,
    }


CHUNKS = [
    _chunk(
        "AAPL-c0",
        "AAPL",
        "Apple Inc.",
        "Item 1A. Risk Factors",
        "supply chain risk apple manufacturing components suppliers",
    ),
    _chunk(
        "NVDA-c0",
        "NVDA",
        "NVIDIA Corporation",
        "Item 7. Management's Discussion and Analysis",
        "data center revenue growth gpus accelerated computing",
    ),
    _chunk(
        "KO-c0",
        "KO",
        "The Coca-Cola Company",
        "Item 1. Business",
        "beverage sales marketing brands bottling partners",
    ),
]

# One orthonormal 4-d vector per chunk (rows aligned to CHUNKS order).
_VECS = np.array(
    [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0]],
    dtype="float32",
)


@pytest.fixture
def tiny_index(monkeypatch):
    faiss_index = faiss.IndexFlatIP(4)
    faiss_index.add(_VECS)
    idx = R._Indexes(
        bm25=BM25Okapi([tokenize(c["text"]) for c in CHUNKS]),
        bm25_chunks=CHUNKS,
        faiss_index=faiss_index,
        dense_chunks=CHUNKS,
        model_name="stub",
    )
    monkeypatch.setattr(R, "_CACHE", idx)
    # Query embeds near the Apple vector so dense agrees with BM25.
    monkeypatch.setattr(
        R,
        "embed_queries",
        lambda texts, model_name=None: np.array([[0.95, 0.1, 0.0, 0.0]], dtype="float32"),
    )
    return idx


def test_retrieve_returns_provenance(tiny_index):
    results = retrieve("apple supply chain risk", top_k=3)
    assert results, "expected results"
    for r in results:
        assert isinstance(r, RetrievedChunk)
        # Every result carries full provenance back to its source filing.
        assert r.chunk_id
        assert r.doc_id
        assert r.ticker in {"AAPL", "NVDA", "KO"}
        assert r.section
        assert r.filing_type == "10-K"
        assert r.filing_date == "2024-01-01"
        assert r.text
        assert r.provenance().startswith(r.ticker)


def test_retrieve_labels_are_sequential(tiny_index):
    results = retrieve("apple supply chain risk", top_k=3)
    assert [r.label for r in results] == ["C1", "C2", "C3"]


def test_retrieve_ranks_relevant_first(tiny_index):
    # Both BM25 (token overlap) and dense (vector proximity) favor Apple.
    results = retrieve("apple supply chain risk manufacturing", top_k=3)
    assert results[0].ticker == "AAPL"
    assert results[0].section == "Item 1A. Risk Factors"


def test_retrieve_scores_present(tiny_index):
    results = retrieve("data center gpu revenue", top_k=3)
    top = results[0]
    assert top.rrf_score > 0
    # Component scores are attached for transparency.
    assert isinstance(top.dense_score, float)
    assert isinstance(top.bm25_score, float)
    assert best_dense_sim(results) == max(r.dense_score for r in results)


def test_retrieve_respects_top_k(tiny_index):
    assert len(retrieve("anything", top_k=1)) == 1
    assert len(retrieve("anything", top_k=2)) == 2
