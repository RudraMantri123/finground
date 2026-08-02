"""LLM-as-judge: score answers where automatic metrics are insufficient.

A single structured call per answered question yields everything the metrics
need:

* **claims** — the answer decomposed into atomic factual claims, each labeled
  supported / unsupported by the *cited* excerpts (feeds faithfulness).
* **citations** — each cited excerpt labeled as genuinely supporting the answer
  or not (feeds citation accuracy).
* **correct** — whether the answer matches the gold answer in meaning (feeds
  correctness), when a gold answer is provided.

Refusals are not sent to the judge — correctness/faithfulness are undefined for
an abstention; those are handled by refusal calibration instead.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

from ..config import CONFIG
from ..llm import LLMClient

JUDGE_SYSTEM = (
    "You are a strict, literal evaluation judge for a financial question-answering "
    "system. You assess whether an answer is grounded in the excerpts it cites and "
    "whether it matches a reference answer. You never use outside knowledge; an "
    "excerpt 'supports' a claim only if the claim can be verified from the excerpt "
    "text alone. Respond with a single JSON object and nothing else."
)

_JUDGE_TEMPLATE = """\
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


@dataclass
class Judgment:
    correct: bool | None
    reason: str = ""
    claims: list[dict] = field(default_factory=list)  # {claim, supported}
    citations: list[dict] = field(default_factory=list)  # {label, supports}
    judged: bool = True  # False when skipped (e.g. refusal)
    error: str | None = None

    # convenience views used by the metrics layer
    @property
    def claim_supports(self) -> list[bool]:
        return [bool(c.get("supported")) for c in self.claims]

    @property
    def citation_supports(self) -> list[bool]:
        return [bool(c.get("supports")) for c in self.citations]

    def to_json(self) -> dict:
        return {
            "correct": self.correct,
            "reason": self.reason,
            "claims": self.claims,
            "citations": self.citations,
            "judged": self.judged,
            "error": self.error,
        }


def _extract_json(text: str) -> dict:
    """Best-effort extraction of the first JSON object in a model response."""
    text = text.strip()
    # Strip code fences if present.
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    start = text.find("{")
    if start == -1:
        raise ValueError("no JSON object found")
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start : i + 1])
    raise ValueError("unbalanced JSON braces")


def _format_excerpts(citations: list[dict]) -> str:
    if not citations:
        return "(no excerpts were cited)"
    return "\n\n".join(
        f"[{c['label']}] ({c.get('provenance', '')})\n{c['text']}" for c in citations
    )


def judge_answer(
    *,
    question: str,
    answer: str,
    citations: list[dict],
    abstained: bool,
    gold_answer: str = "",
    model: str | None = None,
    use_cache: bool = True,
) -> Judgment:
    """Judge one answered question. Refusals are returned unjudged."""
    if abstained:
        return Judgment(correct=None, judged=False, reason="abstained")

    model = model or CONFIG.models.judge
    if gold_answer:
        gold_block = f"Reference (gold) answer:\n{gold_answer}\n\n"
        correct_instruction = (
            "set true iff the candidate answer conveys the same essential facts as "
            "the reference answer (paraphrase is fine; contradictions or missing key "
            "figures are incorrect)."
        )
    else:
        gold_block = ""
        correct_instruction = (
            "no reference answer is provided; set true iff the answer is fully "
            "supported by the cited excerpts (self-consistent grounding)."
        )

    prompt = _JUDGE_TEMPLATE.format(
        question=question,
        gold_block=gold_block,
        answer=answer,
        excerpts=_format_excerpts(citations),
        correct_instruction=correct_instruction,
    )

    client = LLMClient(model, temperature=0.0, use_cache=use_cache)
    resp = client.complete(JUDGE_SYSTEM, prompt, max_tokens=1200)
    try:
        data = _extract_json(resp.text)
    except Exception as exc:  # noqa: BLE001 — surface parse failure, don't crash the run
        return Judgment(
            correct=None, judged=True, error=f"judge parse error: {exc}", reason=resp.text[:200]
        )

    return Judgment(
        correct=(bool(data["correct"]) if data.get("correct") is not None else None),
        reason=str(data.get("reason", "")),
        claims=list(data.get("claims", [])),
        citations=list(data.get("citations", [])),
        judged=True,
    )
