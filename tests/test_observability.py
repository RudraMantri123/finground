"""Tests for operational metrics (percentiles, CIs, citation coverage) and tracing.

Tracing has one hard contract: it must never raise into the request path, even
when a sink or the trace itself is broken. These tests exercise the pipeline
with a stubbed retriever and LLM, so no index, model, or network is needed.
"""

from __future__ import annotations

import json

import pytest

import finground.answer as A
from finground import tracing
from finground.dashboard import build_dashboard
from finground.eval.metrics import (
    bootstrap_ci,
    citation_coverage,
    claim_units,
    failure_rate,
    percentile,
    response_citation_coverage,
)
from finground.eval.summary import summarize_rows
from finground.llm import LLMResponse
from finground.retrieve import RetrievedChunk

# -- percentiles ------------------------------------------------------------


def test_percentile_matches_linear_interpolation():
    xs = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert percentile(xs, 50) == 3.0
    assert percentile(xs, 0) == 1.0
    assert percentile(xs, 100) == 5.0
    assert percentile(xs, 95) == pytest.approx(4.8)  # numpy.percentile(xs, 95)
    assert percentile([10.0, 20.0], 50) == 15.0
    assert percentile([7.0], 95) == 7.0
    assert percentile([], 50) is None
    assert percentile([3.0, 1.0, 2.0], 50) == 2.0  # order-independent


def test_percentile_rejects_bad_q():
    with pytest.raises(ValueError):
        percentile([1.0], 101)


# -- bootstrap CI -----------------------------------------------------------


def _mean(xs):
    return sum(xs) / len(xs) if xs else None


def test_bootstrap_ci_is_seeded_and_brackets_the_estimate():
    data = [1, 0, 1, 1, 0, 1, 0, 1, 1, 1]
    a = bootstrap_ci(data, _mean, n_resamples=1000, seed=0)
    b = bootstrap_ci(data, _mean, n_resamples=1000, seed=0)
    assert a == b  # reproducible
    assert a is not None
    lo, hi = a
    assert 0.0 <= lo <= _mean(data) <= hi <= 1.0
    assert hi - lo > 0.2  # n=10 should give a wide interval


def test_bootstrap_ci_degenerate_cases():
    assert bootstrap_ci([], _mean) is None
    assert bootstrap_ci([1, 1, 1], _mean) == (1.0, 1.0)
    assert bootstrap_ci([1, 2], lambda xs: None) is None  # undefined everywhere


# -- citation coverage -------------------------------------------------------


VALID = {"C1", "C2", "C3"}


def test_claim_units_skip_structure():
    text = (
        "## Summary\n"
        "Apple discloses the following risks:\n"
        "* Supply concentration in Asia [C1].\n"
        "* Component shortages [C2]. Prices may rise [C3].\n"
        "[C1]\n"
    )
    assert claim_units(text) == [
        "Supply concentration in Asia [C1].",
        "Component shortages [C2].",
        "Prices may rise [C3].",
    ]


def test_claim_units_do_not_split_decimals_or_abbreviations():
    assert claim_units("Revenue was $1.5 billion at Apple Inc. in 2024 [C1].") == [
        "Revenue was $1.5 billion at Apple Inc. in 2024 [C1]."
    ]


def test_response_citation_coverage():
    assert response_citation_coverage("Revenue rose [C1]. Margins fell [C2, C3].", VALID)
    # An uncited editorial sentence fails the response.
    assert not response_citation_coverage("Revenue rose [C1]. This suggests strength.", VALID)
    # A citation to an excerpt that was never retrieved fails it too.
    assert not response_citation_coverage("Revenue rose [C9].", VALID)
    assert not response_citation_coverage("Revenue rose [C1, C9].", VALID)
    assert not response_citation_coverage("", VALID)


def test_citation_coverage_and_failure_rate_aggregates():
    assert citation_coverage([True, False, None, True]) == pytest.approx(2 / 3)
    assert citation_coverage([None, None]) is None
    assert failure_rate(10, 1, 2) == pytest.approx(0.3)
    assert failure_rate(0, 0, 0) is None


def test_summarize_rows_end_to_end():
    rows = [
        {
            "id": "q1",
            "answerable": True,
            "abstained": False,
            "answer": "Revenue rose [C1].",
            "retrieved_labels": ["C1", "C2"],
            "latency_s": 1.0,
            "cost_usd": 0.01,
            "judge": {
                "correct": True,
                "claims": [{"supported": True}],
                "citations": [{"supports": True}],
            },
        },
        {
            "id": "q2",
            "answerable": True,
            "abstained": False,
            "answer": "Revenue fell. Costs rose [C2].",
            "retrieved_labels": ["C1", "C2"],
            "latency_s": 3.0,
            "cost_usd": 0.03,
            "judge": {
                "correct": False,
                "claims": [{"supported": True}, {"supported": False}],
                "citations": [{"supports": False}],
            },
        },
        {"id": "q3", "answerable": False, "abstained": True, "answer": A.REFUSAL},
        {"id": "q4", "question": "boom", "error": "timeout"},
    ]
    s = summarize_rows(rows, model="openai:x", judge="openai:j", n_resamples=200)
    assert s["n_questions"] == 4 and s["n_answered"] == 2
    assert s["correctness"] == 0.5
    assert s["citation_accuracy"] == 0.5
    assert s["hallucination_rate"] == pytest.approx(0.25)
    assert s["refusal_calibration"] == 1.0  # answered both answerable, refused the other
    assert s["citation_coverage"] == 0.5  # q2 has an uncited sentence
    assert s["failure_rate"] == pytest.approx(2 / 4)  # q4 exception + q2 unsupported
    assert s["latency_p50_s"] == 2.0
    assert s["latency_p95_s"] == pytest.approx(2.9)
    assert s["cost_per_request"] == pytest.approx(0.01)
    assert s["cost_per_100q"] == pytest.approx(1.0)
    for m in ("correctness", "citation_accuracy", "hallucination_rate"):
        assert s[f"{m}_ci_lo"] <= s[m] <= s[f"{m}_ci_hi"]


# -- tracing ----------------------------------------------------------------


def _rc(label, cid, dense):
    return RetrievedChunk(
        label=label,
        chunk_id=cid,
        doc_id="AAPL-10-K",
        company="Apple Inc.",
        ticker="AAPL",
        section="Item 1A. Risk Factors",
        filing_type="10-K",
        filing_date="2024-01-01",
        text="supplier concentration risk " * 3,
        rrf_score=0.03,
        dense_score=dense,
        bm25_score=1.0,
    )


class _StubClient:
    """Mimics LLMClient including the generation span it records."""

    def __init__(self, model_spec, **kwargs):
        self.model_spec = model_spec

    def complete(self, system, user, **kwargs):
        t0 = tracing.now()
        tracing.record_span("generate", t0, model=self.model_spec, prompt_hash="abc")
        return LLMResponse(
            text="Apple cites supplier concentration [C1].",
            model=self.model_spec,
            prompt_tokens=500,
            completion_tokens=40,
            latency_s=0.9,
        )


class _MemorySink:
    def __init__(self):
        self.records = []

    def write(self, record):
        self.records.append(json.loads(json.dumps(record, default=str)))


class _BrokenSink:
    def write(self, record):
        raise OSError("disk full")


@pytest.fixture
def memory_sink():
    sink = _MemorySink()
    tracing.set_sinks([_BrokenSink(), sink])  # a failing sink must not block the next
    yield sink
    tracing.set_sinks(None)


@pytest.fixture
def stub_pipeline(monkeypatch):
    monkeypatch.setattr(A, "retrieve", lambda q, top_k=None: [_rc("C1", "AAPL-1", 0.7)])
    monkeypatch.setattr(A, "LLMClient", _StubClient)


def test_trace_records_answer_spans_and_metadata(memory_sink, stub_pipeline):
    with tracing.trace("query", source="test", question="Apple risks?") as tr:
        ans = A.answer_question("Apple risks?", model="openai:gpt-4o-mini")
        tracing.record_answer(ans)
    assert tr is not None
    (rec,) = memory_sink.records
    assert rec["trace_id"] == tr.trace_id
    assert rec["question"] == "Apple risks?"
    assert rec["model"] == "openai:gpt-4o-mini"
    assert rec["refused"] is False
    assert rec["citation_coverage"] is True
    assert rec["prompt_tokens"] == 500 and rec["completion_tokens"] == 40
    assert rec["prompt_hash"] == "abc"
    assert rec["retrieved"][0]["chunk_id"] == "AAPL-1"
    assert rec["error"] is None
    names = [s["name"] for s in rec["spans"]]
    assert "evidence_gate" in names and "generate" in names
    assert all(s["duration_ms"] >= 0 for s in rec["spans"])


def test_trace_records_and_reraises_request_errors(memory_sink):
    with pytest.raises(RuntimeError, match="kaput"):
        with tracing.trace("query", question="x"):
            raise RuntimeError("kaput")
    (rec,) = memory_sink.records
    assert rec["error"] == {"type": "RuntimeError", "message": "kaput"}


def test_nested_span_prefixes_child_names(memory_sink):
    with tracing.trace("benchmark_item"):
        with tracing.span("judge"):
            tracing.record_span("generate", tracing.now())
    names = {s["name"] for s in memory_sink.records[0]["spans"]}
    assert names == {"judge.generate", "judge"}


def test_tracing_helpers_are_noops_without_a_trace():
    tracing.record_span("x", tracing.now(), a=1)
    tracing.annotate(a=1)
    tracing.record_error(ValueError("x"))
    tracing.record_answer(object())
    with tracing.span("x"):
        pass
    assert not tracing.active()


def test_tracing_never_raises_on_bad_inputs(memory_sink, monkeypatch):
    with tracing.trace("query") as tr:
        tracing.record_span("bad", "not-a-float")  # type: ignore[arg-type]
        tracing.record_answer(None)
        tracing.annotate(unserialisable=object())  # JSON sink uses default=str
        tr._stack = None  # corrupt internal state
        with tracing.span("still-fine"):
            pass
    assert len(memory_sink.records) == 1

    # Serialisation itself blowing up is swallowed too.
    monkeypatch.setattr(tracing.Trace, "to_record", lambda self: 1 / 0)
    with tracing.trace("query"):
        pass


def test_tracing_disabled_by_env(memory_sink, monkeypatch, stub_pipeline):
    monkeypatch.setenv("FINGROUND_TRACING", "0")
    with tracing.trace("query") as tr:
        A.answer_question("Apple risks?", model="openai:gpt-4o-mini")
    assert tr is None and memory_sink.records == []


def test_jsonl_sink_and_dashboard(tmp_path, stub_pipeline):
    tracing.set_sinks([tracing.JsonlSink(tmp_path)])
    try:
        for q in ("Apple risks?", "Apple suppliers?"):
            with tracing.trace("query", source="test", question=q):
                tracing.annotate(
                    rerank_before=[{"chunk_id": "AAPL-1", "rrf_score": 0.03}],
                    rerank_after=[{"chunk_id": "AAPL-1", "rerank_score": 4.2}],
                )
                tracing.record_answer(A.answer_question(q, model="openai:gpt-4o-mini"))
    finally:
        tracing.set_sinks(None)
    files = list(tmp_path.glob("*.jsonl"))
    assert len(files) == 1
    recs = tracing.load_traces(tmp_path)
    assert [r["question"] for r in recs] == ["Apple risks?", "Apple suppliers?"]

    page = build_dashboard(tmp_path, tmp_path / "missing.csv")
    assert "<title>FinGround Observability</title>" in page
    assert "Span latency over time" in page and "evidence_gate" in page
    assert "Apple suppliers?" in page  # drill-down payload


def test_langfuse_sink_with_fake_sdk(monkeypatch):
    """The optional sink maps a record onto the v3+ SDK surface without the package."""
    import sys
    import types

    calls = []

    class _Obs:
        def __init__(self, **kw):
            calls.append(kw)

        def start_observation(self, **kw):
            return _Obs(**kw)

        def end(self, **kw):
            return self

    class _Client:
        def start_observation(self, **kw):
            return _Obs(**kw)

        @staticmethod
        def create_trace_id(seed=None):
            return "f" * 32

    monkeypatch.setitem(sys.modules, "langfuse", types.SimpleNamespace(Langfuse=_Client))
    sink = tracing.LangfuseSink()
    sink.write(
        {
            "trace_id": "abc",
            "name": "query",
            "question": "q",
            "answer": "a",
            "error": None,
            "spans": [
                {"name": "retrieve", "start_ms": 0, "duration_ms": 5},
                {
                    "name": "generate",
                    "start_ms": 5,
                    "duration_ms": 9,
                    "attrs": {"model": "m", "prompt_tokens": 3, "completion_tokens": 2},
                },
            ],
        }
    )
    assert calls[0]["trace_context"] == {"trace_id": "f" * 32}
    gen = next(c for c in calls if c.get("name") == "generate")
    assert gen["as_type"] == "generation"
    assert gen["usage_details"] == {"input": 3, "output": 2, "total": 5}
