"""Table-preserving ingest: SEC-style HTML tables -> Markdown, and table-aware
chunking. Network-free; the HTML mimics Workiva/EDGAR output (spacer cells,
colspan headers, "$" and ")" in their own cells, inline-XBRL number tags)."""

from __future__ import annotations

import tiktoken
from bs4 import BeautifulSoup

from finground.ingest import chunk_text, html_to_text, table_to_markdown

ENC = tiktoken.get_encoding("cl100k_base")

SEC_TABLE = """
<table>
  <tr><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr>
  <tr><td></td><td colspan="7" style="text-align:center">Years ended</td></tr>
  <tr>
    <td></td>
    <td colspan="3">September 27, 2025</td><td></td>
    <td colspan="3">September 28, 2024</td>
  </tr>
  <tr><td>Net sales:</td><td colspan="3"></td><td></td><td colspan="3"></td></tr>
  <tr>
    <td>Products</td>
    <td>$</td><td><ix:nonFraction>307,003</ix:nonFraction></td><td></td><td>&#160;</td>
    <td>$</td><td>294,866</td><td></td>
  </tr>
  <tr>
    <td>Other income/(expense), net</td>
    <td>(</td><td>321</td><td>)</td><td></td>
    <td colspan="2">269</td><td></td>
  </tr>
  <tr>
    <td>Interest expense</td>
    <td colspan="2">(<span>1,234</span>)</td><td></td><td></td>
    <td colspan="2">&#8212;</td><td></td>
  </tr>
  <tr><td>Gross margin %</td><td colspan="2">46.9</td><td>%</td><td></td>
      <td colspan="2">46.2</td><td>%</td></tr>
  <tr><td></td><td></td><td></td><td></td><td></td><td></td><td></td><td></td></tr>
</table>
"""


def _md(html: str) -> str:
    return table_to_markdown(BeautifulSoup(html, "lxml").find("table"))


def test_sec_table_becomes_markdown():
    lines = _md(SEC_TABLE).splitlines()
    # Grouping header ("Years ended") folds into the first value column header;
    # spacer columns and all-empty rows disappear.
    assert lines[0] == "| | Years ended September 27, 2025 | September 28, 2024 |"
    assert lines[1] == "| --- | --- | --- |"
    assert lines[2] == "| Net sales: | | |"
    assert lines[3] == "| Products | $307,003 | $294,866 |"
    # Paren negatives stay attached whether split across cells or ix-tagged.
    assert lines[4] == "| Other income/(expense), net | (321) | 269 |"
    assert lines[5] == "| Interest expense | (1,234) | — |"
    assert lines[6] == "| Gross margin % | 46.9% | 46.2% |"
    assert len(lines) == 7


def test_header_falls_back_to_first_row_and_pipes_escaped():
    html = (
        "<table><tr><td>Name</td><td>Age</td><td>Position</td></tr>"
        "<tr><td>Jane Doe</td><td>52</td><td>CFO | Treasurer</td></tr></table>"
    )
    assert _md(html).splitlines() == [
        "| Name | Age | Position |",
        "| --- | --- | --- |",
        "| Jane Doe | 52 | CFO \\| Treasurer |",
    ]


def test_layout_tables_become_plain_lines():
    bullets = (
        "<table><tr><td>•</td><td>Supply chain risk.</td></tr>"
        "<tr><td>•</td><td>Currency risk.</td></tr></table>"
    )
    assert _md(bullets) == "• Supply chain risk.\n• Currency risk."
    single = "<table><tr><td>Item 7. Management's Discussion</td></tr></table>"
    assert _md(single) == "Item 7. Management's Discussion"
    heading = "<table><tr><td>Item 1A.</td><td></td><td>Risk Factors</td></tr></table>"
    assert _md(heading) == "Item 1A. Risk Factors"


def test_html_to_text_puts_tables_on_their_own_lines():
    html = f"<html><body><p>The following table shows net sales:</p>{SEC_TABLE}<p>Next.</p></body></html>"
    text = html_to_text(html)
    lines = text.splitlines()
    assert lines[0] == "The following table shows net sales:"
    assert lines[1].startswith("| | Years ended")
    assert lines[-1] == "Next."
    assert "| Products | $307,003 | $294,866 |" in lines


# -- chunking ---------------------------------------------------------------


def _words(n: int, tag: str = "w") -> str:
    return " ".join(f"{tag}{i}" for i in range(n))


def _table(n_rows: int) -> str:
    rows = [f"| Line item {i} | {i * 1000:,} | ({i}) |" for i in range(n_rows)]
    return "\n".join(["| | 2025 | 2024 |", "| --- | --- | --- |", *rows])


def test_small_table_is_never_split():
    table = _table(16)  # ~255 tokens: fits a 300-token chunk, not with the prose
    text = f"{_words(200)}\n{table}\n{_words(200, 'x')}"
    chunks = chunk_text(text, chunk_tokens=300, overlap_tokens=50, encoding=ENC)
    holders = [c for c, _ in chunks if "| Line item 0 |" in c]
    assert holders, "table missing from chunks"
    # Every chunk that has any table row has the whole table.
    for c, _ in chunks:
        if "| Line item" in c:
            assert table in c
    for c, (s, e) in chunks:
        assert len(ENC.encode(c)) <= 300
        assert c == text[s:e].strip()  # spans stay exact substrings
    # Prose is still fully covered: first and last words both appear.
    joined = " ".join(c for c, _ in chunks)
    assert "w0" in joined and "x199" in joined


def test_big_table_splits_on_rows_and_repeats_header():
    table = _table(120)  # well over one 200-token chunk
    text = f"Intro sentence.\n{table}\nClosing sentence."
    chunks = chunk_text(text, chunk_tokens=200, overlap_tokens=40, encoding=ENC)
    table_chunks = [c for c, _ in chunks if "| Line item" in c]
    assert len(table_chunks) > 2
    header = "| | 2025 | 2024 |\n| --- | --- | --- |"
    seen_rows: set[str] = set()
    for c, (s, e) in chunks:
        assert len(ENC.encode(c)) <= 200
        for line in c.splitlines():
            if line.startswith("| Line item"):
                # Whole rows only, and every row lives under the header.
                assert line.endswith(" |")
                seen_rows.add(line)
        if "| Line item" in c:
            assert header in c
            body = c.split(header, 1)[1].strip() if c.startswith(header) else c
            assert body in text[s:e]  # span covers the rows (header is re-attached)
    assert len(seen_rows) == 120


def test_plain_prose_chunking_unchanged():
    # Without tables the windows are the classic sliding window: chunk k starts
    # exactly (chunk_tokens - overlap) * k tokens in.
    text = _words(1000)
    chunks = chunk_text(text, chunk_tokens=200, overlap_tokens=50, encoding=ENC)
    toks = ENC.encode(text)
    for k, (c, _span) in enumerate(chunks):
        assert c == ENC.decode(toks[k * 150 : k * 150 + 200]).strip()
