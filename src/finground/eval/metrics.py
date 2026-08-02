"""The four FinGround metrics, as pure functions over already-derived labels.

Keeping the math side-effect-free (no LLM calls here) makes it unit-testable.
LLM-derived labels (is an answer correct? is a claim supported?) come from
``judge.py``; this module turns those labels into scores.

1. **Answer correctness** — right vs gold. ``answer_correctness_auto`` gives a
   cheap lexical proxy; the judge gives the authoritative binary label.
2. **Citation accuracy** — fraction of *cited* chunks that actually support the
   answer.
3. **Faithfulness / hallucination** — fraction of answer claims supported by
   the cited evidence (hallucination = 1 - faithfulness).
4. **Refusal calibration** — does the system abstain iff it should? Scored as
   balanced accuracy over the answer/abstain decision, with the full confusion
   matrix exposed.
"""

from __future__ import annotations

import re
import string
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# 1. Answer correctness (automatic lexical proxy)
# ---------------------------------------------------------------------------

_ARTICLES = {"a", "an", "the"}
_NUM_RE = re.compile(r"-?\$?\d[\d,]*\.?\d*%?")


def normalize_text(s: str) -> str:
    """Lowercase, strip punctuation and articles, collapse whitespace (SQuAD-style)."""
    s = s.lower()
    s = "".join(ch if ch not in string.punctuation else " " for ch in s)
    tokens = [t for t in s.split() if t not in _ARTICLES]
    return " ".join(tokens)


def token_f1(pred: str, gold: str) -> float:
    """SQuAD-style token-overlap F1 between prediction and gold."""
    pred_toks = normalize_text(pred).split()
    gold_toks = normalize_text(gold).split()
    if not pred_toks and not gold_toks:
        return 1.0
    if not pred_toks or not gold_toks:
        return 0.0
    gold_counts: dict[str, int] = {}
    for t in gold_toks:
        gold_counts[t] = gold_counts.get(t, 0) + 1
    overlap = 0
    seen: dict[str, int] = {}
    for t in pred_toks:
        seen[t] = seen.get(t, 0) + 1
        if seen[t] <= gold_counts.get(t, 0):
            overlap += 1
    if overlap == 0:
        return 0.0
    precision = overlap / len(pred_toks)
    recall = overlap / len(gold_toks)
    return 2 * precision * recall / (precision + recall)


def numbers_in(text: str) -> set[str]:
    """Extract normalized numeric tokens (money/percent/plain) from text."""
    out = set()
    for m in _NUM_RE.findall(text or ""):
        norm = m.replace(",", "").replace("$", "").rstrip("%")
        if norm not in {"", "-", "."}:
            out.add(norm)
    return out


def numeric_match(pred: str, gold: str) -> float:
    """Recall of gold numbers appearing in the prediction (1.0 if gold has none)."""
    gold_nums = numbers_in(gold)
    if not gold_nums:
        return 1.0
    pred_nums = numbers_in(pred)
    return len(gold_nums & pred_nums) / len(gold_nums)


def answer_correctness_auto(pred: str, gold: str) -> float:
    """Cheap correctness proxy: blend token-F1 with gold-number recall."""
    if not gold:
        return 0.0
    return 0.6 * token_f1(pred, gold) + 0.4 * numeric_match(pred, gold)


# ---------------------------------------------------------------------------
# 2. Citation accuracy
# ---------------------------------------------------------------------------


def citation_accuracy(citation_supports: list[bool]) -> float | None:
    """Fraction of cited chunks that actually support the answer.

    ``citation_supports[i]`` is True if cited chunk *i* genuinely supports a
    claim in the answer. Returns None when there are no citations (undefined).
    """
    if not citation_supports:
        return None
    return sum(1 for s in citation_supports if s) / len(citation_supports)


# ---------------------------------------------------------------------------
# 3. Faithfulness / hallucination
# ---------------------------------------------------------------------------


def faithfulness(claim_supports: list[bool]) -> float | None:
    """Fraction of answer claims supported by the cited evidence."""
    if not claim_supports:
        return None
    return sum(1 for s in claim_supports if s) / len(claim_supports)


def hallucination_rate(claim_supports: list[bool]) -> float | None:
    """1 - faithfulness. None when there are no claims to score."""
    f = faithfulness(claim_supports)
    return None if f is None else 1.0 - f


# ---------------------------------------------------------------------------
# 4. Refusal calibration
# ---------------------------------------------------------------------------


@dataclass
class RefusalStats:
    # rows: (should_answer, did_answer)
    true_answer: int = 0  # answerable & answered      (correct)
    false_refuse: int = 0  # answerable & abstained     (over-refusal)
    true_refuse: int = 0  # unanswerable & abstained   (correct)
    false_answer: int = 0  # unanswerable & answered    (hallucination risk)

    @property
    def total(self) -> int:
        return self.true_answer + self.false_refuse + self.true_refuse + self.false_answer

    @property
    def answer_recall(self) -> float | None:
        """Of the answerable questions, how many were answered."""
        denom = self.true_answer + self.false_refuse
        return self.true_answer / denom if denom else None

    @property
    def refusal_recall(self) -> float | None:
        """Of the unanswerable questions, how many were (correctly) refused."""
        denom = self.true_refuse + self.false_answer
        return self.true_refuse / denom if denom else None

    @property
    def calibration(self) -> float:
        """Balanced accuracy over the answer/abstain decision.

        Averages answer-recall and refusal-recall so a model cannot score well
        by always answering (or always refusing). If only one class is present,
        falls back to plain accuracy on that class.
        """
        parts = [r for r in (self.answer_recall, self.refusal_recall) if r is not None]
        return sum(parts) / len(parts) if parts else 0.0

    def to_json(self) -> dict:
        return {
            "true_answer": self.true_answer,
            "false_refuse": self.false_refuse,
            "true_refuse": self.true_refuse,
            "false_answer": self.false_answer,
            "answer_recall": self.answer_recall,
            "refusal_recall": self.refusal_recall,
            "calibration": self.calibration,
            "total": self.total,
        }


def refusal_calibration(decisions: list[tuple[bool, bool]]) -> RefusalStats:
    """Build refusal stats from ``(should_answer, did_answer)`` pairs."""
    stats = RefusalStats()
    for should_answer, did_answer in decisions:
        if should_answer and did_answer:
            stats.true_answer += 1
        elif should_answer and not did_answer:
            stats.false_refuse += 1
        elif not should_answer and not did_answer:
            stats.true_refuse += 1
        else:
            stats.false_answer += 1
    return stats


# ---------------------------------------------------------------------------
# Aggregation helper
# ---------------------------------------------------------------------------


def mean_ignoring_none(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    return sum(present) / len(present) if present else None
