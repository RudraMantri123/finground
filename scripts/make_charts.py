#!/usr/bin/env python3
"""Render comparison charts from results/results.csv into results/charts/.

Reads the benchmark CSV (``N/A`` cells are skipped, never plotted as zero) and
produces:
  * quality_by_model.png  — grouped bars: correctness, citation accuracy,
    faithfulness (=1-hallucination), refusal calibration
  * hallucination_by_model.png — hallucination rate (lower is better)
  * cost_latency.png      — cost per 100 questions and average latency
"""

from __future__ import annotations

import csv

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

from finground.config import CONFIG  # noqa: E402

RESULTS = CONFIG.paths.results / "results.csv"
CHARTS = CONFIG.paths.results / "charts"


def _f(x: str) -> float | None:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def load_rows() -> list[dict]:
    if not RESULTS.exists():
        raise FileNotFoundError(f"{RESULTS} not found. Run scripts/run_benchmark.py first.")
    with open(RESULTS, encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def quality_chart(rows: list[dict]) -> None:
    metrics = [
        ("correctness", "Correctness"),
        ("citation_accuracy", "Citation accuracy"),
        ("faithfulness", "Faithfulness"),
        ("refusal_calibration", "Refusal calibration"),
    ]
    plotted = [r for r in rows if _f(r["correctness"]) is not None]
    if not plotted:
        print("No numeric rows to plot (all N/A). Skipping quality chart.")
        return
    labels = [r["model"] for r in plotted]
    x = range(len(plotted))
    width = 0.2
    fig, ax = plt.subplots(figsize=(1.8 * len(plotted) + 4, 5))
    for i, (key, name) in enumerate(metrics):
        vals = []
        for r in plotted:
            if key == "faithfulness":
                h = _f(r["hallucination_rate"])
                vals.append(1.0 - h if h is not None else 0.0)
            else:
                vals.append(_f(r[key]) or 0.0)
        ax.bar([xi + i * width for xi in x], vals, width, label=name)
    ax.set_xticks([xi + 1.5 * width for xi in x])
    ax.set_xticklabels(labels, rotation=15, ha="right")
    ax.set_ylim(0, 1.05)
    ax.set_ylabel("score (higher is better)")
    ax.set_title("FinGround — faithfulness-first quality by model")
    ax.legend(ncol=4, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    fig.tight_layout()
    out = CHARTS / "quality_by_model.png"
    fig.savefig(out, dpi=140)
    plt.close(fig)
    print(f"Wrote {out}")


def hallucination_chart(rows: list[dict]) -> None:
    plotted = [(r["model"], _f(r["hallucination_rate"])) for r in rows]
    plotted = [(m, v) for m, v in plotted if v is not None]
    if not plotted:
        print("No hallucination data to plot. Skipping.")
        return
    labels = [m for m, _ in plotted]
    vals = [v for _, v in plotted]
    fig, ax = plt.subplots(figsize=(1.6 * len(plotted) + 3, 4.5))
    bars = ax.bar(labels, vals, color="#d1495b")
    ax.set_ylabel("hallucination rate (lower is better)")
    ax.set_title("FinGround — unsupported-claim (hallucination) rate")
    ax.set_ylim(0, max(vals + [0.1]) * 1.3)
    for b, v in zip(bars, vals, strict=True):
        ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.2f}", ha="center", va="bottom", fontsize=9)
    plt.xticks(rotation=15, ha="right")
    fig.tight_layout()
    out = CHARTS / "hallucination_by_model.png"
    fig.savefig(out, dpi=140)
    plt.close(fig)
    print(f"Wrote {out}")


def cost_latency_chart(rows: list[dict]) -> None:
    data = [
        (r["model"], _f(r["cost_per_100q"]), _f(r["avg_latency_s"]))
        for r in rows
        if _f(r["avg_latency_s"]) is not None
    ]
    if not data:
        print("No cost/latency data to plot. Skipping.")
        return
    labels = [d[0] for d in data]
    costs = [d[1] or 0.0 for d in data]
    lats = [d[2] or 0.0 for d in data]
    x = range(len(data))
    fig, ax1 = plt.subplots(figsize=(1.6 * len(data) + 3, 4.5))
    ax1.bar([xi - 0.2 for xi in x], costs, 0.4, color="#2e86ab", label="cost / 100q ($)")
    ax1.set_ylabel("cost per 100 questions ($)", color="#2e86ab")
    ax2 = ax1.twinx()
    ax2.bar([xi + 0.2 for xi in x], lats, 0.4, color="#e9c46a", label="avg latency (s)")
    ax2.set_ylabel("avg latency (s)", color="#b8860b")
    ax1.set_xticks(list(x))
    ax1.set_xticklabels(labels, rotation=15, ha="right")
    ax1.set_title("FinGround — cost and latency by model")
    fig.tight_layout()
    out = CHARTS / "cost_latency.png"
    fig.savefig(out, dpi=140)
    plt.close(fig)
    print(f"Wrote {out}")


def main() -> int:
    CHARTS.mkdir(parents=True, exist_ok=True)
    rows = load_rows()
    quality_chart(rows)
    hallucination_chart(rows)
    cost_latency_chart(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
