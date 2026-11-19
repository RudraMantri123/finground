"""Retrieval-quality metrics over *evidence labels* rather than chunk IDs.

Why evidence labels: chunk IDs are an artefact of the current chunker. Any
change to chunk size, overlap, or table rendering renumbers every chunk and
silently invalidates ID-based relevance judgements. Instead, each answerable
gold question carries a small list of evidence labels::

    {"ticker": "AAPL", "must_contain": ["single or limited sources"]}

A retrieved chunk *satisfies* a label when it comes from that ticker (and
section, if one is given) and contains every ``must_contain`` phrase after
normalisation. Normalisation reduces both sides to lowercase alphanumeric
tokens, so whitespace, curly quotes, bullets, and Markdown table pipes or
separator rows never decide relevance. Keep phrases short (well under the
chunk-overlap length) so at least one chunk always contains the whole phrase
regardless of where chunk boundaries fall.

Metrics are computed per question and macro-averaged:

* **recall@k** — fraction of the question's evidence labels satisfied by at
  least one of the top-k chunks. Label-level (not chunk-level) recall keeps the
  number comparable across chunkers: a fact split over three small chunks or
  held in one big chunk counts the same.
* **MRR@k** — reciprocal rank of the first chunk satisfying *any* label.
* **nDCG@k** — binary gain, credited once per label at the first rank that
  covers it (a second chunk repeating an already-covered fact adds nothing).
  The ideal ranking covers one new label per rank, so IDCG is over
  ``min(n_labels, k)`` positions; a single chunk covering several labels can
  beat that, so the score is capped at 1.0 (a perfect retrieval either way).

Everything here is pure (no I/O, no models) so it is unit-testable on tiny
synthetic data.
"""

from __future__ import annotations

import math
import random
import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

DEFAULT_KS: tuple[int, ...] = (1, 3, 5, 8, 10)
DEFAULT_RANK_CUTOFF = 10  # cutoff for MRR and nDCG

_NON_ALNUM_RE = re.compile(r"[^0-9a-z]+")


def normalize_for_match(text: str) -> str:
    """Reduce text to space-separated lowercase alphanumeric tokens.

    NFKC folds compatibility characters (non-breaking spaces, full-width
    digits); everything that is not a letter or digit (punctuation, Markdown
    ``|`` and ``---`` table syntax, bullets, quotes, ``$``) becomes a separator.
    The result is padded with single spaces so substring tests on padded
    phrases respect token boundaries ("70" does not match "1970").
    """
    text = unicodedata.normalize("NFKC", text).lower()
    tokens = _NON_ALNUM_RE.sub(" ", text).split()
    return " " + " ".join(tokens) + " " if tokens else " "


@dataclass(frozen=True)
class EvidenceLabel:
    """One required piece of evidence for a gold question."""

    ticker: str
    must_contain: tuple[str, ...]
    section: str | None = None  # optional prefix, e.g. "Item 1A"

    @classmethod
    def from_dict(cls, d: Mapping) -> EvidenceLabel:
        phrases = tuple(d.get("must_contain") or ())
        if not phrases:
            raise ValueError(f"evidence label needs at least one must_contain phrase: {d!r}")
        return cls(ticker=d["ticker"], must_contain=phrases, section=d.get("section") or None)

    def matches(self, chunk: Mapping) -> bool:
        """True when ``chunk`` (a dict with ticker/section/text) satisfies this label."""
        if chunk.get("ticker") != self.ticker:
            return False
        if self.section is not None:
            want = normalize_for_match(self.section).strip()
            have = normalize_for_match(chunk.get("section", "")).strip()
            if not have.startswith(want):
                return False
        text = normalize_for_match(chunk.get("text", ""))
        return all(normalize_for_match(p) in text for p in self.must_contain)


def parse_labels(evidence: Iterable[Mapping]) -> list[EvidenceLabel]:
    """Parse the gold set's ``evidence`` field into :class:`EvidenceLabel` objects."""
    return [EvidenceLabel.from_dict(e) for e in evidence]


def label_hits(ranked_chunks: Sequence[Mapping], labels: Sequence[EvidenceLabel]) -> list[set[int]]:
    """For each ranked chunk, the indices of the labels it satisfies."""
    return [{i for i, lab in enumerate(labels) if lab.matches(c)} for c in ranked_chunks]


def unreachable_labels(
    labels: Sequence[EvidenceLabel], corpus: Iterable[Mapping]
) -> list[EvidenceLabel]:
    """Labels that no chunk in ``corpus`` satisfies.

    An unreachable label caps recall below 1.0 for every retriever, so it is a
    labelling or chunking bug (e.g. a phrase split across a chunk boundary, or
    text dropped by a new parser) rather than a retrieval result.
    """
    remaining = list(labels)
    for chunk in corpus:
        remaining = [lab for lab in remaining if not lab.matches(chunk)]
        if not remaining:
            break
    return remaining


# ---------------------------------------------------------------------------
# Per-question metrics over precomputed hits
# ---------------------------------------------------------------------------


def recall_at_k(hits: Sequence[set[int]], n_labels: int, k: int) -> float:
    """Fraction of labels covered by the top-``k`` chunks."""
    if n_labels <= 0:
        raise ValueError("recall is undefined for a question with no evidence labels")
    covered: set[int] = set().union(*hits[:k]) if hits[:k] else set()
    return len(covered) / n_labels


def mrr_at_k(hits: Sequence[set[int]], k: int = DEFAULT_RANK_CUTOFF) -> float:
    """Reciprocal rank of the first relevant chunk within the top ``k`` (0 if none)."""
    for rank, h in enumerate(hits[:k], start=1):
        if h:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(hits: Sequence[set[int]], n_labels: int, k: int = DEFAULT_RANK_CUTOFF) -> float:
    """Label-novelty nDCG: gain 1 the first time each label is covered."""
    if n_labels <= 0:
        raise ValueError("nDCG is undefined for a question with no evidence labels")
    seen: set[int] = set()
    dcg = 0.0
    for rank, h in enumerate(hits[:k], start=1):
        new = h - seen
        if new:
            dcg += len(new) / math.log2(rank + 1)
            seen |= new
    idcg = sum(1.0 / math.log2(r + 1) for r in range(1, min(n_labels, k) + 1))
    return min(1.0, dcg / idcg)


def question_metrics(
    hits: Sequence[set[int]],
    n_labels: int,
    ks: Sequence[int] = DEFAULT_KS,
    cutoff: int = DEFAULT_RANK_CUTOFF,
) -> dict[str, float]:
    """All retrieval metrics for one question, keyed like ``recall@5``."""
    out = {f"recall@{k}": recall_at_k(hits, n_labels, k) for k in ks}
    out[f"mrr@{cutoff}"] = mrr_at_k(hits, cutoff)
    out[f"ndcg@{cutoff}"] = ndcg_at_k(hits, n_labels, cutoff)
    return out


def metric_names(ks: Sequence[int] = DEFAULT_KS, cutoff: int = DEFAULT_RANK_CUTOFF) -> list[str]:
    """Stable column order for tables and threshold files."""
    return [f"recall@{k}" for k in ks] + [f"mrr@{cutoff}", f"ndcg@{cutoff}"]


def macro_average(rows: Sequence[Mapping[str, float]]) -> dict[str, float]:
    """Mean of each metric across questions (every question weighted equally)."""
    if not rows:
        return {}
    keys = rows[0].keys()
    return {key: sum(r[key] for r in rows) / len(rows) for key in keys}


def paired_bootstrap(
    a: Sequence[float], b: Sequence[float], *, n_resamples: int = 5000, seed: int = 0
) -> tuple[float, float, float]:
    """Mean of ``a - b`` with a 95% percentile bootstrap interval over questions.

    Paired because both configurations answer the same questions; resampling
    questions (not chunks) is what tells us whether a gap would survive a
    different draw of questions. Seeded, so reports are reproducible.
    """
    if len(a) != len(b) or not a:
        raise ValueError("paired bootstrap needs two equal-length, non-empty sequences")
    diffs = [x - y for x, y in zip(a, b, strict=True)]
    n = len(diffs)
    rng = random.Random(seed)
    means = sorted(sum(rng.choices(diffs, k=n)) / n for _ in range(n_resamples))
    lo = means[int(0.025 * (n_resamples - 1))]
    hi = means[int(0.975 * (n_resamples - 1))]
    return sum(diffs) / n, lo, hi
