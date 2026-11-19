#!/usr/bin/env python3
"""Evaluate one or more models over the gold set and write results/results.csv.

For each model and each gold question we:
  1. produce a cited answer (or an abstention) with the RAG pipeline,
  2. judge the answer (unless it abstained) for correctness, claim support
     (faithfulness), and citation support,
  3. record the answer/abstain decision for refusal calibration.

Aggregates per model (see ``CSV_COLUMNS``): the four quality metrics, each
with a seeded bootstrap 95% CI (``*_ci_lo`` / ``*_ci_hi``), plus citation
coverage, failure rate, latency p50/p95/avg, cost per request and per 100
questions, counts, and the judge. All of it is computed from the per-question
rows by ``finground.eval.summary``, the same code that recomputes committed runs.

Every item is traced (``traces/``; see ``finground.tracing``), with the trace
id stored on its run row so a bad leaderboard number can be drilled into.

Results are MERGED into results/results.csv: a run updates only the rows for
the models it evaluated, so a single-model community run (e.g.
``--models openai:gpt-4o``) never wipes the rest of the leaderboard.

Models whose provider is unavailable (no key / unreachable) are skipped —
only models that actually ran appear in the results. Per-question detail is
dumped to results/runs/<model>.jsonl for auditing.

Usage:
  python scripts/run_benchmark.py                       # default candidate models
  python scripts/run_benchmark.py --models ollama:llama3 --judge ollama:llama3
  python scripts/run_benchmark.py --limit 5             # quick smoke run
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import uuid
from datetime import UTC, datetime

from finground import tracing
from finground.answer import answer_question
from finground.config import CONFIG
from finground.eval.datasets import load_financebench, load_gold_set
from finground.eval.judge import judge_answer
from finground.eval.metrics import (
    citation_accuracy,
    hallucination_rate,
    is_unsupported,
    response_citation_coverage,
)
from finground.eval.summary import summarize_rows
from finground.llm import available_providers, parse_model

# Candidate models to compare. Unavailable ones are skipped automatically.
DEFAULT_MODELS = [
    "openai:gpt-4o",
    "openai:gpt-4o-mini",
    "anthropic:claude-sonnet-5",
    "ollama:llama3",
]

CSV_COLUMNS = [
    "model",
    "correctness",
    "correctness_ci_lo",
    "correctness_ci_hi",
    "citation_accuracy",
    "citation_accuracy_ci_lo",
    "citation_accuracy_ci_hi",
    "hallucination_rate",
    "hallucination_rate_ci_lo",
    "hallucination_rate_ci_hi",
    "refusal_calibration",
    "refusal_calibration_ci_lo",
    "refusal_calibration_ci_hi",
    "citation_coverage",
    "failure_rate",
    "latency_p50_s",
    "latency_p95_s",
    "avg_latency_s",
    "cost_per_request",
    "cost_per_100q",
    "n_questions",
    "n_answered",
    "judge",
]

# Display precision per column (digits after the point); counts/strings absent.
_PRECISION = {
    "latency_p50_s": 2,
    "latency_p95_s": 2,
    "avg_latency_s": 2,
    "cost_per_request": 6,
    "cost_per_100q": 4,
}


def _fmt(x: float | None, nd: int = 3) -> str:
    return "N/A" if x is None else f"{x:.{nd}f}"


def row_strs(r: dict) -> list[str]:
    """Format one summary dict as a CSV row in ``CSV_COLUMNS`` order."""
    out = []
    for col in CSV_COLUMNS:
        v = r.get(col)
        if col in ("model", "judge", "n_questions", "n_answered"):
            out.append(str(v))
        else:
            out.append(_fmt(v, _PRECISION.get(col, 3)))
    return out


def evaluate_model(model: str, items, judge_model: str, run_id: str = "") -> dict:
    """Run the full pipeline + judge for one model over the gold items."""
    cost_known = True
    n_errors = 0
    detail = []

    for it in items:
        with tracing.trace(
            "benchmark_item",
            source="benchmark",
            run_id=run_id,
            item_id=it.id,
            question=it.question,
            model=model,
            judge_model=judge_model,
            answerable=it.answerable,
        ) as tr:
            row = _evaluate_item(model, it, judge_model)
            if tr is not None:
                row["trace_id"] = tr.trace_id
        if "error" in row or "judge_error" in row:
            n_errors += 1
        if "error" not in row and row.get("cost_usd") is None and parse_model(model)[0] != "ollama":
            cost_known = False  # unknown price for a hosted model: don't report $0
        detail.append(row)

    if n_errors:
        print(f"    ({n_errors} item(s) skipped due to errors for {model})")

    # Dump per-question detail (committed) so leaderboard rows are auditable.
    runs_dir = CONFIG.paths.results / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    safe = model.replace(":", "_").replace("/", "_")
    with open(runs_dir / f"{safe}.jsonl", "w", encoding="utf-8") as fh:
        for row in detail:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    return summarize_rows(detail, model=model, judge=judge_model, cost_known=cost_known)


def _evaluate_item(model: str, it, judge_model: str) -> dict:
    """Answer + judge one question; returns its run row (errors recorded, not raised)."""
    # A single flaky/slow local inference must not abort the whole benchmark.
    try:
        ans = answer_question(it.question, model=model)
    except Exception as exc:  # noqa: BLE001 — record and skip the item
        print(f"    x {it.id}: answer failed: {exc}", file=sys.stderr)
        tracing.record_error(exc)
        return {"id": it.id, "question": it.question, "error": str(exc)}
    tracing.record_answer(ans)

    retrieved_labels = [r["label"] for r in ans.retrieved]
    row = {
        "id": it.id,
        "question": it.question,
        "answerable": it.answerable,
        "has_gold": bool(it.gold_answer),
        "abstained": ans.abstained,
        "answer": ans.answer,
        "best_dense_sim": ans.best_dense_sim,
        "citations": [c["label"] for c in ans.citations],
        "retrieved_labels": retrieved_labels,
        "citation_coverage": (
            None if ans.abstained else response_citation_coverage(ans.answer, set(retrieved_labels))
        ),
        "latency_s": ans.latency_s,
        "cost_usd": ans.cost_usd,
        "prompt_tokens": ans.prompt_tokens,
        "completion_tokens": ans.completion_tokens,
        "cached": ans.cached,
    }
    if ans.abstained:
        return row

    try:
        with tracing.span("judge"):
            j = judge_answer(
                question=it.question,
                answer=ans.answer,
                citations=ans.citations,
                abstained=False,
                gold_answer=it.gold_answer,
                model=judge_model,
            )
    except Exception as exc:  # noqa: BLE001 — skip metrics for this item
        print(f"    x {it.id}: judge failed: {exc}", file=sys.stderr)
        tracing.annotate(judge_error=str(exc)[:500])
        row["judge_error"] = str(exc)
        return row
    row["judge"] = j.to_json()
    if j.error:
        print(f"    ! {it.id}: {j.error}", file=sys.stderr)
    tracing.annotate(
        judge_correct=j.correct,
        judge_unsupported=is_unsupported(j.claim_supports),
        judge_citation_accuracy=citation_accuracy(j.citation_supports),
        judge_hallucination_rate=hallucination_rate(j.claim_supports),
        judge_parse_error=j.error,
    )
    return row


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", default=None, help="comma-separated provider:model list")
    parser.add_argument("--judge", default=None, help="judge model (provider:model)")
    parser.add_argument("--dataset", default="gold", choices=["gold", "financebench"])
    parser.add_argument("--limit", type=int, default=None, help="cap number of questions")
    args = parser.parse_args(argv)

    if args.dataset == "financebench":
        items = load_financebench(limit=args.limit)
    else:
        items = load_gold_set()
        if args.limit:
            items = items[: args.limit]
    print(f"Loaded {len(items)} questions from {args.dataset}.")

    models = [m.strip() for m in args.models.split(",")] if args.models else list(DEFAULT_MODELS)
    providers = available_providers()
    print(f"Available providers: {sorted(providers) or '(none)'}")

    # Pick a judge that is actually available.
    judge_model = args.judge or CONFIG.models.judge
    if parse_model(judge_model)[0] not in providers:
        fallback = next((m for m in models if parse_model(m)[0] in providers), None)
        if fallback is None:
            print("No available judge model. Set a key or run Ollama.", file=sys.stderr)
            return 1
        print(f"Judge {judge_model} unavailable; using {fallback} as judge.")
        judge_model = fallback
    print(f"Judge model: {judge_model}\n")

    run_id = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]
    print(f"Run id: {run_id} (traces -> {tracing.trace_dir()})")
    rows = []
    for model in models:
        provider = parse_model(model)[0]
        if provider not in providers:
            print(f"[skip] {model}: provider unavailable")
            continue
        print(f"[run] {model} ...")
        rows.append(evaluate_model(model, items, judge_model, run_id=run_id))
        r = rows[-1]
        print(
            f"       correctness={_fmt(r['correctness'])} "
            f"citation_acc={_fmt(r['citation_accuracy'])} "
            f"halluc={_fmt(r['hallucination_rate'])} "
            f"refusal_cal={_fmt(r['refusal_calibration'])}\n"
            f"       citation_cov={_fmt(r['citation_coverage'])} "
            f"failure={_fmt(r['failure_rate'])} "
            f"p50={_fmt(r['latency_p50_s'], 2)}s p95={_fmt(r['latency_p95_s'], 2)}s"
        )

    out = CONFIG.paths.results / "results.csv"

    # Merge with the committed leaderboard: rows for models evaluated in this
    # run are replaced in place; everyone else's rows are preserved, so a
    # single-model community contribution never wipes the table.
    new_rows = {r["model"]: row_strs(r) for r in rows}
    merged: list[list[str]] = []
    if out.exists():
        with open(out, encoding="utf-8") as fh:
            for old in csv.DictReader(fh):
                if old["model"] in new_rows:
                    merged.append(new_rows.pop(old["model"]))
                else:
                    merged.append([old.get(c, "") for c in CSV_COLUMNS])
    merged.extend(new_rows[r["model"]] for r in rows if r["model"] in new_rows)

    with open(out, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(CSV_COLUMNS)
        writer.writerows(merged)
    print(f"\nWrote {out} ({len(merged)} model row(s))")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
