"""Faithfulness regression gate: unit tests and mutation tests on the pinned set.

The mutation tests take the committed pinned run, break one answer the way a
regression would (drop a citation, change a figure, answer a trap question,
bump a prompt version, ...), and assert the gate fails *for that reason*. The
unmutated committed data must pass. No LLM, network, FAISS or torch needed.
"""

from __future__ import annotations

import copy
import json
import re
import shutil
import sys
from pathlib import Path

import pytest

from finground.citations import REFUSAL, extract_cited_labels
from finground.config import CONFIG
from finground.eval import faithfulness as F
from finground.eval.faithfulness import (
    answer_figures,
    count_problems,
    current_fingerprint,
    deterministic_metrics,
    extract_figures,
    figure_grounded,
    item_checks,
    judged_metrics,
    rate_problems,
    row_provenance_problems,
    staleness_problems,
    thresholds_from,
)

ROOT = CONFIG.paths.root
sys.path.insert(0, str(ROOT / "scripts"))
import eval_faithfulness as cli  # noqa: E402

THRESHOLDS = ROOT / "results" / "faithfulness_thresholds.json"


def _rows() -> list[dict]:
    with open(F.PINNED_RUN, encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def _manifest() -> dict:
    return json.loads(F.PINNED_MANIFEST.read_text(encoding="utf-8"))


def _spec() -> dict:
    return json.loads(THRESHOLDS.read_text(encoding="utf-8"))


def gate_problems(rows: list[dict], manifest: dict | None = None, **fp_kwargs) -> list[str]:
    """Everything ``--check`` evaluates on a pinned set, minus the file-hash guard."""
    spec = _spec()
    det, counts, items = deterministic_metrics(rows)
    judged, jcounts = judged_metrics(rows)
    counts.update(jcounts)
    current = current_fingerprint(**fp_kwargs)
    return (
        rate_problems({**det, **judged}, spec)
        + count_problems(counts, spec, items)
        + staleness_problems(manifest or _manifest(), current)
        + row_provenance_problems(rows, current)
    )


def _answered(rows, *, answerable=True):
    return [r for r in rows if not r["abstained"] and r["answerable"] == answerable]


# -- figure normalisation -----------------------------------------------------


def _vals(text):
    return [(f.value, f.scale, f.kind, f.negative) for f in extract_figures(text)]


def test_figures_normalise_currency_commas_scale_percent_and_negatives():
    assert _vals("$1,234.5 million") == [(1234.5, 1e6, "plain", False)]
    assert _vals("up 12% or 7 percent") == [(12, 1, "pct", False), (7, 1, "pct", False)]
    assert _vals("a loss of (2,345)") == [(2345, 1, "plain", True)]
    assert _vals("3.2bn and $5M and 50 bps") == [
        (3.2, 1e9, "plain", False),
        (5, 1e6, "plain", False),
        (50, 1, "bps", False),
    ]


def test_identifiers_are_not_figures():
    assert extract_figures("Form 10-K, Item 1A, COVID-19, Q3, 4th quarter, C1") == []


def test_answer_figures_ignore_citations_and_list_numbering():
    text = "1. Apple has 3 segments [C1, C12].\n2) Revenue rose 5% [C2]."
    assert [f.raw for f in answer_figures(text)] == ["3", "5%"]


@pytest.mark.parametrize(
    "claim, grounded",
    [
        ("$107.6 billion", True),  # rounded scale-word form of a table value
        ("$108 billion", True),
        ("107,556", True),
        ("$638 billion", True),
        ("11%", True),
        ("1,234", True),  # parenthesised negative, stated as a magnitude
        ("$109 billion", False),
        ("12%", False),
        ("$107.9 billion", False),  # more precise than, and different from, the source
    ],
)
def test_figure_grounding_against_table_in_millions(claim, grounded):
    evidence = "Net sales (in millions) | AWS | 107,556 | Total | 637,959 | up 11% (1,234)"
    (fig,) = extract_figures(claim)
    assert figure_grounded(fig, evidence) is grounded


# -- per-item checks on synthetic rows ---------------------------------------


def _row(answer, *, answerable=True, abstained=False, chunks=None):
    chunks = chunks or {"C1": "Revenue was $5.2 billion in 2024.", "C2": "Margins were 40%."}
    return {
        "id": "x",
        "answerable": answerable,
        "abstained": abstained,
        "answer": answer,
        "retrieved": [
            {"label": k, "provenance": "AAPL 10-K (2024-11-01) — Item 7", "text": v}
            for k, v in chunks.items()
        ],
    }


def test_item_checks_clean_answer():
    c = item_checks(_row("Revenue was $5.2 billion [C1]. Margins were 40% [C2]."))
    assert c["invalid_citations"] == []
    assert c["uncited_claims"] == []
    assert c["ungrounded_numbers"] == []
    assert (c["n_units"], c["n_figures"]) == (2, 2)


def test_item_checks_flags_each_failure_mode():
    c = item_checks(_row("Revenue was $5.9 billion [C1]. Margins were 40%. Growth [C7]."))
    assert c["invalid_citations"] == ["C7"]
    assert c["uncited_claims"] == ["Margins were 40%.", "Growth [C7]."]
    # 40% is uncited, so it is not grounded by C2 (which the answer never cites).
    assert c["ungrounded_numbers"] == ["$5.9 billion", "40%"]


def test_refusal_decisions():
    trap = item_checks(_row("Revenue was $5.2 billion [C1].", answerable=False))
    assert trap["trap_answered"]
    refused = item_checks(_row(REFUSAL, abstained=True))
    assert refused["false_refusal"] and refused["n_units"] == 0


# -- thresholds ----------------------------------------------------------------


def test_thresholds_from_rounds_outward_and_keeps_counts_exact():
    det = {"citation_coverage": 0.8, "refusal_recall": 1.0, "numeric_grounding": None}
    judged = {"faithfulness": 0.951, "hallucination_rate": 0.049}
    t = thresholds_from(det, {"uncited_claims": 3, "trap_answers": 0}, judged, 0.07)
    assert t["floors"] == {"citation_coverage": 0.73, "refusal_recall": 0.93, "faithfulness": 0.88}
    assert t["ceilings"] == {"hallucination_rate": 0.12}
    assert t["max_violations"] == {"uncited_claims": 3, "trap_answers": 0}


# -- the committed pinned set --------------------------------------------------


def test_committed_pinned_run_passes_the_gate():
    assert gate_problems(_rows()) == []


def test_committed_thresholds_match_committed_pinned_run():
    assert _spec()["pinned_run_sha256"] == F.sha256_file(F.PINNED_RUN)


def test_pinned_rows_are_self_contained():
    rows = _rows()
    assert len(rows) == len(
        [line for line in (ROOT / "results" / "gold_set.jsonl").read_text().splitlines() if line]
    )
    for r in rows:
        assert r["retrieved"], r["id"]
        assert all(c["text"] for c in r["retrieved"])
        if not r["abstained"]:
            assert r["judge"]["prompt_version"] and r["prompt_version"]


def test_cli_check_passes_on_committed_data(tmp_path, capsys):
    assert cli.main(["--check", str(THRESHOLDS), "--out-dir", str(tmp_path)]) == 0
    assert "Faithfulness gate OK" in capsys.readouterr().out


# -- mutations: each must be caught, for the right reason --------------------


def test_mutation_drop_a_citation_is_caught():
    rows = _rows()
    # A claim unit whose only citation group we remove becomes uncited.
    for r in _answered(rows):
        lines = r["answer"].split("\n")
        for i, line in enumerate(lines):
            groups = re.findall(r"\s?\[[^\]]*C\d+[^\]]*\]", line)
            if len(groups) == 1:
                lines[i] = line.replace(groups[0], "")
                r["answer"] = "\n".join(lines)
                break
        else:
            continue
        break
    else:
        pytest.skip("no single-citation line in the pinned set")
    problems = gate_problems(rows)
    assert any(p.startswith("uncited_claims:") for p in problems), problems


def test_mutation_cite_a_chunk_that_was_not_retrieved_is_caught():
    rows = _rows()
    r = _answered(rows)[0]
    first = extract_cited_labels(r["answer"])[0]
    r["answer"] = r["answer"].replace(f"[{first}", "[C99", 1)
    problems = gate_problems(rows)
    assert any(p.startswith("invalid_citations:") for p in problems), problems
    assert any("citation_validity" in p for p in problems) or any(
        "C99" in p for p in problems
    ), problems


def test_mutation_change_a_number_to_one_not_in_the_chunk_is_caught():
    rows = _rows()
    target = None
    for r in _answered(rows):
        for fig in answer_figures(r["answer"]):
            if "%" in fig.raw or fig.value >= 10:
                target = (r, fig)
                break
        if target:
            break
    if target is None:
        # No figures in any pinned answer: inject one into a cited sentence.
        r = _answered(rows)[0]
        label = extract_cited_labels(r["answer"])[0]
        r["answer"] += f"\nThe company reported 987.6 million units [{label}]."
        bad = "987.6 million"
    else:
        r, fig = target
        bad = "987.6%" if fig.kind == "pct" else "987.6 million"
        r["answer"] = r["answer"].replace(fig.raw, bad, 1)
    evidence = " ".join(c["text"] for c in r["retrieved"])
    assert "987.6" not in evidence
    problems = gate_problems(rows)
    hit = [p for p in problems if p.startswith("ungrounded_numbers:")]
    assert hit and bad in hit[0], problems


def test_mutation_answer_a_trap_question_is_caught():
    rows = _rows()
    trap = next(r for r in rows if not r["answerable"])
    donor = _answered(rows)[0]
    trap.update(
        abstained=False,
        answer=donor["answer"],
        retrieved=donor["retrieved"],
        prompt_version=donor["prompt_version"],
        judge=copy.deepcopy(donor["judge"]),
        judge_model=donor.get("judge_model"),
    )
    problems = gate_problems(rows)
    assert any(p.startswith("trap_answers:") and trap["id"] in p for p in problems), problems
    assert any(p.startswith("refusal_recall:") for p in problems), problems


def test_mutation_refuse_answerable_questions_is_caught():
    rows = _rows()
    for r in _answered(rows)[:2]:
        r.update(abstained=True, answer=REFUSAL)
    problems = gate_problems(rows)
    assert any(p.startswith("false_refusals:") for p in problems), problems
    assert any(p.startswith("answer_recall:") for p in problems), problems


def test_mutation_judge_marks_claims_unsupported_is_caught():
    rows = _rows()
    for r in _answered(rows):
        for c in r["judge"]["claims"]:
            c["supported"] = False
    problems = gate_problems(rows)
    assert any(p.startswith("faithfulness:") for p in problems), problems
    assert any(p.startswith("hallucination_rate:") for p in problems), problems


def test_mutation_bump_answer_prompt_version_is_caught(tmp_path):
    # The code moves to answer.v2 (a new file) without re-running the eval.
    prompts = tmp_path / "prompts"
    shutil.copytree(CONFIG.paths.prompts, prompts)
    v1 = (prompts / "answer.v1.toml").read_text()
    (prompts / "answer.v2.toml").write_text(v1.replace('version = "v1"', 'version = "v2"'))
    problems = gate_problems(_rows(), prompts_dir=prompts, answer_version="v2")
    assert any(p.startswith("STALE answer prompt") and "answer.v2" in p for p in problems)
    assert any("answer prompt 'answer.v1' != code 'answer.v2'" in p for p in problems)


def test_mutation_edit_prompt_in_place_is_caught(tmp_path):
    # Same id, different text: only the file hash notices.
    prompts = tmp_path / "prompts"
    shutil.copytree(CONFIG.paths.prompts, prompts)
    path = prompts / "judge.v1.toml"
    path.write_text(path.read_text().replace("strict, literal", "lenient"))
    problems = gate_problems(_rows(), prompts_dir=prompts)
    assert any(p.startswith("STALE judge prompt") for p in problems), problems


def test_mutation_change_gate_model_is_caught(monkeypatch):
    monkeypatch.setattr(F, "GATE_ANSWER_MODEL", "cohere:command-r7b-12-2024")
    problems = gate_problems(_rows())
    assert any(p.startswith("STALE answer model") for p in problems), problems


def test_mutation_change_retrieval_config_is_caught(monkeypatch):
    from dataclasses import replace

    monkeypatch.setattr(F, "CONFIG", replace(CONFIG, retrieval=replace(CONFIG.retrieval, top_k=5)))
    problems = gate_problems(_rows())
    assert any(p.startswith("STALE retrieval config") and "top_k" in p for p in problems)


def test_mutation_edit_gold_set_is_caught(tmp_path):
    gold = tmp_path / "gold.jsonl"
    gold.write_text((ROOT / "results" / "gold_set.jsonl").read_text() + "\n ")
    problems = gate_problems(_rows(), gold_path=gold)
    assert any(p.startswith("STALE gold set") for p in problems), problems


def test_cli_fails_on_a_hand_edited_pinned_run(tmp_path, capsys):
    rows = _rows()
    r = _answered(rows)[0]
    r["answer"] = r["answer"].replace(f"[{extract_cited_labels(r['answer'])[0]}", "[C99", 1)
    run = tmp_path / "pinned_run.jsonl"
    run.write_text("".join(json.dumps(x) + "\n" for x in rows))
    code = cli.main(
        [
            "--run",
            str(run),
            "--check",
            str(THRESHOLDS),
            "--out-dir",
            str(tmp_path / "out"),
        ]
    )
    out = capsys.readouterr().out
    assert code == 1
    assert "FAITHFULNESS REGRESSION CHECK FAILED" in out
    assert "invalid_citations" in out and "pinned run changed" in out


def test_write_thresholds_refuses_to_self_certify_a_regression(tmp_path, capsys):
    """Recalibrating on a worse run must not silently lower the bar."""
    rows = _rows()
    for r in _answered(rows):
        for c in r["judge"]["claims"]:
            c["supported"] = False
    run = tmp_path / "pinned_run.jsonl"
    run.write_text("".join(json.dumps(x) + "\n" for x in rows))
    # Inside the repo root so the recorded path can be made relative.
    out = tmp_path / "thresholds.json"
    shutil.copy(THRESHOLDS, out)
    args = ["--run", str(run), "--write-thresholds", str(out), "--out-dir", str(tmp_path / "o")]
    assert cli.main(args) == 1
    assert "Refusing to recalibrate" in capsys.readouterr().out
    assert json.loads(out.read_text()) == _spec()  # unchanged


def test_thresholds_file_is_well_formed():
    spec = _spec()
    assert set(spec["floors"]) >= {"citation_validity", "refusal_recall", "faithfulness"}
    assert set(spec["ceilings"]) == {"hallucination_rate"}
    assert set(spec["max_violations"]) == set(F.VIOLATION_KINDS)
    assert spec["pinned_run"] == "results/faithfulness/pinned_run.jsonl"


def test_gate_module_imports_without_heavy_dependencies():
    # The CI gate job installs the package without torch/FAISS; the check path
    # must not import them.
    import subprocess

    code = (
        "import sys, finground.eval.faithfulness, importlib.util;"
        "spec = importlib.util.spec_from_file_location('c', sys.argv[1]);"
        "m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m);"
        "bad = [x for x in ('torch', 'faiss', 'sentence_transformers') if x in sys.modules];"
        "sys.exit(1 if bad else 0)"
    )
    script = str(Path(cli.__file__))
    assert subprocess.run([sys.executable, "-c", code, script]).returncode == 0
