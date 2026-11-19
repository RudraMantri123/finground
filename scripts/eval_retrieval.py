#!/usr/bin/env python3
"""Retrieval ablation over the gold set: BM25 vs dense vs hybrid vs hybrid+rerank.

Deterministic and free: no LLM calls, only the local embedding model and the
cross-encoder. Relevance comes from the gold set's phrase-based ``evidence``
labels (see ``finground.eval.retrieval_metrics``), so the numbers stay
meaningful after re-chunking. Unanswerable questions have no evidence and are
excluded.

Two corpora:

* ``--corpus fixture`` (default) — the small committed corpus in
  ``tests/fixtures/retrieval_corpus.jsonl``, indexed in memory on each run.
  This is what CI measures and what ``results/retrieval_thresholds.json`` is
  calibrated against.
* ``--corpus full`` — the locally built ``indexes/`` over every chunk
  (needs ``make ingest && make index``). Not available in CI.

Outputs ``results/retrieval_eval[_full].csv`` (one row per configuration) and
``results/retrieval_eval[_full]_per_question.jsonl`` (ranked chunks and which
labels each one satisfied, for auditing).

Usage:
  python scripts/eval_retrieval.py                                   # fixture, all configs
  python scripts/eval_retrieval.py --check results/retrieval_thresholds.json
  python scripts/eval_retrieval.py --corpus full
  python scripts/eval_retrieval.py --write-thresholds results/retrieval_thresholds.json
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
import time
from pathlib import Path

from finground import retrieve as R
from finground.config import CONFIG
from finground.eval.datasets import GoldItem, load_gold_set
from finground.eval.retrieval_metrics import (
    DEFAULT_KS,
    EvidenceLabel,
    label_hits,
    macro_average,
    metric_names,
    paired_bootstrap,
    parse_labels,
    question_metrics,
    unreachable_labels,
)

FIXTURE_PATH = CONFIG.paths.root / "tests" / "fixtures" / "retrieval_corpus.jsonl"

# name -> retrieve() keyword overrides. Everything else (company filter, pool
# sizes, RRF constant, rerank pool) is the production config, so each row is
# exactly "the shipped pipeline minus/plus one component".
CONFIGS: dict[str, dict] = {
    "bm25": {"mode": "bm25", "use_reranker": False},
    "dense": {"mode": "dense", "use_reranker": False},
    "hybrid_rrf": {"mode": "hybrid", "use_reranker": False},
    "hybrid_rerank": {"mode": "hybrid", "use_reranker": True},
}

# One question's worth of evidence on the 15-question set (1/15 ~= 0.067),
# rounded up. Thresholds sit this far below the measured value, so losing all
# of one question's evidence (or a near-tie flipping between CPU architectures)
# still passes, while losing more than that fails the gate.
DEFAULT_MARGIN = 0.07


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_fixture(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def labelled_items(items: list[GoldItem]) -> list[tuple[GoldItem, list[EvidenceLabel]]]:
    """Answerable gold items that carry evidence labels."""
    return [(it, parse_labels(it.evidence)) for it in items if it.answerable and it.evidence]


def run_config(
    name: str,
    overrides: dict,
    labelled: list[tuple[GoldItem, list[EvidenceLabel]]],
    indexes,
    top_k: int,
) -> tuple[list[dict[str, float]], list[dict]]:
    """Retrieve for every labelled question; return (per-question metrics, audit rows)."""
    per_q: list[dict[str, float]] = []
    audit: list[dict] = []
    for item, labels in labelled:
        results = R.retrieve(item.question, top_k=top_k, indexes=indexes, **overrides)
        chunks = [
            {"ticker": r.ticker, "section": r.section, "text": r.text, "chunk_id": r.chunk_id}
            for r in results
        ]
        hits = label_hits(chunks, labels)
        m = question_metrics(hits, len(labels))
        per_q.append(m)
        audit.append(
            {
                "config": name,
                "id": item.id,
                "question": item.question,
                "n_labels": len(labels),
                "metrics": {k: round(v, 4) for k, v in m.items()},
                "ranked": [
                    {
                        "rank": i,
                        "chunk_id": c["chunk_id"],
                        "ticker": c["ticker"],
                        "section": c["section"],
                        "labels_hit": sorted(h),
                    }
                    for i, (c, h) in enumerate(zip(chunks, hits, strict=True), start=1)
                ],
            }
        )
    return per_q, audit


def print_table(rows: list[dict], names: list[str]) -> None:
    header = f"{'config':<15}" + "".join(f"{n:>11}" for n in names)
    print(header)
    print("-" * len(header))
    for row in rows:
        print(f"{row['config']:<15}" + "".join(f"{row[n]:>11.3f}" for n in names))


def print_significance(
    per_config: dict[str, list[dict[str, float]]], baseline: str, metrics: list[str]
) -> None:
    """Paired-bootstrap 95% CIs of each config minus ``baseline``.

    With ~15 questions, a gap whose interval straddles zero is not evidence
    that one configuration is better; this prints that caveat next to the table.
    """
    if baseline not in per_config or len(per_config) < 2:
        return
    print(f"\nPaired bootstrap vs {baseline} (mean diff [95% CI], questions resampled):")
    for name, rows in per_config.items():
        if name == baseline:
            continue
        parts = []
        for m in metrics:
            d, lo, hi = paired_bootstrap([r[m] for r in rows], [r[m] for r in per_config[baseline]])
            flag = "" if lo > 0 or hi < 0 else " ~"
            parts.append(f"{m} {d:+.3f} [{lo:+.3f}, {hi:+.3f}]{flag}")
        print(f"  {name:<14} " + "   ".join(parts))
    print("  (~ = interval includes 0: not distinguishable on this question set)")


def check_thresholds(
    rows: list[dict], spec: dict, corpus: str, fixture_sha: str | None
) -> list[str]:
    """Return human-readable violations (empty list == pass)."""
    problems: list[str] = []
    if spec.get("corpus") != corpus:
        problems.append(
            f"thresholds were calibrated on corpus={spec.get('corpus')!r}, "
            f"but this run measured corpus={corpus!r}"
        )
    want_sha = spec.get("fixture_sha256")
    if corpus == "fixture" and want_sha and fixture_sha != want_sha:
        problems.append(
            "fixture corpus changed since thresholds were calibrated; re-measure and "
            "update with --write-thresholds (and say why in the PR)"
        )
    by_config = {r["config"]: r for r in rows}
    for config, metrics in spec.get("thresholds", {}).items():
        if config not in by_config:
            problems.append(f"{config}: not measured in this run")
            continue
        for metric, floor in metrics.items():
            got = by_config[config].get(metric)
            if got is None:
                problems.append(f"{config}/{metric}: metric missing")
            elif got + 1e-9 < floor:
                problems.append(f"{config}/{metric}: {got:.3f} < threshold {floor:.3f}")
    return problems


def thresholds_from(rows: list[dict], names: list[str], margin: float) -> dict:
    """Floor each measured metric ``margin`` below its value (2 dp, never < 0)."""
    return {
        r["config"]: {n: max(0.0, math.floor((r[n] - margin) * 100) / 100) for n in names}
        for r in rows
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--corpus", choices=["fixture", "full"], default="fixture")
    ap.add_argument("--fixture", type=Path, default=FIXTURE_PATH)
    ap.add_argument("--gold", type=Path, default=None, help="gold set (default results/)")
    ap.add_argument("--configs", nargs="+", choices=list(CONFIGS), default=list(CONFIGS))
    ap.add_argument("--check", type=Path, help="thresholds JSON; exit 1 on any regression")
    ap.add_argument("--write-thresholds", type=Path, help="calibrate thresholds from this run")
    ap.add_argument("--margin", type=float, default=DEFAULT_MARGIN)
    ap.add_argument("--out-dir", type=Path, default=CONFIG.paths.results)
    args = ap.parse_args()

    labelled = labelled_items(load_gold_set(args.gold))
    if not labelled:
        print("No answerable gold items with evidence labels.")
        return 1
    top_k = max(DEFAULT_KS)
    names = metric_names()

    t0 = time.time()
    fixture_sha: str | None = None
    if args.corpus == "fixture":
        if not args.fixture.exists():
            print(f"Fixture corpus not found at {args.fixture}.")
            return 1
        corpus = load_fixture(args.fixture)
        fixture_sha = file_sha256(args.fixture)
        print(f"Indexing fixture corpus ({len(corpus)} chunks) in memory...")
        indexes = R.indexes_from_chunks(corpus)
    else:
        indexes = R.load_indexes()
        corpus = indexes.bm25_chunks
    print(f"Corpus ready in {time.time() - t0:.1f}s; {len(labelled)} labelled questions.")

    # A label nothing in the corpus satisfies is a data bug, not a retrieval
    # miss: report it and fail, since it silently caps every config's recall.
    broken = [
        (item.id, lab) for item, labels in labelled for lab in unreachable_labels(labels, corpus)
    ]
    for qid, lab in broken:
        print(f"[unreachable] {qid} {lab.ticker} {list(lab.must_contain)}")

    if any(CONFIGS[c]["use_reranker"] for c in args.configs) and not R.reranker_available():
        print("Cross-encoder could not be loaded; refusing to report reranked numbers.")
        return 2

    rows: list[dict] = []
    audit: list[dict] = []
    per_config: dict[str, list[dict[str, float]]] = {}
    for name in args.configs:
        t = time.time()
        per_q, q_audit = run_config(name, CONFIGS[name], labelled, indexes, top_k)
        per_config[name] = per_q
        rows.append({"corpus": args.corpus, "config": name, "n_questions": len(labelled)})
        rows[-1].update(macro_average(per_q))
        audit.extend(q_audit)
        print(f"  {name}: {time.time() - t:.1f}s")

    print()
    print_table(rows, names)
    print_significance(per_config, "hybrid_rerank", ["recall@5", "mrr@10", "ndcg@10"])

    args.out_dir.mkdir(parents=True, exist_ok=True)
    stem = "retrieval_eval" if args.corpus == "fixture" else "retrieval_eval_full"
    csv_path = args.out_dir / f"{stem}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["corpus", "config", "n_questions", *names])
        w.writeheader()
        for r in rows:
            w.writerow({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items()})
    jsonl_path = args.out_dir / f"{stem}_per_question.jsonl"
    with open(jsonl_path, "w", encoding="utf-8") as fh:
        for rec in audit:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"\nWrote {csv_path} and {jsonl_path}")

    if args.write_thresholds:
        spec = {
            "corpus": args.corpus,
            "fixture_sha256": fixture_sha,
            "margin": args.margin,
            "note": (
                "Floors = measured value minus margin, rounded down to 2 dp. The margin is "
                "one question's worth of evidence on the 15-question set (1/15, rounded up): "
                "a near-tie flipping across CPUs, or one question losing its evidence, "
                "passes; losing more than that fails. Recalibrate (and justify in the PR) "
                "when the fixture, models, or retrieval config change on purpose."
            ),
            "thresholds": thresholds_from(rows, names, args.margin),
        }
        args.write_thresholds.write_text(json.dumps(spec, indent=2) + "\n", encoding="utf-8")
        print(f"Wrote thresholds to {args.write_thresholds}")

    if args.check:
        spec = json.loads(args.check.read_text(encoding="utf-8"))
        problems = check_thresholds(rows, spec, args.corpus, fixture_sha)
        problems += [f"unreachable evidence label in {qid}" for qid, _ in broken]
        if problems:
            print("\nRETRIEVAL REGRESSION CHECK FAILED:")
            for p in problems:
                print(f"  - {p}")
            return 1
        print(f"\nRetrieval thresholds OK ({args.check}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
