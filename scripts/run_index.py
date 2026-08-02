#!/usr/bin/env python3
"""Build BM25 + FAISS dense indexes from data/chunks.jsonl."""

from __future__ import annotations

from finground.config import CONFIG
from finground.index import build_all
from finground.ingest import load_chunks


def main() -> int:
    if not CONFIG.paths.chunks.exists():
        print(f"No chunks at {CONFIG.paths.chunks}. Run `make ingest` first.")
        return 1
    chunks = load_chunks()
    print(f"Loaded {len(chunks)} chunks.")
    build_all(chunks)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
