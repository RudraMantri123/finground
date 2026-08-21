<!-- For model-eval contributions, keep the checklist below. For code/doc PRs, delete it and describe the change. -->

## Model eval submission

**Model(s):** `provider:model`
**Judge:** `provider:model`
**Run date:**
**Anything unusual (rate limits, retries, pinned snapshot):**

### Checklist

- [ ] `results/results.csv` row(s) produced by `scripts/run_benchmark.py` (not hand-edited)
- [ ] `results/runs/<model>.jsonl` audit dump included
- [ ] `make charts && make readme` re-run; charts + README table updated
