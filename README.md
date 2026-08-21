# FinGround

[![CI](https://github.com/RudraMantri123/finground/actions/workflows/ci.yml/badge.svg)](https://github.com/RudraMantri123/finground/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

**Faithfulness-first Financial RAG over SEC filings — a system that grounds every
answer in cited evidence, abstains when the filings can't support one, and a
benchmark that measures *hallucination*, not just correctness.**

Most RAG demos optimize "did it get the right answer?" In high-stakes finance the
more dangerous failure is a confident, well-written answer that isn't supported by
the source — or an answer to a question the filings never address. FinGround is
built around that failure mode: answers carry inline `[C#]` citations back to
specific 10-K sections, the system refuses when evidence is weak, and the
evaluation harness scores four dimensions including an explicit, human-validated
**faithfulness / hallucination** metric.

**What the benchmark has already caught** (details in [Results](#results)):

- A **silent context-truncation bug** that cost 8× correctness and 90× hallucination
  with identical model weights — configuration, not parameters.
- Three free **"finance-specialized" models losing to their general base model** on
  every grounding metric; one of them never refuses an unanswerable question.
- A judge whose **faithfulness verdicts agree with humans at κ = 0.84** — and whose
  correctness verdicts (κ = 0.49) are honestly flagged as the weak link.

---

## Motivation

- **Hallucination is the tail risk that matters.** A wrong number in a financial
  summary, stated fluently and without a source, is worse than a refusal. FinGround
  rewards abstention over guessing and measures unsupported-claim rate directly.
- **Grounding must be verifiable.** Every retrieved chunk and every citation traces
  to a specific filing, item/section, and character span. "Trust me" is not a
  citation.
- **Evaluation is the product.** The differentiator here isn't the retriever — it's a
  harness that decomposes each answer into atomic claims and checks whether the
  *cited* evidence actually supports them, validated against human labels
  (Cohen's κ).

---

## Architecture

```mermaid
flowchart LR
    subgraph Ingest
        A[SEC EDGAR<br/>10-K filings] --> B[HTML → text<br/>Item sectioning]
        B --> C[Token chunking<br/>+ provenance]
    end
    subgraph Index
        C --> D[BM25<br/>sparse]
        C --> E[FAISS + BGE<br/>dense]
    end
    subgraph Answer
        Q[Question] --> R[Hybrid retrieve<br/>RRF fusion]
        D --> R
        E --> R
        R --> F[Company filter<br/>+ cross-encoder rerank]
        F --> G{Evidence<br/>strong enough?}
        G -- no --> X[Abstain:<br/>Not answerable]
        G -- yes --> L[LLM answerer<br/>cite-only prompt]
        L --> Y[Cited answer<br/>+ provenance]
        L -.-> X
    end
    subgraph Evaluate
        Y --> J[LLM-as-judge]
        X --> M[Refusal<br/>calibration]
        J --> M2[Correctness ·<br/>Citation accuracy ·<br/>Faithfulness]
        J -. validated vs .- H[Human labels<br/>Cohen's κ]
    end
```

**Pipeline:** ingest → hybrid retrieve → filter/rerank → cite-or-refuse → evaluate.
When the query names a corpus company, retrieval prefers that filer's chunks (an
Apple question is never answered with — or cited to — another company's filing);
a cross-encoder (`ms-marco-MiniLM`) then reranks the fused pool for precision,
degrading gracefully to RRF order when the model can't be downloaded. The evidence
gate (dense cosine below threshold ⇒ abstain) short-circuits weak questions before
spending a token, and the answerer is separately instructed to abstain when the
excerpts don't support an answer.

---

## Results

Numbers below come from real runs of `scripts/run_benchmark.py` over the 20-question
FinGround gold set, judged by an LLM-as-judge (see **Evaluation methodology**).
Only models that actually ran are listed — numbers are never invented. The
`Judge` column records which LLM judged each row.

> ### 🌍 Help wanted: hosted-model evals
>
> This leaderboard was produced on a machine with **no paid API keys**, so every
> scored model so far runs locally via Ollama. GPT-4o, GPT-4o-mini, and Claude
> are fully supported — someone with a key just needs to press the button.
> **If you have an OpenAI or Anthropic key**, you can put a hosted model on the
> board in ~10 minutes and typically under $1–2:
>
> ```bash
> make setup && make ingest && make index
> .venv/bin/python scripts/run_benchmark.py --models openai:gpt-4o --judge openai:gpt-4o
> make charts && make readme
> ```
>
> Results **merge** — your run only touches your model's row. Open a PR with the
> updated `results/results.csv` and the `results/runs/<model>.jsonl` audit dump.
> Full steps and checklist: [CONTRIBUTING.md](CONTRIBUTING.md).

<!-- RESULTS_TABLE_START -->
| Model | Correctness ↑ | Citation acc ↑ | Hallucination ↓ | Refusal cal ↑ | Latency (s) | $/100q | n | answered | Judge |
|---|---|---|---|---|---|---|---|---|---|
| ollama:llama3 | 0.467 | 0.900 | 0.007 | 1.000 | 51.59 | 0.0000 | 20 | 15 | ollama:llama3 |
| ollama:martain7r/finance-llama-8b:q4_k_m | 0.214 | 0.415 | 0.512 | 0.567 | 149.71 | 0.0000 | 20 | 18 | ollama:llama3 |
| ollama:0xroyce/plutus:latest | 0.500 | 0.803 | 0.207 | 0.500 | 61.25 | 0.0000 | 20 | 20 | ollama:llama3 |
| ollama:jjansen/adapt-finance-llama2-7b:latest | 0.267 | 0.708 | 0.420 | 0.600 | 14.35 | 0.0000 | 20 | 19 | ollama:llama3 |
<!-- RESULTS_TABLE_END -->

**Charts** (`results/charts/`, regenerate with `make charts`):

![Quality by model](results/charts/quality_by_model.png)
![Hallucination rate by model](results/charts/hallucination_by_model.png)

**Judge validation** — the whole benchmark is only as trustworthy as its judge, so
we measure judge-vs-human agreement on the committed human labels:

<!-- JUDGE_VALIDATION_START -->
Judge model: `ollama:llama3` · n = 13 examples

| Axis | Raw agreement | Cohen's κ |
|---|---|---|
| Correctness | 76.9% | 0.494 |
| Faithfulness | 92.3% | 0.843 |
<!-- JUDGE_VALIDATION_END -->

> **Run context.** The committed numbers were produced on a machine with no hosted
> API keys, so every scored model runs locally via Ollama, and `ollama:llama3`
> serves as the fixed judge for all rows (comparable scores; disclosed weakness: an
> 8B judge is noisy on correctness and may favor its own model family). Re-run with
> your own keys to populate the hosted-model rows. Small-n numbers throughout;
> treat as directional.
>
> **Finding: "finance-tuned" ≠ better grounded financial QA.** Three free models
> claiming finance specialization were benchmarked against the general llama3-8B
> baseline on the identical pipeline. The baseline won on every grounding metric —
> near-zero hallucination (0.007), top citation accuracy (0.900), and perfect
> refusal calibration. `plutus` edged correctness (0.500 vs 0.467) but answered
> **all five unanswerable questions** (refusal calibration 0.500 — it never
> refuses) with ~30× the baseline's hallucination rate. `finance-llama-8b`
> (tuned on 500k finance examples) scored worst across the board — domain
> fine-tuning appears to have eroded the instruction-following (inline citation,
> abstention) that grounded RAG depends on. `adapt-finance-llama2-7b` carries a
> hard 4K context window against our ~4-5K-token prompts, so its inputs truncate;
> its scores mostly measure that limit. Marketing claims are not grounding
> guarantees — measure.
>
> **A measured lesson in silent truncation.** An earlier committed run scored
> correctness 0.067 / hallucination 0.833 for llama3. The cause was not the
> model: Ollama's default ~2k `num_ctx` silently truncated the front of the
> RAG prompt, cutting off the system rules and the question itself. Fixing
> `num_ctx` (plus excerpts-first prompt order, semantic refusal detection, and
> company-aware retrieval) moved correctness to ~0.5 and hallucination to ~0.01
> — an 8× / 90× swing from configuration, not parameters. The eval harness is
> what made the bug visible.

---

## Evaluation methodology

Four metrics, each defined in `src/finground/eval/metrics.py` (pure, unit-tested)
and fed by the judge in `eval/judge.py`:

| Metric | What it asks | How it's scored |
|---|---|---|
| **Answer correctness** | Does the answer match the gold answer in meaning? | LLM judge (binary), over answerable questions that were answered. A lexical proxy (`token_f1` + gold-number recall) is also available. |
| **Citation accuracy** | Does each *cited* chunk actually support the answer? | Fraction of cited chunks the judge marks as genuinely supporting. |
| **Faithfulness / hallucination** | Are the answer's claims backed by the cited evidence? | Answer is decomposed into atomic claims; hallucination rate = fraction unsupported by any cited chunk. |
| **Refusal calibration** | Does it abstain iff it should? | Balanced accuracy over the answer/abstain decision (mean of answer-recall and refusal-recall) so "always answer" and "always refuse" both score 0.5. Full confusion matrix retained. |

**LLM-as-judge.** One structured JSON call per answered question returns: the
per-claim support labels (faithfulness), per-citation support labels (citation
accuracy), and a correctness verdict against the gold answer. Refusals are not sent
to the judge — correctness/faithfulness are undefined for an abstention; those are
captured by refusal calibration instead.

**Human validation (essential, not skipped).** `eval/validate_judge.py` runs the
judge over `results/human_labels/seed_labels.jsonl` — self-contained examples
spanning contradictions, wrong numbers, fabricated additions, and correct-but-
mis-cited answers — and reports **Cohen's κ** between judge and human labels for
both correctness and faithfulness.

**Datasets.** The primary set is the FinGround gold set (`results/gold_set.jsonl`),
written to be answerable — or deliberately *not* answerable — from the exact filings
we ingested, so correctness and refusal signals are clean. It includes a
**geoeconomic** category (trade / tariff / export-control exposure drawn from
risk-factor sections). A FinanceBench (`PatronusAI/financebench`) loader anchors to a
public dataset; because its evidence lives in specific filing versions, it is
optionally restricted to the companies in our corpus (coverage caveat below).

---

## Reproducibility

From a fresh clone (Python 3.11):

```bash
make setup                      # venv + install (pins in pyproject.toml)
cp .env.example .env            # add keys you have; missing providers are skipped

# Build the corpus + indexes (no API key needed):
make ingest                     # ~8 latest 10-Ks from SEC EDGAR -> data/chunks.jsonl
make index                      # BM25 + FAISS/BGE indexes

# Try it:
make serve                      # http://localhost:8000  (demo UI + POST /query)

# Evaluate (needs at least one LLM: a hosted key, or local Ollama):
python scripts/make_gold_set.py         # (already committed; regenerate if edited)
python scripts/make_human_labels.py     # (already committed)
make benchmark                          # -> results/results.csv
make charts                             # -> results/charts/*.png
make validate-judge                     # judge vs human labels (Cohen's kappa)
python scripts/update_readme.py         # wire this README's tables from results/

make test                       # unit tests (chunking, retrieval, metrics, answering)
make lint                       # ruff + black + mypy
```

Set `SEC_EDGAR_USER_AGENT` in `.env` to a descriptive string with contact info —
EDGAR requires it. Local models: point `OLLAMA_BASE_URL` at a running Ollama and use
`--models ollama:<name> --judge ollama:<name>`. `OLLAMA_NUM_CTX` (default 8192) sets
the context window explicitly — never rely on Ollama's small default, which silently
truncates RAG prompts. Retrieval knobs (`company_filter`, `use_reranker`, `top_k`)
live in `src/finground/config.py`; the reranker downloads from Hugging Face on first
use and falls back to RRF order offline. LLM responses are cached on disk
(`llm_cache/`) so re-runs don't re-bill; generation options are part of the cache
key, so changing them re-generates instead of serving stale outputs.

---

## Limitations & honesty

- **Small sample.** 20 gold questions and 13 human labels demonstrate the protocol;
  they are not a statistically powerful benchmark. Kappa on 13 items has wide
  confidence intervals. Scale both before drawing strong conclusions.
- **Single-annotator seed labels.** The human labels are author-adjudicated. Real
  validation needs multiple independent annotators and inter-annotator agreement.
- **Judge bias & self-judging.** An LLM judge shares blind spots with the models it
  scores; using the *same* local model as answerer and judge (as in the committed
  llama3 row) is the weakest configuration and is disclosed as such. When comparing
  models, a fixed llama3 judge may also favor outputs from its own model family
  (two of the finance models are Llama-3 derivatives, partially leveling this).
  Prefer a stronger, unrelated judge.
- **Model context windows.** The pipeline sends ~4-5K-token prompts; models with
  smaller windows (e.g. Llama-2's 4K) silently truncate and their scores reflect
  that limit, not just their weights. `OLLAMA_NUM_CTX` must exceed the prompt size
  or the same failure occurs by configuration.
- **Data contamination.** LLMs have very likely seen these public 10-Ks in
  pretraining, which can inflate correctness independent of retrieval. Faithfulness
  (claims-vs-cited-evidence) is more robust to this than correctness.
- **Sectioning heuristics.** Item splitting uses a longest-segment heuristic to beat
  the table of contents; unusual filing layouts can mislabel a section (provenance
  still points at real text, just possibly the wrong item label).
- **FinanceBench alignment.** Its gold evidence may reference filing versions we did
  not index, so retrieval can miss the intended passage; treat cross-dataset numbers
  as directional.

---

## How I'd scale this

- **Retrieval:** shard the FAISS index (IVF/HNSW) per company/year; distill the
  existing cross-encoder reranker into the bi-encoder to keep its precision without
  its latency. Cache query embeddings.
- **Answering:** stream tokens; batch retrieval; move the evidence gate to a small
  calibrated classifier over retrieval features rather than a single cosine
  threshold.
- **Evaluation:** a judge ensemble with majority vote and disagreement routing to
  humans; per-category and per-section slices; bootstrap confidence intervals on
  every metric; track judge drift over time.
- **Data:** incremental EDGAR ingestion (only new filings), 10-Q coverage, table- and
  XBRL-aware chunking so numeric facts keep their row/column context.
- **Serving:** async workers, per-tenant rate limits, and an answer cache keyed by
  (question, index version) with provenance-stable invalidation.

---

## Repository layout

```
src/finground/       ingest · index · retrieve · answer · llm · serve · eval/
scripts/             run_ingest · run_index · run_benchmark · make_charts · make_gold_set · make_human_labels · update_readme
results/             results.csv · charts/ · judge_validation.json · gold_set.jsonl · human_labels/
demo/                static grounded-QA page hitting /query
tests/               chunking · retrieval provenance · metric math · answering (33 tests)
```

## License

MIT — see [LICENSE](LICENSE).
