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

# (header, renderer) per README column. Quality metrics show their bootstrap
# 95% CI inline; blanks (values that could not be recomputed for older rows)
# render as "—" rather than a made-up number.
_BLANK = {"", "N/A", None}


def _val(r: dict, col: str) -> str:
    v = r.get(col)
    return "—" if v in _BLANK else str(v)


def _with_ci(col: str):
    def render(r: dict) -> str:
        lo, hi = r.get(f"{col}_ci_lo"), r.get(f"{col}_ci_hi")
        base = _val(r, col)
        if base == "—" or lo in _BLANK or hi in _BLANK:
            return base
        return f"{base} [{float(str(lo)):.2f}, {float(str(hi)):.2f}]"

    return render


def _latency(r: dict) -> str:
    p50, p95 = r.get("latency_p50_s"), r.get("latency_p95_s")
    if p50 in _BLANK or p95 in _BLANK:
        avg = r.get("avg_latency_s")
        return "—" if avg in _BLANK else f"avg {avg}"
    return f"{p50} / {p95}"


COLUMNS = [
    ("Model", lambda r: _val(r, "model")),
    ("Correctness ↑", _with_ci("correctness")),
    ("Citation acc ↑", _with_ci("citation_accuracy")),
    ("Hallucination ↓", _with_ci("hallucination_rate")),
    ("Refusal cal ↑", _with_ci("refusal_calibration")),
    ("Cite coverage ↑", lambda r: _val(r, "citation_coverage")),
    ("Failure ↓", lambda r: _val(r, "failure_rate")),
    ("Latency p50 / p95 (s)", _latency),
    ("$/request", lambda r: _val(r, "cost_per_request")),
    ("n", lambda r: _val(r, "n_questions")),
    ("answered", lambda r: _val(r, "n_answered")),
    ("Judge", lambda r: _val(r, "judge")),
]


def _replace_block(text: str, start: str, end: str, body: str) -> str:
    s = text.index(start) + len(start)
    e = text.index(end)
    return text[:s] + "\n" + body + "\n" + text[e:]


def results_table() -> str:
    if not RESULTS.exists():
        return "_No results yet — run `make benchmark`._"
    with open(RESULTS, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    header = "| " + " | ".join(h for h, _ in COLUMNS) + " |"
    sep = "|" + "|".join(["---"] * len(COLUMNS)) + "|"
    lines = [header, sep]
    for r in rows:
        lines.append("| " + " | ".join(render(r) for _, render in COLUMNS) + " |")
    lines.append("")
    lines.append(
        "Brackets: bootstrap 95% CI (1,000 seeded resamples over questions). "
        "Cite coverage: share of answers where every sentence carries a valid `[C#]`. "
        "Failure: (exceptions + answers with any judge-unsupported claim) / n. "
        "Latency: LLM generation time, p50 / p95."
    )
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
