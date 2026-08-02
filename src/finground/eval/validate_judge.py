"""Validate the LLM judge against human labels (Cohen's kappa).

This is the credibility check on the whole evaluation: an LLM-as-judge is only
worth trusting to the extent it agrees with humans. We run the judge on the
committed, self-contained examples in ``results/human_labels/`` and report
agreement on two axes:

* **correctness** — judge ``correct`` vs ``human_correct``
* **faithfulness** — judge (all-claims-supported) vs ``human_faithful``

Reported with Cohen's kappa (chance-corrected) and raw agreement. Requires a
judge LLM to be available (``--model`` or ``FINGROUND_JUDGE_MODEL``); results are
cached so re-runs are free.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from sklearn.metrics import cohen_kappa_score

from ..config import CONFIG
from ..llm import LLMUnavailable, available_providers, parse_model
from .judge import judge_answer


def load_human_labels(directory: Path | None = None) -> list[dict]:
    directory = directory or CONFIG.paths.human_labels
    records: list[dict] = []
    for path in sorted(Path(directory).glob("*.jsonl")):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    return records


def _agreement(human: list[bool], judge: list[bool]) -> dict:
    n = len(human)
    raw = sum(1 for h, j in zip(human, judge, strict=True) if h == j) / n if n else 0.0
    # kappa is undefined when a rater is constant; guard it.
    try:
        kappa = float(cohen_kappa_score(human, judge))
    except Exception:  # noqa: BLE001
        kappa = float("nan")
    return {"n": n, "raw_agreement": raw, "cohen_kappa": kappa}


def validate(model: str | None = None) -> dict:
    model = model or CONFIG.models.judge
    provider, _ = parse_model(model)
    if provider not in available_providers():
        raise LLMUnavailable(
            f"Judge provider {provider!r} unavailable. Set its key or pass --model."
        )

    labels = load_human_labels()
    if not labels:
        raise FileNotFoundError(
            f"No human labels found in {CONFIG.paths.human_labels}. "
            "Run scripts/make_human_labels.py first."
        )

    human_correct: list[bool] = []
    judge_correct: list[bool] = []
    human_faithful: list[bool] = []
    judge_faithful: list[bool] = []
    rows = []

    for rec in labels:
        j = judge_answer(
            question=rec["question"],
            answer=rec["candidate_answer"],
            citations=rec["citations"],
            abstained=False,
            gold_answer=rec.get("gold_answer", ""),
            model=model,
        )
        if j.error:
            print(f"  ! {rec['id']}: judge error: {j.error}", file=sys.stderr)
            continue
        jc = bool(j.correct)
        # Judge deems an answer faithful iff every extracted claim is supported.
        jf = len(j.claim_supports) > 0 and all(j.claim_supports)

        human_correct.append(bool(rec["human_correct"]))
        judge_correct.append(jc)
        human_faithful.append(bool(rec["human_faithful"]))
        judge_faithful.append(jf)
        rows.append(
            {
                "id": rec["id"],
                "human_correct": bool(rec["human_correct"]),
                "judge_correct": jc,
                "human_faithful": bool(rec["human_faithful"]),
                "judge_faithful": jf,
            }
        )

    report = {
        "model": model,
        "n_examples": len(rows),
        "correctness": _agreement(human_correct, judge_correct),
        "faithfulness": _agreement(human_faithful, judge_faithful),
        "rows": rows,
    }
    return report


def _print_report(report: dict) -> None:
    print(f"\nJudge validation — model: {report['model']}  (n={report['n_examples']})")
    for axis in ("correctness", "faithfulness"):
        a = report[axis]
        print(
            f"  {axis:13s}  raw agreement {a['raw_agreement']:.2%}   "
            f"Cohen's kappa {a['cohen_kappa']:.3f}"
        )
    disagreements = [
        r
        for r in report["rows"]
        if r["human_correct"] != r["judge_correct"] or r["human_faithful"] != r["judge_faithful"]
    ]
    if disagreements:
        print("  disagreements:")
        for r in disagreements:
            print(f"    {r['id']}: {r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate LLM judge vs human labels.")
    parser.add_argument("--model", default=None, help="provider:model for the judge")
    parser.add_argument("--out", default=None, help="write JSON report to this path")
    args = parser.parse_args(argv)

    try:
        report = validate(args.model)
    except (LLMUnavailable, FileNotFoundError) as exc:
        print(f"Cannot validate: {exc}", file=sys.stderr)
        return 1

    _print_report(report)
    out = Path(args.out) if args.out else CONFIG.paths.results / "judge_validation.json"
    out.write_text(json.dumps(report, indent=2))
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
