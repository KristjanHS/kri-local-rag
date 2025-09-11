# Declare phony targets
.PHONY: help setup-hooks test-up test-down test-logs test-up-force-build test-clean \
        test-integration integration push-pr setup-uv export-reqs \
        ruff-format ruff-fix yamlfmt pyright pre-commit unit pip-audit \
        semgrep-local actionlint uv-sync-test pre-push stack-up stack-down stack-reset ingest cli app-logs ask e2e coverage coverage-html dev-setup ollama-pull deptry

# Use bash with strict flags for recipes
SHELL := bash
.SHELLFLAGS := -euo pipefail -c
.ONESHELL:
.DEFAULT_GOAL := help

# Avoid repeating long compose invocations
COMPOSE_APP := docker compose -f docker/docker-compose.yml

# Tool resolver shortcuts (prefer .venv, fallback to uv/uvx)
PYTEST := $(if $(wildcard .venv/bin/python),.venv/bin/python -m pytest,uv run -m pytest)
RUFF := $(if $(wildcard .venv/bin/ruff),.venv/bin/ruff,uv run ruff)
PYRIGHT_BIN := $(if $(wildcard .venv/bin/pyright),.venv/bin/pyright,uvx pyright)
PYTEST_BASE := -q

# Configurable pyright config path (default to repo config)
PYRIGHT_CONFIG ?= ./pyrightconfig.json

# Ensure uv uses a repo-local cache in sandboxed environments
UV_CACHE_DIR := $(CURDIR)/.uv_cache

# ---------------------------------------------------------------------------
# Sections
#   - Setup
#   - App Runtime
#   - Docker Test Environment
#   - Tests (local)
#   - Security / CI Linters
#   - Lint & Type
#   - CI Helpers & Git
# ---------------------------------------------------------------------------

help: ## Show this help (grouped)
	@awk '
	  BEGIN {
	    FS = ":.*##";
	    last = "";
	    saw_sep = 0; pending = ""; section = "";
	  }
	  # Detect section banners of the form:\n# =========================\n# Name\n# =========================
	  /^# =+/ { if (saw_sep == 0) { saw_sep = 1 } else if (saw_sep == 1 && pending != "") { section = pending; pending = ""; saw_sep = 0 } ; next }
	  saw_sep == 1 && match($$0, /^# (.+)$$/, m) { pending = m[1]; next }

	  # Targets with inline help "## description"
	  /^[a-zA-Z0-9_.-]+:.*##/ {
	    tgt = $$1; gsub(/^\s+|\s+$$/, "", tgt);
	    # Recompute desc from original line to preserve colons before ##
	    idx = index($$0, "##"); desc = substr($$0, idx + 2);
	    gsub(/^\s+/, "", desc);
	    sec = (section == "" ? "Other" : section);
	    if (sec != last) { if (last != "") print ""; print sec ":"; last = sec }
	    printf "  %-22s %s\n", tgt, desc;
	  }
	' $(MAKEFILE_LIST)

# =========================
# Setup
# =========================
setup-hooks: ## Configure Git hooks path
	@echo "Configuring Git hooks path..."
	@git config core.hooksPath scripts/git-hooks
	@echo "Done."

setup-uv: ## Create venv and sync dev/test via uv
	@./run_uv.sh

export-reqs: ## Export requirements.txt from uv.lock (omits torch/GPU extras)
	@echo ">> Exporting requirements.txt from uv.lock (incl dev/test groups), excluding torch and GPU-specific wheels"
	mkdir -p $(UV_CACHE_DIR)
	UV_CACHE_DIR=$(UV_CACHE_DIR) uv export \
	  --no-hashes \
	  --group test \
	  --locked \
	  --no-emit-project \
	  --no-emit-package torch \
	  --format requirements-txt \
	  > requirements.txt
	@echo ">> Wrote requirements.txt (torch and GPU extras removed)"

# =========================
# App Runtime
# =========================
# Start of full stack (Weaviate, Ollama, App)
stack-up: ## Build and start app + deps via script
	@./scripts/docker/docker-setup.sh

# Non-interactive: start app stack (weaviate, ollama, app) and wait for health
app-up: ## Start app stack (compose --wait) non-interactively
	@$(COMPOSE_APP) up -d --wait weaviate ollama app

# Non-interactive: stop app stack and remove containers (preserve volumes)
app-down: ## Stop app stack (compose down)
	@$(COMPOSE_APP) down

# Ingest documents (default path inside script is ./data). Override path with INGEST_SRC=/path
ingest: ## Ingest documents (override path with INGEST_SRC=/path)
	@if [ -n "$(INGEST_SRC)" ]; then \
		./scripts/ingest.sh "$(INGEST_SRC)"; \
	else \
		./scripts/ingest.sh; \
	fi

stack-down: ## Stop all app services (preserves volumes)
	@$(COMPOSE_APP) down

# Destructive: stop and remove containers, networks, and volumes
stack-reset: ## Full reset via docker-reset.sh (destructive)
	@./scripts/docker/docker-reset.sh

app-logs: ## Fetch/tail app/weaviate/ollama logs (LINES=200, FOLLOW=1)
	@LINES=$${LINES:-200}; FOLLOW_FLAG=""; if [ "$${FOLLOW:-0}" != "0" ]; then FOLLOW_FLAG="-f"; fi; $(COMPOSE_APP) logs -n "$$LINES" $$FOLLOW_FLAG app weaviate ollama

cli: ## Start CLI Q&A (pass ARGS='--question "..."')
	@./scripts/cli.sh ${ARGS}

# Convenience: ask a one-off question without passing ARGS
ask: ## One-off question via CLI (Q='...')
	@if [ -z "$(Q)" ]; then \
		echo "Usage: make ask Q='Your question here'"; \
		exit 1; \
	fi
	@$(MAKE) cli ARGS="--question '$(Q)'"

# Pull an Ollama model inside the container
ollama-pull: ## Pull Ollama model in container (MODEL=...)
	@if [ -z "$(MODEL)" ]; then \
		echo "Usage: make ollama-pull MODEL=model/name[:tag]"; \
		exit 1; \
	fi
		@if [ -z "$$(\
			$(COMPOSE_APP) ps -q ollama 2>/dev/null\
		)" ]; then \
			echo "Ollama service is not running. Start the stack first: make stack-up"; \
			exit 1; \
		fi
	@$(COMPOSE_APP) exec -T ollama ollama pull "$(MODEL)"

# Run E2E tests with automatic stack lifecycle
e2e: ## Run E2E tests (stack-up → test → optional stack-down). Set PRESERVE=0 to stack-down
    @set -euo pipefail; \
    $(MAKE) stack-up; \
    EXIT=0; \
    $(PYTEST) tests/e2e $(PYTEST_BASE) $${PYTEST_ARGS:-} || EXIT=$$?; \
    if [ "$${PRESERVE:-1}" = "0" ]; then \
        $(MAKE) stack-down; \
    else \
        echo "Skipping stack-down: PRESERVE=1 (containers/networks preserved)"; \
    fi; \
    exit $$EXIT
	
# Run E2E tests and write reports (assumes test environment is already running)
test-e2e: ## Run E2E tests and write reports
	mkdir -p reports
	$(PYTEST) tests/e2e $(PYTEST_BASE) --junitxml=reports/junit_e2e.xml ${PYTEST_ARGS}

# Coverage run (host)
coverage: ## Run coverage across repo (HTML=1 for HTML report)
	@mkdir -p reports
	HTML_FLAG=""; if [ "$${HTML:-0}" != "0" ]; then mkdir -p reports/coverage; HTML_FLAG="--cov-report=html:reports/coverage"; fi; \
	$(PYTEST) -v -m "not environment" --cov=. --cov-report=term $$HTML_FLAG --cov-report=xml:reports/coverage.xml $${PYTEST_ARGS:-}

# Coverage run (host) with HTML output
coverage-html: ## Run coverage and write HTML to reports/coverage
	@$(MAKE) coverage HTML=1

# Developer setup wrapper
dev-setup: ## Bootstrap dev env (venv, deps, tools)
	bash scripts/dev/setup-dev-env.sh

# =========================
# Docker Test Environment
# =========================
test-up: ## Start docker test env; use FORCE=1 to rebuild
	bash scripts/dev/test-env.sh up $(if $(FORCE),--force,)

test-up-force-build: ## Alias for test-up with FORCE=1
	bash scripts/dev/test-env.sh up --force

test-down: ## Stop docker test env if running
	bash scripts/dev/test-env.sh down

test-logs: ## Show docker test env logs
	bash scripts/dev/test-env.sh logs

# Run integration tests inside the app container using existing .run_id
test-integration: ## Run integration tests inside docker test env
	bash scripts/dev/test-env.sh run-integration

test-e2e: ## Run E2E tests on host against docker test env using existing .run_id
	bash scripts/dev/test-env.sh run-e2e

test-clean: ## Remove test env run/build metadata
	bash scripts/dev/test-env.sh clean

# =========================
# Tests
# =========================
# Run unit tests and write reports
unit: ## Run unit tests and write reports
	mkdir -p reports
	$(PYTEST) tests/unit -n 1 --maxfail=1 $(PYTEST_BASE) --junitxml=reports/junit.xml ${PYTEST_ARGS}

# Run local integration tests; prefer uv if available, then .venv fallback
integration: ## Run local integration tests (venv or uv)
	@if [ -x .venv/bin/python ]; then \
		.venv/bin/python -m pytest tests/integration -q ${PYTEST_ARGS}; \
	elif command -v uv >/dev/null 2>&1; then \
		uv run -m pytest tests/integration -q ${PYTEST_ARGS}; \
	else \
		echo ".venv/bin/python not found and uv not available. Create the venv (./run_uv.sh or python -m venv .venv) then run '.venv/bin/python -m pytest tests/integration -q'"; \
		exit 1; \
	fi

 

# =========================
# Security / CI Linters
# =========================
# audits the already existing env (after export)
pip-audit: export-reqs ## Audit dependencies based on requirements.txt
	@echo ">> Auditing dependencies (based on requirements.txt)"
	uvx --from pip-audit pip-audit -r requirements.txt

 # Lint GitHub Actions workflows locally using official container
actionlint: ## Lint GitHub workflows using actionlint in Docker
	@docker run --rm \
		--user "$(shell id -u):$(shell id -g)" \
		-v "$(CURDIR)":/repo \
		-w /repo \
		rhysd/actionlint:latest -color && echo "Actionlint: no issues found"

# Run Semgrep locally using uvx, mirroring the local workflow
semgrep-local: ## Run Semgrep locally via uvx (no metrics)
	@if command -v uv >/dev/null 2>&1; then \
		uvx --from semgrep semgrep ci \
		  --config auto \
		  --metrics off \
		  --sarif \
		  --output semgrep_local.sarif; \
		echo "Semgrep SARIF written to semgrep_local.sarif"; \
		if command -v jq >/dev/null 2>&1; then \
		  COUNT=$$(jq '[.runs[0].results[]] | length' semgrep_local.sarif 2>/dev/null || echo 0); \
		  echo "Semgrep findings: $${COUNT} (see semgrep_local.sarif)"; \
		else \
		  COUNT=$$(grep -o '"ruleId"' -c semgrep_local.sarif 2>/dev/null || echo 0); \
		  echo "Semgrep findings: $${COUNT} (approx; no jq)"; \
		fi; \
	else \
		echo "uv not found. Install uv: https://astral.sh/uv"; \
		exit 1; \
	fi


# Dependency health check using deptry (reads pyproject config)
deptry: ## Analyze Python dependencies with deptry
	@if command -v uv >/dev/null 2>&1; then \
		uvx --from deptry deptry . --json-output deptry_report.json; \
		echo "Deptry JSON report written to deptry_report.json"; \
	else \
		echo "uv not found. Install uv: https://astral.sh/uv"; \
		exit 1; \
	fi


# =========================
# Lint & Type
# =========================
PYRIGHT_LEVEL ?= error

pyright: ## Run Pyright type checking
	@# Determine interpreter path: prefer .venv, then system python
	@PY_INTERP=""; \
	if [ -x .venv/bin/python ]; then PY_INTERP=".venv/bin/python"; \
	elif command -v python3 >/dev/null 2>&1; then PY_INTERP=$$(command -v python3); \
	else PY_INTERP=$$(command -v python); fi; \
	$(PYRIGHT_BIN) --level $(PYRIGHT_LEVEL) --pythonpath "$$PY_INTERP" --project $(PYRIGHT_CONFIG)

yamlfmt: ## Validate YAML formatting via pre-commit
	# Ensure dev + test groups are present so later test steps still work
	uv sync --group dev --group test --frozen
	uv run pre-commit run yamlfmt -a

# Ruff targets
ruff-format: ## Auto-format code with Ruff
	$(RUFF) format .

ruff-fix: ## Run Ruff lint with autofix
	$(RUFF) check --fix .

# Run full pre-commit suite (dev deps required)
pre-commit: ## Run all pre-commit hooks on all files
	# Keep test deps installed to avoid breaking local test runs after this target
	uv sync --group dev --group test --frozen
	uv run pre-commit run --all-files

# =========================
# CI Helpers & Git
# =========================
uv-sync-test: ## uv sync test group (frozen) + pip check
	uv sync --group test --frozen
	uv pip check

# Run the same checks as the Git pre-push hook, forcing all SKIP flags to 0
pre-push: ## Run pre-push checks with all SKIP=0
	SKIP_LOCAL_SEC_SCANS=0 SKIP_LINT=0 SKIP_PYRIGHT=0 SKIP_TESTS=0 scripts/git-hooks/pre-push

# Convenience: push, then run local integration tests, then create/show PR
push-pr: ## Push branch, run local integration tests, and create/show PR
	@bash scripts/dev/pushpr.sh ${ARGS}
