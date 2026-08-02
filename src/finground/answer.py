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

from .config import CONFIG
from .llm import LLMClient, LLMResponse
from .retrieve import RetrievedChunk, best_dense_sim, retrieve

REFUSAL = "Not answerable from the provided filings."

SYSTEM_PROMPT = (
    "You are a meticulous financial analyst assistant. You answer questions about "
    "SEC filings using ONLY the provided excerpts.\n\n"
    "Rules:\n"
    "1. Use only information contained in the excerpts. Never use outside knowledge.\n"
    "2. Support every factual claim with an inline citation to the excerpt(s) that "
    "back it, using bracket labels like [C1] or [C2, C3].\n"
    "3. If the excerpts do not contain enough information to answer the question, "
    f"respond with exactly this sentence and nothing else: {REFUSAL}\n"
    "4. Prefer abstaining over guessing. Do not speculate.\n"
    "5. Be concise and precise; quote figures exactly as written in the excerpts."
)

_CITATION_RE = re.compile(r"\[([^\]]*?C\d+[^\]]*?)\]")
_LABEL_RE = re.compile(r"C(\d+)")


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
    normalized = answer_text.strip().lower().rstrip(".")
    return normalized.startswith("not answerable from the provided filings")


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
    evidence = best_dense_sim(retrieved)

    # Hard evidence gate: too weak to answer -> abstain without spending tokens.
    if not retrieved or evidence < CONFIG.retrieval.min_dense_sim:
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

    user_prompt = f"Question: {question}\n\nExcerpts:\n{_format_excerpts(retrieved)}"
    client = LLMClient(model, temperature=temperature, use_cache=use_cache)
    resp: LLMResponse = client.complete(SYSTEM_PROMPT, user_prompt)

    abstained = is_refusal(resp.text)
    cited_labels = [] if abstained else extract_cited_labels(resp.text)
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
        answer=resp.text.strip(),
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
    )
