#!/usr/bin/env python3
"""Evaluate one or more models over the gold set and write results/results.csv.

For each model and each gold question we:
  1. produce a cited answer (or an abstention) with the RAG pipeline,
  2. judge the answer (unless it abstained) for correctness, claim support
     (faithfulness), and citation support,
  3. record the answer/abstain decision for refusal calibration.

Aggregates per model:
  model, correctness, citation_accuracy, hallucination_rate,
  refusal_calibration, avg_latency_s, cost_per_100q, n_questions, n_answered,
  judge.

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

from finground.answer import answer_question
from finground.config import CONFIG
from finground.eval.datasets import load_financebench, load_gold_set
from finground.eval.judge import judge_answer
from finground.eval.metrics import (
    citation_accuracy,
    hallucination_rate,
    mean_ignoring_none,
    refusal_calibration,
)
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
    "citation_accuracy",
    "hallucination_rate",
    "refusal_calibration",
    "avg_latency_s",
    "cost_per_100q",
    "n_questions",
    "n_answered",
    "judge",
]


def _fmt(x: float | None, nd: int = 3) -> str:
    return "N/A" if x is None else f"{x:.{nd}f}"


def evaluate_model(model: str, items, judge_model: str) -> dict:
    """Run the full pipeline + judge for one model over the gold items."""
    correctness_labels: list[bool] = []
    citation_scores: list[float | None] = []
    hallucination_scores: list[float | None] = []
    decisions: list[tuple[bool, bool]] = []
    latencies: list[float] = []
    total_cost = 0.0
    cost_known = True
    n_answered = 0
    n_errors = 0
    detail = []

    for it in items:
        # A single flaky/slow local inference must not abort the whole benchmark.
        try:
            ans = answer_question(it.question, model=model)
        except Exception as exc:  # noqa: BLE001 — record and skip the item
            n_errors += 1
            print(f"    x {it.id}: answer failed: {exc}", file=sys.stderr)
            detail.append({"id": it.id, "question": it.question, "error": str(exc)})
            continue

        did_answer = not ans.abstained
        decisions.append((it.answerable, did_answer))
        if ans.latency_s:
            latencies.append(ans.latency_s)
        if ans.cost_usd is None:
            # Unknown price (e.g. local model). Treat as zero but flag.
            if parse_model(model)[0] != "ollama":
                cost_known = False
        else:
            total_cost += ans.cost_usd

        row = {
            "id": it.id,
            "question": it.question,
            "answerable": it.answerable,
            "abstained": ans.abstained,
            "answer": ans.answer,
            "best_dense_sim": ans.best_dense_sim,
            "citations": [c["label"] for c in ans.citations],
        }
        # Prompt provenance (the judge's version is recorded inside row["judge"]).
        row["prompt_version"] = ans.prompt_version

        if did_answer:
            n_answered += 1
            try:
                j = judge_answer(
                    question=it.question,
                    answer=ans.answer,
                    citations=ans.citations,
                    abstained=False,
                    gold_answer=it.gold_answer,
                    model=judge_model,
                )
            except Exception as exc:  # noqa: BLE001 — skip metrics for this item
                n_errors += 1
                print(f"    x {it.id}: judge failed: {exc}", file=sys.stderr)
                row["judge_error"] = str(exc)
                detail.append(row)
                continue
            row["judge"] = j.to_json()
            if j.error:
                print(f"    ! {it.id}: {j.error}", file=sys.stderr)
            # Correctness only counts where we have a gold answer to compare to.
            if it.gold_answer and j.correct is not None:
                correctness_labels.append(bool(j.correct))
            citation_scores.append(citation_accuracy(j.citation_supports))
            hallucination_scores.append(hallucination_rate(j.claim_supports))
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

    stats = refusal_calibration(decisions)
    correctness = (
        (sum(correctness_labels) / len(correctness_labels)) if correctness_labels else None
    )
    cost_per_100q = None
    if cost_known:
        cost_per_100q = (total_cost / len(items)) * 100 if items else 0.0

    return {
        "model": model,
        "correctness": correctness,
        "citation_accuracy": mean_ignoring_none(citation_scores),
        "hallucination_rate": mean_ignoring_none(hallucination_scores),
        "refusal_calibration": stats.calibration,
        "avg_latency_s": (sum(latencies) / len(latencies)) if latencies else None,
        "cost_per_100q": cost_per_100q,
        "n_questions": len(items),
        "n_answered": n_answered,
        "judge": judge_model,
    }


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

    rows = []
    for model in models:
        provider = parse_model(model)[0]
        if provider not in providers:
            print(f"[skip] {model}: provider unavailable")
            continue
        print(f"[run] {model} ...")
        rows.append(evaluate_model(model, items, judge_model))
        r = rows[-1]
        print(
            f"       correctness={_fmt(r['correctness'])} "
            f"citation_acc={_fmt(r['citation_accuracy'])} "
            f"halluc={_fmt(r['hallucination_rate'])} "
            f"refusal_cal={_fmt(r['refusal_calibration'])}"
        )

    out = CONFIG.paths.results / "results.csv"

    def _row_strs(r: dict) -> list[str]:
        return [
            r["model"],
            _fmt(r["correctness"]),
            _fmt(r["citation_accuracy"]),
            _fmt(r["hallucination_rate"]),
            _fmt(r["refusal_calibration"]),
            _fmt(r["avg_latency_s"], 2),
            _fmt(r["cost_per_100q"], 4),
            str(r["n_questions"]),
            str(r["n_answered"]),
            r["judge"],
        ]

    # Merge with the committed leaderboard: rows for models evaluated in this
    # run are replaced in place; everyone else's rows are preserved, so a
    # single-model community contribution never wipes the table.
    new_rows = {r["model"]: _row_strs(r) for r in rows}
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
