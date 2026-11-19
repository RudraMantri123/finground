# Retrieval evaluation and the CI regression gate

**CI measures retrieval on a small committed fixture corpus. The leaderboard
(`results/results.csv`, `make benchmark`) measures generation (correctness,
faithfulness, citations, refusals) on the full locally built corpus.** The two
answer different questions and their numbers are not interchangeable.

| | Retrieval eval (this doc) | Leaderboard |
|---|---|---|
| Question | Does the evidence reach the top-k? | Is the generated answer right and grounded? |
| Corpus | `tests/fixtures/retrieval_corpus.jsonl` in CI; `indexes/` optionally on your machine | `indexes/` over all chunks |
| Cost | Free, deterministic, no LLM calls | LLM calls (answerer + judge) |
| Runs | Every push / PR (`retrieval-eval` job) | Manually |

## Relevance labels that survive re-chunking

Chunk IDs change whenever chunk size, overlap, or table rendering changes, so
relevance is not stored as chunk IDs. Each answerable item in
`results/gold_set.jsonl` has an `evidence` list (written by
`scripts/make_gold_set.py`):

```json
{"ticker": "AAPL", "must_contain": ["single or limited sources"], "verified": true,
 "note": "Item 1 supply + Item 1A risk factor."}
```

- A chunk **satisfies** a label when its ticker matches, its section starts with
  `section` (optional, unused today because the parser mislabels some sections),
  and it contains **every** `must_contain` phrase.
- Matching runs on normalised text: NFKC, lowercase, and everything that isn't a
  letter or digit becomes a separator. Whitespace, curly quotes, bullets, `$`,
  and Markdown table pipes and `---` rows don't affect matching, and matches
  respect token boundaries (`70%` does not match `1970`).
- Phrases are kept short (well under the 75-token chunk overlap), so whatever
  the chunk boundaries, at least one chunk contains the whole phrase.
- Each label is one distinct supporting fact. A question with two labels needs
  both facts in the top-k to get full recall.
- `verified: true` means a person read every corpus chunk the label matches and
  confirmed it supports the gold answer. `uncertain: true` marks labels to
  review first (currently fg-005 #3, fg-012 #1–2, fg-013 #3; see their `note`).
- Unanswerable items have no evidence and are excluded from retrieval metrics.

How the labels were made: for each gold answer, its key phrases were searched in
`data/chunks.jsonl` for the gold ticker. A verbatim span from the passage that
states the fact was chosen as the label. Every chunk that label matches was then
read. `tests/test_gold_evidence.py` checks that every answerable item has labels,
that each label's ticker is one of the item's gold tickers, and that each label
matches at least one fixture chunk.

## Metrics (`src/finground/eval/retrieval_metrics.py`)

Per question, then averaged with every question weighted equally:

- **recall@k** (k = 1, 3, 5, 8, 10): the fraction of the question's labels
  satisfied by at least one top-k chunk. Counting labels instead of chunks keeps
  the number comparable across chunkers.
- **MRR@10**: 1 / rank of the first chunk that satisfies any label.
- **nDCG@10**: binary gain, credited once per label at the first rank that
  covers it. IDCG is one new label per rank. The score is capped at 1.0 because
  one large chunk can cover several labels at once.

The script also prints **paired-bootstrap 95% intervals** (questions resampled)
for each configuration minus `hybrid_rerank`.

## Configurations

`scripts/eval_retrieval.py` calls the production `retrieve()` with one toggle
changed per configuration. Company filter, pool sizes, the RRF constant and the
rerank pool all stay as shipped.

| config | `mode` | `use_reranker` |
|---|---|---|
| `bm25` | `bm25` | off |
| `dense` | `dense` (BGE-base) | off |
| `hybrid_rrf` | `hybrid` (BM25 + dense, RRF) | off |
| `hybrid_rerank` (production) | `hybrid` | on (ms-marco MiniLM-L-6 cross-encoder over the fused top 24) |

If the cross-encoder can't be loaded, the eval exits 2. It doesn't fall back
silently the way serving does, because that would report RRF numbers under the
rerank label.

## Current numbers (15 labelled questions)

Fixture corpus (618 chunks). This is what CI measures and what the thresholds
are calibrated on:

| config | R@1 | R@3 | R@5 | R@8 | R@10 | MRR@10 | nDCG@10 |
|---|---|---|---|---|---|---|---|
| bm25 | 0.400 | 0.656 | 0.756 | 0.778 | 0.778 | 0.669 | 0.685 |
| dense | 0.167 | 0.367 | 0.489 | 0.689 | 0.778 | 0.461 | 0.522 |
| hybrid_rrf | 0.300 | 0.522 | 0.589 | 0.689 | 0.778 | 0.613 | 0.617 |
| hybrid_rerank | 0.300 | 0.489 | 0.678 | 0.800 | 0.833 | 0.551 | 0.633 |

Full local corpus (1,875 chunks, `--corpus full`). Not reproducible in CI:

| config | R@1 | R@3 | R@5 | R@8 | R@10 | MRR@10 | nDCG@10 |
|---|---|---|---|---|---|---|---|
| bm25 | 0.400 | 0.656 | 0.756 | 0.778 | 0.778 | 0.669 | 0.685 |
| dense | 0.167 | 0.367 | 0.489 | 0.689 | 0.778 | 0.461 | 0.522 |
| hybrid_rrf | 0.300 | 0.522 | 0.622 | 0.756 | 0.811 | 0.616 | 0.633 |
| hybrid_rerank | 0.300 | 0.489 | 0.678 | 0.800 | 0.833 | 0.551 | 0.633 |

The fixture matches the full corpus exactly for three of the four
configurations, and is within 0.07 for `hybrid_rrf`.

**Reading these honestly.** BM25 alone has the best early precision and
reranking gives the best deep recall (R@8/R@10), but with 15 questions the
paired-bootstrap intervals for bm25 vs hybrid_rerank and hybrid_rrf vs
hybrid_rerank all include 0. **This set cannot tell those three apart.** The
one difference that holds up is that **dense-only is worse** than the
production pipeline at mid-depth recall (R@5 −0.19, 95% CI [−0.36, −0.06]).
Its nDCG@10 gap (−0.11, CI [−0.24, +0.01]) is borderline. Two more caveats:

- The labels were found by lexical search and are verbatim filing phrases.
  That may favour BM25, which matches surface wording.
- The general-domain MS MARCO cross-encoder sometimes promotes the wrong kind of
  risk. On fg-006 (NVIDIA foundry dependence) it fills the top 10 with
  supplier security-incident passages and pushes out the foundry risk factor
  that BM25 ranks first. A finance-tuned reranker or a larger question set would be needed to
  settle "does reranking help on 10-Ks?".

## Fixture corpus

`scripts/make_retrieval_fixture.py` builds the fixture from the full local
corpus (metadata in `tests/fixtures/retrieval_corpus.meta.json`):

1. **Positives**: every chunk that satisfies any label (43).
2. **Hard negatives**: the top 30 chunks per question from BM25, dense and
   hybrid over the full corpus, so the passages each ranker actually confuses
   with the evidence are present.
3. **Background**: a seeded sample of 25 chunks per company, so BM25 IDF and the
   company filter see a realistic mix.

The result is 618 chunks (~1.7 MB of filing text), embedded in memory on each run
(~15 s on a laptop CPU).

## Thresholds and the CI gate

`results/retrieval_thresholds.json` stores a floor for every metric of every
configuration. Each floor is the measured fixture value minus a **0.07 margin**,
rounded down to 2 dp. 0.07 is one question's worth of evidence on a
15-question set (1/15 ≈ 0.067), rounded up. So a near-tie that flips between
CPU architectures, or one question losing its evidence, still passes. Losing
more than that fails. The file also records the fixture's SHA-256. If the
fixture changes without recalibration, `--check` fails rather than comparing
against stale numbers. `--check` also fails if any label matches no corpus chunk.

The `retrieval-eval` job in `.github/workflows/ci.yml` does the following:

1. Installs CPU-only torch, then the package.
2. Restores `~/.cache/huggingface` with `actions/cache`. On a cache miss it
   downloads BGE-base and the MiniLM cross-encoder.
3. Runs `python scripts/eval_retrieval.py --check results/retrieval_thresholds.json`
   with `HF_HUB_OFFLINE=1`.
4. Uploads the per-question audit JSONL as a build artifact.

Embedding the fixture is the slowest step: about 15 s on a laptop, and
  expected to take a minute or two on a hosted runner. The job is capped at
  15 minutes.

Run the same check locally (offline once the models are cached):

```bash
make eval-retrieval        # HF_HUB_OFFLINE=1 python scripts/eval_retrieval.py --check results/retrieval_thresholds.json
```

## After a chunking or retrieval change

1. Rebuild `data/` and `indexes/` (`make ingest && make index`).
2. Run `python scripts/make_retrieval_fixture.py` to rebuild the fixture from the
   new chunks. Labels don't need to change; `tests/test_gold_evidence.py`
   flags any that no longer match.
3. Run `python scripts/eval_retrieval.py --corpus full` to see the real effect.
4. Run `python scripts/eval_retrieval.py --write-thresholds results/retrieval_thresholds.json`.
5. Commit the fixture, meta, thresholds and `results/retrieval_eval*.csv`
   together, and explain any threshold that went down in the PR.

Known residual risks:

- Hugging Face model revisions and `sentence-transformers`/`torch` versions are
  not pinned, so an upstream change can move the numbers. The margin absorbs
  small drift, and the uploaded audit shows what moved.
- The current parser appears to drop most of Microsoft's Item 1 overview, so fg-012's
  labels point at the segment note and MD&A metric definitions instead.
