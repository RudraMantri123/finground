# FinGround task runner.
# Reproducible commands from a fresh clone. See README for the full walkthrough.

PYTHON ?= python3.11
VENV   ?= .venv
BIN     = $(VENV)/bin
PORT   ?= 8000

.DEFAULT_GOAL := help

.PHONY: help
help:  ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

$(VENV):
	$(PYTHON) -m venv $(VENV)

.PHONY: setup
setup: $(VENV)  ## Create venv and install the package with dev tooling
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -e ".[dev]"
	@echo "Done. Copy .env.example to .env and add your keys."

.PHONY: ingest
ingest:  ## Download + parse + chunk SEC filings into data/
	$(BIN)/python scripts/run_ingest.py

.PHONY: index
index:  ## Build BM25 + FAISS dense indexes from chunks
	$(BIN)/python scripts/run_index.py

.PHONY: serve
serve:  ## Run the FastAPI query service + demo page
	$(BIN)/uvicorn finground.serve:app --reload --port $(PORT)

.PHONY: benchmark
benchmark:  ## Evaluate models -> results/results.csv
	$(BIN)/python scripts/run_benchmark.py

.PHONY: charts
charts:  ## Render comparison charts from results/results.csv
	$(BIN)/python scripts/make_charts.py

.PHONY: dashboard
dashboard:  ## Build the observability report (traces + leaderboard) -> traces/dashboard.html
	$(BIN)/python scripts/make_dashboard.py

.PHONY: readme
readme:  ## Re-render the README results + judge-validation tables from results/
	$(BIN)/python scripts/update_readme.py

.PHONY: validate-judge
validate-judge:  ## Report LLM-judge vs human-label agreement (Cohen's kappa)
	$(BIN)/python -m finground.eval.validate_judge

.PHONY: test
test:  ## Run the unit test suite
	$(BIN)/pytest

.PHONY: lint
lint:  ## Ruff + black --check + mypy
	$(BIN)/ruff check src scripts tests
	$(BIN)/black --check src scripts tests
	$(BIN)/mypy

.PHONY: format
format:  ## Auto-format with black + ruff --fix
	$(BIN)/ruff check --fix src scripts tests
	$(BIN)/black src scripts tests

.PHONY: clean
clean:  ## Remove caches and build artifacts (keeps data/ and indexes/)
	rm -rf .mypy_cache .ruff_cache .pytest_cache **/__pycache__ *.egg-info src/*.egg-info
