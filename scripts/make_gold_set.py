#!/usr/bin/env python3
"""Author the FinGround gold set (results/gold_set.jsonl).

Questions are written to be answerable — or deliberately NOT answerable — from
the latest 10-Ks of the eight ingested companies. Gold answers are qualitative
reference statements; the LLM judge scores meaning, not string match. Keeping
the generator in code makes the set easy to review, extend, and regenerate.

Answerable items also carry retrieval ``evidence`` labels (see
``finground.eval.retrieval_metrics``): ticker + short verbatim phrases from the
filing rather than chunk IDs, so the labels survive re-chunking. They were
proposed by searching the chunk corpus for the gold answer's key phrases and
then checked by reading every matching chunk. ``verified`` records that check;
``uncertain`` flags labels a human reviewer should look at first.
"""

from __future__ import annotations

from finground.eval.datasets import GoldItem, write_gold_set

ITEMS: list[GoldItem] = [
    # ---- answerable: risk factors ----
    GoldItem(
        id="fg-001",
        question="What risks does Apple disclose from relying on outsourced/contract manufacturing?",
        answerable=True,
        gold_answer=(
            "Apple relies on outsourcing partners and contract manufacturers, largely "
            "located outside the U.S., to assemble its products; disruptions, capacity "
            "constraints, quality problems, or the loss of such partners could harm its "
            "business and results."
        ),
        gold_tickers=["AAPL"],
        category="risk_factors",
    ),
    GoldItem(
        id="fg-002",
        question="What does Apple say about dependence on single or limited sources for components?",
        answerable=True,
        gold_answer=(
            "Apple depends on components and technology, including custom parts, that "
            "are available from single or limited sources; supply shortages, price "
            "increases, or supplier problems could materially affect its operations."
        ),
        gold_tickers=["AAPL"],
        category="risk_factors",
    ),
    GoldItem(
        id="fg-003",
        question="What cybersecurity or information-security risks does Microsoft describe?",
        answerable=True,
        gold_answer=(
            "Microsoft faces cyberattacks and security incidents targeting its products, "
            "services, and infrastructure that could disrupt operations, compromise data, "
            "harm its reputation, and expose it to liability and remediation costs."
        ),
        gold_tickers=["MSFT"],
        category="risk_factors",
    ),
    GoldItem(
        id="fg-004",
        question="What does Amazon identify about competition in its markets?",
        answerable=True,
        gold_answer=(
            "Amazon operates in intensely competitive, rapidly evolving markets across "
            "retail, cloud (AWS), advertising, and devices, competing with many firms, "
            "some with greater resources; competition could pressure its results."
        ),
        gold_tickers=["AMZN"],
        category="risk_factors",
    ),
    GoldItem(
        id="fg-005",
        question="What does Alphabet say about its dependence on advertising revenue?",
        answerable=True,
        gold_answer=(
            "Alphabet generates a substantial majority of its revenue from advertising; a "
            "reduction in ad spending, loss of advertisers, or shifts in the ad market "
            "would materially harm its financial results."
        ),
        gold_tickers=["GOOGL"],
        category="risk_factors",
    ),
    GoldItem(
        id="fg-006",
        question="What risks does NVIDIA disclose about relying on third-party semiconductor manufacturers?",
        answerable=True,
        gold_answer=(
            "NVIDIA is fabless and depends on third-party foundries and suppliers to "
            "manufacture, assemble, test, and package its products; capacity limits, "
            "supply constraints, or disruptions at these partners could harm its business."
        ),
        gold_tickers=["NVDA"],
        category="risk_factors",
    ),
    GoldItem(
        id="fg-007",
        question="What does Tesla disclose about dependence on key personnel?",
        answerable=True,
        gold_answer=(
            "Tesla is highly dependent on the services of key employees, including its "
            "CEO Elon Musk; the loss of key personnel or inability to attract and retain "
            "talent could disrupt operations and harm the business."
        ),
        gold_tickers=["TSLA"],
        category="risk_factors",
    ),
    GoldItem(
        id="fg-008",
        question="What regulatory or capital-requirement risks does JPMorgan describe?",
        answerable=True,
        gold_answer=(
            "JPMorgan is subject to extensive and evolving regulation, including capital, "
            "liquidity, and stress-testing requirements; changes or noncompliance could "
            "constrain activities, raise costs, and affect its results and distributions."
        ),
        gold_tickers=["JPM"],
        category="risk_factors",
    ),
    GoldItem(
        id="fg-009",
        question="What risks does Coca-Cola describe related to changing consumer preferences and health concerns?",
        answerable=True,
        gold_answer=(
            "Coca-Cola faces risks from shifting consumer preferences and concerns about "
            "sugar, obesity, and health, along with related regulation and taxes, which "
            "could reduce demand for its products and harm its business."
        ),
        gold_tickers=["KO"],
        category="risk_factors",
    ),
    # ---- answerable: business ----
    GoldItem(
        id="fg-010",
        question="How does Amazon describe its reportable operating segments?",
        answerable=True,
        gold_answer=(
            "Amazon reports three segments: North America, International, and Amazon Web "
            "Services (AWS)."
        ),
        gold_tickers=["AMZN"],
        category="business",
    ),
    GoldItem(
        id="fg-011",
        question="How does Coca-Cola describe its business model with respect to concentrates and bottling partners?",
        answerable=True,
        gold_answer=(
            "Coca-Cola primarily manufactures and sells concentrates, beverage bases, and "
            "syrups to bottling partners, and also finished beverages; independent and "
            "company-owned bottlers convert these into finished products for sale."
        ),
        gold_tickers=["KO"],
        category="business",
    ),
    GoldItem(
        id="fg-012",
        question="What does Microsoft describe about its cloud offerings such as Azure?",
        answerable=True,
        gold_answer=(
            "Microsoft offers cloud services including Azure, part of its Intelligent "
            "Cloud business, providing computing, storage, AI, and platform services to "
            "enterprises and developers."
        ),
        gold_tickers=["MSFT"],
        category="business",
    ),
    # ---- answerable: geoeconomic / trade & export controls ----
    GoldItem(
        id="fg-013",
        question="What does NVIDIA disclose about U.S. export controls affecting sales to China?",
        answerable=True,
        gold_answer=(
            "NVIDIA discloses that U.S. government export controls and licensing "
            "requirements restrict sales of certain products (including advanced data "
            "center GPUs) to China and other regions, which has and could further harm "
            "its revenue and competitive position."
        ),
        gold_tickers=["NVDA"],
        category="geoeconomic",
    ),
    GoldItem(
        id="fg-014",
        question="What does Apple disclose about risks from international trade, tariffs, or trade tensions?",
        answerable=True,
        gold_answer=(
            "Apple discloses that its international operations expose it to risks from "
            "tariffs, trade restrictions, and geopolitical tensions, which could increase "
            "costs, disrupt its supply chain, and adversely affect its results."
        ),
        gold_tickers=["AAPL"],
        category="geoeconomic",
    ),
    GoldItem(
        id="fg-015",
        question="What does JPMorgan describe about risks from geopolitical events or global economic conditions?",
        answerable=True,
        gold_answer=(
            "JPMorgan discloses that geopolitical instability, conflicts, sanctions, and "
            "adverse global economic conditions could disrupt markets, increase credit "
            "and market risk, and negatively affect its businesses and results."
        ),
        gold_tickers=["JPM"],
        category="geoeconomic",
    ),
    # ---- unanswerable: should be refused ----
    GoldItem(
        id="fg-016",
        question="What is Apple's projected total revenue for fiscal year 2030?",
        answerable=False,
        gold_answer="",
        gold_tickers=["AAPL"],
        category="unanswerable",
        notes="Forward revenue projection is not disclosed in a 10-K.",
    ),
    GoldItem(
        id="fg-017",
        question="Which cryptocurrency token does Coca-Cola issue to its customers?",
        answerable=False,
        gold_answer="",
        gold_tickers=["KO"],
        category="unanswerable",
        notes="False premise; not in the filing.",
    ),
    GoldItem(
        id="fg-018",
        question="How many employees does OpenAI report in this filing?",
        answerable=False,
        gold_answer="",
        gold_tickers=[],
        category="unanswerable",
        notes="OpenAI is not among the ingested companies.",
    ),
    GoldItem(
        id="fg-019",
        question="What risks does Tesla disclose about operating its chain of fast-food restaurants?",
        answerable=False,
        gold_answer="",
        gold_tickers=["TSLA"],
        category="unanswerable",
        notes="False premise; Tesla does not operate fast-food restaurants.",
    ),
    GoldItem(
        id="fg-020",
        question="What was JPMorgan's closing share price on March 15, 2024?",
        answerable=False,
        gold_answer="",
        gold_tickers=["JPM"],
        category="unanswerable",
        notes="A specific historical market quote is not stated in the 10-K.",
    ),
]


def _ev(ticker: str, *phrases: str, note: str = "", uncertain: bool = False) -> dict:
    """One evidence label; all ``phrases`` must appear in a relevant chunk."""
    label: dict = {"ticker": ticker, "must_contain": list(phrases), "verified": True}
    if uncertain:
        label["uncertain"] = True
    if note:
        label["note"] = note
    return label


# Section names are deliberately not used as filters: the current parser
# mislabels several sections (e.g. JPM and MSFT risk factors appear under
# "Item 1. Business"), and the phrase + ticker pair is already specific.
EVIDENCE: dict[str, list[dict]] = {
    "fg-001": [
        _ev(
            "AAPL",
            "depends on component and product manufacturing and logistical services "
            "provided by outsourcing partners",
            note="Item 1A risk factor heading sentence.",
        ),
        _ev(
            "AAPL",
            "reduce the Company's direct control over production and distribution",
            note="Item 1A: consequence of outsourcing (cost, quality, quantity).",
        ),
    ],
    "fg-002": [
        _ev("AAPL", "single or limited sources", note="Item 1 supply + Item 1A risk factor."),
        _ev(
            "AAPL",
            "custom components available from only one source",
            note="Covers the 'custom parts' part of the gold answer.",
        ),
    ],
    "fg-003": [
        _ev(
            "MSFT",
            "Cyberattacks and security vulnerabilities could lead to reduced revenue, "
            "increased costs, liability claims",
            note="Risk factor heading (parser files it under Item 1).",
        ),
        _ev(
            "MSFT",
            "experienced cybersecurity incidents in which such actors have gained "
            "unauthorized access",
        ),
    ],
    "fg-004": [
        _ev(
            "AMZN",
            "businesses are rapidly evolving and intensely competitive",
            note="Risk factor 'We Face Intense Competition' (parser files it under Item 7).",
        ),
        _ev(
            "AMZN",
            "marketplace in which we compete is evolving rapidly and intensely competitive",
            note="Item 1 'Competition' paragraph (parser files it under Item 2).",
        ),
    ],
    "fg-005": [
        _ev("GOOGL", "generate a significant portion of our revenues from advertising"),
        _ev(
            "GOOGL",
            "more than 70% of total revenues from online advertising",
            note="Quantifies 'substantial majority'; same paragraph as label 1 today.",
        ),
        _ev(
            "GOOGL",
            "fluctuations in the amounts our advertisers spend on advertising",
            note="Tail of the same risk factor (ad-spend reductions harm results); "
            "added after reading the chunk every config ranks highest. Partial support.",
            uncertain=True,
        ),
    ],
    "fg-006": [
        _ev("NVDA", "depend on foundries to manufacture our semiconductor wafers"),
        _ev("NVDA", "fabless and contracting manufacturing strategy", note="Item 1 Manufacturing."),
    ],
    "fg-007": [
        _ev("TSLA", "highly dependent on the services of Elon Musk"),
        _ev("TSLA", "unable to attract, hire and retain key employees"),
    ],
    "fg-008": [
        _ev(
            "JPM",
            "businesses are highly regulated and are significantly affected by applicable law",
            note="'Legal and Regulatory' risk factor.",
        ),
        _ev(
            "JPM",
            "ability to distribute capital to shareholders",
            "regulatory capital requirements",
            note="'Capital' risk factor and its summary bullet.",
        ),
    ],
    "fg-009": [
        _ev("KO", "Obesity and other health-related concerns may reduce demand"),
        _ev("KO", "address evolving consumer product and shopping preferences"),
        _ev("KO", "taxes on sweetened beverages"),
    ],
    "fg-010": [
        _ev(
            "AMZN",
            "three segments: North America, International, and",
            note="Phrase stops before 'AWS' / 'Amazon Web Services' so both wordings match.",
        ),
    ],
    "fg-011": [
        _ev("KO", "two lines of business: concentrate operations and finished product operations"),
        _ev("KO", "bottling partners combine concentrates with still or sparkling water"),
    ],
    "fg-012": [
        _ev(
            "MSFT",
            "Intelligent Cloud segment consists of our public, private, and hybrid server "
            "products and cloud services",
            note="Segment note in Item 8.",
            uncertain=True,
        ),
        _ev(
            "MSFT",
            "Azure and other cloud services",
            "consumption-based services",
            note="Segment note + MD&A metric definition.",
            uncertain=True,
        ),
    ],
    "fg-013": [
        _ev("NVDA", "export restrictions and export licensing requirements targeting China"),
        _ev("NVDA", "competitive position has been harmed by export controls"),
        _ev(
            "NVDA",
            "requires a license for export to China",
            "H20",
            note="More specific than the gold answer (H20 licence); drop if too narrow.",
            uncertain=True,
        ),
    ],
    "fg-014": [
        _ev("AAPL", "Restrictions on international trade, such as tariffs"),
        _ev(
            "AAPL",
            "reciprocal tariffs on imports from the U.S.",
            note="Item 1A + MD&A 'Tariffs and Other Measures'.",
        ),
    ],
    "fg-015": [
        _ev("JPM", "economic uncertainty resulting from political and geopolitical developments"),
        _ev("JPM", "Adverse economic and market events and conditions could negatively affect"),
    ],
}


def main() -> int:
    for item in ITEMS:
        item.evidence = EVIDENCE.get(item.id, [])
    missing = [i.id for i in ITEMS if i.answerable and not i.evidence]
    if missing:
        raise SystemExit(f"answerable items without evidence labels: {missing}")
    n = write_gold_set(ITEMS)
    answerable = sum(1 for i in ITEMS if i.answerable)
    print(f"Wrote {n} gold items ({answerable} answerable, {n - answerable} unanswerable).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
