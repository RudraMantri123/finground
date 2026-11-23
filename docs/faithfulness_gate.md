# Faithfulness regression gate

**Goal:** the eval set runs in CI and the build fails when faithfulness drops,
with prompts and config versioned alongside the code.

CI has no LLM keys and no Ollama, so a judge cannot run on every push. The gate
is built in three layers, each honest about what it can see:

| Layer | Runs | Needs | Catches |
|---|---|---|---|
| 1. Deterministic checks on the pinned answer set | every push / PR (`faithfulness-gate` job) | nothing (no LLM, no torch) | invalid `[C#]`, uncited claims, figures not in the cited chunk, answered trap questions, refusals of answerable questions |
| 2. Judged-score thresholds + staleness | every push / PR (same job) | nothing | a worse judged run being committed; prompt / model / retrieval / corpus / gold-set changes that were not re-evaluated |
| 3. Live regenerate + judge | push to `main`, manual dispatch, only if a `COHERE_API_KEY` secret exists (`faithfulness-live` job) | Cohere key, embedding + reranker models | the shipped pipeline actually producing less faithful answers today |

## The pinned answer set

`results/faithfulness/pinned_run.jsonl` holds one row per gold question (all 20:
15 answerable, 5 unanswerable traps) with everything the checks need, so it is
self-contained:

- the question, `answerable`, the answer text, `abstained`, the evidence-gate
  outcome;
- **all retrieved chunks** (`label`, `chunk_id`, provenance, full text), exactly
  as shown to the model;
- the answer model and `prompt_version`; the judge model and the judge's
  per-claim / per-citation labels with the judge's `prompt_version`.

It is generated over the **committed fixture corpus**
(`tests/fixtures/retrieval_corpus.jsonl`, the same one the retrieval gate uses),
not the full local index. That is what makes layer 3 reproducible in CI and lets
the staleness check verify the corpus hash. Numbers here are therefore *not*
comparable with the leaderboard (`results/results.csv`, full corpus).

`results/faithfulness/pinned_manifest.json` is the run's fingerprint: answer and
judge model, temperature, answer/judge prompt ids **and SHA-256 of the prompt
files**, the refusal sentence, the full retrieval config, embedding and reranker
model names, and the SHA-256 of the fixture corpus and the gold set.

The gate's model pair is declared in code, in
`src/finground/eval/faithfulness.py` (`GATE_ANSWER_MODEL`, `GATE_JUDGE_MODEL`;
currently `cohere:command-a-03-2025` for both).

## Layer 1: deterministic checks

Implemented in `src/finground/eval/faithfulness.py`, recomputed from the text on
every run:

- **Citation validity:** share of cited labels that name a retrieved chunk.
  `[C9]` with eight chunks retrieved is invalid.
- **Citation coverage:** share of claim units (sentences and bullets, from
  `metrics.claim_units`; lead-in lines ending in `:` and headings are not
  claims) that carry at least one citation, all valid. Sentence-level and
  strict: a citation at the end of a paragraph does not cover the paragraph's
  earlier sentences.
- **Numeric grounding:** every figure in an answer must appear in at least one
  chunk the answer cites (provenance header included, so a filing year counts).
  Normalisation:
  - `$` and thousands separators are dropped, and decimals are kept;
  - `million`, `billion`, `thousand` and `bn`/`mn`/`M`/`B` scale words apply;
  - `%`, `percent` and `bps` are kept as their own kinds;
  - an accounting negative `(1,234)` reads as 1,234, because prose states the
    direction in words;
  - a bare table number also stands for the statement's unit when the chunk says
    `in millions` / `in thousands` / `in billions`.

  A match allows half a unit of the answer's last written digit: `$61 billion`
  is grounded by `60,922` in a table "in millions", but `$60.95 billion` is not.
  Citation labels, list numbering and identifiers such as `10-K`, `Item 1A`,
  `COVID-19` and `Q3` are not figures. Spelled-out numbers ("three segments")
  are not checked.
- **Refusal correctness:** refusal recall on the unanswerable traps.
- **Abstention:** answer recall on answerable questions. A refusal there counts
  as a false refusal.

## Layer 2: judged thresholds and staleness

The judged rates come from the committed judge labels and use the leaderboard's
own code (`eval/summary.py`):

- faithfulness, the mean share of supported claims per answered question;
- hallucination rate, which is 1 − faithfulness;
- citation accuracy.

Correctness is reported but not gated, because it is not a faithfulness
property.

**Staleness.** The gate rebuilds the fingerprint from the code and compares it
with the manifest field by field. Any difference fails the build and names the
field. The fields are:

- the gate models and temperature;
- the active prompt versions (`FINGROUND_*_PROMPT_VERSION`, default `v1`) and
  the SHA-256 of those prompt files;
- the `Retrieval` dataclass, the embedding and reranker models;
- the fixture and gold-set hashes.

Every answered row must also carry the expected answer and judge
`prompt_version` and models. That way a manifest edited to match the code cannot
hide answers that were produced with something else. The result is that you
can't change a prompt, even in place, without re-running and committing the
judged eval.

## Thresholds (`results/faithfulness_thresholds.json`)

This mirrors the retrieval gate's `--check`, `--write-thresholds` and `--margin`
design, with two kinds of threshold:

- **Rate floors and ceilings** sit at the measured value minus (or plus) the
  margin, rounded outward to 2 dp. The default margin is 0.07, one question's
  worth on the 15 answerable items. These bounds are what a regenerated (live)
  run is held to, because LLM output varies between runs.
- **`max_violations`** are exact counts on the pinned set:
  - invalid citations;
  - uncited claims;
  - ungrounded numbers;
  - trap answers;
  - false refusals;
  - judge errors.

  The pinned text never changes between CI runs, so the deterministic checks are
  exactly reproducible. Any new violation is a regression, and no margin is
  needed. The failure message lists the offending sentence, figure or label.

The thresholds also record `pinned_run_sha256`. A hand-edited pinned run fails
and has to be regenerated instead.

**Re-pinning can't self-certify a regression.** When the thresholds file already
exists, `--write-thresholds` first checks the new run against the existing rate
floors. If the new run regresses past them, it refuses to write. To go ahead
anyway, pass `--accept-regression "why"`, and the reason is recorded in the
file for review.

## Current pinned run

Pinned with `cohere:command-a-03-2025` (answer and judge), `answer.v1` and
`judge.v1`, over the fixture corpus. The 20 questions took 33 hosted calls: 15
answers, 15 judgments, and 5 trap refusals that the model produced itself (the
evidence gate passed all 5).

| Check | Value | Threshold |
|---|---|---|
| citation validity (63 citations) | 1.000 | ≥ 0.93, 0 invalid |
| citation coverage (127 claim units) | 0.874 | ≥ 0.80, ≤ 16 uncited |
| numeric grounding (4 figures) | 1.000 | ≥ 0.93, 0 ungrounded |
| refusal recall (5 traps) | 1.000 | ≥ 0.93, 0 answered |
| answer recall (15 answerable) | 1.000 | ≥ 0.93, 0 refused |
| faithfulness (judged) | 1.000 | ≥ 0.93 |
| hallucination rate (judged) | 0.000 | ≤ 0.07 |
| citation accuracy (judged) | 0.959 | ≥ 0.88 |
| correctness (judged, not gated) | 0.533 | none |

Uncited claims are mostly the opening sentences of paragraphs whose citation
comes at the paragraph's end. `faithfulness_eval_per_item.jsonl` lists every
one.

## Commands

```bash
# What CI runs (no LLM calls, seconds):
python scripts/eval_faithfulness.py --check results/faithfulness_thresholds.json
make eval-faithfulness

# After an intended change to prompts / gate models / retrieval / fixture / gold set
# (needs COHERE_API_KEY; ~2 calls per answered question, ~35 for the 20 questions):
HF_HUB_OFFLINE=1 python scripts/eval_faithfulness.py --regenerate --pin \
    --write-thresholds results/faithfulness_thresholds.json \
    --check results/faithfulness_thresholds.json
# then commit results/faithfulness/ and results/faithfulness_thresholds.json together.

# Live check without touching the pinned set (what the faithfulness-live job runs):
python scripts/eval_faithfulness.py --regenerate --check results/faithfulness_thresholds.json
```

`--out-dir` (default `results/faithfulness/`) receives `faithfulness_eval.csv`
and `faithfulness_eval_per_item.jsonl`, the per-question findings that CI
uploads as an artifact.

## The live job (layer 3)

`faithfulness-live` in `.github/workflows/ci.yml` runs on pushes to `main` and on
manual dispatch. Pull requests are skipped because fork PRs never see secrets.
Its first step checks whether `COHERE_API_KEY` is set. If not, it prints a
notice and every later step is skipped, so the job passes cleanly. With a key,
it does the following:

1. Installs CPU torch and restores the Hugging Face model cache.
2. Indexes the fixture corpus.
3. Re-answers and re-judges all 20 questions with the gate's model pair, about
   35 calls per run and nothing cached in CI. Mind trial-key monthly limits.
4. Holds the result to the rate floors and ceilings.

The exact violation counts are not applied here, because they are specific to
the pinned text. The regenerated run is uploaded as an artifact.

## Tests

`tests/test_faithfulness_gate.py` covers the normalisation and matching rules
and asserts that the committed data passes. It then mutates the pinned set the
way a regression would and asserts that the gate fails, and for the right
reason:

- **Drop a citation:** `uncited_claims` goes over budget.
- **Cite `[C99]`:** `invalid_citations` goes over budget.
- **Change a figure to one not in the chunk:** `ungrounded_numbers` goes over
  budget, and the message names the figure.
- **Answer a trap question:** `trap_answers` goes over budget and
  `refusal_recall` drops below its floor.
- **Refuse answerable questions:** `false_refusals` goes over budget and
  `answer_recall` drops below its floor.
- **Judge marks claims unsupported:** `faithfulness` drops below its floor and
  `hallucination_rate` rises above its ceiling.
- **Bump the answer prompt to v2, or edit `judge.v1.toml` in place:** the build
  fails with `STALE answer prompt` or `STALE judge prompt`.
- **Change the gate model, `top_k`, or the gold set:** the matching `STALE …`
  line appears.
- **Hand-edit the pinned file:** the end-to-end CLI exits 1.
- **Recalibrate on a worse run:** `--write-thresholds` refuses to write.

## Limitations

- **Small sample.** There are 20 questions with 5 traps. The rate floors are
  coarse, and the exact counts are what make single-answer regressions visible
  on the pinned set.
- **The judge is the answering model.** The gate uses the same Cohere model to
  answer and to judge, and self-judging can be lenient. On the 13 human-labelled
  examples (`results/human_labels/`), this judge agrees with people on
  faithfulness 13/13 (κ = 1.00) and on correctness 11/13 (κ = 0.70); see
  `results/faithfulness/judge_validation.json`. Thirteen examples is a small
  sample, which is one reason the deterministic layer exists. (The
  leaderboard's κ = 0.84 was measured for its `ollama:llama3` judge.)
- **Few figures in the current set.** The gold questions are mostly qualitative,
  so the pinned answers contain only 4 figures, all grounded. The check is
  exercised mainly by the unit and mutation tests, until numeric questions are
  added to the gold set.
- **Numeric grounding is necessary, not sufficient.** A figure that occurs
  somewhere in the cited chunk passes even if it is attached to the wrong line
  item. Small integers almost always occur somewhere in a chunk.
- **Pinned results describe the fixture corpus.** They don't describe the full
  index.
