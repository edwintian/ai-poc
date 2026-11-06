# Singapore Employment Contract Checker — common tasks.
# Run `make help` to see all targets. Run from the repository root.

PYTHON_BIN ?= python3.11
VENV       ?= .venv
PY         := $(VENV)/bin/python
PIP        := $(VENV)/bin/pip

.DEFAULT_GOAL := help
.PHONY: help setup env test run samples eval kb secrets-check clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

$(VENV)/.installed: requirements.txt
	@command -v $(PYTHON_BIN) >/dev/null || { echo "$(PYTHON_BIN) not found. Install Python 3.11 or run: make setup PYTHON_BIN=python3"; exit 1; }
	@test -d $(VENV) || $(PYTHON_BIN) -m venv $(VENV)
	$(PIP) install -r requirements.txt
	@touch $@

setup: $(VENV)/.installed env ## Create .venv, install dependencies, create .env

env: ## Create .env from .env.example if missing
	@if [ ! -f .env ]; then cp .env.example .env; \
		echo "Created .env — edit it and set OPENAI_API_KEY and APP_PASSWORD."; \
	fi

test: $(VENV)/.installed ## Run the test suite (offline, LLMs stubbed)
	$(PY) -m pytest -q

run: $(VENV)/.installed env ## Start the Streamlit app
	$(VENV)/bin/streamlit run app.py

samples: $(VENV)/.installed ## Regenerate the sample contract PDFs
	$(PY) -m sample_contracts.make_samples --samples

eval: $(VENV)/.installed ## Run the accuracy eval (real model, costs a few cents)
	$(PY) scripts/eval.py

kb: $(VENV)/.installed ## Rebuild the knowledge-base index (needs OPENAI_API_KEY)
	$(PY) scripts/build_kb.py

secrets-check: ## Fail if secrets are tracked in git
	@! git ls-files | grep -E '(^|/)\.env$$|secrets\.toml$$' || { echo "Secret file tracked!"; exit 1; }
	@! git grep -nE 'sk-[A-Za-z0-9_-]{20,}' || { echo "API key found in tracked files!"; exit 1; }
	@echo "No tracked secrets found."

clean: ## Remove the virtualenv and caches
	rm -rf $(VENV) .pytest_cache
	find . -name __pycache__ -type d -prune -not -path './myenv/*' -exec rm -rf {} +
