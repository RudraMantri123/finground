#!/usr/bin/env python3
"""Check the draft gold-set expansion and write a human review sheet.

``results/gold_set_draft.jsonl`` holds candidate items that a person verifies
before promotion into ``results/gold_set.jsonl``. They follow the gold-set
schema plus two review fields, ``status`` ("draft", or "approved" once a person
has checked it) and ``difficulty``. ``scripts/make_gold_set.py`` promotes the
approved rows.

This script:

1. validates every draft row (schema, unique ids that don't collide with the
   real gold set, evidence only on answerable items, label tickers within
   ``gold_tickers``);
2. matches every evidence label against the full local corpus
   (``data/chunks.jsonl``) with the same matcher the retrieval eval uses and
   fails if any label matches no chunk;
3. with ``--review PATH``, writes a Markdown review sheet listing, per item, the
   question, gold answer, and supporting excerpts (ticker + chunk id), or the
   search notes for unanswerable traps. Riskiest items come first.

Usage::

    python scripts/check_gold_draft.py
    python scripts/check_gold_draft.py --review results/goldset_review.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import fields
from pathlib import Path

from finground.config import CONFIG
from finground.eval.datasets import GoldItem, load_gold_set
from finground.eval.retrieval_metrics import EvidenceLabel

DRAFT_PATH = CONFIG.paths.results / "gold_set_draft.jsonl"
REVIEW_FIELDS = {"status", "difficulty"}
# "draft" until a person has checked the item against the filing, then "approved".
STATUSES = {"draft", "approved"}
DIFFICULTIES = {"easy", "medium", "hard"}
EXCERPT_CHARS = 300
MAX_EXCERPTS_PER_LABEL = 2

# Review order: riskiest first.
_RISK_ORDER = {"computed": 1, "cross_company": 2, "unanswerable": 4}


def load_draft(path: Path = DRAFT_PATH) -> list[dict]:
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def load_corpus(path: Path | None = None) -> list[dict]:
    path = path or CONFIG.paths.chunks
    with open(path, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def to_gold_item(row: dict) -> GoldItem:
    """Strip the review-only fields so the row loads as a real GoldItem."""
    known = {f.name for f in fields(GoldItem)}
    return GoldItem(**{k: v for k, v in row.items() if k in known})


def schema_problems(rows: list[dict], existing_ids: set[str]) -> list[str]:
    problems: list[str] = []
    seen: set[str] = set()
    known = {f.name for f in fields(GoldItem)} | REVIEW_FIELDS
    for row in rows:
        rid = row.get("id", "?")
        extra = set(row) - known
        if extra:
            problems.append(f"{rid}: unknown fields {sorted(extra)}")
        if rid in seen:
            problems.append(f"{rid}: duplicate id")
        # Approved rows are expected in gold_set.jsonl once promoted.
        if rid in existing_ids and row.get("status") != "approved":
            problems.append(f"{rid}: collides with an id in gold_set.jsonl")
        seen.add(rid)
        if row.get("status") not in STATUSES:
            problems.append(f"{rid}: status must be one of {sorted(STATUSES)}")
        if row.get("difficulty") not in DIFFICULTIES:
            problems.append(f"{rid}: difficulty must be one of {sorted(DIFFICULTIES)}")
        try:
            item = to_gold_item(row)
        except TypeError as exc:
            problems.append(f"{rid}: {exc}")
            continue
        if item.answerable:
            if not item.gold_answer.strip():
                problems.append(f"{rid}: answerable item without gold_answer")
            if not item.evidence:
                problems.append(f"{rid}: answerable item without evidence")
            for ev in item.evidence:
                if ev.get("ticker") not in item.gold_tickers:
                    problems.append(f"{rid}: label ticker {ev.get('ticker')} not in gold_tickers")
                if not ev.get("must_contain"):
                    problems.append(f"{rid}: label without must_contain")
        else:
            if item.evidence:
                problems.append(f"{rid}: unanswerable item has evidence")
            if item.gold_answer:
                problems.append(f"{rid}: unanswerable item has a gold_answer")
            if not item.notes.strip():
                problems.append(f"{rid}: trap without search notes")
    return problems


def label_matches(row: dict, corpus: list[dict]) -> list[tuple[dict, list[dict]]]:
    """For each evidence label of ``row``: (label dict, chunks it matches)."""
    out = []
    for ev in row.get("evidence") or []:
        lab = EvidenceLabel.from_dict(ev)
        out.append((ev, [c for c in corpus if lab.matches(c)]))
    return out


def _phrase_regex(phrase: str) -> re.Pattern[str]:
    toks = re.findall(r"[0-9a-z]+", unicodedata.normalize("NFKC", phrase).lower())
    return re.compile(r"[^0-9a-z]+".join(map(re.escape, toks)))


def excerpt(text: str, phrase: str, width: int = EXCERPT_CHARS) -> str:
    """A window of ``text`` around the first occurrence of ``phrase``."""
    folded = unicodedata.normalize("NFKC", text)
    m = _phrase_regex(phrase).search(folded.lower())
    if not m:
        snippet = folded[:width]
    else:
        pad = max(0, (width - (m.end() - m.start())) // 2)
        start = max(0, m.start() - pad)
        snippet = folded[start : start + width]
    return " ".join(snippet.split()).replace("|", "\\|")


def _risk_key(row: dict) -> tuple:
    uncertain = any(ev.get("uncertain") for ev in row.get("evidence") or [])
    rank = 0 if uncertain else _RISK_ORDER.get(row["category"], 3)
    return (rank, row["id"])


def write_review(rows: list[dict], corpus: list[dict], path: Path) -> None:
    lines = [
        "# Gold-set draft review sheet",
        "",
        f"{len(rows)} draft items from `results/gold_set_draft.jsonl`, riskiest first: "
        "uncertain labels, then computed, cross-company, single-filing lookups/text, "
        "and unanswerable traps. Excerpts are windows of at most "
        f"{EXCERPT_CHARS} characters around each label's first phrase "
        f"(up to {MAX_EXCERPTS_PER_LABEL} matching chunks per label; the total match count "
        "is shown). Regenerate with `python scripts/check_gold_draft.py --review "
        "results/goldset_review.md`.",
        "",
        "Reviewer checklist: the number or claim in the gold answer appears in the excerpt for "
        "the right period/column; computed items' arithmetic in Notes is right; trap notes show "
        "the filing really cannot answer. Mark OK / FIX in the box.",
        "",
        'To promote: set `"status": "approved"` on each OK row in '
        "`results/gold_set_draft.jsonl` (fix or delete FIX rows), then run "
        "`python scripts/check_gold_draft.py`, `python scripts/make_gold_set.py`, "
        "`python scripts/make_retrieval_fixture.py`, and `python scripts/eval_retrieval.py "
        "--write-thresholds results/retrieval_thresholds.json`.",
        "",
    ]
    for row in sorted(rows, key=_risk_key):
        flag = " (UNCERTAIN LABEL)" if _risk_key(row)[0] == 0 else ""
        lines += [
            f"## {row['id']} - {row['category']} - {row['difficulty']}{flag}",
            "",
            f"- [ ] **Q:** {row['question']}",
            f"- **Tickers:** {', '.join(row['gold_tickers']) or '-'}",
        ]
        if row["answerable"]:
            lines.append(f"- **Gold answer:** {row['gold_answer']}")
            if row.get("notes"):
                lines.append(f"- **Notes:** {row['notes']}")
            for i, (ev, hits) in enumerate(label_matches(row, corpus), 1):
                status = "verified" if ev.get("verified") else "UNVERIFIED"
                if ev.get("uncertain"):
                    status += ", uncertain"
                phrases = " + ".join(f"`{p}`" for p in ev["must_contain"])
                lines.append(
                    f"- **Label {i}** ({ev['ticker']}, {status}, {len(hits)} matching chunk(s)): {phrases}"
                )
                if ev.get("note"):
                    lines.append(f"  - note: {ev['note']}")
                for c in hits[:MAX_EXCERPTS_PER_LABEL]:
                    lines.append(
                        f'  - `{c["chunk_id"]}`: "{excerpt(c["text"], ev["must_contain"][0])}"'
                    )
        else:
            lines.append("- **Gold answer:** (unanswerable - model should refuse)")
            lines.append(f"- **Search notes:** {row['notes']}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--draft", type=Path, default=DRAFT_PATH)
    ap.add_argument("--review", type=Path, default=None, help="write a Markdown review sheet")
    args = ap.parse_args(argv)

    rows = load_draft(args.draft)
    existing = {it.id for it in load_gold_set()}
    problems = schema_problems(rows, existing)

    corpus = load_corpus()
    n_labels = 0
    for row in rows:
        for ev, hits in label_matches(row, corpus):
            n_labels += 1
            if not hits:
                problems.append(f"{row['id']}: label matches no chunk: {ev['must_contain']}")

    for p in problems:
        print("PROBLEM", p)
    n_ans = sum(r["answerable"] for r in rows)
    print(
        f"{len(rows)} draft items ({n_ans} answerable, {len(rows) - n_ans} traps), {n_labels} labels"
    )
    if args.review:
        write_review(rows, corpus, args.review)
        print(f"wrote {args.review}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
