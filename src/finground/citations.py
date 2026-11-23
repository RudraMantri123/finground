"""Citation and refusal parsing shared by the answerer, the metrics and the CI gate.

Pure string handling with no heavy imports (no FAISS / torch), so the
faithfulness regression gate can parse committed answers in a CI job that
installs nothing but the package itself.
"""

from __future__ import annotations

import re

REFUSAL = "Not answerable from the provided filings."

_CITATION_RE = re.compile(r"\[([^\]]*?C\d+[^\]]*?)\]")
_LABEL_RE = re.compile(r"C(\d+)")

# Semantic-abstention markers. Models (especially small local ones) often
# refuse in their own words instead of echoing the exact REFUSAL sentence;
# an answer *opening* with one of these is an abstention in substance and must
# be scored as one. Checked only against the start of the answer so that
# ordinary answers which merely *mention* missing info later are not caught.
_REFUSAL_PATTERNS = (
    "not answerable from the provided filings",
    "not applicable",
    "cannot be answered",
    "cannot answer",
    "can't answer",
    "unable to answer",
    "do not contain enough information",
    "does not contain enough information",
    "do not contain information",
    "does not contain information",
    "not possible to answer",
    "no information in the provided excerpts",
    "the provided excerpts do not",
    "the excerpts do not",
)


def extract_cited_labels(answer_text: str) -> list[str]:
    """Return the ordered, de-duplicated ``C#`` labels cited in the answer."""
    labels: list[str] = []
    for group in _CITATION_RE.findall(answer_text):
        for num in _LABEL_RE.findall(group):
            label = f"C{num}"
            if label not in labels:
                labels.append(label)
    return labels


def strip_citations(text: str) -> str:
    """Remove ``[C1]`` / ``[C2, C3]`` groups (so their digits are not read as figures)."""
    return _CITATION_RE.sub(" ", text)


def is_refusal(answer_text: str) -> bool:
    """True if the answer is an abstention — canonical or in the model's own words."""
    head = answer_text.strip().lower()[:160]
    return any(p in head for p in _REFUSAL_PATTERNS)
