#!/usr/bin/env python3
"""Fill new leaderboard columns for committed rows from results/runs/*.jsonl.

Rows written before the observability columns existed have blanks for them.
This recomputes what the committed per-question dumps support — bootstrap CIs,
citation coverage, failure rate, cost per request — and leaves the rest blank
rather than inventing it. Existing values are never overwritten; a recomputed
quality metric that disagrees with the committed one is reported, not "fixed".

Latency percentiles need per-question latencies, which older dumps lack. With
``--latency-from-cache`` they are recovered by replaying each question through
the pipeline in *cache-only* mode (the LLM is never called; a cache miss leaves
that question out) and accepting a cached latency only when the cached answer
is identical to the committed answer. The check against the committed average
latency is printed so the recovery can be audited.

Usage:
  python scripts/recompute_results.py                      # CIs, coverage, failure, cost
  python scripts/recompute_results.py --latency-from-cache # + p50/p95 where verifiable
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from pathlib import Path

from finground.config import CONFIG
from finground.eval.summary import QUALITY_METRICS, summarize_rows

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_benchmark import CSV_COLUMNS, row_strs  # noqa: E402

RESULTS = CONFIG.paths.results / "results.csv"
RUNS = CONFIG.paths.results / "runs"


def _safe(model: str) -> str:
    return model.replace(":", "_").replace("/", "_")


def _load_rows(model: str) -> list[dict] | None:
    path = RUNS / f"{_safe(model)}.jsonl"
    if not path.exists():
        return None
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _gold_ids() -> dict[str, bool]:
    path = CONFIG.paths.results / "gold_set.jsonl"
    out: dict[str, bool] = {}
    if path.exists():
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    d = json.loads(line)
                    out[d["id"]] = bool(d.get("gold_answer"))
    return out


def _recover_latencies(model: str, rows: list[dict]) -> tuple[int, int]:
    """Attach ``latency_s`` to rows whose cached answer matches; returns (hits, eligible)."""
    import finground.llm as llm
    from finground.answer import answer_question

    def _cache_only(self, system, user, max_tokens):  # never reach a provider
        raise llm.LLMUnavailable("cache miss (cache-only replay)")

    llm.LLMClient._dispatch = _cache_only  # type: ignore[method-assign]
    hits = eligible = 0
    for r in rows:
        if "error" in r or r.get("latency_s"):
            continue
        # Model-worded refusals did call the LLM and count toward latency, so
        # abstained rows are replayed too; only evidence-gated ones are skipped.
        try:
            ans = answer_question(r["question"], model=model)
        except llm.LLMUnavailable:
            eligible += 1
            continue
        if not ans.cached:
            continue  # evidence gate fired: no LLM call, no latency (as in the run)
        eligible += 1
        if ans.answer == r.get("answer") and ans.abstained == r.get("abstained"):
            r["latency_s"] = ans.latency_s
            hits += 1
    return hits, eligible


def _fmt_or_blank(value: str) -> str:
    return "" if value == "N/A" else value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--latency-from-cache", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="print, don't write")
    args = parser.parse_args(argv)
    os.environ.setdefault("FINGROUND_TRACING", "0")  # replays are not real requests

    with open(RESULTS, encoding="utf-8") as fh:
        old_rows = list(csv.DictReader(fh))
    gold = _gold_ids()
    merged: list[list[str]] = []
    for old in old_rows:
        model = old["model"]
        base = [old.get(c, "") or "" for c in CSV_COLUMNS]
        rows = _load_rows(model)
        if rows is None:
            print(f"[keep] {model}: no run dump, left as is")
            merged.append(base)
            continue
        for r in rows:
            r.setdefault("has_gold", gold.get(r["id"], True))
        legacy_cost = not any("cost_usd" in r for r in rows)
        if args.latency_from_cache and not any(r.get("latency_s") for r in rows):
            hits, eligible = _recover_latencies(model, rows)
            print(f"[latency] {model}: verified {hits}/{eligible} cached answers")
            if hits < eligible:
                # A partial sample would bias the percentiles; leave them blank.
                for r in rows:
                    r.pop("latency_s", None)
        summary = summarize_rows(
            rows, model=model, judge=old.get("judge", ""), cost_known=not legacy_cost
        )
        if legacy_cost and old.get("cost_per_100q") not in ("", "N/A", None):
            # cost_per_100q was total/n*100, so per-request cost is exact from it.
            summary["cost_per_request"] = float(old["cost_per_100q"]) / 100
        if summary["avg_latency_s"] is not None and old.get("avg_latency_s"):
            print(
                f"[latency] {model}: recomputed avg {summary['avg_latency_s']:.2f}s "
                f"vs committed {old['avg_latency_s']}s"
            )
        for m in QUALITY_METRICS:
            committed, recomputed = old.get(m, ""), summary.get(m)
            if committed not in ("", "N/A") and recomputed is not None:
                if abs(float(committed) - recomputed) > 5e-4:
                    print(
                        f"[warn] {model}: {m} committed {committed} != recomputed {recomputed:.3f}"
                    )
        fresh = [_fmt_or_blank(v) for v in row_strs(summary)]
        # Never overwrite a committed value; only fill blanks.
        merged.append([b if b != "" else f for b, f in zip(base, fresh, strict=True)])
        print(f"[fill] {model}")

    if args.dry_run:
        print(",".join(CSV_COLUMNS))
        for row in merged:
            print(",".join(row))
        return 0
    with open(RESULTS, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(CSV_COLUMNS)
        writer.writerows(merged)
    print(f"Wrote {RESULTS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
