#!/usr/bin/env python3
"""Download + parse + chunk SEC filings, writing chunks to data/chunks.jsonl.

Usage:
    python scripts/run_ingest.py                 # all curated companies
    python scripts/run_ingest.py AAPL MSFT       # a subset by ticker
"""

from __future__ import annotations

import sys

from finground.config import CONFIG
from finground.ingest import COMPANIES, ingest_all, write_chunks


def main(argv: list[str]) -> int:
    tickers = {t.upper() for t in argv}
    companies = [c for c in COMPANIES if not tickers or c.ticker in tickers]
    if not companies:
        print(
            f"No matching companies for {sorted(tickers)}. Known: {[c.ticker for c in COMPANIES]}"
        )
        return 1

    print(f"Ingesting {len(companies)} companies from SEC EDGAR...")
    print(f"  User-Agent: {CONFIG.sec_user_agent}")
    chunks = ingest_all(companies)
    if not chunks:
        print("No chunks produced. Check network / User-Agent.")
        return 1

    n = write_chunks(chunks)
    print(f"\nWrote {n} chunks to {CONFIG.paths.chunks}")
    sections = {c.section for c in chunks}
    print(f"Companies: {len({c.ticker for c in chunks})}  |  distinct sections: {len(sections)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
