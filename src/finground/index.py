"""Build the sparse (BM25) and dense (FAISS + BGE) indexes over chunk records.

Both indexes are row-aligned to the same ordered list of chunks, so a row index
returned by either retriever maps back to the exact same provenanced chunk.
"""

from __future__ import annotations

import json
import pickle
import re
from pathlib import Path

import faiss
import numpy as np
from rank_bm25 import BM25Okapi

from .config import CONFIG

# BGE retrieval instruction: prepended to *queries* only (not passages).
BGE_QUERY_INSTRUCTION = "Represent this sentence for searching relevant passages: "

_TOKEN_RE = re.compile(r"[a-z0-9]+")

# Cache the embedding model so we load it once per process.
_EMBED_MODEL = None


def tokenize(text: str) -> list[str]:
    """Lowercase word/number tokenization used by the BM25 index."""
    return _TOKEN_RE.findall(text.lower())


def _load_embed_model(name: str | None = None):
    global _EMBED_MODEL
    if _EMBED_MODEL is None:
        from sentence_transformers import SentenceTransformer

        _EMBED_MODEL = SentenceTransformer(name or CONFIG.models.embed)
    return _EMBED_MODEL


def embed_passages(
    texts: list[str], *, model_name: str | None = None, batch_size: int = 32
) -> np.ndarray:
    """Embed passages (documents). Returns L2-normalized float32 vectors."""
    model = _load_embed_model(model_name)
    vecs = model.encode(
        texts,
        batch_size=batch_size,
        normalize_embeddings=True,
        show_progress_bar=len(texts) > 200,
        convert_to_numpy=True,
    )
    return vecs.astype("float32")


def embed_queries(texts: list[str], *, model_name: str | None = None) -> np.ndarray:
    """Embed queries with the BGE retrieval instruction prefix."""
    model = _load_embed_model(model_name)
    prefixed = [BGE_QUERY_INSTRUCTION + t for t in texts]
    vecs = model.encode(prefixed, normalize_embeddings=True, convert_to_numpy=True)
    return vecs.astype("float32")


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


def build_bm25(chunks: list[dict], path: Path | None = None) -> None:
    """Build and persist the BM25 index alongside its row-aligned chunks."""
    path = path or CONFIG.paths.bm25_index
    tokenized = [tokenize(c["text"]) for c in chunks]
    bm25 = BM25Okapi(tokenized)
    with open(path, "wb") as fh:
        pickle.dump({"bm25": bm25, "chunks": chunks}, fh)


def build_dense(chunks: list[dict], *, model_name: str | None = None) -> None:
    """Build and persist the FAISS dense index + row-aligned chunk metadata."""
    model_name = model_name or CONFIG.models.embed
    texts = [c["text"] for c in chunks]
    vecs = embed_passages(texts, model_name=model_name)
    dim = vecs.shape[1]
    # Inner product on normalized vectors == cosine similarity.
    faiss_index = faiss.IndexFlatIP(dim)
    faiss_index.add(vecs)
    faiss.write_index(faiss_index, str(CONFIG.paths.dense_index))
    meta = {"model": model_name, "dim": dim, "chunks": chunks}
    with open(CONFIG.paths.dense_meta, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, ensure_ascii=False)


def build_all(chunks: list[dict], *, model_name: str | None = None) -> None:
    CONFIG.paths.ensure()
    print(f"Building BM25 index over {len(chunks)} chunks...")
    build_bm25(chunks)
    print(f"Building dense (FAISS) index with {model_name or CONFIG.models.embed}...")
    build_dense(chunks, model_name=model_name)
    print(f"Indexes written to {CONFIG.paths.indexes}")
