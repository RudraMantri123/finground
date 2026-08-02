"""Unit tests for cited answering, citation parsing, and the refusal gate.

The LLM and retriever are stubbed, so these run with no API key or network.
"""

from __future__ import annotations

import finground.answer as A
from finground.answer import (
    answer_question,
    extract_cited_labels,
    is_refusal,
)
from finground.llm import LLMResponse
from finground.retrieve import RetrievedChunk


def _rc(label, cid, ticker, section, text, dense):
    return RetrievedChunk(
        label=label,
        chunk_id=cid,
        doc_id=f"{ticker}-10-K-acc",
        company=f"{ticker} Inc.",
        ticker=ticker,
        section=section,
        filing_type="10-K",
        filing_date="2024-01-01",
        text=text,
        rrf_score=0.03,
        dense_score=dense,
        bm25_score=1.0,
        span=(0, len(text)),
    )


# -- pure parsing -----------------------------------------------------------


def test_extract_cited_labels_variants():
    assert extract_cited_labels("Revenue rose [C1].") == ["C1"]
    assert extract_cited_labels("Both [C2, C3] and later [C2].") == ["C2", "C3"]
    assert extract_cited_labels("No citations here.") == []


def test_is_refusal():
    assert is_refusal("Not answerable from the provided filings.")
    assert is_refusal("not answerable from the provided filings")
    assert not is_refusal("Apple faces supply chain risk [C1].")


# -- evidence gate (no LLM call) -------------------------------------------


def test_evidence_gate_abstains_on_weak_retrieval(monkeypatch):
    weak = [_rc("C1", "x-0", "MSFT", "Item 2. Properties", "office leases", dense=0.20)]
    monkeypatch.setattr(A, "retrieve", lambda q, top_k=None: weak)

    def _boom(*a, **k):  # LLM must NOT be constructed when gated
        raise AssertionError("LLM should not be called when evidence is gated")

    monkeypatch.setattr(A, "LLMClient", _boom)
    ans = answer_question("What is the capital of France?")
    assert ans.abstained
    assert ans.answer == A.REFUSAL
    assert ans.citations == []
    assert ans.meta.get("gate") == "evidence_below_threshold"


# -- full answer path with a stubbed LLM ------------------------------------


class _StubClient:
    def __init__(self, model_spec, **kwargs):
        self.model_spec = model_spec

    def complete(self, system, user, **kwargs):
        return LLMResponse(
            text="Apple cites component supplier concentration [C1] and manufacturing in Asia [C2].",
            model=self.model_spec,
            prompt_tokens=500,
            completion_tokens=40,
            latency_s=0.9,
        )


def test_cited_answer_maps_citations(monkeypatch):
    strong = [
        _rc("C1", "AAPL-1", "AAPL", "Item 1A. Risk Factors", "supplier concentration risk", 0.70),
        _rc(
            "C2",
            "AAPL-2",
            "AAPL",
            "Item 1A. Risk Factors",
            "manufacturing concentrated in Asia",
            0.66,
        ),
        _rc("C3", "AAPL-3", "AAPL", "Item 1. Business", "product lineup overview", 0.55),
    ]
    monkeypatch.setattr(A, "retrieve", lambda q, top_k=None: strong)
    monkeypatch.setattr(A, "LLMClient", _StubClient)

    ans = answer_question("What supply chain risks does Apple cite?", model="openai:gpt-4o-mini")
    assert not ans.abstained
    assert {c["label"] for c in ans.citations} == {"C1", "C2"}  # only cited ones
    # Citations resolve to the right chunk_ids / provenance.
    by_label = {c["label"]: c for c in ans.citations}
    assert by_label["C1"]["chunk_id"] == "AAPL-1"
    assert "Risk Factors" in by_label["C1"]["provenance"]
    assert ans.prompt_tokens == 500
    assert ans.completion_tokens == 40


def test_model_refusal_is_detected(monkeypatch):
    strong = [_rc("C1", "AAPL-1", "AAPL", "Item 1A. Risk Factors", "some text", 0.70)]
    monkeypatch.setattr(A, "retrieve", lambda q, top_k=None: strong)

    class _RefuseClient(_StubClient):
        def complete(self, system, user, **kwargs):
            return LLMResponse(A.REFUSAL, self.model_spec, 300, 8, 0.4)

    monkeypatch.setattr(A, "LLMClient", _RefuseClient)
    ans = answer_question("Something the excerpts don't cover", model="openai:gpt-4o-mini")
    assert ans.abstained
    assert ans.citations == []
