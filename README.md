# FinGround

**Faithfulness-first Financial RAG over SEC filings — with a benchmark that measures hallucination, not just correctness.**

FinGround answers questions over 10-K / 10-Q filings with **inline citations** to
source chunks, **abstains** when the evidence is insufficient, and ships an
**evaluation harness** that scores four dimensions most RAG demos ignore:

1. **Answer correctness** — is the answer right?
2. **Citation accuracy** — does each cited chunk actually support the claim?
3. **Faithfulness / hallucination rate** — what fraction of claims are unsupported by any cited chunk?
4. **Refusal calibration** — does it abstain when it should, and answer when it should?

> **Status: under construction.** This README is a stub scaffold (Phase 1). The
> full design-doc README with the results table and architecture diagram lands
> in Phase 7. Result numbers are produced by real runs only — see
> `scripts/run_benchmark.py`. Nothing here is fabricated.

## Quickstart

```bash
make setup          # venv + install
cp .env.example .env # add your API keys (optional; missing providers are skipped)
make ingest         # download + chunk a small set of SEC filings
make index          # build BM25 + FAISS dense indexes
make serve          # FastAPI /query endpoint + demo page at http://localhost:8000
```

## Evaluation

```bash
make benchmark       # evaluate available models -> results/results.csv
make charts          # render comparison charts
make validate-judge  # LLM-judge vs human-label agreement (Cohen's kappa)
```

## Layout

```
src/finground/       # library: ingest, index, retrieve, answer, llm, serve, eval/
scripts/             # run_ingest, run_index, run_benchmark, make_charts
results/             # committed: results.csv, charts, human_labels/
demo/                # static page hitting /query
tests/               # pytest: chunking, retrieval provenance, metric math
```

## License

MIT — see [LICENSE](LICENSE).
