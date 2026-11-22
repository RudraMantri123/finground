#!/usr/bin/env python3
"""Author the human-label seed set for judge validation.

Each record is a SELF-CONTAINED example: a question, a reference (gold) answer,
a candidate answer, and the excerpt(s) that candidate cites — plus two human
judgments:

* ``human_correct``   — does the candidate match the gold answer in meaning?
* ``human_faithful``  — is every claim in the candidate supported by the CITED
  excerpts (i.e. no hallucination and no citation mismatch)?

``validate_judge.py`` runs the LLM judge on these same examples and reports
judge-vs-human agreement (Cohen's kappa). The examples span the failure modes
that matter: contradictions, wrong numbers, fabricated additions, and
correct-but-mis-cited answers (right content, wrong grounding).

Honesty note: these are author-adjudicated *seed* labels by a single annotator.
They are enough to demonstrate the validation protocol; a production benchmark
should expand them with multiple independent annotators. See README limitations.
"""

from __future__ import annotations

import json

from finground.config import CONFIG

OUT = CONFIG.paths.human_labels / "seed_labels.jsonl"

# Reusable excerpt snippets (paraphrased from typical 10-K disclosures).
E_AAPL_MFG = {
    "label": "C1",
    "provenance": "AAPL 10-K — Item 1A. Risk Factors",
    "text": (
        "Substantially all of the Company's hardware products are manufactured by "
        "outsourcing partners that are located primarily in Asia, including China "
        "mainland, India, Japan, South Korea, Taiwan and Vietnam."
    ),
}
E_AMZN_SEG = {
    "label": "C1",
    "provenance": "AMZN 10-K — Item 8. Financial Statements",
    "text": (
        "We have organized our operations into three segments: North America, "
        "International, and Amazon Web Services (AWS)."
    ),
}
E_NVDA_EXPORT = {
    "label": "C1",
    "provenance": "NVDA 10-K — Item 1A. Risk Factors",
    "text": (
        "U.S. government licensing requirements restrict the export of certain of our "
        "products, including advanced data center GPUs, to China and other destinations, "
        "which has adversely affected and could further adversely affect our revenue."
    ),
}
E_KO_HEALTH = {
    "label": "C1",
    "provenance": "KO 10-K — Item 1A. Risk Factors",
    "text": "Obesity and other health concerns may reduce demand for some of our products.",
}
E_MSFT_PROPERTIES = {
    "label": "C1",
    "provenance": "MSFT 10-K — Item 2. Properties",
    "text": "Our corporate headquarters consists of buildings located in Redmond, Washington.",
}
E_JPM_REG = {
    "label": "C1",
    "provenance": "JPM 10-K — Item 1A. Risk Factors",
    "text": (
        "We are subject to extensive and evolving regulation, including capital and "
        "liquidity requirements that could restrict our activities and increase our costs."
    ),
}
E_TSLA_MUSK = {
    "label": "C1",
    "provenance": "TSLA 10-K — Item 1A. Risk Factors",
    "text": "We are highly dependent on the services of Elon Musk, our Chief Executive Officer.",
}
E_GOOGL_ADS = {
    "label": "C1",
    "provenance": "GOOGL 10-K — Item 1A. Risk Factors",
    "text": "We generate a substantial majority of our revenues from advertising.",
}

LABELS = [
    # 1: correct + faithful
    dict(
        id="hl-01",
        question="Where are Apple's hardware products manufactured?",
        gold_answer="Apple's hardware is made by outsourcing partners located primarily in Asia.",
        candidate_answer="Apple's hardware products are manufactured by outsourcing partners located primarily in Asia [C1].",
        citations=[E_AAPL_MFG],
        human_correct=True,
        human_faithful=True,
    ),
    # 2: contradiction -> incorrect + unfaithful
    dict(
        id="hl-02",
        question="Where are Apple's hardware products manufactured?",
        gold_answer="Apple's hardware is made by outsourcing partners located primarily in Asia.",
        candidate_answer="Apple manufactures all of its products in the United States at company-owned factories [C1].",
        citations=[E_AAPL_MFG],
        human_correct=False,
        human_faithful=False,
    ),
    # 3: correct core + fabricated extra claim -> incorrect + unfaithful
    dict(
        id="hl-03",
        question="Where are Apple's hardware products manufactured?",
        gold_answer="Apple's hardware is made by outsourcing partners located primarily in Asia.",
        candidate_answer="Apple's products are made by outsourcing partners in Asia [C1], and Apple guarantees a 10% annual price cut from every supplier [C1].",
        citations=[E_AAPL_MFG],
        human_correct=False,
        human_faithful=False,
    ),
    # 4: correct + faithful (enumeration)
    dict(
        id="hl-04",
        question="What are Amazon's reportable segments?",
        gold_answer="Three segments: North America, International, and AWS.",
        candidate_answer="Amazon has three reportable segments: North America, International, and Amazon Web Services (AWS) [C1].",
        citations=[E_AMZN_SEG],
        human_correct=True,
        human_faithful=True,
    ),
    # 5: wrong count -> incorrect + unfaithful
    dict(
        id="hl-05",
        question="What are Amazon's reportable segments?",
        gold_answer="Three segments: North America, International, and AWS.",
        candidate_answer="Amazon has four reportable segments: North America, International, AWS, and Advertising [C1].",
        citations=[E_AMZN_SEG],
        human_correct=False,
        human_faithful=False,
    ),
    # 6: correct + faithful (export controls)
    dict(
        id="hl-06",
        question="What does NVIDIA disclose about export controls affecting China sales?",
        gold_answer="U.S. export licensing requirements restrict sales of certain advanced GPUs to China, hurting revenue.",
        candidate_answer="NVIDIA states that U.S. export licensing requirements restrict exports of certain advanced data center GPUs to China, adversely affecting its revenue [C1].",
        citations=[E_NVDA_EXPORT],
        human_correct=True,
        human_faithful=True,
    ),
    # 7: correct + faithful (health)
    dict(
        id="hl-07",
        question="What health-related demand risk does Coca-Cola disclose?",
        gold_answer="Obesity and health concerns may reduce demand for some products.",
        candidate_answer="Coca-Cola discloses that obesity and other health concerns may reduce demand for some of its products [C1].",
        citations=[E_KO_HEALTH],
        human_correct=True,
        human_faithful=True,
    ),
    # 8: right content, WRONG citation (grounding failure) -> correct but unfaithful
    dict(
        id="hl-08",
        question="What cybersecurity risk does Microsoft disclose?",
        gold_answer="Microsoft faces cyberattacks and security incidents that could disrupt operations and compromise data.",
        candidate_answer="Microsoft faces cyberattacks and security incidents that could disrupt its operations and compromise data [C1].",
        citations=[E_MSFT_PROPERTIES],  # excerpt is about properties, not security
        human_correct=True,
        human_faithful=False,
    ),
    # 9: correct + faithful (regulation)
    dict(
        id="hl-09",
        question="What regulatory risk does JPMorgan disclose?",
        gold_answer="JPMorgan is subject to extensive regulation, including capital and liquidity requirements.",
        candidate_answer="JPMorgan is subject to extensive and evolving regulation, including capital and liquidity requirements that could restrict its activities and raise costs [C1].",
        citations=[E_JPM_REG],
        human_correct=True,
        human_faithful=True,
    ),
    # 10: fabricated specific number -> incorrect + unfaithful
    dict(
        id="hl-10",
        question="What regulatory risk does JPMorgan disclose?",
        gold_answer="JPMorgan is subject to extensive regulation, including capital and liquidity requirements.",
        candidate_answer="JPMorgan is required to maintain a 15% common equity tier 1 capital ratio under the rules described [C1].",
        citations=[E_JPM_REG],
        human_correct=False,
        human_faithful=False,
    ),
    # 11: correct + faithful (key personnel)
    dict(
        id="hl-11",
        question="What does Tesla disclose about dependence on key personnel?",
        gold_answer="Tesla is highly dependent on key personnel, including CEO Elon Musk.",
        candidate_answer="Tesla is highly dependent on the services of its CEO, Elon Musk [C1].",
        citations=[E_TSLA_MUSK],
        human_correct=True,
        human_faithful=True,
    ),
    # 12: correct + faithful (advertising)
    dict(
        id="hl-12",
        question="How dependent is Alphabet on advertising revenue?",
        gold_answer="Alphabet generates a substantial majority of its revenue from advertising.",
        candidate_answer="Alphabet generates a substantial majority of its revenues from advertising [C1].",
        citations=[E_GOOGL_ADS],
        human_correct=True,
        human_faithful=True,
    ),
    # 13: wrong locations -> incorrect + unfaithful
    dict(
        id="hl-13",
        question="Where are Apple's hardware products manufactured?",
        gold_answer="Apple's hardware is made by outsourcing partners located primarily in Asia.",
        candidate_answer="Apple manufactures its hardware products primarily in Ireland and Brazil [C1].",
        citations=[E_AAPL_MFG],
        human_correct=False,
        human_faithful=False,
    ),
]


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        for rec in LABELS:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    n_correct = sum(1 for r in LABELS if r["human_correct"])
    n_faithful = sum(1 for r in LABELS if r["human_faithful"])
    print(
        f"Wrote {len(LABELS)} human labels to {OUT} ({n_correct} correct, {n_faithful} faithful)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
