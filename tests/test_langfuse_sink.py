"""LangfuseSink against a fake SDK client: no server, no network, no ``langfuse``.

Covers the record -> observation mapping (nesting, types, prompt / response,
tokens, cost, prompt version, evidence-gate decision, rerank movement, errors),
the backdated-timestamp path, and the contract that everything stays inert
when Langfuse is not configured.
"""

from __future__ import annotations

import json
import sys
import types

import pytest

from finground import tracing
from finground.llm import LLMClient

TID = "0123456789abcdef0123456789abcdef"


@pytest.fixture(autouse=True)
def _no_langfuse_env(monkeypatch):
    for var in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "FINGROUND_TRACE_PROMPTS"):
        monkeypatch.delenv(var, raising=False)
    tracing.set_sinks(None)
    yield
    tracing.set_sinks(None)


class _Obs:
    """Records what the sink asked for; mimics LangfuseSpan.start_observation/end."""

    def __init__(self, log: list, parent: _Obs | None, **kw):
        self.log, self.parent, self.kw, self.ended = log, parent, kw, None
        log.append(self)

    def start_observation(self, **kw):
        return _Obs(self.log, self, **kw)

    def end(self, **kw):
        self.ended = kw
        return self


class _PublicClient:
    """Only the public v3+ surface (no OpenTelemetry internals)."""

    def __init__(self):
        self.log: list[_Obs] = []

    def start_observation(self, **kw):
        return _Obs(self.log, None, **kw)

    @staticmethod
    def create_trace_id(seed=None):
        return "f" * 32


def _record(**over):
    rec = {
        "schema": 1,
        "trace_id": TID,
        "name": "query",
        "ts": "2026-11-23T06:00:00.000+00:00",
        "duration_ms": 120.0,
        "source": "api",
        "question": "What risks does Apple disclose?",
        "model": "cohere:command-r7b-12-2024",
        "prompt_version": "answer.v1",
        "answer": "Supply chain concentration [C1].",
        "refused": False,
        "gate": None,
        "citations": ["C1"],
        "error": None,
        "retrieved": [{"label": "C1", "chunk_id": "AAPL-1", "dense_score": 0.7, "text": "..."}],
        "rerank_before": [
            {"chunk_id": "AAPL-2", "rrf_score": 0.03},
            {"chunk_id": "AAPL-1", "rrf_score": 0.02},
        ],
        "rerank_after": [
            {"chunk_id": "AAPL-1", "rerank_score": 5.0},
            {"chunk_id": "AAPL-2", "rerank_score": 1.0},
        ],
        "spans": [
            {"name": "retrieve.bm25", "start_ms": 1.0, "duration_ms": 2.0, "attrs": {"pool": 50}},
            {"name": "retrieve.rerank", "start_ms": 4.0, "duration_ms": 6.0, "attrs": {"pool": 2}},
            {"name": "retrieve", "start_ms": 0.5, "duration_ms": 10.0, "attrs": {"top_k": 1}},
            {
                "name": "evidence_gate",
                "start_ms": 11.0,
                "duration_ms": 0.01,
                "attrs": {"best_dense_sim": 0.7, "threshold": 0.4, "passed": True},
            },
            {
                "name": "generate",
                "start_ms": 12.0,
                "duration_ms": 100.0,
                "attrs": {
                    "model": "cohere:command-r7b-12-2024",
                    "prompt_tokens": 500,
                    "completion_tokens": 40,
                    "cost_usd": 0.0001,
                    "temperature": 0.0,
                    "prompt_hash": "h",
                    "prompt_system": "SYS",
                    "prompt_user": "USER",
                    "response_text": "Supply chain concentration [C1].",
                },
            },
        ],
    }
    rec.update(over)
    return rec


def _by_name(client):
    return {o.kw["name"]: o for o in client.log}


def test_maps_record_to_nested_observations():
    client = _PublicClient()
    tracing.LangfuseSink(client).write(_record())
    obs = _by_name(client)
    root = obs["finground.query"]
    assert root.parent is None
    assert root.kw["trace_context"] == {"trace_id": TID}  # same id as X-Trace-Id
    assert root.kw["input"]["question"] == "What risks does Apple disclose?"
    assert root.kw["version"] == "answer.v1"
    # dotted spans nest under their prefix span; top-level spans under the root
    assert obs["retrieve.bm25"].parent is obs["retrieve"]
    assert obs["retrieve.rerank"].parent is obs["retrieve"]
    assert obs["retrieve"].parent is root and obs["generate"].parent is root
    assert obs["retrieve"].kw["as_type"] == "retriever"
    assert obs["retrieve"].kw["output"][0]["chunk_id"] == "AAPL-1"
    assert obs["evidence_gate"].kw["as_type"] == "guardrail"
    assert obs["evidence_gate"].kw["output"]["decision"] == "pass"
    gen = obs["generate"].kw
    assert gen["as_type"] == "generation"
    assert gen["input"] == [
        {"role": "system", "content": "SYS"},
        {"role": "user", "content": "USER"},
    ]
    assert gen["output"] == "Supply chain concentration [C1]."
    assert gen["usage_details"] == {"input": 500, "output": 40, "total": 540}
    assert gen["cost_details"] == {"total": 0.0001}
    assert gen["version"] == "answer.v1"
    assert gen["model_parameters"] == {"temperature": 0.0}
    assert "prompt_user" not in gen["metadata"]  # raw text is IO, not metadata
    assert gen["metadata"]["duration_ms"] == 100.0
    assert all(o.ended is not None for o in client.log)


def test_rerank_movement():
    moves = tracing.rerank_movement(_record())
    assert moves[0] == {
        "chunk_id": "AAPL-1",
        "rank_before": 2,
        "rank_after": 1,
        "moved": 1,
        "rrf_score": 0.02,
        "rerank_score": 5.0,
    }
    assert moves[1]["moved"] == -1


def test_gate_refusal_and_errors_set_levels():
    client = _PublicClient()
    rec = _record(refused=True, gate="evidence_below_threshold", answer="Not answerable.")
    rec["spans"][3]["attrs"]["passed"] = False
    rec["spans"] = rec["spans"][:4]  # gated: no generate span
    tracing.LangfuseSink(client).write(rec)
    gate = _by_name(client)["evidence_gate"].kw
    assert gate["output"]["decision"] == "refuse" and gate["level"] == "WARNING"
    assert tracing.LangfuseSink._tags(rec)[:2] == ["refused", "gate:evidence_below_threshold"]

    client = _PublicClient()
    rec = _record(error={"type": "LLMUnavailable", "message": "OPENAI_API_KEY not set"})
    rec["spans"][4]["attrs"] = {
        "model": "openai:x",
        "error": "LLMUnavailable",
        "error_message": "m",
    }
    tracing.LangfuseSink(client).write(rec)
    obs = _by_name(client)
    assert obs["finground.query"].kw["level"] == "ERROR"
    assert "OPENAI_API_KEY" in obs["finground.query"].kw["status_message"]
    assert obs["generate"].kw["level"] == "ERROR"
    assert obs["generate"].kw["status_message"] == "LLMUnavailable: m"
    assert "output" not in obs["generate"].kw  # no fake answer on a failed call


def test_backdated_path_uses_real_span_times():
    otel_trace = pytest.importorskip("opentelemetry.trace")
    started = []

    class _Span:
        def __init__(self, name, start_time):
            self.name, self.start_time, self.attrs = name, start_time, {}

        def set_attribute(self, k, v):
            self.attrs[k] = v

    class _Tracer:
        def start_span(self, name, context=None, start_time=None):
            span = _Span(name, start_time)
            started.append(span)
            return span

    class _Wrapped(_Obs):
        def __init__(self, log, otel_span, **kw):
            super().__init__(log, None, **kw)
            self._otel_span = otel_span

    class _OtelClient(_PublicClient):
        _otel_tracer = _Tracer()

        def _create_remote_parent_span(self, trace_id, parent_span_id):
            return otel_trace.NonRecordingSpan(otel_trace.INVALID_SPAN_CONTEXT)

        def _create_observation_from_otel_span(self, otel_span, **kw):
            return _Wrapped(self.log, otel_span, name=otel_span.name, **kw)

    client = _OtelClient()
    sink = tracing.LangfuseSink(client)
    sink.write(_record())
    assert sink._backdate is True
    base = tracing._epoch_ns("2026-11-23T06:00:00.000+00:00")
    by = {s.name: s for s in started}
    assert by["finground.query"].start_time == base
    assert by["finground.query"].attrs["langfuse.internal.as_root"] is True
    assert by["generate"].start_time == base + 12_000_000
    gen = next(o for o in client.log if o.kw["name"] == "generate")
    assert gen.ended == {"end_time": base + 112_000_000}


def test_falls_back_to_public_api_when_sdk_internals_change():
    class _Broken(_PublicClient):
        _otel_tracer = None  # attribute present but unusable

    client = _Broken()
    sink = tracing.LangfuseSink(client)
    sink.write(_record())
    assert sink._backdate is False
    assert len(client.log) == 6 and all(o.ended == {} for o in client.log)


def test_inert_without_keys(monkeypatch):
    calls = []
    monkeypatch.setitem(
        sys.modules, "langfuse", types.SimpleNamespace(Langfuse=lambda: calls.append(1))
    )
    assert not tracing.LangfuseSink.configured()
    assert not tracing.capture_prompts()
    assert [type(s).__name__ for s in tracing._sinks()] == ["JsonlSink"]
    assert calls == []  # the SDK is never even constructed


def test_missing_package_disables_only_that_sink(monkeypatch):
    monkeypatch.setitem(sys.modules, "langfuse", None)  # import raises ImportError
    sink = tracing.LangfuseSink()
    sink.write(_record())  # no error
    assert sink._failed


def test_broken_langfuse_never_breaks_request_or_jsonl(tmp_path):
    class _Exploding:
        def start_observation(self, **kw):
            raise RuntimeError("server down")

    tracing.set_sinks([tracing.LangfuseSink(_Exploding()), tracing.JsonlSink(tmp_path)])
    with tracing.trace("query", question="q"):
        tracing.record_span("retrieve", tracing.now())
    assert len(tracing.load_traces(tmp_path)) == 1


def _llm_span(monkeypatch, tmp_path):
    """Run LLMClient.complete with a stubbed provider inside a trace."""
    monkeypatch.setattr(LLMClient, "_dispatch", lambda self, s, u, m: ("ANSWER", 10, 2))
    tracing.set_sinks([tracing.JsonlSink(tmp_path)])
    captured = []
    with tracing.trace("query", question="q") as tr:
        LLMClient("cohere:command-r7b-12-2024", use_cache=False).complete("SYS", "USER")
        captured = [dict(s) for s in tr.spans]
    on_disk = json.loads(next(tmp_path.glob("*.jsonl")).read_text())
    return captured[0]["attrs"], on_disk["spans"][0]["attrs"]


def test_raw_prompt_captured_for_langfuse_but_not_written_to_jsonl(monkeypatch, tmp_path):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk")
    in_memory, on_disk = _llm_span(monkeypatch, tmp_path)
    assert in_memory["prompt_user"] == "USER" and in_memory["response_text"] == "ANSWER"
    assert not set(tracing.RAW_TEXT_ATTRS) & set(on_disk)
    assert on_disk["prompt_hash"] == in_memory["prompt_hash"]


def test_raw_prompt_absent_by_default_and_kept_with_flag(monkeypatch, tmp_path):
    in_memory, on_disk = _llm_span(monkeypatch, tmp_path / "a")
    assert "prompt_user" not in in_memory and "prompt_user" not in on_disk
    monkeypatch.setenv("FINGROUND_TRACE_PROMPTS", "1")
    _, on_disk = _llm_span(monkeypatch, tmp_path / "b")
    assert on_disk["prompt_system"] == "SYS" and on_disk["response_text"] == "ANSWER"
