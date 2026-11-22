#!/usr/bin/env python3
"""Build the compact retrieval-eval corpus committed for CI.

CI has no ``data/`` or ``indexes/`` (both gitignored and expensive to rebuild
from EDGAR), so the retrieval regression gate runs on a small, committed
subset of the chunk corpus, indexed in memory on each run:

1. **Positives** — every chunk that satisfies any gold evidence label.
2. **Hard negatives** — for each labelled question, the top ``--hard-k``
   chunks from BM25, dense, and hybrid retrieval over the *full* corpus. These
   are the passages each ranker actually confuses with the evidence, so the
   fixture keeps the competition that matters at k <= 10.
3. **Background** — a seeded random sample of ``--per-ticker`` chunks from
   every company, so BM25 IDF and the company filter see a realistic mix and
   no company is represented only by passages chosen for a question.

Chunks keep their original corpus order. Because relevance is phrase-based,
the fixture does not need to keep chunk IDs stable: after a chunking change,
rebuild ``data/`` and ``indexes/``, re-run this script, re-measure with
``scripts/eval_retrieval.py --write-thresholds``, and commit all three files.

Usage:
  python scripts/make_retrieval_fixture.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path

from finground import retrieve as R
from finground.config import CONFIG
from finground.eval.datasets import load_gold_set
from finground.eval.retrieval_metrics import parse_labels

FIXTURE_PATH = CONFIG.paths.root / "tests" / "fixtures" / "retrieval_corpus.jsonl"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, default=FIXTURE_PATH)
    ap.add_argument("--hard-k", type=int, default=30, help="per-ranker hard negatives/question")
    ap.add_argument("--per-ticker", type=int, default=25, help="random background per company")
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    indexes = R.load_indexes()
    chunks = indexes.bm25_chunks
    order = {c["chunk_id"]: i for i, c in enumerate(chunks)}
    labelled = [
        (it, parse_labels(it.evidence)) for it in load_gold_set() if it.answerable and it.evidence
    ]

    keep: set[str] = set()
    positives = {
        c["chunk_id"] for c in chunks for _, labs in labelled for lab in labs if lab.matches(c)
    }
    keep |= positives

    hard: set[str] = set()
    for item, _labels in labelled:
        for mode in R.RETRIEVAL_MODES:
            for r in R.retrieve(
                item.question, top_k=args.hard_k, mode=mode, use_reranker=False, indexes=indexes
            ):
                hard.add(r.chunk_id)
    keep |= hard

    rng = random.Random(args.seed)
    by_ticker: dict[str, list[str]] = {}
    for c in chunks:
        by_ticker.setdefault(c["ticker"], []).append(c["chunk_id"])
    background: set[str] = set()
    for ticker in sorted(by_ticker):
        ids = by_ticker[ticker]
        background |= set(rng.sample(ids, min(args.per_ticker, len(ids))))
    keep |= background

    selected = sorted(keep, key=order.__getitem__)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        for cid in selected:
            fh.write(json.dumps(chunks[order[cid]], ensure_ascii=False) + "\n")

    meta = {
        "source_chunks": len(chunks),
        "source_chunks_sha256": hashlib.sha256(CONFIG.paths.chunks.read_bytes()).hexdigest(),
        "fixture_chunks": len(selected),
        "positives": len(positives),
        "hard_negative_pool": len(hard - positives),
        "background_only": len(background - hard - positives),
        "params": {"hard_k": args.hard_k, "per_ticker": args.per_ticker, "seed": args.seed},
    }
    meta_path = args.out.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    size_kb = args.out.stat().st_size / 1024
    print(f"Wrote {len(selected)} chunks ({size_kb:.0f} KB) to {args.out}")
    print(json.dumps(meta, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
