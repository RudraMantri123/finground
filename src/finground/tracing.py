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

Raw prompts are not stored by default (they embed whole filing excerpts and
make trace files large); the prompt is identified by a SHA-256 hash instead.
Set ``FINGROUND_TRACE_PROMPTS=1`` to keep the raw text too.
"""

from __future__ import annotations

import contextvars
import hashlib
import json
import os
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
    return _env_flag("FINGROUND_TRACE_PROMPTS", False)


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


class JsonlSink:
    """Append-only JSONL, one file per UTC day (easy to rotate / grep / ship)."""

    def __init__(self, directory: Path | None = None):
        self.directory = directory
        self._lock = threading.Lock()

    def write(self, record: dict[str, Any]) -> None:
        directory = self.directory or trace_dir()
        directory.mkdir(parents=True, exist_ok=True)
        day = str(record.get("ts", ""))[:10] or datetime.now(UTC).strftime("%Y-%m-%d")
        line = json.dumps(record, ensure_ascii=False, default=str) + "\n"
        with self._lock, open(directory / f"{day}.jsonl", "a", encoding="utf-8") as fh:
            fh.write(line)


class LangfuseSink:
    """Forward finished traces to Langfuse when configured; otherwise inert.

    Traces are exported after the fact, so span timings travel as metadata
    (``duration_ms`` / ``start_ms``) rather than as backdated timestamps. The
    Langfuse trace id is derived from the FinGround trace id, so a JSONL record
    and its Langfuse view can be cross-referenced.
    """

    def __init__(self) -> None:
        self._client: Any = None
        self._failed = False

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

    def write(self, record: dict[str, Any]) -> None:
        client = self._get_client()
        if client is None:
            return
        if hasattr(client, "start_observation"):  # SDK v3+ (OpenTelemetry based)
            self._write_otel(client, record)
        elif hasattr(client, "trace"):  # SDK v2
            self._write_v2(client, record)

    @staticmethod
    def _summary(record: dict[str, Any]) -> dict[str, Any]:
        skip = {"spans", "answer", "question", "retrieved", "prompt_system", "prompt_user"}
        return {k: v for k, v in record.items() if k not in skip}

    def _write_otel(self, client: Any, record: dict[str, Any]) -> None:
        trace_context = None
        create_id = getattr(client, "create_trace_id", None)
        if callable(create_id):
            trace_context = {"trace_id": create_id(seed=record["trace_id"])}
        root = client.start_observation(
            trace_context=trace_context,
            name=f"finground.{record.get('name', 'trace')}",
            input={"question": record.get("question")},
            output={"answer": record.get("answer"), "error": record.get("error")},
            metadata=self._summary(record),
            level="ERROR" if record.get("error") else None,
        )
        for s in record.get("spans", []):
            is_gen = s["name"].endswith("generate")
            attrs = s.get("attrs", {})
            kwargs: dict[str, Any] = {
                "name": s["name"],
                "as_type": "generation" if is_gen else "span",
                "metadata": {"start_ms": s["start_ms"], "duration_ms": s["duration_ms"], **attrs},
            }
            if is_gen:
                kwargs["model"] = attrs.get("model")
                kwargs["usage_details"] = {
                    "input": int(attrs.get("prompt_tokens") or 0),
                    "output": int(attrs.get("completion_tokens") or 0),
                }
                if attrs.get("cost_usd") is not None:
                    kwargs["cost_details"] = {"total": float(attrs["cost_usd"])}
            root.start_observation(**kwargs).end()
        root.end()

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
