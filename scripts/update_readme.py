#!/usr/bin/env python3
"""Wire the README results table + judge-validation block from results/.

Idempotent: replaces the content between the HTML markers in README.md with a
fresh rendering of results/results.csv and results/judge_validation.json. Run
after `make benchmark` and `make validate-judge`.
"""

from __future__ import annotations

import csv
import json

from finground.config import CONFIG

README = CONFIG.paths.root / "README.md"
RESULTS = CONFIG.paths.results / "results.csv"
VALIDATION = CONFIG.paths.results / "judge_validation.json"

_PRETTY = {
    "model": "Model",
    "correctness": "Correctness ↑",
    "citation_accuracy": "Citation acc ↑",
    "hallucination_rate": "Hallucination ↓",
    "refusal_calibration": "Refusal cal ↑",
    "avg_latency_s": "Latency (s)",
    "cost_per_100q": "$/100q",
    "n_questions": "n",
    "n_answered": "answered",
}


def _replace_block(text: str, start: str, end: str, body: str) -> str:
    s = text.index(start) + len(start)
    e = text.index(end)
    return text[:s] + "\n" + body + "\n" + text[e:]


def results_table() -> str:
    if not RESULTS.exists():
        return "_No results yet — run `make benchmark`._"
    with open(RESULTS, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    cols = list(_PRETTY)
    header = "| " + " | ".join(_PRETTY[c] for c in cols) + " |"
    sep = "|" + "|".join(["---"] * len(cols)) + "|"
    lines = [header, sep]
    for r in rows:
        lines.append("| " + " | ".join(str(r.get(c, "")) for c in cols) + " |")
    return "\n".join(lines)


def validation_block() -> str:
    if not VALIDATION.exists():
        return "_No validation yet — run `make validate-judge`._"
    d = json.loads(VALIDATION.read_text())
    lines = [
        f"Judge model: `{d['model']}` · n = {d['n_examples']} examples",
        "",
        "| Axis | Raw agreement | Cohen's κ |",
        "|---|---|---|",
    ]
    for axis in ("correctness", "faithfulness"):
        a = d[axis]
        lines.append(f"| {axis.title()} | {a['raw_agreement']:.1%} | {a['cohen_kappa']:.3f} |")
    return "\n".join(lines)


def main() -> int:
    text = README.read_text()
    text = _replace_block(
        text, "<!-- RESULTS_TABLE_START -->", "<!-- RESULTS_TABLE_END -->", results_table()
    )
    text = _replace_block(
        text,
        "<!-- JUDGE_VALIDATION_START -->",
        "<!-- JUDGE_VALIDATION_END -->",
        validation_block(),
    )
    README.write_text(text)
    print(f"Updated {README}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
