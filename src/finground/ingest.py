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

import requests
import tiktoken
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

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
        body = text[start:next_start].strip()
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


def chunk_text(
    text: str,
    *,
    chunk_tokens: int = 500,
    overlap_tokens: int = 75,
    encoding: tiktoken.Encoding | None = None,
) -> list[tuple[str, tuple[int, int]]]:
    """Split ``text`` into overlapping token windows.

    Returns a list of ``(chunk_text, (start_char, end_char))`` where the char
    span is measured within ``text``. Windows are ``chunk_tokens`` long with
    ``overlap_tokens`` of overlap between consecutive windows. The char spans
    are exact because they are derived by decoding token prefixes of the same
    encoding used to split.
    """
    if chunk_tokens <= 0:
        raise ValueError("chunk_tokens must be positive")
    if not 0 <= overlap_tokens < chunk_tokens:
        raise ValueError("overlap_tokens must be in [0, chunk_tokens)")

    enc = encoding or _encoding()
    text = text.strip()
    if not text:
        return []

    tokens = enc.encode(text)
    if not tokens:
        return []

    step = chunk_tokens - overlap_tokens
    chunks: list[tuple[str, tuple[int, int]]] = []
    start = 0
    n = len(tokens)
    while start < n:
        window = tokens[start : start + chunk_tokens]
        chunk_str = enc.decode(window)
        start_char = len(enc.decode(tokens[:start]))
        end_char = start_char + len(chunk_str)
        stripped = chunk_str.strip()
        if stripped:
            chunks.append((stripped, (start_char, end_char)))
        if start + chunk_tokens >= n:
            break
        start += step
    return chunks


def build_chunk_records(
    *,
    company: Company,
    filing_type: str,
    filing_date: str,
    accession: str,
    sections: dict[str, str],
    chunk_tokens: int = 500,
    overlap_tokens: int = 75,
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


def html_to_text(html: str) -> str:
    """Extract readable text from a filing's primary HTML document."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style"]):
        tag.decompose()
    # Table cells joined by spaces keep numbers legible; blocks separated.
    text = soup.get_text(separator=" ")
    # Normalize whitespace: collapse runs, but keep it readable.
    text = re.sub(r"[ \t ]+", " ", text)
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


def latest_filing_ref(cik: str, form: str = "10-K") -> FilingRef | None:
    """Look up the most recent filing of ``form`` for ``cik`` via EDGAR."""
    cik10 = cik.zfill(10)
    url = f"https://data.sec.gov/submissions/CIK{cik10}.json"
    resp = _session().get(url, timeout=30)
    resp.raise_for_status()
    recent = resp.json().get("filings", {}).get("recent", {})
    forms = recent.get("form", [])
    for i, f in enumerate(forms):
        if f == form:
            return FilingRef(
                accession=recent["accessionNumber"][i],
                primary_document=recent["primaryDocument"][i],
                filing_date=recent["filingDate"][i],
                form=f,
            )
    return None


def fetch_filing_html(cik: str, ref: FilingRef) -> str:
    """Download the primary HTML document for a filing."""
    acc_nodash = ref.accession.replace("-", "")
    cik_int = str(int(cik))
    url = f"https://www.sec.gov/Archives/edgar/data/{cik_int}/{acc_nodash}/{ref.primary_document}"
    resp = _session().get(url, timeout=60)
    resp.raise_for_status()
    return resp.text


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def ingest_company(
    company: Company, form: str = "10-K", *, polite_delay: float = 0.5
) -> list[Chunk]:
    """Download, parse, and chunk the latest ``form`` filing for one company."""
    ref = latest_filing_ref(company.cik, form)
    if ref is None:
        raise RuntimeError(f"No {form} found for {company.ticker}")
    time.sleep(polite_delay)  # be gentle with EDGAR
    html = fetch_filing_html(company.cik, ref)
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


def ingest_all(companies: list[Company] | None = None, form: str = "10-K") -> list[Chunk]:
    """Ingest every company in the curated set (or a provided subset)."""
    companies = companies or COMPANIES
    all_chunks: list[Chunk] = []
    for company in companies:
        try:
            chunks = ingest_company(company, form)
            all_chunks.extend(chunks)
            print(f"  {company.ticker}: {len(chunks)} chunks")
        except Exception as exc:  # noqa: BLE001 — report and continue
            print(f"  {company.ticker}: FAILED — {exc}")
    return all_chunks
