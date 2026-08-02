"""Unit tests for the metric math (no LLM calls)."""

from __future__ import annotations

import math

from finground.eval.metrics import (
    answer_correctness_auto,
    citation_accuracy,
    faithfulness,
    hallucination_rate,
    mean_ignoring_none,
    numbers_in,
    numeric_match,
    refusal_calibration,
    token_f1,
)

# -- correctness helpers ----------------------------------------------------


def test_token_f1_exact_and_disjoint():
    assert token_f1("net revenue increased", "net revenue increased") == 1.0
    assert token_f1("apples oranges", "cars planes") == 0.0


def test_token_f1_partial():
    score = token_f1(
        "Apple relies on outsourced manufacturing in Asia",
        "Apple relies on manufacturing partners in Asia",
    )
    assert 0.5 < score < 1.0


def test_numbers_in_and_numeric_match():
    assert numbers_in("Revenue was $12,345.6 million, up 7%") == {"12345.6", "7"}
    assert numeric_match("grew 7%", "growth of 7%") == 1.0
    assert numeric_match("grew 5%", "growth of 7%") == 0.0
    assert numeric_match("no numbers here", "also none") == 1.0  # vacuously true


def test_answer_correctness_blend():
    # identical text with the same number -> near 1.0
    s = answer_correctness_auto(
        "revenue rose 7% to $391 billion", "revenue rose 7% to $391 billion"
    )
    assert s > 0.95
    assert answer_correctness_auto("anything", "") == 0.0


# -- citation accuracy ------------------------------------------------------


def test_citation_accuracy():
    assert citation_accuracy([True, True, False, True]) == 0.75
    assert citation_accuracy([True, True]) == 1.0
    assert citation_accuracy([]) is None  # undefined with no citations


# -- faithfulness / hallucination ------------------------------------------


def test_faithfulness_and_hallucination_complement():
    supports = [True, True, True, False]
    f = faithfulness(supports)
    h = hallucination_rate(supports)
    assert f == 0.75
    assert h == 0.25
    assert math.isclose(f + h, 1.0)


def test_faithfulness_empty():
    assert faithfulness([]) is None
    assert hallucination_rate([]) is None


# -- refusal calibration ----------------------------------------------------


def test_refusal_calibration_confusion_and_balanced_accuracy():
    # (should_answer, did_answer)
    decisions = [
        (True, True),  # true_answer
        (True, True),  # true_answer
        (True, False),  # false_refuse (over-refusal)
        (False, False),  # true_refuse
        (False, True),  # false_answer (hallucination risk)
    ]
    stats = refusal_calibration(decisions)
    assert stats.true_answer == 2
    assert stats.false_refuse == 1
    assert stats.true_refuse == 1
    assert stats.false_answer == 1
    assert stats.total == 5
    assert math.isclose(stats.answer_recall, 2 / 3)
    assert math.isclose(stats.refusal_recall, 1 / 2)
    # balanced accuracy = mean(2/3, 1/2)
    assert math.isclose(stats.calibration, (2 / 3 + 1 / 2) / 2)


def test_refusal_calibration_all_answered_is_not_perfect():
    # A model that always answers gets perfect answer_recall but 0 refusal_recall.
    decisions = [(True, True), (False, True), (False, True)]
    stats = refusal_calibration(decisions)
    assert stats.answer_recall == 1.0
    assert stats.refusal_recall == 0.0
    assert stats.calibration == 0.5  # balanced accuracy punishes the always-answer strategy


# -- aggregation ------------------------------------------------------------


def test_mean_ignoring_none():
    assert mean_ignoring_none([1.0, None, 0.0]) == 0.5
    assert mean_ignoring_none([None, None]) is None
