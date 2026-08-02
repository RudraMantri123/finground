"""Evaluation datasets: our own aligned gold set + a FinanceBench loader.

Two sources feed the harness:

1. **FinGround gold set** (``results/gold_set.jsonl``) — questions written to be
   answerable (or deliberately *not* answerable) from the exact filings we
   ingested. Because it is aligned to our corpus it gives clean correctness and
   refusal-calibration signal. Includes both answerable and unanswerable items.

2. **FinanceBench** (``PatronusAI/financebench`` on Hugging Face) — a public
   QA-with-evidence benchmark over filings, used to anchor results to an
   external dataset. Coverage caveat: its evidence lives in specific filing
   versions that may differ from the ones we indexed, so we optionally restrict
   to questions about companies present in our corpus.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..config import CONFIG

GOLD_PATH = CONFIG.paths.results / "gold_set.jsonl"


@dataclass
class GoldItem:
    """One evaluation question with its ground-truth expectations."""

    id: str
    question: str
    answerable: bool  # can the ingested filings answer it?
    gold_answer: str = ""  # reference answer (empty for unanswerable items)
    gold_tickers: list[str] = field(default_factory=list)
    category: str = "general"  # e.g. risk_factors, business, geoeconomic
    source: str = "finground_gold"
    notes: str = ""

    def to_json(self) -> dict:
        return asdict(self)


def load_gold_set(path: Path | None = None) -> list[GoldItem]:
    """Load the FinGround gold set from JSONL."""
    path = path or GOLD_PATH
    if not path.exists():
        raise FileNotFoundError(f"Gold set not found at {path}")
    items: list[GoldItem] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                items.append(GoldItem(**json.loads(line)))
    return items


def write_gold_set(items: list[GoldItem], path: Path | None = None) -> int:
    path = path or GOLD_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        for it in items:
            fh.write(json.dumps(it.to_json(), ensure_ascii=False) + "\n")
    return len(items)


# ---------------------------------------------------------------------------
# FinanceBench
# ---------------------------------------------------------------------------

# Company-name substrings -> ticker, to map FinanceBench rows onto our corpus.
_NAME_TO_TICKER = {
    "apple": "AAPL",
    "microsoft": "MSFT",
    "amazon": "AMZN",
    "alphabet": "GOOGL",
    "google": "GOOGL",
    "nvidia": "NVDA",
    "tesla": "TSLA",
    "jpmorgan": "JPM",
    "coca": "KO",
}


def _guess_ticker(text: str) -> str | None:
    low = (text or "").lower()
    for name, ticker in _NAME_TO_TICKER.items():
        if name in low:
            return ticker
    return None


def load_financebench(
    *,
    only_our_companies: bool = True,
    limit: int | None = None,
) -> list[GoldItem]:
    """Load FinanceBench and normalize rows into :class:`GoldItem`.

    Requires ``datasets`` and network access on first call. Raises a clear error
    if the dataset id/split cannot be resolved so the benchmark can skip it.
    """
    try:
        from datasets import load_dataset
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("`datasets` not installed; cannot load FinanceBench") from exc

    ds = None
    last_err: Exception | None = None
    # The dataset has shipped under a few config/split conventions; try the
    # common ones and surface a clear error if none resolve.
    for kwargs in ({"split": "train"}, {"split": "test"}, {}):
        try:
            ds = load_dataset("PatronusAI/financebench", **kwargs)
            break
        except Exception as exc:  # noqa: BLE001
            last_err = exc
    if ds is None:
        raise RuntimeError(f"Could not load PatronusAI/financebench: {last_err}")

    rows = ds if hasattr(ds, "__iter__") and not hasattr(ds, "keys") else ds[next(iter(ds.keys()))]

    items: list[GoldItem] = []
    for i, row in enumerate(rows):
        company = row.get("company") or row.get("doc_name") or ""
        ticker = _guess_ticker(str(company)) or _guess_ticker(str(row.get("question", "")))
        if only_our_companies and ticker is None:
            continue
        fid = str(row.get("financebench_id") or row.get("id") or f"fb-{i:04d}")
        items.append(
            GoldItem(
                id=fid,
                question=str(row.get("question", "")).strip(),
                answerable=True,  # FinanceBench questions are answerable by design
                gold_answer=str(row.get("answer", "")).strip(),
                gold_tickers=[ticker] if ticker else [],
                category=str(row.get("question_type", "financebench")),
                source="financebench",
            )
        )
        if limit and len(items) >= limit:
            break
    return items
