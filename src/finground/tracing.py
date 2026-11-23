"""Request tracing: one trace per question, with per-stage spans.

Why this exists: aggregate benchmark numbers say *that* quality moved, not
*why*. A trace keeps the evidence for one request — what was retrieved, how the
cross-encoder reordered it, whether the evidence gate fired, which model and
prompt version answered, what it cost and how long each stage took — so a
regression can be traced to the stage that caused it.

Design constraints:

* **Never break the request path.** Every public helper swallows its own
  failures. The only exception that escapes :func:`trace` is the one raised by
  the traced code itself, which is recorded and then re-raised untouched.
* **Negligible overhead.** With no active trace every helper is a context-var
  lookup and a return. Callers guard expensive attribute building with
  :func:`active`. Emission is one JSON line appended to a local file.
* **Merge-friendly instrumentation.** Pipeline code records leaf spans with
  ``t0 = tracing.now(); ...; tracing.record_span("name", t0)`` — added lines
  only, no re-indented blocks.

Sinks:

* JSONL (default): ``traces/YYYY-MM-DD.jsonl`` (UTC day), append-only. Override
  the directory with ``FINGROUND_TRACE_DIR``; disable all tracing with
  ``FINGROUND_TRACING=0``.
* Langfuse (optional): enabled when ``LANGFUSE_PUBLIC_KEY`` and
  ``LANGFUSE_SECRET_KEY`` are set *and* the ``langfuse`` package is importable
  (``pip install -e ".[observability]"``). Missing package or a failing server
  only disables that sink.

Raw prompts are not written to JSONL by default (they embed whole filing
excerpts and make trace files large); the prompt is identified by a SHA-256
hash instead. Set ``FINGROUND_TRACE_PROMPTS=1`` to keep the raw text too. When
Langfuse is configured the exact prompt and raw response are always exported
there (that is the point of a trace UI), still without growing the JSONL.
"""

from __future__ import annotations

import contextvars
import hashlib
import json
import os
import re
import threading
import time
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import CONFIG

SCHEMA_VERSION = 1

# Characters of chunk text kept per retrieved chunk for the dashboard drill-down.
# Enough to recognise the passage; the full text is recoverable by chunk_id.
CHUNK_PREVIEW_CHARS = 280

now = time.perf_counter  # span clock (monotonic); re-exported for call sites


def _env_flag(name: str, default: bool) -> bool:
    val = os.environ.get(name)
    if val is None or val == "":
        return default
    return val.strip().lower() not in {"0", "false", "no", "off"}


def enabled() -> bool:
    """Tracing is on unless ``FINGROUND_TRACING`` is set to a false value."""
    return _env_flag("FINGROUND_TRACING", True)


def store_prompts() -> bool:
    """Keep raw prompt / response text in the JSONL trace files."""
    return _env_flag("FINGROUND_TRACE_PROMPTS", False)


# Span attributes holding raw prompt / response text. Captured whenever a sink
# wants them (JSONL with FINGROUND_TRACE_PROMPTS=1, or Langfuse), but written to
# JSONL only when FINGROUND_TRACE_PROMPTS=1.
RAW_TEXT_ATTRS = ("prompt_system", "prompt_user", "response_text")


def capture_prompts() -> bool:
    """Whether call sites should record raw prompt / response text on spans."""
    return store_prompts() or LangfuseSink.configured()


def trace_dir() -> Path:
    override = os.environ.get("FINGROUND_TRACE_DIR")
    return Path(override) if override else CONFIG.paths.root / "traces"


def prompt_hash(*parts: str) -> str:
    """Stable hash identifying the exact prompt sent to the model."""
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8", errors="replace"))
        h.update(b"\x00")
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Trace object
# ---------------------------------------------------------------------------


class Trace:
    """In-memory record of one request; serialised once when it finishes."""

    __slots__ = ("trace_id", "name", "started_at", "_t0", "attrs", "spans", "error", "_stack")

    def __init__(self, name: str, attrs: dict[str, Any]):
        self.trace_id = uuid.uuid4().hex
        self.name = name
        self.started_at = datetime.now(UTC)
        self._t0 = now()
        self.attrs: dict[str, Any] = dict(attrs)
        self.spans: list[dict[str, Any]] = []
        self.error: dict[str, str] | None = None
        self._stack: list[str] = []  # names of open span() blocks, for nesting

    def _full_name(self, name: str) -> str:
        return ".".join([*self._stack, name]) if self._stack else name

    def add_span(self, name: str, start: float, end: float, attrs: dict[str, Any]) -> None:
        self.spans.append(
            {
                "name": self._full_name(name),
                "start_ms": round((start - self._t0) * 1000, 3),
                "duration_ms": round((end - start) * 1000, 3),
                **({"attrs": attrs} if attrs else {}),
            }
        )

    def to_record(self) -> dict[str, Any]:
        record: dict[str, Any] = {
            "schema": SCHEMA_VERSION,
            "trace_id": self.trace_id,
            "name": self.name,
            "ts": self.started_at.isoformat(timespec="milliseconds"),
            "duration_ms": round((now() - self._t0) * 1000, 3),
        }
        record.update(self.attrs)
        record["error"] = self.error
        record["spans"] = self.spans
        return record


_CURRENT: contextvars.ContextVar[Trace | None] = contextvars.ContextVar(
    "finground_trace", default=None
)


def current() -> Trace | None:
    return _CURRENT.get()


def active() -> bool:
    """Cheap guard so call sites skip building trace-only data when untraced."""
    return _CURRENT.get() is not None


def current_trace_id() -> str | None:
    t = _CURRENT.get()
    return t.trace_id if t is not None else None


# ---------------------------------------------------------------------------
# Recording API (all no-ops without an active trace; none of them raise)
# ---------------------------------------------------------------------------


def record_span(name: str, start: float, **attrs: Any) -> None:
    """Record a finished leaf span that began at ``start`` (from :data:`now`)."""
    t = _CURRENT.get()
    if t is None:
        return
    try:
        t.add_span(name, start, now(), attrs)
    except Exception:  # noqa: BLE001 — tracing must never break the request
        pass


def annotate(**attrs: Any) -> None:
    """Attach top-level fields to the current trace (later calls win)."""
    t = _CURRENT.get()
    if t is None:
        return
    try:
        t.attrs.update(attrs)
    except Exception:  # noqa: BLE001
        pass


def record_error(exc: BaseException) -> None:
    """Mark the current trace failed without raising (for handled errors)."""
    t = _CURRENT.get()
    if t is None:
        return
    try:
        t.error = {"type": type(exc).__name__, "message": str(exc)[:500]}
    except Exception:  # noqa: BLE001
        pass


@contextmanager
def span(name: str, **attrs: Any) -> Iterator[None]:
    """Time a block; leaf spans recorded inside it are nested under ``name``."""
    t = _CURRENT.get()
    if t is None:
        yield
        return
    start = now()
    pushed = False
    try:
        t._stack.append(name)
        pushed = True
    except Exception:  # noqa: BLE001
        pass
    try:
        yield
    except BaseException as exc:
        attrs = {**attrs, "error": type(exc).__name__}
        raise
    finally:
        try:
            if pushed:
                t._stack.pop()
            t.add_span(name, start, now(), attrs)
        except Exception:  # noqa: BLE001
            pass


@contextmanager
def trace(name: str, **attrs: Any) -> Iterator[Trace | None]:
    """Open a trace for one request and emit it to the sinks when done.

    Yields the :class:`Trace` (or ``None`` when tracing is disabled or setup
    failed). Exceptions from the body are recorded on the trace and re-raised.
    Nested ``trace()`` calls join the outer trace instead of starting a new one.
    """
    if _CURRENT.get() is not None:
        yield _CURRENT.get()
        return
    tr: Trace | None = None
    token = None
    try:
        if enabled():
            tr = Trace(name, attrs)
            token = _CURRENT.set(tr)
    except Exception:  # noqa: BLE001
        tr = None
    try:
        yield tr
    except BaseException as exc:
        if tr is not None and tr.error is None:
            try:
                tr.error = {"type": type(exc).__name__, "message": str(exc)[:500]}
            except Exception:  # noqa: BLE001
                pass
        raise
    finally:
        if token is not None:
            try:
                _CURRENT.reset(token)
            except Exception:  # noqa: BLE001
                pass
        if tr is not None:
            emit(tr)


# ---------------------------------------------------------------------------
# Domain helpers
# ---------------------------------------------------------------------------


def _preview(text: Any) -> str:
    s = str(text or "")
    return s if len(s) <= CHUNK_PREVIEW_CHARS else s[:CHUNK_PREVIEW_CHARS] + "…"


def resolve_prompt_version(meta: dict | None = None) -> str | None:
    """Best-effort prompt version, read defensively.

    Prompt versioning is introduced separately from tracing, so its exact shape
    is not assumed: an explicit ``Answer.meta['prompt_version']`` wins, then a
    ``PROMPT_VERSION``-style constant on ``finground.prompts`` or
    ``finground.answer``. Anything unexpected yields ``None``.
    """
    try:
        if meta and meta.get("prompt_version"):
            return str(meta["prompt_version"])
        import importlib

        for mod_name in ("finground.prompts", "finground.answer"):
            try:
                mod = importlib.import_module(mod_name)
            except Exception:  # noqa: BLE001
                continue
            for attr in ("ANSWER_PROMPT_VERSION", "PROMPT_VERSION"):
                val = getattr(mod, attr, None)
                if isinstance(val, str | int | float) and str(val):
                    return str(val)
            getter = getattr(mod, "prompt_version", None)
            if callable(getter):
                try:
                    val = getter("answer")
                except TypeError:
                    val = getter()
                if val:
                    return str(val)
    except Exception:  # noqa: BLE001
        return None
    return None


def record_answer(ans: Any) -> None:
    """Copy the outcome of ``answer_question`` onto the current trace.

    Takes the ``Answer`` duck-typed so this module never imports the pipeline
    (which would pull in FAISS / torch just to trace).
    """
    t = _CURRENT.get()
    if t is None:
        return
    try:
        from .eval.metrics import response_citation_coverage

        retrieved = list(getattr(ans, "retrieved", []) or [])
        meta = dict(getattr(ans, "meta", {}) or {})
        abstained = bool(getattr(ans, "abstained", False))
        answer_text = str(getattr(ans, "answer", ""))
        valid_labels = {r.get("label") for r in retrieved}
        t.attrs.update(
            {
                "question": t.attrs.get("question") or getattr(ans, "question", None),
                "model": getattr(ans, "model", None),
                "prompt_version": getattr(ans, "prompt_version", None)
                or resolve_prompt_version(meta),
                "answer": answer_text,
                "refused": abstained,
                "gate": meta.get("gate"),
                "best_dense_sim": getattr(ans, "best_dense_sim", None),
                "citations": [c.get("label") for c in getattr(ans, "citations", []) or []],
                "citation_coverage": (
                    None if abstained else response_citation_coverage(answer_text, valid_labels)
                ),
                "prompt_tokens": getattr(ans, "prompt_tokens", 0),
                "completion_tokens": getattr(ans, "completion_tokens", 0),
                "prompt_hash": next(
                    (
                        sp.get("attrs", {}).get("prompt_hash")
                        for sp in t.spans
                        if sp.get("name") == "generate"
                    ),
                    None,
                ),
                "cost_usd": getattr(ans, "cost_usd", None),
                "cache_hit": bool(getattr(ans, "cached", False)),
                "llm_latency_s": getattr(ans, "latency_s", None),
                "retrieved": [
                    {
                        "label": r.get("label"),
                        "chunk_id": r.get("chunk_id"),
                        "ticker": r.get("ticker"),
                        "section": r.get("section"),
                        "dense_score": r.get("dense_score"),
                        "bm25_score": r.get("bm25_score"),
                        "rrf_score": r.get("rrf_score"),
                        "text": _preview(r.get("text")),
                    }
                    for r in retrieved
                ],
            }
        )
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------------------
# Sinks
# ---------------------------------------------------------------------------


def _without_raw_text(record: dict[str, Any]) -> dict[str, Any]:
    """Copy of ``record`` with raw prompt / response text dropped from its spans."""
    spans = record.get("spans") or []
    if not any(k in (sp.get("attrs") or {}) for sp in spans for k in RAW_TEXT_ATTRS):
        return record
    out = dict(record)
    out["spans"] = [
        (
            {
                **sp,
                "attrs": {k: v for k, v in sp["attrs"].items() if k not in RAW_TEXT_ATTRS},
            }
            if sp.get("attrs")
            else sp
        )
        for sp in spans
    ]
    return out


class JsonlSink:
    """Append-only JSONL, one file per UTC day (easy to rotate / grep / ship)."""

    def __init__(self, directory: Path | None = None):
        self.directory = directory
        self._lock = threading.Lock()

    def write(self, record: dict[str, Any]) -> None:
        if not store_prompts():
            record = _without_raw_text(record)
        directory = self.directory or trace_dir()
        directory.mkdir(parents=True, exist_ok=True)
        day = str(record.get("ts", ""))[:10] or datetime.now(UTC).strftime("%Y-%m-%d")
        line = json.dumps(record, ensure_ascii=False, default=str) + "\n"
        with self._lock, open(directory / f"{day}.jsonl", "a", encoding="utf-8") as fh:
            fh.write(line)


_HEX32 = re.compile(r"[0-9a-f]{32}")


def _epoch_ns(ts: Any) -> int | None:
    """ISO-8601 trace start (``record['ts']``) -> epoch nanoseconds."""
    try:
        dt = datetime.fromisoformat(str(ts))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return int(dt.timestamp() * 1_000_000_000)
    except Exception:  # noqa: BLE001
        return None


def rerank_movement(record: dict[str, Any]) -> list[dict[str, Any]]:
    """How the cross-encoder reordered the fused candidates, one row per chunk.

    ``moved`` is positive when the reranker promoted a chunk (rank 5 -> 2 is +3).
    """
    before = [d.get("chunk_id") for d in record.get("rerank_before") or []]
    rrf = {d.get("chunk_id"): d.get("rrf_score") for d in record.get("rerank_before") or []}
    out: list[dict[str, Any]] = []
    for rank_after, d in enumerate(record.get("rerank_after") or [], start=1):
        cid = d.get("chunk_id")
        rank_before = before.index(cid) + 1 if cid in before else None
        out.append(
            {
                "chunk_id": cid,
                "rank_before": rank_before,
                "rank_after": rank_after,
                "moved": None if rank_before is None else rank_before - rank_after,
                "rrf_score": rrf.get(cid),
                "rerank_score": d.get("rerank_score"),
            }
        )
    return out


def _observation_type(name: str) -> str:
    """Langfuse observation type for a FinGround span name."""
    if name.rsplit(".", 1)[-1] == "generate":
        return "generation"
    if name == "retrieve" or name.startswith("retrieve."):
        return "retriever"
    if name == "evidence_gate":
        return "guardrail"
    if name == "judge":
        return "evaluator"
    return "span"


def _parent_index(spans: list[dict[str, Any]]) -> list[int | None]:
    """Nest ``a.b`` under the span named ``a`` (the one whose interval contains it).

    Spans are recorded flat with dotted names (``retrieve.bm25``,
    ``judge.generate``); this rebuilds the tree. ``None`` means "under the root".
    """
    parents: list[int | None] = []
    for s in spans:
        name = str(s.get("name", ""))
        prefix = name.rsplit(".", 1)[0] if "." in name else None
        candidates = [
            j for j, p in enumerate(spans) if prefix is not None and p.get("name") == prefix
        ]
        start = float(s.get("start_ms") or 0.0)
        end = start + float(s.get("duration_ms") or 0.0)
        best = None
        for j in candidates:
            ps = float(spans[j].get("start_ms") or 0.0)
            pe = ps + float(spans[j].get("duration_ms") or 0.0)
            if ps <= start + 1e-3 and end <= pe + 1e-3:
                best = j
                break
        parents.append(best if best is not None else (candidates[0] if candidates else None))
    return parents


class LangfuseSink:
    """Forward finished traces to Langfuse when configured; otherwise inert.

    Targets the OpenTelemetry-based Python SDK (v3 and later; tested on v5).
    Each FinGround trace becomes one Langfuse trace with the **same id** (the
    32-hex id returned in ``X-Trace-Id``), a root observation for the request
    and one nested observation per recorded span:

    * ``retrieve`` (retriever) — query in, retrieved chunks with scores out;
      ``retrieve.bm25`` / ``.dense`` / ``.fusion`` / ``.company_filter`` /
      ``.rerank`` nested under it, the rerank output being the rank movement;
    * ``evidence_gate`` (guardrail) — the pass / refuse decision, WARNING level
      when it refuses;
    * ``generate`` (generation) — exact system + user prompt in, raw model
      response out, model, token usage, cost and ``prompt_version``;
    * ``judge`` (evaluator) with ``judge.generate`` nested, in benchmarks.

    Spans are exported after the request finishes, so they are backdated to
    their real start / end times. That uses the SDK's OpenTelemetry tracer
    (``Langfuse._otel_tracer``), which is not public API; if a future SDK drops
    it the sink falls back to the public ``start_observation`` and timings stay
    available as ``start_ms`` / ``duration_ms`` metadata on every observation.
    """

    def __init__(self, client: Any = None) -> None:
        self._client: Any = client
        self._failed = False
        self._backdate = True

    @staticmethod
    def configured() -> bool:
        return bool(os.environ.get("LANGFUSE_PUBLIC_KEY") and os.environ.get("LANGFUSE_SECRET_KEY"))

    def _get_client(self) -> Any:
        if self._client is None and not self._failed:
            try:
                from langfuse import Langfuse  # optional dependency

                self._client = Langfuse()
            except Exception:  # noqa: BLE001 — missing package / bad config
                self._failed = True
        return self._client

    def flush(self) -> None:
        client = self._client
        if client is not None and hasattr(client, "flush"):
            client.flush()

    def write(self, record: dict[str, Any]) -> None:
        client = self._get_client()
        if client is None:
            return
        if hasattr(client, "start_observation"):  # SDK v3+ (OpenTelemetry based)
            self._write_otel(client, record)
        elif hasattr(client, "trace"):  # SDK v2
            self._write_v2(client, record)

    # -- record -> observation fields -----------------------------------------

    @staticmethod
    def _summary(record: dict[str, Any]) -> dict[str, Any]:
        skip = {
            "spans",
            "answer",
            "question",
            "retrieved",
            "rerank_before",
            "rerank_after",
            "prompt_system",
            "prompt_user",
        }
        return {k: v for k, v in record.items() if k not in skip}

    @staticmethod
    def _tags(record: dict[str, Any]) -> list[str]:
        if record.get("error"):
            outcome = "error"
        elif record.get("refused"):
            outcome = "refused"
        else:
            outcome = "answered"
        tags = [outcome]
        if record.get("gate"):
            tags.append(f"gate:{record['gate']}")
        for key in ("source", "model", "prompt_version"):
            if record.get(key):
                tags.append(str(record[key]))
        return tags

    def _root_fields(self, record: dict[str, Any]) -> dict[str, Any]:
        err = record.get("error")
        fields: dict[str, Any] = {
            "name": f"finground.{record.get('name', 'trace')}",
            "as_type": "span",
            "input": {"question": record.get("question"), "model": record.get("model")},
            "output": {
                "answer": record.get("answer"),
                "refused": record.get("refused"),
                "gate": record.get("gate"),
                "citations": record.get("citations"),
                "error": err,
            },
            "metadata": self._summary(record),
        }
        if record.get("prompt_version"):
            fields["version"] = str(record["prompt_version"])
        if err:
            fields["level"] = "ERROR"
            fields["status_message"] = f"{err.get('type')}: {err.get('message')}"
        return fields

    def _span_fields(self, s: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
        name = str(s.get("name", "span"))
        attrs = dict(s.get("attrs") or {})
        prompt_system = attrs.pop("prompt_system", None)
        prompt_user = attrs.pop("prompt_user", None)
        response_text = attrs.pop("response_text", None)
        as_type = _observation_type(name)
        fields: dict[str, Any] = {
            "name": name,
            "as_type": as_type,
            "metadata": {
                "start_ms": s.get("start_ms"),
                "duration_ms": s.get("duration_ms"),
                **attrs,
            },
        }
        if name == "retrieve":
            fields["input"] = {"query": record.get("question"), "top_k": attrs.get("top_k")}
            fields["output"] = record.get("retrieved")
        elif name == "retrieve.rerank":
            fields["input"] = {"pool": attrs.get("pool")}
            fields["output"] = rerank_movement(record)
        elif name == "evidence_gate":
            passed = bool(attrs.get("passed"))
            fields["input"] = {
                "best_dense_sim": attrs.get("best_dense_sim"),
                "threshold": attrs.get("threshold"),
            }
            fields["output"] = {"decision": "pass" if passed else "refuse", "passed": passed}
            if not passed:
                fields["level"] = "WARNING"
                fields["status_message"] = "evidence below threshold: refused without LLM call"
        elif as_type == "generation":
            if prompt_system is not None or prompt_user is not None:
                fields["input"] = [
                    {"role": "system", "content": prompt_system},
                    {"role": "user", "content": prompt_user},
                ]
            else:
                fields["input"] = {"prompt_hash": attrs.get("prompt_hash")}
            if response_text is not None:
                fields["output"] = response_text
            elif name == "generate" and not attrs.get("error"):
                fields["output"] = record.get("answer")
            fields["model"] = attrs.get("model")
            in_tok = int(attrs.get("prompt_tokens") or 0)
            out_tok = int(attrs.get("completion_tokens") or 0)
            fields["usage_details"] = {
                "input": in_tok,
                "output": out_tok,
                "total": in_tok + out_tok,
            }
            if attrs.get("cost_usd") is not None:
                fields["cost_details"] = {"total": float(attrs["cost_usd"])}
            if attrs.get("temperature") is not None:
                fields["model_parameters"] = {"temperature": attrs["temperature"]}
            if name == "generate" and record.get("prompt_version"):
                fields["version"] = str(record["prompt_version"])
        if attrs.get("error"):
            fields["level"] = "ERROR"
            detail = attrs.get("error_message")
            fields["status_message"] = (
                f"{attrs['error']}: {detail}" if detail else str(attrs["error"])
            )
        return fields

    # -- export ----------------------------------------------------------------

    def _trace_id(self, client: Any, record: dict[str, Any]) -> str | None:
        tid = str(record.get("trace_id") or "")
        if _HEX32.fullmatch(tid):
            return tid  # keep X-Trace-Id == Langfuse trace id
        create_id = getattr(client, "create_trace_id", None)
        return create_id(seed=tid) if callable(create_id) else None

    def _open(
        self, client: Any, parent: Any, trace_id: str | None, start_ns: int | None, f: dict
    ) -> tuple[Any, bool]:
        """Start an observation; returns ``(observation, backdated)``."""
        if self._backdate and start_ns is not None and trace_id is not None:
            try:
                return self._open_backdated(client, parent, trace_id, start_ns, f), True
            except Exception:  # noqa: BLE001 — SDK internals moved: use the public API
                self._backdate = False
        if parent is None:
            ctx = {"trace_id": trace_id} if trace_id else None
            return client.start_observation(trace_context=ctx, **f), False
        return parent.start_observation(**f), False

    @staticmethod
    def _open_backdated(
        client: Any, parent: Any, trace_id: str, start_ns: int, fields: dict
    ) -> Any:
        from opentelemetry import context as otel_context
        from opentelemetry import trace as otel_trace

        tracer = client._otel_tracer
        if parent is None:
            remote = client._create_remote_parent_span(trace_id=trace_id, parent_span_id=None)
            ctx = otel_trace.set_span_in_context(remote, otel_context.get_current())
        else:
            ctx = otel_trace.set_span_in_context(parent._otel_span, otel_context.get_current())
        otel_span = tracer.start_span(name=fields["name"], context=ctx, start_time=start_ns)
        if parent is None:
            otel_span.set_attribute("langfuse.internal.as_root", True)
        kwargs = {k: v for k, v in fields.items() if k != "name"}
        return client._create_observation_from_otel_span(otel_span=otel_span, **kwargs)

    def _write_otel(self, client: Any, record: dict[str, Any]) -> None:
        propagate_attributes: Any = None
        try:
            from langfuse import propagate_attributes
        except Exception:  # noqa: BLE001 — older SDKs: trace attributes are optional
            pass
        if propagate_attributes is None:
            self._export_otel(client, record)
            return
        meta = {
            k: str(record[k])[:200]
            for k in ("trace_id", "source", "model", "prompt_version", "gate")
            if record.get(k)
        }
        with propagate_attributes(
            trace_name=f"finground.{record.get('name', 'trace')}",
            tags=self._tags(record),
            metadata=meta,
        ):
            self._export_otel(client, record)

    def _export_otel(self, client: Any, record: dict[str, Any]) -> None:
        trace_id = self._trace_id(client, record)
        base_ns = _epoch_ns(record.get("ts"))
        spans = list(record.get("spans") or [])

        def ns(ms: Any) -> int | None:
            return None if base_ns is None else base_ns + int(float(ms or 0.0) * 1_000_000)

        root, root_backdated = self._open(
            client, None, trace_id, base_ns, self._root_fields(record)
        )
        opened: list[tuple[Any, bool, int | None]] = []
        parents = _parent_index(spans)
        # Parents before children: a dotted child is recorded before its parent.
        order = sorted(range(len(spans)), key=lambda i: (str(spans[i].get("name")).count("."), i))
        by_index: dict[int, Any] = {}
        for i in order:
            s = spans[i]
            p = parents[i]
            parent_obs = by_index.get(p, root) if p is not None else root
            start = ns(s.get("start_ms"))
            obs, backdated = self._open(
                client, parent_obs, trace_id, start, self._span_fields(s, record)
            )
            by_index[i] = obs
            end = None if start is None else start + int(float(s.get("duration_ms") or 0) * 1e6)
            opened.append((obs, backdated, end))
        for obs, backdated, end in reversed(opened):
            obs.end(end_time=end) if backdated else obs.end()
        root_end = ns(record.get("duration_ms"))
        root.end(end_time=root_end) if root_backdated else root.end()

    def _write_v2(self, client: Any, record: dict[str, Any]) -> None:
        tr = client.trace(
            id=record["trace_id"],
            name=f"finground.{record.get('name', 'trace')}",
            input={"question": record.get("question")},
            output={"answer": record.get("answer"), "error": record.get("error")},
            metadata=self._summary(record),
        )
        for s in record.get("spans", []):
            attrs = s.get("attrs", {})
            meta = {"start_ms": s["start_ms"], "duration_ms": s["duration_ms"], **attrs}
            if s["name"].endswith("generate"):
                tr.generation(
                    name=s["name"],
                    model=attrs.get("model"),
                    usage={
                        "input": int(attrs.get("prompt_tokens") or 0),
                        "output": int(attrs.get("completion_tokens") or 0),
                    },
                    metadata=meta,
                )
            else:
                tr.span(name=s["name"], metadata=meta)


_SINKS: list[Any] | None = None
_SINKS_LOCK = threading.Lock()


def _sinks() -> list[Any]:
    global _SINKS
    if _SINKS is None:
        with _SINKS_LOCK:
            if _SINKS is None:
                sinks: list[Any] = [JsonlSink()]
                if LangfuseSink.configured():
                    sinks.append(LangfuseSink())
                _SINKS = sinks
    return _SINKS


def set_sinks(sinks: list[Any] | None) -> None:
    """Replace the sinks (tests, or embedding apps with their own exporter).

    ``None`` restores the environment-derived defaults on next use.
    """
    global _SINKS
    _SINKS = sinks


def flush() -> None:
    """Block until sinks with background export (Langfuse) have sent everything.

    Long-running servers never need this; short scripts can call it before exit
    (the Langfuse SDK also flushes on interpreter shutdown).
    """
    for sink in _SINKS or []:
        try:
            if hasattr(sink, "flush"):
                sink.flush()
        except Exception:  # noqa: BLE001
            pass


_warned = False


def emit(tr: Trace) -> None:
    """Serialise and hand the trace to each sink; sink failures are isolated."""
    global _warned
    try:
        record = tr.to_record()
        sinks = _sinks()
    except Exception:  # noqa: BLE001
        return
    for sink in sinks:
        try:
            sink.write(record)
        except Exception as exc:  # noqa: BLE001 — one bad sink must not affect others
            if not _warned:
                _warned = True
                try:
                    print(
                        f"[tracing] sink {type(sink).__name__} failed: {exc!r} (further errors muted)"
                    )
                except Exception:  # noqa: BLE001
                    pass


def load_traces(directory: Path | None = None, *, limit: int | None = None) -> list[dict]:
    """Read trace records (oldest first), skipping malformed lines."""
    directory = directory or trace_dir()
    out: list[dict] = []
    if not directory.exists():
        return out
    for path in sorted(directory.glob("*.jsonl")):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(rec, dict) and "trace_id" in rec:
                    out.append(rec)
    out.sort(key=lambda r: str(r.get("ts", "")))
    return out[-limit:] if limit else out
