#!/usr/bin/env python3
"""Faithfulness regression gate over the pinned, judged answer set.

Default mode makes **no LLM calls**: it reads the committed pinned run
(``results/faithfulness/pinned_run.jsonl`` + ``pinned_manifest.json``) and

1. recomputes deterministic faithfulness checks from the answer and chunk text
   (citation validity, citation coverage, numeric grounding, refusals on trap
   questions, abstentions on answerable ones);
2. recomputes the judged scores (faithfulness, hallucination rate, citation
   accuracy) from the committed judge labels;
3. checks the pinned run is not stale: its answer/judge models, prompt ids and
   prompt-file hashes, retrieval config, fixture corpus and gold set must match
   the code.

``--regenerate`` re-answers and re-judges the gold set with the gate's model
pair over the committed fixture corpus (needs COHERE_API_KEY, the embedding and
reranker models; about 2 calls per answered question). Add ``--pin`` to make
that run the new pinned run.

Usage:
  python scripts/eval_faithfulness.py --check results/faithfulness_thresholds.json
  python scripts/eval_faithfulness.py --regenerate --check results/faithfulness_thresholds.json
  python scripts/eval_faithfulness.py --regenerate --pin \\
      --write-thresholds results/faithfulness_thresholds.json
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from finground.config import CONFIG
from finground.eval.datasets import load_gold_set
from finground.eval.faithfulness import (
    DEFAULT_MARGIN,
    FIXTURE_PATH,
    GATE_ANSWER_MODEL,
    GATE_JUDGE_MODEL,
    GATE_TEMPERATURE,
    PINNED_MANIFEST,
    PINNED_RUN,
    count_problems,
    current_fingerprint,
    deterministic_metrics,
    judged_metrics,
    rate_problems,
    row_provenance_problems,
    sha256_file,
    staleness_problems,
    thresholds_from,
)

RATE_COLUMNS = [
    "citation_validity",
    "citation_coverage",
    "numeric_grounding",
    "refusal_recall",
    "answer_recall",
    "faithfulness",
    "hallucination_rate",
    "citation_accuracy",
    "correctness",
]


def load_rows(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def write_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def regenerate(gold_path: Path | None, limit: int | None) -> list[dict]:
    """Answer + judge every gold item over the fixture corpus with the gate's models."""
    # Heavy imports (FAISS, torch, sentence-transformers) only on this path.
    from finground import retrieve as R
    from finground.answer import answer_question
    from finground.eval.judge import judge_answer
    from finground.llm import available_providers, parse_model

    for spec in (GATE_ANSWER_MODEL, GATE_JUDGE_MODEL):
        if parse_model(spec)[0] not in available_providers():
            raise SystemExit(f"{spec}: provider unavailable (missing API key?)")
    if not R.reranker_available():
        raise SystemExit("Cross-encoder could not be loaded; refusing to regenerate.")

    with open(FIXTURE_PATH, encoding="utf-8") as fh:
        corpus = [json.loads(line) for line in fh if line.strip()]
    print(f"Indexing fixture corpus ({len(corpus)} chunks) in memory...")
    indexes = R.indexes_from_chunks(corpus)

    items = load_gold_set(gold_path)
    if limit:
        items = items[:limit]
    rows: list[dict] = []
    fresh_calls = 0
    for it in items:
        ans = answer_question(
            it.question, model=GATE_ANSWER_MODEL, temperature=GATE_TEMPERATURE, indexes=indexes
        )
        fresh_calls += int(bool(ans.prompt_version) and not ans.cached)
        row = {
            "id": it.id,
            "question": it.question,
            "answerable": it.answerable,
            "has_gold": bool(it.gold_answer),
            "abstained": ans.abstained,
            "answer": ans.answer,
            "model": GATE_ANSWER_MODEL,
            "prompt_version": ans.prompt_version,
            "gate": ans.meta.get("gate"),
            "best_dense_sim": round(ans.best_dense_sim, 6),
            "citations": [c["label"] for c in ans.citations],
            "retrieved": [
                {k: c[k] for k in ("label", "chunk_id", "provenance", "ticker", "section", "text")}
                for c in ans.retrieved
            ],
            "prompt_tokens": ans.prompt_tokens,
            "completion_tokens": ans.completion_tokens,
            "latency_s": round(ans.latency_s, 3),
        }
        if not ans.abstained:
            j = judge_answer(
                question=it.question,
                answer=ans.answer,
                citations=ans.citations,
                abstained=False,
                gold_answer=it.gold_answer,
                model=GATE_JUDGE_MODEL,
            )
            fresh_calls += 1  # judge responses are cached too; upper bound
            row["judge_model"] = GATE_JUDGE_MODEL
            row["judge"] = j.to_json()
        rows.append(row)
        print(f"  {it.id}: {'abstained' if ans.abstained else 'answered'}")
    print(f"Regenerated {len(rows)} items (<= {fresh_calls} LLM calls; cached ones are free).")
    return rows


def print_report(det: dict, judged: dict, counts: dict) -> None:
    values = {**det, **judged}
    print(
        f"\nItems {det['n_items']} (answered {det['n_answered']}); "
        f"{det['n_citations']} citations, {det['n_claim_units']} claim units, "
        f"{det['n_figures']} figures."
    )
    for name in RATE_COLUMNS:
        v = values.get(name)
        print(f"  {name:<20} {'n/a' if v is None else f'{v:.3f}'}")
    print("  violations: " + ", ".join(f"{k}={v}" for k, v in counts.items()))


def write_outputs(out_dir: Path, det: dict, judged: dict, counts: dict, items: list[dict]):
    out_dir.mkdir(parents=True, exist_ok=True)
    csv_path = out_dir / "faithfulness_eval.csv"
    row = {**{k: det.get(k, judged.get(k)) for k in RATE_COLUMNS}, **counts}
    row.update({k: det[k] for k in ("n_items", "n_answered", "n_claim_units", "n_figures")})
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(row))
        w.writeheader()
        w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in row.items()})
    audit_path = out_dir / "faithfulness_eval_per_item.jsonl"
    write_rows(audit_path, items)
    print(f"\nWrote {csv_path} and {audit_path}")


def _repo_relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(CONFIG.paths.root).as_posix()
    except ValueError:
        return str(path)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--run", type=Path, default=PINNED_RUN, help="pinned run JSONL")
    ap.add_argument("--manifest", type=Path, default=PINNED_MANIFEST)
    ap.add_argument("--gold", type=Path, default=None, help="gold set (default results/)")
    ap.add_argument("--check", type=Path, help="thresholds JSON; exit 1 on any regression")
    ap.add_argument("--write-thresholds", type=Path, help="calibrate thresholds from this run")
    ap.add_argument("--margin", type=float, default=DEFAULT_MARGIN)
    ap.add_argument(
        "--accept-regression",
        metavar="REASON",
        help="allow --write-thresholds to lower floors below the existing ones (recorded)",
    )
    ap.add_argument("--regenerate", action="store_true", help="re-answer + re-judge (LLM calls)")
    ap.add_argument("--pin", action="store_true", help="with --regenerate: overwrite pinned run")
    ap.add_argument("--limit", type=int, default=None, help="with --regenerate: first N items")
    ap.add_argument("--out-dir", type=Path, default=CONFIG.paths.results / "faithfulness")
    args = ap.parse_args(argv)

    if args.pin and not args.regenerate:
        ap.error("--pin requires --regenerate")
    if args.pin and args.limit:
        ap.error("--pin needs the full gold set (drop --limit)")

    current = current_fingerprint(gold_path=args.gold)
    if args.regenerate:
        t0 = time.time()
        rows = regenerate(args.gold, args.limit)
        manifest = {
            **current,
            "created_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "n_items": len(rows),
            "note": (
                "Fingerprint of everything that produced pinned_run.jsonl. "
                "scripts/eval_faithfulness.py fails CI when the code no longer matches it."
            ),
        }
        print(f"Regeneration took {time.time() - t0:.0f}s.")
        if args.pin:
            write_rows(args.run, rows)
            args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
            print(f"Pinned {len(rows)} rows -> {args.run} (+ {args.manifest.name})")
        else:
            write_rows(args.out_dir / "regenerated_run.jsonl", rows)
    else:
        if not args.run.exists() or not args.manifest.exists():
            print(f"Pinned run not found ({args.run}, {args.manifest}).")
            return 1
        rows = load_rows(args.run)
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))

    det, counts, items = deterministic_metrics(rows)
    judged, judge_counts = judged_metrics(rows)
    counts.update(judge_counts)
    print_report(det, judged, counts)
    write_outputs(args.out_dir, det, judged, counts, items)
    values = {**det, **judged}
    # Pinned set == the committed file being checked, or the run just pinned.
    is_pinned = not args.regenerate or args.pin

    if args.write_thresholds:
        if not is_pinned:
            ap.error("--write-thresholds calibrates on the pinned run (use --pin)")
        new = thresholds_from(det, counts, judged, args.margin)
        if args.write_thresholds.exists():
            # Re-pinning must not quietly self-certify a worse pipeline: the new
            # run has to clear the old rate floors unless the regression is owned.
            old = json.loads(args.write_thresholds.read_text(encoding="utf-8"))
            regressed = rate_problems(values, old)
            if regressed and not args.accept_regression:
                print("\nRefusing to recalibrate: this run regresses past the existing thresholds:")
                for p in regressed:
                    print(f"  - {p}")
                print("Fix the regression, or pass --accept-regression 'why' to record it.")
                return 1
        spec = {
            "pinned_run": _repo_relative(args.run),
            "pinned_run_sha256": sha256_file(args.run),
            "margin": args.margin,
            "accepted_regression": args.accept_regression,
            "note": (
                "Rate floors/ceilings = measured value -/+ margin, rounded outward to 2 dp "
                "(margin = one question's worth on the 15 answerable items), and they are "
                "what a regenerated run is held to. max_violations are exact counts on the "
                "fixed pinned set: the deterministic checks re-run on identical text, so "
                "any new uncited claim, ungrounded figure, invalid citation, answered trap "
                "or false refusal is a regression. Recalibrate only together with a new "
                "pinned run (--regenerate --pin) and say why in the PR."
            ),
            **new,
        }
        args.write_thresholds.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote thresholds to {args.write_thresholds}")

    if args.check:
        spec = json.loads(args.check.read_text(encoding="utf-8"))
        problems = rate_problems(values, spec)
        if is_pinned:
            problems += count_problems(counts, spec, items)
            if spec.get("pinned_run_sha256") != sha256_file(args.run):
                problems.append(
                    "pinned run changed since thresholds were calibrated; regenerate it "
                    "(--regenerate --pin) and recalibrate instead of editing it by hand"
                )
            problems += staleness_problems(manifest, current)
            problems += row_provenance_problems(rows, current)
        if problems:
            print("\nFAITHFULNESS REGRESSION CHECK FAILED:")
            for p in problems:
                print(f"  - {p}")
            return 1
        print(f"\nFaithfulness gate OK ({args.check}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
