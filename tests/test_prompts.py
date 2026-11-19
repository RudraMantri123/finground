"""Prompt files must reproduce the pre-versioning prompts byte-for-byte.

The LLM response cache is keyed on the exact system + user text, so any drift
(a stray newline, a re-wrapped sentence) would silently miss every cached
response and change benchmark numbers. The constants below are frozen copies
of the prompts as they were hard-coded before moving to ``prompts/*.v1.toml``.
"""

from __future__ import annotations

import pytest

import finground.answer as A
import finground.eval.judge as J
from finground.prompts import answer_prompt, judge_prompt, load_prompt

_REFUSAL = "Not answerable from the provided filings."

_OLD_SYSTEM_PROMPT = (
    "You are a meticulous financial analyst assistant. You answer questions about "
    "SEC filings using ONLY the provided excerpts.\n\n"
    "Rules:\n"
    "1. Use only information contained in the excerpts. Never use outside knowledge.\n"
    "2. Support every factual claim with an inline citation to the excerpt(s) that "
    "back it, using bracket labels like [C1] or [C2, C3].\n"
    "3. If the excerpts do not contain enough information to answer the question, "
    f"respond with exactly this sentence and nothing else: {_REFUSAL}\n"
    "4. Prefer abstaining over guessing. Do not speculate.\n"
    "5. Be concise and precise; quote figures exactly as written in the excerpts."
)


def _old_user_prompt(excerpts: str, question: str) -> str:
    return (
        f"Excerpts from SEC filings:\n\n{excerpts}\n\n"
        f"---\n"
        f"Question: {question}\n\n"
        f"Answer the question using ONLY the excerpts above. Cite the excerpt(s) "
        f"supporting each claim inline with their bracket labels, e.g. [C1] or "
        f"[C2, C3]. If the excerpts do not contain the answer, reply exactly: "
        f"{_REFUSAL}"
    )


_OLD_JUDGE_SYSTEM = (
    "You are a strict, literal evaluation judge for a financial question-answering "
    "system. You assess whether an answer is grounded in the excerpts it cites and "
    "whether it matches a reference answer. You never use outside knowledge; an "
    "excerpt 'supports' a claim only if the claim can be verified from the excerpt "
    "text alone. Respond with a single JSON object and nothing else."
)

_OLD_JUDGE_TEMPLATE = """\
Question:
{question}

{gold_block}Candidate answer:
{answer}

Cited excerpts (only these may support the answer):
{excerpts}

Do the following and return ONE JSON object:
1. "claims": break the candidate answer into a list of atomic factual claims.
   For each, set "supported" true iff the claim is verifiable from AT LEAST ONE
   cited excerpt above. Ignore hedging/meta sentences.
2. "citations": for each cited excerpt label, set "supports" true iff that
   excerpt genuinely supports at least one claim in the answer.
3. "correct": {correct_instruction}

JSON schema:
{{"claims": [{{"claim": "...", "supported": true}}],
  "citations": [{{"label": "C1", "supports": true}}],
  "correct": true,
  "reason": "one short sentence"}}
"""


def test_answer_v1_is_byte_identical():
    p = load_prompt("answer", "v1")
    assert p.id == "answer.v1"
    assert A.REFUSAL == _REFUSAL
    assert p.system.format(refusal=_REFUSAL) == _OLD_SYSTEM_PROMPT
    assert A.SYSTEM_PROMPT == _OLD_SYSTEM_PROMPT
    # Excerpts/questions with braces must pass through untouched.
    excerpts = "[C1] (AAPL 10-K | Item 7)\n| Net sales | $416,161 |\n{not a field}"
    question = "What was net sales {in 2025}?"
    rendered = p.user.format(excerpts=excerpts, question=question, refusal=_REFUSAL)
    assert rendered == _old_user_prompt(excerpts, question)


def test_judge_v1_is_byte_identical():
    p = load_prompt("judge", "v1")
    assert p.id == "judge.v1"
    assert p.system == _OLD_JUDGE_SYSTEM
    assert p.user == _OLD_JUDGE_TEMPLATE
    assert J.JUDGE_SYSTEM == _OLD_JUDGE_SYSTEM
    assert J._JUDGE_TEMPLATE == _OLD_JUDGE_TEMPLATE


def test_defaults_are_v1():
    assert answer_prompt().id == "answer.v1"
    assert judge_prompt().id == "judge.v1"


def test_unknown_version_lists_available():
    with pytest.raises(FileNotFoundError, match="answer.v1.toml"):
        load_prompt("answer", "v999")


def test_answer_records_prompt_version(monkeypatch):
    from finground.llm import LLMResponse
    from finground.retrieve import RetrievedChunk

    chunk = RetrievedChunk(
        label="C1",
        chunk_id="AAPL-1",
        doc_id="AAPL-10-K-acc",
        company="Apple Inc.",
        ticker="AAPL",
        section="Item 7",
        filing_type="10-K",
        filing_date="2025-10-31",
        text="Net sales were $416,161 million.",
        rrf_score=0.03,
        dense_score=0.8,
        bm25_score=1.0,
        span=(0, 10),
    )
    seen = {}

    class _Client:
        def __init__(self, model_spec, **kwargs):
            self.model_spec = model_spec

        def complete(self, system, user, **kwargs):
            seen["system"], seen["user"] = system, user
            return LLMResponse("Net sales were $416,161 million [C1].", self.model_spec, 1, 1, 0.1)

    monkeypatch.setattr(A, "retrieve", lambda q, top_k=None: [chunk])
    monkeypatch.setattr(A, "LLMClient", _Client)
    ans = A.answer_question("What were net sales?", model="openai:gpt-4o-mini")
    assert ans.prompt_version == "answer.v1"
    assert seen["system"] == _OLD_SYSTEM_PROMPT
    assert seen["user"] == _old_user_prompt(A._format_excerpts([chunk]), "What were net sales?")
