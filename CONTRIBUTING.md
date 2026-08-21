# Contributing to FinGround

Thanks for helping build an honest, faithfulness-first financial RAG benchmark.
The single most valuable contribution right now is a **hosted-model eval** —
see below.

## Contribute a model eval

The committed leaderboard was produced on a machine with **no paid API keys**,
so every scored model so far runs locally via Ollama. If you have an OpenAI or
Anthropic key, you can put GPT-4o, GPT-4o-mini, or Claude on the board in about
ten minutes of wall-clock time and typically **under ~$1–2 per model** for the
20-question set (answering + judging; LLM responses are disk-cached, so
re-runs are free).

### Steps

```bash
git clone https://github.com/RudraMantri123/finground.git
cd finground
make setup                    # venv + editable install
cp .env.example .env          # add your OPENAI_API_KEY and/or ANTHROPIC_API_KEY
make ingest                   # download + chunk the SEC filings (deterministic)
make index                    # build BM25 + FAISS indexes
```

Then run the benchmark for the model(s) you want to contribute. Use
`openai:gpt-4o` as the judge if you have an OpenAI key — it's the project's
default judge, and the judge used is recorded per row in the leaderboard:

```bash
.venv/bin/python scripts/run_benchmark.py --models openai:gpt-4o --judge openai:gpt-4o
.venv/bin/python scripts/run_benchmark.py --models anthropic:claude-sonnet-5 --judge openai:gpt-4o
```

Results **merge** into `results/results.csv` — your run updates only the rows
for the models you evaluated and leaves the rest of the leaderboard untouched.
Finally, regenerate the derived artifacts:

```bash
make charts
make readme
```

### PR checklist

Open a pull request containing:

- [ ] The updated `results/results.csv` row(s) — with the `judge` column filled in
- [ ] The per-question audit dump `results/runs/<model>.jsonl` (committed on purpose — it's what lets others verify your row)
- [ ] Regenerated `results/charts/*.png` and the README results table (`make charts && make readme`)
- [ ] A one-line note in the PR description: date of the run and anything unusual (rate limits, retries, model snapshot/version if pinned)

Please don't hand-edit numbers in `results.csv` or the README table — they
must come from `scripts/run_benchmark.py` so every row is reproducible.

## Contribute a provider

The LLM wrapper (`src/finground/llm.py`) is provider-agnostic — models are
named `provider:model` and unavailable providers are skipped. Adding Gemini,
Mistral, Groq, Together, etc. is a small, well-contained patch: implement the
provider call, register it in `available_providers()` / the dispatch, and add
the key to `.env.example`. PRs very welcome.

## Contribute gold questions or human labels

- **Gold set** (`results/gold_set.jsonl`): more questions — especially
  unanswerable-by-design ones — make the benchmark stronger. Each item needs a
  question, the gold answer (or `answerable: false`), and the source filing.
- **Human labels** (`results/human_labels/`): judge-vs-human agreement (Cohen's
  κ) is the benchmark's trust anchor. More labeled examples tighten it.

## Code contributions

```bash
make test    # pytest
make lint    # ruff + black --check + mypy
```

CI runs ruff, black, and pytest on every PR. Keep changes small and covered by
a test where it's practical.
