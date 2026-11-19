"""Unit tests for evidence-label relevance and retrieval metrics (tiny synthetic data)."""

from __future__ import annotations

import math

import pytest

from finground.eval.retrieval_metrics import (
    EvidenceLabel,
    label_hits,
    macro_average,
    metric_names,
    mrr_at_k,
    ndcg_at_k,
    normalize_for_match,
    paired_bootstrap,
    parse_labels,
    question_metrics,
    recall_at_k,
    unreachable_labels,
)


def _c(ticker, text, section="Item 1A. Risk Factors"):
    return {"ticker": ticker, "section": section, "text": text}


# -- normalisation + matching ------------------------------------------------


def test_normalize_strips_markdown_tables_quotes_and_whitespace():
    md = "| Segment | Revenue |\n|---|---:|\n| AWS   | $ 107,556 |"
    assert normalize_for_match(md) == " segment revenue aws 107 556 "
    assert normalize_for_match("the Company’s  supply chain") == " the company s supply chain "


def test_label_matches_across_rechunked_markdown_table():
    lab = EvidenceLabel("AMZN", ("AWS 107,556",))
    prose = _c("AMZN", "Net sales: AWS 107,556 in 2024.")
    table = _c("AMZN", "| Segment | 2024 |\n|---|---|\n| **AWS** | 107,556 |")
    assert lab.matches(prose)
    assert lab.matches(table)


def test_label_requires_ticker_all_phrases_and_token_boundaries():
    lab = EvidenceLabel("AAPL", ("single or limited sources", "pricing risks"))
    assert lab.matches(_c("AAPL", "Single or limited sources... significant pricing risks."))
    assert not lab.matches(_c("MSFT", "single or limited sources and pricing risks"))
    assert not lab.matches(_c("AAPL", "single or limited sources only"))
    # "70%" must not match inside "1970".
    assert not EvidenceLabel("X", ("70%",)).matches(_c("X", "founded in 1970"))
    assert EvidenceLabel("X", ("70%",)).matches(_c("X", "more than 70 % of revenue"))


def test_section_is_an_optional_prefix_filter():
    lab = EvidenceLabel("KO", ("obesity",), section="Item 1A")
    assert lab.matches(_c("KO", "obesity concerns", section="Item 1A. Risk Factors"))
    assert not lab.matches(_c("KO", "obesity concerns", section="Item 7. MD&A"))


def test_parse_labels_ignores_review_metadata_and_rejects_empty():
    labs = parse_labels(
        [{"ticker": "T", "must_contain": ["a b"], "verified": True, "note": "x", "uncertain": True}]
    )
    assert labs == [EvidenceLabel("T", ("a b",))]
    with pytest.raises(ValueError):
        parse_labels([{"ticker": "T", "must_contain": []}])


def test_unreachable_labels():
    labs = [EvidenceLabel("T", ("alpha",)), EvidenceLabel("T", ("omega",))]
    corpus = [_c("T", "alpha beta"), _c("U", "omega")]
    assert unreachable_labels(labs, corpus) == [labs[1]]


# -- metrics -----------------------------------------------------------------

# Two labels; ranks: 1 irrelevant, 2 covers label 0, 3 covers label 0 again,
# 4 covers label 1.
LABELS = [EvidenceLabel("T", ("fact one",)), EvidenceLabel("T", ("fact two",))]
RANKED = [
    _c("T", "noise"),
    _c("T", "fact one here"),
    _c("T", "fact one repeated"),
    _c("T", "and fact two"),
]


def test_label_hits():
    assert label_hits(RANKED, LABELS) == [set(), {0}, {0}, {1}]


def test_recall_is_label_level():
    hits = label_hits(RANKED, LABELS)
    assert recall_at_k(hits, 2, 1) == 0.0
    assert recall_at_k(hits, 2, 2) == 0.5
    assert recall_at_k(hits, 2, 3) == 0.5  # a duplicate of label 0 adds nothing
    assert recall_at_k(hits, 2, 10) == 1.0
    assert recall_at_k([], 2, 5) == 0.0
    with pytest.raises(ValueError):
        recall_at_k(hits, 0, 5)


def test_mrr():
    hits = label_hits(RANKED, LABELS)
    assert mrr_at_k(hits, 10) == 0.5
    assert mrr_at_k(hits, 1) == 0.0
    assert mrr_at_k([{0}], 10) == 1.0


def test_ndcg_credits_each_label_once():
    hits = label_hits(RANKED, LABELS)
    dcg = 1 / math.log2(3) + 1 / math.log2(5)
    idcg = 1 / math.log2(2) + 1 / math.log2(3)
    assert ndcg_at_k(hits, 2, 10) == pytest.approx(dcg / idcg)
    # Perfect ranking -> 1.0; nothing relevant -> 0.0.
    assert ndcg_at_k([{0}, {1}], 2, 10) == pytest.approx(1.0)
    assert ndcg_at_k([set(), set()], 2, 10) == 0.0
    # One (large) chunk covering both labels at rank 1 is also perfect: capped at 1.0.
    assert ndcg_at_k([{0, 1}], 2, 10) == 1.0


def test_question_metrics_and_macro_average():
    hits = label_hits(RANKED, LABELS)
    m = question_metrics(hits, 2, ks=(1, 5), cutoff=10)
    assert list(m) == ["recall@1", "recall@5", "mrr@10", "ndcg@10"]
    assert metric_names((1, 5), 10) == list(m)
    avg = macro_average([{"a": 1.0}, {"a": 0.0}])
    assert avg == {"a": 0.5}
    assert macro_average([]) == {}


def test_paired_bootstrap_is_deterministic_and_brackets_mean():
    a = [1.0, 0.5, 1.0, 0.0, 1.0]
    b = [0.5, 0.5, 0.0, 0.0, 1.0]
    d1 = paired_bootstrap(a, b, n_resamples=500, seed=1)
    d2 = paired_bootstrap(a, b, n_resamples=500, seed=1)
    assert d1 == d2
    mean, lo, hi = d1
    assert mean == pytest.approx(0.3)
    assert lo <= mean <= hi
    with pytest.raises(ValueError):
        paired_bootstrap([1.0], [])
