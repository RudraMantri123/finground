"""Ingestion: download SEC 10-K filings, parse them into sections, and chunk.

The output is a JSONL file of chunk records, each carrying full **provenance**
back to a specific filing and section. Provenance is the whole point of
FinGround — every retrieved chunk and every citation must trace to a source.

Pure functions (``chunk_text``, ``split_into_sections``, ``build_chunk_records``)
are network-free and unit-tested. Network functions live behind ``fetch_*``.
"""

from __future__ import annotations

import json
import re
import time
import warnings
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path

import requests
import tiktoken
from bs4 import BeautifulSoup, NavigableString, XMLParsedAsHTMLWarning

from .config import CONFIG

# Some filings ship their primary document as inline-XBRL XML; the lxml HTML
# parser still extracts the text fine, so silence the cosmetic warning.
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# ---------------------------------------------------------------------------
# Curated company set. CIKs are hard-coded so ingestion does not depend on a
# ticker-lookup round-trip. These are large, well-known filers with rich
# risk-factor and MD&A sections — good material for financial QA.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Company:
    ticker: str
    name: str
    cik: str  # 10-digit zero-padded


COMPANIES: list[Company] = [
    Company("AAPL", "Apple Inc.", "0000320193"),
    Company("MSFT", "Microsoft Corporation", "0000789019"),
    Company("AMZN", "Amazon.com, Inc.", "0001018724"),
    Company("GOOGL", "Alphabet Inc.", "0001652044"),
    Company("NVDA", "NVIDIA Corporation", "0001045810"),
    Company("TSLA", "Tesla, Inc.", "0001318605"),
    Company("JPM", "JPMorgan Chase & Co.", "0000019617"),
    Company("KO", "The Coca-Cola Company", "0000021344"),
]


# ---------------------------------------------------------------------------
# Chunk record schema
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Chunk:
    """A retrievable unit of text with provenance back to its source filing."""

    chunk_id: str  # stable, unique, e.g. "AAPL-10K-2023-c0007"
    doc_id: str  # filing identifier, e.g. "AAPL-10-K-0000320193-23-000106"
    company: str
    ticker: str
    cik: str
    filing_type: str
    filing_date: str
    section: str  # human-readable section label, e.g. "Item 1A. Risk Factors"
    span: tuple[int, int]  # [start_char, end_char] within the section text
    text: str

    def to_json(self) -> dict:
        d = asdict(self)
        d["span"] = list(self.span)
        return d


# ---------------------------------------------------------------------------
# Sectioning: split 10-K text into Item sections
# ---------------------------------------------------------------------------

# Canonical 10-K item labels for nicer section names.
_ITEM_NAMES: dict[str, str] = {
    "1": "Item 1. Business",
    "1A": "Item 1A. Risk Factors",
    "1B": "Item 1B. Unresolved Staff Comments",
    "1C": "Item 1C. Cybersecurity",
    "2": "Item 2. Properties",
    "3": "Item 3. Legal Proceedings",
    "4": "Item 4. Mine Safety Disclosures",
    "5": "Item 5. Market for Registrant's Common Equity",
    "6": "Item 6. Selected Financial Data",
    "7": "Item 7. Management's Discussion and Analysis",
    "7A": "Item 7A. Quantitative and Qualitative Disclosures About Market Risk",
    "8": "Item 8. Financial Statements and Supplementary Data",
    "9": "Item 9. Changes in and Disagreements with Accountants",
    "9A": "Item 9A. Controls and Procedures",
    "9B": "Item 9B. Other Information",
    "10": "Item 10. Directors, Executive Officers and Corporate Governance",
    "11": "Item 11. Executive Compensation",
    "12": "Item 12. Security Ownership",
    "13": "Item 13. Certain Relationships and Related Transactions",
    "14": "Item 14. Principal Accountant Fees and Services",
    "15": "Item 15. Exhibits and Financial Statement Schedules",
}

# Match "Item 1A", "Item 7", "ITEM 1B." etc. Capture the item key.
_ITEM_RE = re.compile(r"(?i)\bitem\s+(\d{1,2}[abc]?)[\.\s—:)-]")


def _norm_item_key(raw: str) -> str:
    return raw.upper()


def split_into_sections(text: str) -> dict[str, str]:
    """Split filing text into ``{section_label: text}`` keyed by 10-K item.

    10-K filings typically contain each item marker twice: once in the table of
    contents, once at the real section body. We disambiguate by keeping, for
    each item, the occurrence whose following segment is longest (the body),
    which reliably beats the short TOC entry. If no item markers are found the
    whole document is returned as a single ``"Full Filing"`` section.
    """
    matches = list(_ITEM_RE.finditer(text))
    if not matches:
        return {"Full Filing": text.strip()} if text.strip() else {}

    positions = [m.start() for m in matches]
    # For each match, the segment runs until the next match (or end of text).
    ends = positions[1:] + [len(text)]

    # For each item key, keep the occurrence with the longest following segment.
    best: dict[str, tuple[int, int]] = {}  # key -> (start, end) of longest segment
    for m, start, end in zip(matches, positions, ends, strict=True):
        key = _norm_item_key(m.group(1))
        seg_len = end - start
        if key not in best or seg_len > (best[key][1] - best[key][0]):
            best[key] = (start, end)

    # Recompute each chosen section's true end as the next *chosen* start, so
    # sections do not bleed into a later item's TOC-length duplicate.
    chosen = sorted(best.items(), key=lambda kv: kv[1][0])  # by start pos
    sections: dict[str, str] = {}
    for i, (key, (start, _end)) in enumerate(chosen):
        next_start = chosen[i + 1][1][0] if i + 1 < len(chosen) else len(text)
        # An item marker inside a Markdown row (e.g. the table of contents)
        # leaves the row's opening "|" dangling at the end of the prior section.
        body = text[start:next_start].strip().removesuffix("|").rstrip()
        if not body:
            continue
        label = _ITEM_NAMES.get(key, f"Item {key}")
        sections[label] = body
    return sections


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

_ENCODING_NAME = "cl100k_base"


def _encoding() -> tiktoken.Encoding:
    return tiktoken.get_encoding(_ENCODING_NAME)


# A Markdown table line as emitted by :func:`table_to_markdown`.
_TABLE_LINE_RE = re.compile(r"^\|.*\|[ \t]*$")
_TABLE_SEP_RE = re.compile(r"^\|(?:\s*:?-{3,}:?\s*\|)+[ \t]*$")


@dataclass(frozen=True)
class _Segment:
    """A contiguous slice of section text: prose, or one Markdown table."""

    start: int
    end: int
    is_table: bool


def _segments(text: str) -> list[_Segment]:
    """Split text into alternating prose / Markdown-table segments.

    A table is a maximal run of lines that start and end with ``|``; its
    segment includes the trailing newline so prose segments stay clean.
    """
    segs: list[_Segment] = []
    pos = 0
    table_start: int | None = None
    prose_start = 0
    for line in text.splitlines(keepends=True):
        is_tbl = bool(_TABLE_LINE_RE.match(line.rstrip("\n")))
        if is_tbl and table_start is None:
            if pos > prose_start:
                segs.append(_Segment(prose_start, pos, False))
            table_start = pos
        elif not is_tbl and table_start is not None:
            segs.append(_Segment(table_start, pos, True))
            table_start = None
            prose_start = pos
        pos += len(line)
    if table_start is not None:
        segs.append(_Segment(table_start, pos, True))
    elif pos > prose_start:
        segs.append(_Segment(prose_start, pos, False))
    return segs


def chunk_text(
    text: str,
    *,
    chunk_tokens: int = 500,
    overlap_tokens: int = 100,
    encoding: tiktoken.Encoding | None = None,
) -> list[tuple[str, tuple[int, int]]]:
    """Split ``text`` into overlapping token windows that respect tables.

    Returns a list of ``(chunk_text, (start_char, end_char))`` where the char
    span is measured within ``text``. Prose is cut into ``chunk_tokens`` windows
    with ``overlap_tokens`` of overlap, exactly as a plain sliding window.

    Markdown tables are treated as atoms: a financial statement cut in half
    leaves one chunk with the line items and another with the numbers, and
    neither can answer a question on its own. So a window never ends inside a
    table that fits the budget; it either stops before the table or slides its
    start forward (shrinking overlap, never skipping unseen text) so the whole
    table fits. Tables larger than a chunk are split on row boundaries, and
    every continuation chunk gets the table's header row prepended so its
    columns stay interpretable. In that one case the chunk text is the header
    plus ``text[start:end]``; otherwise it is exactly that substring (stripped).
    """
    if chunk_tokens <= 0:
        raise ValueError("chunk_tokens must be positive")
    if not 0 <= overlap_tokens < chunk_tokens:
        raise ValueError("overlap_tokens must be in [0, chunk_tokens)")

    enc = encoding or _encoding()
    text = text.strip()
    if not text:
        return []

    # Tokenize segment-by-segment (tables line-by-line) so every segment and
    # table-row boundary is also a token boundary. Concatenated, the tokens
    # still decode to exactly ``text``.
    tokens: list[int] = []
    # Atoms are token ranges a window must not cut: whole small tables, or row
    # groups of big tables. ``atom_of[i]`` is the atom index of token i or -1.
    atom_of: list[int] = []
    atoms: list[tuple[int, int]] = []
    # Big tables: (continuation_start_tok, end_tok, header_text, header_tokens).
    big_tables: list[tuple[int, int, str, int]] = []

    def _add_atom(toks: list[int]) -> None:
        atoms.append((len(tokens), len(tokens) + len(toks)))
        atom_of.extend([len(atoms) - 1] * len(toks))
        tokens.extend(toks)

    for seg in _segments(text):
        seg_text = text[seg.start : seg.end]
        if not seg.is_table:
            toks = enc.encode(seg_text)
            tokens.extend(toks)
            atom_of.extend([-1] * len(toks))
            continue
        lines = seg_text.splitlines(keepends=True)
        line_toks = [enc.encode(ln) for ln in lines]
        total = sum(len(t) for t in line_toks)
        if total <= chunk_tokens:
            _add_atom([t for lt in line_toks for t in lt])
            continue
        # Big table: header (first row + separator) stays with the first group;
        # later groups get it re-attached at emission, so budget for it.
        n_hdr = 2 if len(lines) > 1 and _TABLE_SEP_RE.match(lines[1].rstrip("\n")) else 0
        header_text = "".join(lines[:n_hdr])
        hdr_toks = sum(len(t) for t in line_toks[:n_hdr])
        budget = chunk_tokens - hdr_toks
        group: list[int] = [t for lt in line_toks[:n_hdr] for t in lt]
        cont_start: int | None = None  # first token after the header's own group
        for lt in line_toks[n_hdr:]:
            if group and len(group) + len(lt) > budget:
                _add_atom(group)
                group = []
                if cont_start is None:
                    cont_start = len(tokens)
            if len(lt) > budget:  # a single oversized row: let windows cut it
                tokens.extend(lt)
                atom_of.extend([-1] * len(lt))
            else:
                group.extend(lt)
        if group:
            _add_atom(group)
        if n_hdr and cont_start is not None:
            big_tables.append((cont_start, len(tokens), header_text, hdr_toks))

    n = len(tokens)
    if not n:
        return []
    decoded, offsets = enc.decode_with_offsets(tokens)
    if decoded != text:  # pragma: no cover — guards the span invariant
        raise RuntimeError("segment tokenization did not round-trip")

    def _char(i: int) -> int:
        return offsets[i] if i < n else len(text)

    def _cuts(i: int) -> bool:  # True if a boundary at token i splits an atom
        return 0 < i < n and atom_of[i] != -1 and atom_of[i] == atom_of[i - 1]

    def _continued_table(i: int) -> tuple[str, int] | None:
        """Header to re-attach if a window starting at token i is mid-table."""
        for cont_start, end, hdr, hdr_n in big_tables:
            if cont_start <= i < end:
                return hdr, hdr_n
        return None

    chunks: list[tuple[str, tuple[int, int]]] = []
    start, prev_end = 0, 0
    while start < n:
        cont = _continued_table(start)
        budget = chunk_tokens - (cont[1] if cont else 0)
        end = min(start + budget, n)
        if _cuts(end):
            a0, a1 = atoms[atom_of[end]]
            slid = a1 - budget
            if _cuts(slid):  # never open a chunk on a partial table
                slid = atoms[atom_of[slid]][1]
            if start <= slid <= prev_end and _continued_table(slid) == cont:
                # Slide the window forward so the atom fits whole; only text
                # already emitted in the previous chunk is dropped from overlap.
                start, end = slid, a1
            elif a0 > start:
                end = a0
        s_char, e_char = _char(start), _char(end)
        body = text[s_char:e_char]
        stripped = body.strip()
        if stripped:
            if cont:
                stripped = cont[0] + stripped
            chunks.append((stripped, (s_char, e_char)))
        if end >= n:
            break
        prev_end = end
        nxt = end - overlap_tokens
        if nxt <= start:
            nxt = end
        if _cuts(nxt):  # overlap would begin mid-atom: skip to the atom's end
            nxt = atoms[atom_of[nxt]][1]
        start = nxt
    return chunks


def build_chunk_records(
    *,
    company: Company,
    filing_type: str,
    filing_date: str,
    accession: str,
    sections: dict[str, str],
    chunk_tokens: int = 500,
    overlap_tokens: int = 100,
) -> list[Chunk]:
    """Turn parsed sections into fully-provenanced :class:`Chunk` records."""
    enc = _encoding()
    doc_id = f"{company.ticker}-{filing_type}-{accession}"
    year = filing_date[:4] if filing_date else "----"
    records: list[Chunk] = []
    counter = 0
    for section_label, section_text in sections.items():
        for chunk_str, span in chunk_text(
            section_text,
            chunk_tokens=chunk_tokens,
            overlap_tokens=overlap_tokens,
            encoding=enc,
        ):
            chunk_id = f"{company.ticker}-{filing_type}-{year}-c{counter:04d}"
            records.append(
                Chunk(
                    chunk_id=chunk_id,
                    doc_id=doc_id,
                    company=company.name,
                    ticker=company.ticker,
                    cik=company.cik,
                    filing_type=filing_type,
                    filing_date=filing_date,
                    section=section_label,
                    span=span,
                    text=chunk_str,
                )
            )
            counter += 1
    return records


# ---------------------------------------------------------------------------
# HTML parsing
# ---------------------------------------------------------------------------


# Cells that are only a currency sign / opening paren belong to the number on
# their right; a lone ")" or "%" belongs to the number on its left. SEC filings
# (Workiva, Toppan Merrill, ...) put each of these in its own <td>.
_PREFIX_CELL_RE = re.compile(r"^[\$€£¥(]+$")
_SUFFIX_CELL_RE = re.compile(r"^(?:\)|%|\)%|%\))$")
_NUMERIC_CELL_RE = re.compile(r"^[\$€£¥(]*\s*-?[\d,.]+\s*\)?%?$|^[—–-]+$")


def _cell_text(cell) -> str:
    text = cell.get_text(" ", strip=True).replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    # Inline-XBRL wraps the digits in their own tag, so "(" 321 ")" arrive as
    # separate strings; re-attach signs and parens to the number they mark.
    text = re.sub(r"([\$€£¥(])\s+(?=[\d.(])", r"\1", text)
    text = re.sub(r"(?<=[\d%])\s+(?=\))", "", text)
    return text.replace("|", "\\|")


def _row_cells(tr) -> list[tuple[str, int, int]]:
    """Non-empty logical cells of a row as ``(text, first_col, last_col)``.

    Column indices come from expanding ``colspan`` so cells in different rows
    can be aligned; currency/paren marker cells are fused into their number.
    """
    raw: list[tuple[str, int, int]] = []
    col = 0
    for cell in tr.find_all(["td", "th"], recursive=False):
        try:
            span = max(1, int(cell.get("colspan", 1)))
        except (TypeError, ValueError):
            span = 1
        text = _cell_text(cell)
        if text:
            raw.append((text, col, col + span - 1))
        col += span
    fused: list[tuple[str, int, int]] = []
    pending: tuple[str, int] | None = None  # prefix text + its first column
    for text, c0, c1 in raw:
        if _PREFIX_CELL_RE.match(text):
            pending = (pending[0] + text, pending[1]) if pending else (text, c0)
            continue
        if pending:
            text, c0 = pending[0] + text, pending[1]
            pending = None
        if _SUFFIX_CELL_RE.match(text) and fused:
            prev, p0, _p1 = fused[-1]
            fused[-1] = (prev + text, p0, c1)
            continue
        fused.append((text, c0, c1))
    if pending:
        fused.append((pending[0], pending[1], pending[1]))
    return fused


def _column_slots(rows: list[list[tuple[str, int, int]]]) -> list[tuple[int, int]]:
    """Cluster cell column-ranges into the table's logical columns.

    A cell spanning two or more disjoint ranges (e.g. "Years ended" over three
    fiscal-year columns) is a grouping header, not a column, so it is ignored
    here; spacer cells are already gone, so their columns simply vanish.
    """
    spans = sorted({(c0, c1) for row in rows for _t, c0, c1 in row})

    def _overlaps(a: tuple[int, int], b: tuple[int, int]) -> bool:
        return a[0] <= b[1] and b[0] <= a[1]

    def _is_grouping(sp: tuple[int, int]) -> bool:
        inner = [o for o in spans if o != sp and _overlaps(o, sp)]
        return any(not _overlaps(x, y) for i, x in enumerate(inner) for y in inner[i + 1 :])

    slots: list[list[int]] = []
    for sp in (sp for sp in spans if not _is_grouping(sp)):
        if slots and sp[0] <= slots[-1][1]:
            slots[-1][1] = max(slots[-1][1], sp[1])
        else:
            slots.append([sp[0], sp[1]])
    return [(a, b) for a, b in slots]


def table_to_markdown(table) -> str:
    """Render one HTML ``<table>`` as a Markdown table (or plain lines).

    Flattening a financial statement with ``get_text`` interleaves line items
    and numbers into an unreadable stream, and the model then misattributes
    figures to years or rows. Markdown keeps each value on its row and under
    its column header, which both the retriever and the answerer can read.

    Leading rows with an empty first cell (the fiscal-year headings in SEC
    statements) or made of ``<th>`` are merged into the header; if there are
    none the first row serves as header. Layout-only tables (one logical
    column, a single row such as an "Item 1A. | Risk Factors" heading, or
    bullet/footnote-marker + text) are emitted as plain lines.
    """
    rows: list[list[tuple[str, int, int]]] = []
    th_rows: list[bool] = []  # row made only of <th> cells
    for tr in table.find_all("tr"):
        cells = _row_cells(tr)
        if cells:
            rows.append(cells)
            th_rows.append(not tr.find_all("td", recursive=False))
    if not rows:
        return ""
    slots = _column_slots(rows)
    if not slots:
        return ""

    def _slot_of(c0: int, c1: int) -> int:
        for i, (a, b) in enumerate(slots):
            if c0 <= b and a <= c1:
                return i
        return len(slots) - 1

    grid: list[list[str]] = []
    for row in rows:
        out = [""] * len(slots)
        for text, c0, c1 in row:
            i = _slot_of(c0, c1)
            out[i] = f"{out[i]} {text}".strip()
        grid.append(out)

    width = len(slots)
    if (
        width == 1
        or len(grid) == 1
        or (width == 2 and all(len(r[0]) <= 4 and not _NUMERIC_CELL_RE.match(r[1]) for r in grid))
    ):
        return "\n".join(" ".join(c for c in r if c) for r in grid)

    n_head = 0
    for cells, is_th in zip(grid, th_rows, strict=True):
        if cells[0] and not is_th:  # a row label: the header block is over
            break
        n_head += 1
    if n_head == 0 or n_head == len(grid):
        n_head = 1

    def _line(cells: list[str]) -> str:
        return "|" + "".join(f" {c} |" if c else " |" for c in cells)

    header = [" ".join(c for c in col if c) for col in zip(*grid[:n_head], strict=True)]
    lines = [_line(header), "|" + " --- |" * width]
    lines += [_line(r) for r in grid[n_head:]]
    return "\n".join(lines)


def html_to_text(html: str) -> str:
    """Extract readable text from a filing's primary HTML document.

    Tables become Markdown (see :func:`table_to_markdown`) on their own lines so
    the chunker can recognise and keep them whole; everything else is flattened
    to whitespace-normalised text as before.
    """
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    # Innermost tables first so a nested table is rendered before its parent.
    for table in reversed(soup.find_all("table")):
        md = table_to_markdown(table)
        table.replace_with(NavigableString(f"\n{md}\n" if md else " "))
    text = soup.get_text(separator=" ")
    # Normalize whitespace: collapse runs, but keep it readable.
    text = re.sub(r"[ \t\xa0]+", " ", text)
    text = re.sub(r"\s*\n\s*", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ---------------------------------------------------------------------------
# EDGAR REST API access
# ---------------------------------------------------------------------------

_SEC_SESSION: requests.Session | None = None


def _session() -> requests.Session:
    global _SEC_SESSION
    if _SEC_SESSION is None:
        s = requests.Session()
        s.headers.update({"User-Agent": CONFIG.sec_user_agent, "Accept-Encoding": "gzip, deflate"})
        _SEC_SESSION = s
    return _SEC_SESSION


@dataclass(frozen=True)
class FilingRef:
    accession: str  # e.g. "0000320193-23-000106"
    primary_document: str  # e.g. "aapl-20230930.htm"
    filing_date: str
    form: str


def latest_filing_ref(
    cik: str, form: str = "10-K", *, accession: str | None = None
) -> FilingRef | None:
    """Look up the most recent filing of ``form`` for ``cik`` via EDGAR.

    ``accession`` pins a specific filing instead of "latest": "latest" drifts as
    companies file new 10-Ks, and a rebuild that silently switches fiscal years
    would invalidate the gold set's answers.
    """
    cik10 = cik.zfill(10)
    url = f"https://data.sec.gov/submissions/CIK{cik10}.json"
    resp = _session().get(url, timeout=30)
    resp.raise_for_status()
    recent = resp.json().get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    for i, f in enumerate(forms):
        if f == form and (accession is None or recent["accessionNumber"][i] == accession):
            return FilingRef(
                accession=recent["accessionNumber"][i],
                primary_document=recent["primaryDocument"][i],
                filing_date=recent["filingDate"][i],
                form=f,
            )
    return None


def _cached_filing_path(ticker: str, ref: FilingRef) -> Path:
    return CONFIG.paths.filings / f"{ticker}-{ref.accession}.htm"


def fetch_filing_html(cik: str, ref: FilingRef, *, ticker: str | None = None) -> str:
    """Return the primary HTML document for a filing, downloading at most once.

    With ``ticker`` given, the raw HTML is cached under ``data/filings`` so that
    re-parsing (e.g. after a change to table extraction) does not re-hit EDGAR.
    Filings are immutable once accepted, so the cache never goes stale.
    """
    cache = _cached_filing_path(ticker, ref) if ticker else None
    if cache is not None and cache.exists():
        return cache.read_text(encoding="utf-8")
    acc_nodash = ref.accession.replace("-", "")
    cik_int = str(int(cik))
    url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_nodash}/{ref.primary_document}"
    resp = _session().get(url, timeout=60)
    resp.raise_for_status()
    if cache is not None:
        CONFIG.paths.ensure()
        cache.write_text(resp.text, encoding="utf-8")
        cache.with_suffix(".json").write_text(json.dumps(asdict(ref)), encoding="utf-8")
    return resp.text


def _cached_filing_ref(ticker: str, accession: str) -> FilingRef | None:
    """Filing metadata saved next to a cached document, so a pinned re-ingest
    of already-downloaded filings needs no network at all."""
    meta = CONFIG.paths.filings / f"{ticker}-{accession}.json"
    if not meta.exists():
        return None
    return FilingRef(**json.loads(meta.read_text(encoding="utf-8")))


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def ingest_company(
    company: Company,
    form: str = "10-K",
    *,
    accession: str | None = None,
    polite_delay: float = 0.5,
) -> list[Chunk]:
    """Download, parse, and chunk the latest (or a pinned) ``form`` filing."""
    ref = _cached_filing_ref(company.ticker, accession) if accession else None
    if ref is None:
        ref = latest_filing_ref(company.cik, form, accession=accession)
        if ref is None:
            raise RuntimeError(f"No {form} found for {company.ticker} (accession={accession})")
        time.sleep(polite_delay)  # be gentle with EDGAR
    html = fetch_filing_html(company.cik, ref, ticker=company.ticker)
    text = html_to_text(html)
    sections = split_into_sections(text)
    return build_chunk_records(
        company=company,
        filing_type=form,
        filing_date=ref.filing_date,
        accession=ref.accession,
        sections=sections,
        chunk_tokens=CONFIG.retrieval.chunk_tokens,
        overlap_tokens=CONFIG.retrieval.chunk_overlap_tokens,
    )


def write_chunks(chunks: Iterable[Chunk], path=None) -> int:
    """Persist chunk records as JSONL. Returns the number written."""
    path = path or CONFIG.paths.chunks
    CONFIG.paths.ensure()
    count = 0
    with open(path, "w", encoding="utf-8") as fh:
        for c in chunks:
            fh.write(json.dumps(c.to_json(), ensure_ascii=False) + "\n")
            count += 1
    return count


def load_chunks(path=None) -> list[dict]:
    """Load chunk records from JSONL."""
    path = path or CONFIG.paths.chunks
    records: list[dict] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def pinned_accessions(chunks_path=None) -> dict[str, str]:
    """``{ticker: accession}`` of the filings behind an existing chunks file.

    Lets a re-ingest reproduce exactly the filings the current indexes (and the
    gold set written against them) were built from.
    """
    pins: dict[str, str] = {}
    for rec in load_chunks(chunks_path):
        prefix = f"{rec['ticker']}-{rec['filing_type']}-"
        pins.setdefault(rec["ticker"], rec["doc_id"].removeprefix(prefix))
    return pins


def ingest_all(
    companies: list[Company] | None = None,
    form: str = "10-K",
    *,
    accessions: dict[str, str] | None = None,
) -> list[Chunk]:
    """Ingest every company in the curated set (or a provided subset)."""
    companies = companies or COMPANIES
    accessions = accessions or {}
    all_chunks: list[Chunk] = []
    for company in companies:
        try:
            chunks = ingest_company(company, form, accession=accessions.get(company.ticker))
            all_chunks.extend(chunks)
            print(f"  {company.ticker}: {len(chunks)} chunks")
        except Exception as exc:  # noqa: BLE001 — report and continue
            print(f"  {company.ticker}: FAILED — {exc}")
    return all_chunks
