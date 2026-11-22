"""Turn per-question benchmark rows into one leaderboard row.

The per-question rows are exactly what ``scripts/run_benchmark.py`` dumps to
``results/runs/<model>.jsonl``. Computing the leaderboard *from those dumps*
(rather than from in-memory accumulators) means the same code serves a live
run and a later recomputation of committed runs, so the two cannot drift.

Row fields consumed (all optional except ``id``): ``error``, ``judge_error``,
``answerable``, ``abstained``, ``has_gold``, ``judge`` (``correct``, ``claims``,
``citations``, ``error``), ``answer``, ``citations``, ``citation_coverage``,
``latency_s``, ``cost_usd``.
"""

from __future__ import annotations

from collections.abc import Callable

from .metrics import (
    bootstrap_ci,
    citation_accuracy,
    citation_coverage,
    failure_rate,
    hallucination_rate,
    is_unsupported,
    mean_ignoring_none,
    percentile,
    refusal_calibration,
    response_citation_coverage,
)

# Default top_k: committed runs predate storing retrieved labels, and every one
# of them retrieved C1..C8, so that is the valid-label set used to recompute
# citation coverage for them.
LEGACY_RETRIEVED_LABELS = {f"C{i}" for i in range(1, 9)}

N_BOOTSTRAP = 1000
BOOTSTRAP_SEED = 0

QUALITY_METRICS = ("correctness", "citation_accuracy", "hallucination_rate", "refusal_calibration")


def _answered(r: dict) -> bool:
    return "error" not in r and not r.get("abstained", False)


def _judgment(r: dict) -> dict | None:
    j = r.get("judge")
    return j if isinstance(j, dict) else None


def correctness_of(rows: list[dict]) -> float | None:
    labels = []
    for r in rows:
        j = _judgment(r)
        if _answered(r) and j and r.get("has_gold", True) and j.get("correct") is not None:
            labels.append(bool(j["correct"]))
    return sum(labels) / len(labels) if labels else None


def citation_accuracy_of(rows: list[dict]) -> float | None:
    scores = []
    for r in rows:
        j = _judgment(r)
        if _answered(r) and j:
            scores.append(
                citation_accuracy([bool(c.get("supports")) for c in j.get("citations", [])])
            )
    return mean_ignoring_none(scores)


def hallucination_rate_of(rows: list[dict]) -> float | None:
    scores = []
    for r in rows:
        j = _judgment(r)
        if _answered(r) and j:
            scores.append(
                hallucination_rate([bool(c.get("supported")) for c in j.get("claims", [])])
            )
    return mean_ignoring_none(scores)


def refusal_calibration_of(rows: list[dict]) -> float | None:
    decisions = [
        (bool(r.get("answerable", True)), not r.get("abstained", False))
        for r in rows
        if "error" not in r
    ]
    return refusal_calibration(decisions).calibration if decisions else None


STATISTICS: dict[str, Callable[[list[dict]], float | None]] = {
    "correctness": correctness_of,
    "citation_accuracy": citation_accuracy_of,
    "hallucination_rate": hallucination_rate_of,
    "refusal_calibration": refusal_calibration_of,
}


def row_citation_coverage(r: dict) -> bool | None:
    """Coverage flag for one row; ``None`` when the row was not answered."""
    if not _answered(r):
        return None
    if r.get("citation_coverage") is not None:
        return bool(r["citation_coverage"])
    labels = r.get("retrieved_labels") or LEGACY_RETRIEVED_LABELS
    return response_citation_coverage(r.get("answer", ""), set(labels))


def summarize_rows(
    rows: list[dict],
    *,
    model: str,
    judge: str,
    cost_known: bool = True,
    n_resamples: int = N_BOOTSTRAP,
    seed: int = BOOTSTRAP_SEED,
) -> dict:
    """Leaderboard metrics + bootstrap 95% CIs for one model's run."""
    n = len(rows)
    out: dict = {"model": model, "judge": judge, "n_questions": n}
    out["n_answered"] = sum(1 for r in rows if _answered(r))

    for name, fn in STATISTICS.items():
        out[name] = fn(rows)
        ci = (
            bootstrap_ci(rows, fn, n_resamples=n_resamples, seed=seed)
            if out[name] is not None
            else None
        )
        out[f"{name}_ci_lo"], out[f"{name}_ci_hi"] = ci if ci else (None, None)

    out["citation_coverage"] = citation_coverage([row_citation_coverage(r) for r in rows])

    n_exceptions = sum(1 for r in rows if "error" in r or "judge_error" in r)
    n_unsupported = 0
    for r in rows:
        j = _judgment(r)
        if _answered(r) and j and "judge_error" not in r:
            if is_unsupported([bool(c.get("supported")) for c in j.get("claims", [])]):
                n_unsupported += 1
    out["failure_rate"] = failure_rate(n, n_exceptions, n_unsupported)

    latencies = [float(r["latency_s"]) for r in rows if r.get("latency_s")]
    out["latency_p50_s"] = percentile(latencies, 50)
    out["latency_p95_s"] = percentile(latencies, 95)
    out["avg_latency_s"] = sum(latencies) / len(latencies) if latencies else None

    if cost_known and n:
        total = sum(float(r.get("cost_usd") or 0.0) for r in rows)
        out["cost_per_request"] = total / n
        out["cost_per_100q"] = total / n * 100
    else:
        out["cost_per_request"] = None
        out["cost_per_100q"] = None
    return out
