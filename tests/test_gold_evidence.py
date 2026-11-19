"""Integrity checks tying the gold set's evidence labels to the committed fixture.

Cheap (no models): they catch a label typo, a gold-set edit that drops labels,
or a regenerated fixture that no longer contains some evidence, before the
slower retrieval eval would report it as a mysterious recall drop.
"""

from __future__ import annotations

import json

from finground.config import CONFIG
from finground.eval.datasets import load_gold_set
from finground.eval.retrieval_metrics import parse_labels, unreachable_labels

FIXTURE = CONFIG.paths.root / "tests" / "fixtures" / "retrieval_corpus.jsonl"


def test_answerable_items_have_evidence_and_unanswerable_do_not():
    for item in load_gold_set():
        if item.answerable:
            assert item.evidence, f"{item.id} has no evidence labels"
            for lab in parse_labels(item.evidence):
                assert lab.ticker in item.gold_tickers, f"{item.id}: {lab.ticker}"
        else:
            assert not item.evidence, f"{item.id} is unanswerable but has evidence"


def test_every_label_is_reachable_in_the_fixture():
    with open(FIXTURE, encoding="utf-8") as fh:
        corpus = [json.loads(line) for line in fh if line.strip()]
    for item in load_gold_set():
        missing = unreachable_labels(parse_labels(item.evidence), corpus)
        assert not missing, f"{item.id}: {[lab.must_contain for lab in missing]}"
