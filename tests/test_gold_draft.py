"""Integrity checks for the draft gold-set expansion (results/gold_set_draft.jsonl).

The draft's evidence labels are checked against the full local corpus
(data/chunks.jsonl), which is gitignored, so the corpus test skips when the
corpus hasn't been built (e.g. in CI). Schema checks need only the draft file.
"""

from __future__ import annotations

import sys

import pytest

from finground.config import CONFIG
from finground.eval.datasets import load_gold_set

sys.path.insert(0, str(CONFIG.paths.root / "scripts"))
import check_gold_draft as cgd  # noqa: E402

pytestmark = pytest.mark.skipif(not cgd.DRAFT_PATH.exists(), reason="no draft gold set")


def test_draft_schema_is_valid():
    rows = cgd.load_draft()
    existing = {it.id for it in load_gold_set()}
    assert cgd.schema_problems(rows, existing) == []


@pytest.mark.skipif(not CONFIG.paths.chunks.exists(), reason="full corpus not built")
def test_every_draft_label_matches_the_corpus():
    rows = cgd.load_draft()
    corpus = cgd.load_corpus()
    missing = [
        (row["id"], ev["must_contain"])
        for row in rows
        for ev, hits in cgd.label_matches(row, corpus)
        if not hits
    ]
    assert not missing, missing


def test_only_approved_drafts_are_promoted(tmp_path):
    import make_gold_set as mgs

    rows = cgd.load_draft()[:3]
    rows[0]["status"] = "approved"
    path = tmp_path / "draft.jsonl"
    path.write_text("".join(__import__("json").dumps(r) + "\n" for r in rows))

    promoted = mgs.approved_draft_items(path)
    assert [i.id for i in promoted] == [rows[0]["id"]]
    assert not hasattr(promoted[0], "status")


def test_promoted_ids_do_not_count_as_collisions():
    rows = cgd.load_draft()[:2]
    rows[0]["status"] = "approved"
    problems = cgd.schema_problems(rows, {rows[0]["id"], rows[1]["id"]})
    assert problems == [f"{rows[1]['id']}: collides with an id in gold_set.jsonl"]
