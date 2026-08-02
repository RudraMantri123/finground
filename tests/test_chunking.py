"""Unit tests for chunking, sectioning, and provenance — all network-free."""

from __future__ import annotations

import tiktoken

from finground.ingest import (
    Company,
    build_chunk_records,
    chunk_text,
    split_into_sections,
)

ENC = tiktoken.get_encoding("cl100k_base")


def _make_text(n_words: int) -> str:
    return " ".join(f"word{i}" for i in range(n_words))


def test_chunk_text_respects_token_budget():
    text = _make_text(4000)
    chunks = chunk_text(text, chunk_tokens=500, overlap_tokens=75, encoding=ENC)
    assert len(chunks) > 1
    for chunk_str, _span in chunks:
        assert len(ENC.encode(chunk_str)) <= 500


def test_chunk_text_overlaps():
    text = _make_text(2000)
    chunks = chunk_text(text, chunk_tokens=200, overlap_tokens=50, encoding=ENC)
    # Consecutive chunks should share text because of the overlap.
    assert len(chunks) >= 3
    first_tail = chunks[0][0].split()[-10:]
    second_head = chunks[1][0].split()
    assert any(w in second_head for w in first_tail)


def test_chunk_text_spans_are_monotonic_and_in_bounds():
    text = _make_text(1500)
    chunks = chunk_text(text, chunk_tokens=300, overlap_tokens=60, encoding=ENC)
    prev_start = -1
    for _chunk_str, (start, end) in chunks:
        assert 0 <= start < end <= len(text)
        assert start > prev_start  # windows advance
        prev_start = start


def test_chunk_text_covers_full_text():
    text = _make_text(1200)
    chunks = chunk_text(text, chunk_tokens=250, overlap_tokens=50, encoding=ENC)
    # The last chunk should reach the end of the text.
    _last_str, (_start, end) = chunks[-1]
    assert end >= len(text) - 2  # allow tiny rounding from decode boundaries


def test_chunk_text_empty():
    assert chunk_text("", chunk_tokens=100, overlap_tokens=10) == []
    assert chunk_text("   \n  ", chunk_tokens=100, overlap_tokens=10) == []


def test_split_into_sections_prefers_body_over_toc():
    # A tiny table of contents followed by a long body for the same items.
    toc = "Item 1. Business 5 Item 1A. Risk Factors 12 "
    body = "Item 1. Business " + _make_text(300) + " Item 1A. Risk Factors " + _make_text(300)
    text = toc + body
    sections = split_into_sections(text)
    assert "Item 1. Business" in sections
    assert "Item 1A. Risk Factors" in sections
    # Body version wins: each section is long, not the ~2-word TOC entry.
    assert len(sections["Item 1. Business"].split()) > 50
    assert len(sections["Item 1A. Risk Factors"].split()) > 50


def test_split_into_sections_no_items_returns_full():
    text = "This filing has no recognizable item headers at all."
    sections = split_into_sections(text)
    assert list(sections) == ["Full Filing"]


def test_build_chunk_records_attaches_provenance():
    company = Company("TEST", "Test Corp", "0000000001")
    sections = {"Item 1A. Risk Factors": _make_text(800)}
    records = build_chunk_records(
        company=company,
        filing_type="10-K",
        filing_date="2024-02-15",
        accession="0000000001-24-000001",
        sections=sections,
    )
    assert records, "expected at least one chunk"
    for r in records:
        assert r.company == "Test Corp"
        assert r.ticker == "TEST"
        assert r.cik == "0000000001"
        assert r.filing_type == "10-K"
        assert r.filing_date == "2024-02-15"
        assert r.section == "Item 1A. Risk Factors"
        assert r.text
        assert r.span[0] < r.span[1]
        assert r.chunk_id.startswith("TEST-10-K-2024-c")
        assert r.doc_id == "TEST-10-K-0000000001-24-000001"
    # chunk_ids are unique
    ids = [r.chunk_id for r in records]
    assert len(ids) == len(set(ids))
