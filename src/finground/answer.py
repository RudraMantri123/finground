"""Cited answering with evidence-gated refusal.

Given a question, retrieve supporting chunks, then ask the LLM to answer using
*only* those chunks, citing them inline as ``[C1]``, ``[C2, C3]``, etc. If the
retrieved evidence is too weak (dense similarity below threshold), we abstain
*without* calling the LLM. The model is also instructed to abstain when the
excerpts do not support an answer.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field

from . import tracing
from .config import CONFIG
from .llm import LLMClient, LLMResponse
from .prompts import answer_prompt
from .retrieve import RetrievedChunk, best_dense_sim, retrieve

REFUSAL = "Not answerable from the provided filings."

# The prompt text lives in prompts/answer.<version>.toml (see prompts.py).
# Kept as a module attribute for callers that import it; it reflects the
# version active at import time.
SYSTEM_PROMPT = answer_prompt().system.format(refusal=REFUSAL)

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


@dataclass
class Answer:
    question: str
    answer: str
    abstained: bool
    citations: list[dict]  # cited chunks that actually appear in the answer
    retrieved: list[dict]  # all retrieved chunks with scores (for eval)
    model: str
    best_dense_sim: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_s: float = 0.0
    cost_usd: float | None = None
    cached: bool = False
    prompt_version: str = ""  # e.g. "answer.v1"; empty when gated before prompting
    meta: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        return asdict(self)


def _format_excerpts(chunks: list[RetrievedChunk]) -> str:
    blocks = []
    for c in chunks:
        header = f"[{c.label}] ({c.provenance()})"
        blocks.append(f"{header}\n{c.text}")
    return "\n\n".join(blocks)


def extract_cited_labels(answer_text: str) -> list[str]:
    """Return the ordered, de-duplicated ``C#`` labels cited in the answer."""
    labels: list[str] = []
    for group in _CITATION_RE.findall(answer_text):
        for num in _LABEL_RE.findall(group):
            label = f"C{num}"
            if label not in labels:
                labels.append(label)
    return labels


def is_refusal(answer_text: str) -> bool:
    """True if the answer is an abstention — canonical or in the model's own words."""
    head = answer_text.strip().lower()[:160]
    return any(p in head for p in _REFUSAL_PATTERNS)


def answer_question(
    question: str,
    *,
    model: str | None = None,
    top_k: int | None = None,
    temperature: float = 0.0,
    use_cache: bool = True,
) -> Answer:
    """Retrieve, then produce a cited answer or an evidence-gated refusal."""
    model = model or CONFIG.models.answer
    retrieved = retrieve(question, top_k=top_k)
    retrieved_json = [
        {
            "label": r.label,
            "chunk_id": r.chunk_id,
            "provenance": r.provenance(),
            "ticker": r.ticker,
            "section": r.section,
            "filing_date": r.filing_date,
            "dense_score": r.dense_score,
            "bm25_score": r.bm25_score,
            "rrf_score": r.rrf_score,
            "text": r.text,
        }
        for r in retrieved
    ]
    t_gate = tracing.now()
    evidence = best_dense_sim(retrieved)
    gated = not retrieved or evidence < CONFIG.retrieval.min_dense_sim
    tracing.record_span(
        "evidence_gate",
        t_gate,
        best_dense_sim=evidence,
        threshold=CONFIG.retrieval.min_dense_sim,
        passed=not gated,
    )

    # Hard evidence gate: too weak to answer -> abstain without spending tokens.
    if gated:
        return Answer(
            question=question,
            answer=REFUSAL,
            abstained=True,
            citations=[],
            retrieved=retrieved_json,
            model=model,
            best_dense_sim=evidence,
            meta={"gate": "evidence_below_threshold", "threshold": CONFIG.retrieval.min_dense_sim},
        )

    # Excerpts first, question and rules last: models (small ones especially)
    # attend most to the end of the prompt, and a long excerpt block placed
    # after the question tends to bury it.
    prompt = answer_prompt()
    user_prompt = prompt.user.format(
        excerpts=_format_excerpts(retrieved), question=question, refusal=REFUSAL
    )
    client = LLMClient(model, temperature=temperature, use_cache=use_cache)
    resp: LLMResponse = client.complete(prompt.system.format(refusal=REFUSAL), user_prompt)

    # Small models sometimes append the refusal template after a complete,
    # cited answer (echoing the prompt's last instruction). Strip that dangling
    # boilerplate first — it is not a claim; a pure refusal strips to empty.
    answer_text = re.sub(
        rf"\s*{re.escape(REFUSAL.rstrip('.'))}\.?\s*$", "", resp.text.strip()
    ).strip()
    abstained = not answer_text or is_refusal(answer_text)
    if abstained:
        answer_text = REFUSAL
    cited_labels = [] if abstained else extract_cited_labels(answer_text)
    by_label = {r.label: r for r in retrieved}
    citations = [
        {
            "label": lbl,
            "chunk_id": by_label[lbl].chunk_id,
            "provenance": by_label[lbl].provenance(),
            "text": by_label[lbl].text,
        }
        for lbl in cited_labels
        if lbl in by_label
    ]

    return Answer(
        question=question,
        answer=answer_text,
        abstained=abstained,
        citations=citations,
        retrieved=retrieved_json,
        model=model,
        best_dense_sim=evidence,
        prompt_tokens=resp.prompt_tokens,
        completion_tokens=resp.completion_tokens,
        latency_s=resp.latency_s,
        cost_usd=resp.cost_usd,
        cached=resp.cached,
        prompt_version=prompt.id,
    )
