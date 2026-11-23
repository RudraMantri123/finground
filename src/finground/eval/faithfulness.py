"""Faithfulness regression gate: deterministic checks, judged thresholds, staleness.

CI has no LLM keys and no Ollama, so the gate works in layers over a committed,
*pinned* answer set (``results/faithfulness/pinned_run.jsonl``: answers, their
retrieved chunks, and the judge's labels, produced over the committed fixture
corpus by ``scripts/eval_faithfulness.py --regenerate --pin``):

1. **Deterministic checks** (no LLM; recomputed from the answer text and the
   chunk text on every CI run):

   * *citation validity* — every ``[C#]`` names a chunk that was retrieved;
   * *citation coverage* — share of claim units (sentences / bullets, see
     ``metrics.claim_units``) carrying at least one valid citation;
   * *numeric grounding* — every figure in an answer (after normalising ``$``,
     thousands separators, million/billion scale words, ``%``, and
     parenthesised negatives) appears in at least one chunk it cites;
   * *refusal correctness* — unanswerable (trap) questions are refused;
   * *abstention* — answerable questions are not refused.

2. **Judged scores** — faithfulness, hallucination rate and citation accuracy
   recomputed from the committed judge labels (the same code as the
   leaderboard, ``summary.py``).

3. **Staleness** — the pinned run's manifest records the answer/judge model,
   prompt ids *and file hashes*, the retrieval config, the fixture corpus and
   gold set hashes. If any of those differ from the code, the pinned judged
   numbers no longer describe the shipped pipeline and the gate fails until
   the eval is re-run and committed.

Everything here is pure (no network, no FAISS/torch), so it is unit-testable
and runs in a minimal CI install.
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from ..citations import REFUSAL, extract_cited_labels, strip_citations
from ..config import CONFIG
from .metrics import claim_units
from .summary import citation_accuracy_of, correctness_of, hallucination_rate_of

# The model pair the pinned run is generated and judged with. These are part of
# the gate's configuration: changing either one without re-running and
# committing the pinned eval fails the staleness check. Cohere because it is the
# hosted provider the project has a key for (a free trial key works); the CI
# live job re-runs exactly this pair when a COHERE_API_KEY secret is present.
GATE_ANSWER_MODEL = "cohere:command-a-03-2025"
GATE_JUDGE_MODEL = "cohere:command-a-03-2025"
GATE_TEMPERATURE = 0.0

PINNED_DIR = CONFIG.paths.results / "faithfulness"
PINNED_RUN = PINNED_DIR / "pinned_run.jsonl"
PINNED_MANIFEST = PINNED_DIR / "pinned_manifest.json"
THRESHOLDS = CONFIG.paths.results / "faithfulness_thresholds.json"
FIXTURE_PATH = CONFIG.paths.root / "tests" / "fixtures" / "retrieval_corpus.jsonl"

# Same reasoning as the retrieval gate: one question's worth on the 15
# answerable items (1/15, rounded up). Applied to rate floors/ceilings only;
# violation counts on the fixed pinned set are exact (see thresholds_from).
DEFAULT_MARGIN = 0.07

# Rates gated with a floor (higher is better) / a ceiling (lower is better).
DETERMINISTIC_FLOORS = (
    "citation_validity",
    "citation_coverage",
    "numeric_grounding",
    "refusal_recall",
    "answer_recall",
)
JUDGED_FLOORS = ("faithfulness", "citation_accuracy")
JUDGED_CEILINGS = ("hallucination_rate",)
# Counts gated exactly on the pinned set: any new violation is a regression.
VIOLATION_KINDS = (
    "invalid_citations",
    "uncited_claims",
    "ungrounded_numbers",
    "trap_answers",
    "false_refusals",
    "judge_errors",
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(Path(path).read_bytes())


# ---------------------------------------------------------------------------
# Numeric grounding
# ---------------------------------------------------------------------------

_SCALE_WORDS = {
    "thousand": 1e3,
    "k": 1e3,
    "million": 1e6,
    "mn": 1e6,
    "m": 1e6,
    "billion": 1e9,
    "bn": 1e9,
    "b": 1e9,
    "trillion": 1e12,
}

# A figure: optional "(" / sign / "$", digits with optional thousands commas and
# decimals, optional ")" and unit. Not glued to a word on either side, so
# "10-K", "COVID-19", "Item 1A", "Q3", "4th" and "C1" are not figures.
_FIGURE_RE = re.compile(
    r"""
    (?<![\w.,/-])
    (?P<open>\()?
    (?P<neg>[-−])?
    (?P<cur>\$)?\s?
    (?P<int>\d{1,3}(?:,\d{3})+|\d+)
    (?P<dec>\.\d+)?
    (?P<close>\))?
    (?:\s?(?P<unit>%|percent\b|per\s?cent\b|basis\s+points?\b|bps\b
        |thousand\b|million\b|billion\b|trillion\b|bn\b|mn\b|[kKmMbB]\b))?
    (?![\w]|-\w)
    """,
    re.VERBOSE | re.IGNORECASE,
)
_ISO_DATE_RE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_BULLET_PREFIX_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+", re.MULTILINE)
# Table / statement unit hints ("(in millions)", "in millions, except ...").
_SCALE_HINT_RE = re.compile(r"\bin\s+(thousands|millions|billions)\b", re.IGNORECASE)


@dataclass(frozen=True)
class Figure:
    """A normalised number mention."""

    raw: str
    value: float  # magnitude in its own unit (sign is ignored when matching)
    scale: float  # multiplier from a scale word (1 if none)
    kind: str  # "plain" | "pct" | "bps"
    decimals: int
    negative: bool

    @property
    def absolute(self) -> float:
        return self.value * self.scale

    @property
    def tolerance(self) -> float:
        """Half a unit in the last written digit: "$61 billion" covers 60.5-61.5bn."""
        return 0.5 * 10 ** (-self.decimals) * self.scale


def extract_figures(text: str) -> list[Figure]:
    """All numeric mentions in ``text``, normalised.

    Handles ``$``, thousands separators, decimals, ``%`` / percent, basis
    points, million/billion/thousand (and bn/mn/M/B) scale words, and
    accounting negatives ``(1,234)``. Spelled-out numbers ("three segments") are
    not figures. Signs are recorded but not compared: prose states direction
    in words ("decreased by $1.2 billion") while statements use parentheses.
    """
    out: list[Figure] = []
    for m in _FIGURE_RE.finditer(text or ""):
        digits = m.group("int").replace(",", "")
        dec = m.group("dec") or ""
        unit = (m.group("unit") or "").lower().replace(" ", "")
        kind = "plain"
        scale = 1.0
        if unit in ("%", "percent", "percent.", "percent,") or unit.startswith("per"):
            kind = "pct"
        elif unit.startswith("basis") or unit == "bps":
            kind = "bps"
        elif unit:
            scale = _SCALE_WORDS.get(unit, 1.0)
        negative = bool(m.group("neg")) or bool(m.group("open") and m.group("close"))
        out.append(
            Figure(
                raw=m.group(0).strip(),
                value=float(digits + dec),
                scale=scale,
                kind=kind,
                decimals=max(len(dec) - 1, 0),
                negative=negative,
            )
        )
    return out


def answer_figures(answer_text: str) -> list[Figure]:
    """Figures asserted by an answer: citations and list numbering removed first."""
    text = _BULLET_PREFIX_RE.sub("", strip_citations(answer_text or ""))
    return extract_figures(text)


def evidence_text(chunk: dict) -> str:
    """What the model saw for one excerpt: its provenance header plus its text."""
    head = f"{chunk.get('provenance', '')}\n{chunk.get('text', '')}"
    return _ISO_DATE_RE.sub(r"\1 \2 \3", head)


def _candidate_values(fig: Figure, hint_scales: set[float]) -> list[float]:
    """Absolute values an evidence figure may denote.

    A bare table number may be in the statement's unit ("(in millions)"), so
    besides its face value it also stands for each scale hinted in its chunk.
    """
    if fig.scale != 1.0 or fig.kind != "plain":
        return [fig.absolute]
    return [fig.value] + [fig.value * s for s in hint_scales]


def figure_grounded(fig: Figure, evidence: str) -> bool:
    """True iff ``fig`` matches some figure in ``evidence`` within its rounding."""
    hints = {
        {"thousands": 1e3, "millions": 1e6, "billions": 1e9}[h.lower()]
        for h in _SCALE_HINT_RE.findall(evidence)
    }
    # A scale word in prose ("$61 billion") also licenses its bare table form.
    for ev in extract_figures(evidence):
        if fig.kind == "pct" and ev.kind == "bps":
            continue
        if fig.kind == "bps" and ev.kind == "pct":
            continue
        if fig.kind in ("pct", "bps") or ev.kind in ("pct", "bps"):
            if abs(fig.value - ev.value) <= 0.5 * 10 ** (-fig.decimals) + 1e-9:
                return True
            continue
        for v in _candidate_values(ev, hints):
            if abs(fig.absolute - v) <= fig.tolerance + 1e-9 * max(1.0, fig.absolute):
                return True
    return False


# ---------------------------------------------------------------------------
# Per-item deterministic checks
# ---------------------------------------------------------------------------


def _answered(row: dict) -> bool:
    return "error" not in row and not row.get("abstained", False)


def item_checks(row: dict) -> dict:
    """Deterministic faithfulness findings for one pinned row.

    Returns counts plus the offending strings, so a CI failure names the exact
    sentence / figure / label at fault.
    """
    answerable = bool(row.get("answerable", True))
    answered = _answered(row)
    out: dict = {
        "id": row.get("id"),
        "answerable": answerable,
        "answered": answered,
        "trap_answered": (not answerable) and answered,
        "false_refusal": answerable and not answered and "error" not in row,
        "n_citations": 0,
        "invalid_citations": [],
        "n_units": 0,
        "uncited_claims": [],
        "n_figures": 0,
        "ungrounded_numbers": [],
    }
    if not answered:
        return out

    answer = row.get("answer", "")
    retrieved = {c["label"]: c for c in row.get("retrieved", [])}

    cited = extract_cited_labels(answer)
    out["n_citations"] = len(cited)
    out["invalid_citations"] = [lbl for lbl in cited if lbl not in retrieved]

    units = claim_units(answer)
    out["n_units"] = len(units)
    for unit in units:
        labels = extract_cited_labels(unit)
        if not labels or any(lbl not in retrieved for lbl in labels):
            out["uncited_claims"].append(unit)

    # Figures are checked against the excerpts the *answer* cites (anywhere in
    # it): a figure must be traceable to evidence the reader is pointed at.
    evidence = "\n\n".join(evidence_text(retrieved[lbl]) for lbl in cited if lbl in retrieved)
    figures = answer_figures(answer)
    out["n_figures"] = len(figures)
    out["ungrounded_numbers"] = [f.raw for f in figures if not figure_grounded(f, evidence)]
    return out


def deterministic_metrics(rows: list[dict]) -> tuple[dict, dict, list[dict]]:
    """Aggregate rates, violation counts and the per-item findings."""
    items = [item_checks(r) for r in rows]
    n_cit = sum(i["n_citations"] for i in items)
    n_units = sum(i["n_units"] for i in items)
    n_fig = sum(i["n_figures"] for i in items)
    traps = [i for i in items if not i["answerable"]]
    answerable = [i for i in items if i["answerable"]]

    def rate(num: int, den: int) -> float | None:
        return num / den if den else None

    counts = {
        "invalid_citations": sum(len(i["invalid_citations"]) for i in items),
        "uncited_claims": sum(len(i["uncited_claims"]) for i in items),
        "ungrounded_numbers": sum(len(i["ungrounded_numbers"]) for i in items),
        "trap_answers": sum(1 for i in items if i["trap_answered"]),
        "false_refusals": sum(1 for i in items if i["false_refusal"]),
    }
    metrics = {
        "citation_validity": rate(n_cit - counts["invalid_citations"], n_cit),
        "citation_coverage": rate(n_units - counts["uncited_claims"], n_units),
        "numeric_grounding": rate(n_fig - counts["ungrounded_numbers"], n_fig),
        "refusal_recall": rate(len(traps) - counts["trap_answers"], len(traps)),
        "answer_recall": rate(len(answerable) - counts["false_refusals"], len(answerable)),
        "n_items": len(items),
        "n_answered": sum(1 for i in items if i["answered"]),
        "n_citations": n_cit,
        "n_claim_units": n_units,
        "n_figures": n_fig,
    }
    return metrics, counts, items


def judged_metrics(rows: list[dict]) -> tuple[dict, dict]:
    """Judge-derived rates (same code as the leaderboard) and judge error count."""
    halluc = hallucination_rate_of(rows)
    metrics = {
        "faithfulness": None if halluc is None else 1.0 - halluc,
        "hallucination_rate": halluc,
        "citation_accuracy": citation_accuracy_of(rows),
        "correctness": correctness_of(rows),  # reported, not gated (not faithfulness)
    }
    errors = 0
    for r in rows:
        if not _answered(r):
            continue
        j = r.get("judge")
        if "judge_error" in r or not isinstance(j, dict) or j.get("error"):
            errors += 1
    return metrics, {"judge_errors": errors}


# ---------------------------------------------------------------------------
# Staleness: what the pinned run was produced with vs what the code says now
# ---------------------------------------------------------------------------


def current_fingerprint(
    *,
    prompts_dir: Path | None = None,
    answer_version: str | None = None,
    judge_version: str | None = None,
    gold_path: Path | None = None,
    fixture_path: Path | None = None,
) -> dict:
    """Everything that determines the pinned answers and their judgments.

    Prompt files are hashed, not just versioned: an in-place edit of
    ``answer.v1.toml`` changes the behaviour without changing the id.
    """
    prompts_dir = prompts_dir or CONFIG.paths.prompts
    answer_version = answer_version or CONFIG.prompts.answer_version
    judge_version = judge_version or CONFIG.prompts.judge_version
    gold_path = gold_path or (CONFIG.paths.results / "gold_set.jsonl")
    fixture_path = fixture_path or FIXTURE_PATH

    def prompt_fp(name: str, version: str) -> dict:
        path = prompts_dir / f"{name}.{version}.toml"
        return {
            "id": f"{name}.{version}",
            "sha256": sha256_file(path) if path.exists() else None,
        }

    return {
        "answer_model": GATE_ANSWER_MODEL,
        "judge_model": GATE_JUDGE_MODEL,
        "temperature": GATE_TEMPERATURE,
        "answer_prompt": prompt_fp("answer", answer_version),
        "judge_prompt": prompt_fp("judge", judge_version),
        "refusal": REFUSAL,
        "retrieval": asdict(CONFIG.retrieval),
        "embed_model": CONFIG.models.embed,
        "reranker_model": CONFIG.models.reranker,
        "corpus": "fixture",
        "fixture_sha256": sha256_file(fixture_path) if fixture_path.exists() else None,
        "gold_set_sha256": sha256_file(gold_path) if gold_path.exists() else None,
    }


_FINGERPRINT_LABELS = {
    "answer_model": "answer model",
    "judge_model": "judge model",
    "temperature": "generation temperature",
    "answer_prompt": "answer prompt",
    "judge_prompt": "judge prompt",
    "refusal": "refusal sentence",
    "retrieval": "retrieval config",
    "embed_model": "embedding model",
    "reranker_model": "reranker model",
    "corpus": "corpus",
    "fixture_sha256": "fixture corpus (tests/fixtures/retrieval_corpus.jsonl)",
    "gold_set_sha256": "gold set (results/gold_set.jsonl)",
}

_REPIN_HINT = (
    "re-run and commit the judged eval: python scripts/eval_faithfulness.py "
    "--regenerate --pin --write-thresholds results/faithfulness_thresholds.json"
)


def _describe(value) -> str:
    if isinstance(value, dict) and "id" in value:
        sha = (value.get("sha256") or "missing")[:12]
        return f"{value['id']} (sha256 {sha})"
    if isinstance(value, dict):
        return ", ".join(f"{k}={v}" for k, v in sorted(value.items()))
    return repr(value)


def staleness_problems(recorded: dict, current: dict) -> list[str]:
    """Fingerprint fields where the pinned run no longer matches the code."""
    problems: list[str] = []
    for key, label in _FINGERPRINT_LABELS.items():
        want, got = recorded.get(key), current.get(key)
        if want == got:
            continue
        if isinstance(want, dict) and isinstance(got, dict) and "id" not in want:
            diffs = sorted(k for k in set(want) | set(got) if want.get(k) != got.get(k))
            detail = "; ".join(f"{k}: pinned {want.get(k)!r} != code {got.get(k)!r}" for k in diffs)
        else:
            detail = f"pinned {_describe(want)} != code {_describe(got)}"
        problems.append(f"STALE {label}: {detail}")
    if problems:
        problems.append(f"(pinned judged eval is stale; {_REPIN_HINT})")
    return problems


def row_provenance_problems(rows: list[dict], current: dict) -> list[str]:
    """Rows must carry the prompt ids / models the manifest claims.

    Guards against a manifest edited to match the code while the answers and
    judgments underneath were produced with something else.
    """
    want_answer = current["answer_prompt"]["id"]
    want_judge = current["judge_prompt"]["id"]
    problems: list[str] = []
    for r in rows:
        rid = r.get("id")
        if r.get("model") and r["model"] != current["answer_model"]:
            problems.append(
                f"STALE {rid}: answered by {r['model']}, gate uses {current['answer_model']}"
            )
        if not _answered(r):
            continue  # gated refusals never reach the prompt or the judge
        if r.get("prompt_version") != want_answer:
            problems.append(
                f"STALE {rid}: answer prompt {r.get('prompt_version')!r} != code {want_answer!r}"
            )
        j = r.get("judge") or {}
        if j.get("prompt_version") != want_judge:
            problems.append(
                f"STALE {rid}: judge prompt {j.get('prompt_version')!r} != code {want_judge!r}"
            )
        if r.get("judge_model") and r["judge_model"] != current["judge_model"]:
            problems.append(
                f"STALE {rid}: judged by {r['judge_model']}, gate uses {current['judge_model']}"
            )
    return problems


# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------


def _floor(v: float, margin: float) -> float:
    return max(0.0, math.floor(round((v - margin) * 100, 6)) / 100)


def _ceiling(v: float, margin: float) -> float:
    return min(1.0, math.ceil(round((v + margin) * 100, 6)) / 100)


def thresholds_from(det: dict, counts: dict, judged: dict, margin: float) -> dict:
    """Rate floors/ceilings ``margin`` from the measured values; counts exact."""
    return {
        "floors": {
            k: _floor(v, margin)
            for k in (*DETERMINISTIC_FLOORS, *JUDGED_FLOORS)
            if (v := {**det, **judged}.get(k)) is not None
        },
        "ceilings": {
            k: _ceiling(judged[k], margin) for k in JUDGED_CEILINGS if judged.get(k) is not None
        },
        "max_violations": {k: int(counts[k]) for k in VIOLATION_KINDS if k in counts},
    }


def rate_problems(values: dict, spec: dict) -> list[str]:
    """Floors / ceilings only (what a regenerated or re-pinned run is held to)."""
    problems: list[str] = []
    for metric, floor in spec.get("floors", {}).items():
        got = values.get(metric)
        if got is None:
            problems.append(f"{metric}: not measurable on this run (threshold {floor:.2f})")
        elif got + 1e-9 < floor:
            problems.append(f"{metric}: {got:.3f} < floor {floor:.2f}")
    for metric, ceiling in spec.get("ceilings", {}).items():
        got = values.get(metric)
        if got is None:
            problems.append(f"{metric}: not measurable on this run (threshold {ceiling:.2f})")
        elif got - 1e-9 > ceiling:
            problems.append(f"{metric}: {got:.3f} > ceiling {ceiling:.2f}")
    return problems


def count_problems(counts: dict, spec: dict, items: list[dict] | None = None) -> list[str]:
    """Exact violation budgets on the pinned set, with the offending evidence."""
    problems: list[str] = []
    detail_key = {
        "invalid_citations": "invalid_citations",
        "uncited_claims": "uncited_claims",
        "ungrounded_numbers": "ungrounded_numbers",
    }
    for kind, budget in spec.get("max_violations", {}).items():
        got = counts.get(kind, 0)
        if got <= budget:
            continue
        line = f"{kind}: {got} > allowed {budget}"
        if items:
            if kind in detail_key:
                hits = [f"{i['id']}: {x!r}"[:160] for i in items for x in i[detail_key[kind]]]
            elif kind == "trap_answers":
                hits = [str(i["id"]) for i in items if i["trap_answered"]]
            elif kind == "false_refusals":
                hits = [str(i["id"]) for i in items if i["false_refusal"]]
            else:
                hits = []
            if hits:
                line += "\n      " + "\n      ".join(hits)
        problems.append(line)
    return problems
