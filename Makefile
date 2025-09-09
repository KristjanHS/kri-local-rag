# Declare phony targets
.PHONY: setup-hooks test-up test-down test-logs test-up-force-build test-clean \
        _test-up-with-id _test-down-with-id _test-logs-with-id build-if-needed \
        test-run-integration integration-local push-pr help setup-uv export-reqs \
        ruff-format ruff-fix yamlfmt pyright pre-commit unit-local pip-audit \
        semgrep-local actionlint uv-sync-test pre-push

# Use bash with strict flags for recipes
SHELL := bash
.SHELLFLAGS := -euo pipefail -c

# Stable project/session handling
RUN_ID_FILE := .run_id
LOG_DIR := logs
BUILD_HASH_FILE := .test-build.hash

# Only files that should trigger an image rebuild (no mounted app/test code here)
BUILD_DEPS := requirements.txt requirements-dev.txt pyproject.toml \
              docker/app.Dockerfile docker/docker-compose.yml

# Avoid repeating long compose invocations (use test profile)
COMPOSE := docker compose -f docker/docker-compose.yml --profile test

# Configurable pyright config path (default to repo config)
PYRIGHT_CONFIG ?= ./pyrightconfig.json

# ---------------------------------------------------------------------------
# Sections
#   - Setup
#   - Docker Test Environment
#   - Tests (local)
#   - Lint & Type
#   - Security / CI Linters
#   - CI Helpers & Git
# ---------------------------------------------------------------------------

help:
	@echo "Available targets:"
	@echo "  -- Setup --"
	@echo "  setup-hooks        - Configure Git hooks path"
	@echo "  setup-uv           - Create venv and sync dev/test via uv"
	@echo "  export-reqs        - Export requirements.txt from uv.lock"
	@echo ""
	@echo "  -- Lint & Type Check --"
	@echo "  ruff-format        - Auto-format code with Ruff"
	@echo "  ruff-fix           - Run Ruff lint with autofix"
	@echo "  yamlfmt            - Validate YAML formatting via pre-commit"
	@echo "  pyright            - Run Pyright type checking"
	@echo "  pre-commit         - Run all pre-commit hooks on all files"
	@echo ""
	@echo "  -- Tests --"
	@echo "  unit-local         - Run unit tests (local) and write reports"
	@echo "  integration-local  - Run integration tests (uv preferred)"
	@echo ""
	@echo "  -- Security / CI linters --"
	@echo "  pip-audit          - Export from uv.lock and audit prod/dev+test deps"
	@echo "  semgrep-local      - Run Semgrep locally via uvx (no metrics)"
	@echo "  actionlint         - Lint GitHub workflows using actionlint in Docker"
	@echo ""
	@echo "  -- CI helpers & Git --"
	@echo "  uv-sync-test       - uv sync test group (frozen) + pip check"
	@echo "  pre-push           - Run pre-push checks with all SKIP=0"

# =========================
# Setup
# =========================
setup-hooks:
	@echo "Configuring Git hooks path..."
	@git config core.hooksPath scripts/git-hooks
	@echo "Done."

setup-uv:
	@./run_uv.sh

export-reqs:
	@echo ">> Exporting requirements.txt from uv.lock (incl dev/test groups)"
	uv export --no-hashes --group test --locked --no-emit-project --no-emit-package torch --format requirements-txt > requirements.txt

# =========================
# Docker Test Environment
# =========================
test-up:
	@if [ -f $(RUN_ID_FILE) ]; then \
		EXISTING_RUN_ID=$$(cat $(RUN_ID_FILE)); \
		if $(COMPOSE) -p "$$EXISTING_RUN_ID" ps -q 2>/dev/null | grep -q .; then \
			echo "Test env RUN_ID=$$EXISTING_RUN_ID already running."; \
			echo "Use 'make test-down' to stop it, or 'make test-logs' to view logs."; \
			exit 0; \
		else \
			echo "Stale RUN_ID file found, cleaning up..."; \
			rm -f $(RUN_ID_FILE); \
		fi; \
	fi; \
	RUN_ID=$$(date +%s); \
	echo $$RUN_ID > $(RUN_ID_FILE); \
	$(MAKE) _test-up-with-id RUN_ID=$$RUN_ID

_test-up-with-id:
	@echo "Starting test environment with RUN_ID=$(RUN_ID)..."
	@$(MAKE) build-if-needed RUN_ID=$(RUN_ID)
	@$(COMPOSE) -p "$(RUN_ID)" up -d --wait --wait-timeout 120 weaviate ollama app-test
	@echo "Test environment started."

build-if-needed:
	@mkdir -p $(LOG_DIR)
	@NEW_HASH=$$(sha256sum $(BUILD_DEPS) | sha256sum | awk '{print $$1}'); \
	OLD_HASH=$$(cat $(BUILD_HASH_FILE) 2>/dev/null || echo ''); \
	if [ "$$NEW_HASH" != "$$OLD_HASH" ]; then \
		echo "Build deps changed; rebuilding images..."; \
		DOCKER_BUILDKIT=1 $(COMPOSE) -p "$(RUN_ID)" build app-test 2>&1 \
		  | tee $(LOG_DIR)/test-build-$(RUN_ID).log; \
		# Update stable symlink and prune older test-build logs (keep latest 5) \
		ln -sf "test-build-$(RUN_ID).log" "$(LOG_DIR)/test-build.log"; \
		ls -1t $(LOG_DIR)/test-build-*.log 2>/dev/null | tail -n +6 | xargs -r rm --; \
		echo $$NEW_HASH > $(BUILD_HASH_FILE); \
	else \
		echo "Build deps unchanged; skipping 'docker compose build'."; \
	fi

test-up-force-build:
	@echo "Force rebuilding test environment..."
	@rm -f $(BUILD_HASH_FILE)
	@if [ -f $(RUN_ID_FILE) ]; then \
		EXISTING_RUN_ID=$$(cat $(RUN_ID_FILE)); \
		$(MAKE) _test-down-with-id RUN_ID=$$EXISTING_RUN_ID; \
		rm -f $(RUN_ID_FILE); \
	fi; \
	RUN_ID=$$(date +%s); \
	echo $$RUN_ID > $(RUN_ID_FILE); \
	$(MAKE) _test-up-with-id RUN_ID=$$RUN_ID

test-down:
	@if [ -f $(RUN_ID_FILE) ]; then \
		RUN_ID=$$(cat $(RUN_ID_FILE)); \
		$(MAKE) _test-down-with-id RUN_ID=$$RUN_ID; \
		rm -f $(RUN_ID_FILE); \
	else \
		echo "No active test environment found."; \
	fi

_test-down-with-id:
	@echo "Stopping test environment with RUN_ID=$(RUN_ID) ..."
	@$(COMPOSE) -p "$(RUN_ID)" down -v

test-logs:
	@if [ -f $(RUN_ID_FILE) ]; then \
		RUN_ID=$$(cat $(RUN_ID_FILE)); \
		$(MAKE) _test-logs-with-id RUN_ID=$$RUN_ID; \
	else \
		echo "No active test environment found."; \
	fi

_test-logs-with-id:
	@echo "Fetching logs for test environment with RUN_ID=$(RUN_ID) ..."
	@$(COMPOSE) -p "$(RUN_ID)" logs -n 200 app-test weaviate ollama

# Run integration tests inside the app container using existing .run_id
test-run-integration:
	@if [ -f $(RUN_ID_FILE) ]; then \
		RUN_ID=$$(cat $(RUN_ID_FILE)); \
		$(COMPOSE) -p "$$RUN_ID" exec -T app-test /opt/venv/bin/python3 -m pytest tests/integration -q --junitxml=reports/junit_compose_integration.xml; \
	else \
		echo "No active test environment found. Run 'make test-up' first."; \
		exit 1; \
	fi

test-clean:
	@echo "Cleaning up test environment and build cache..."
	@rm -f $(BUILD_HASH_FILE) $(RUN_ID_FILE)
	@echo "Test build cache cleaned."

# =========================
# Tests (local)
# =========================
# (moved) unit-local defined under Tests section above

# Run local integration tests; prefer uv if available, then .venv fallback
integration-local:
	@if command -v uv >/dev/null 2>&1; then \
		uv run -m pytest tests/integration -q ${PYTEST_ARGS}; \
	elif [ -x .venv/bin/python ]; then \
		.venv/bin/python -m pytest tests/integration -q ${PYTEST_ARGS}; \
	else \
		echo "uv not found and .venv/bin/python missing. Install uv (https://astral.sh/uv) and run './run_uv.sh', or create venv then run '.venv/bin/python -m pytest tests/integration -q'"; \
		exit 1; \
	fi

# (moved) push-pr under CI Helpers & Git

# (removed legacy grouping header; replaced by explicit sections)

# =========================
# Security / CI Linters
# =========================
# audits the already existing env (after export)
pip-audit: export-reqs
	@echo ">> Auditing dependencies (based on requirements.txt)"
	uvx --from pip-audit pip-audit -r requirements.txt

# (moved) CI Helpers & Git at end of file

# New canonical unit test target
unit-local:
	mkdir -p reports
	@if [ -x .venv/bin/python ]; then \
		.venv/bin/python -m pytest tests/unit -n auto --maxfail=1 -q --junitxml=reports/junit.xml ${PYTEST_ARGS}; \
	else \
		uv run -m pytest tests/unit -n auto --maxfail=1 -q --junitxml=reports/junit.xml ${PYTEST_ARGS}; \
	fi

# =========================
# Lint & Type
# =========================
pyright:
	@# Determine interpreter path: prefer .venv, then system python
	@PY_INTERP=""; \
	if [ -x .venv/bin/python ]; then \
		PY_INTERP=".venv/bin/python"; \
	elif command -v python3 >/dev/null 2>&1; then \
		PY_INTERP=$$(command -v python3); \
	else \
		PY_INTERP=$$(command -v python); \
	fi; \
	if [ -x .venv/bin/pyright ]; then \
		.venv/bin/pyright --pythonpath "$$PY_INTERP" --project $(PYRIGHT_CONFIG); \
	else \
		uvx pyright --pythonpath "$$PY_INTERP" --project $(PYRIGHT_CONFIG); \
	fi

yamlfmt:
	# Ensure dev + test groups are present so later test steps still work
	uv sync --group dev --group test --frozen
	uv run pre-commit run yamlfmt -a

# Ruff targets
ruff-format:
	@if [ -x .venv/bin/ruff ]; then \
		.venv/bin/ruff format .; \
	else \
		uv run ruff format .; \
	fi

ruff-fix:
	@if [ -x .venv/bin/ruff ]; then \
		.venv/bin/ruff check --fix .; \
	else \
		uv run ruff check --fix .; \
	fi

# Run full pre-commit suite (dev deps required)
pre-commit:
	# Keep test deps installed to avoid breaking local test runs after this target
	uv sync --group dev --group test --frozen
	uv run pre-commit run --all-files


# Security / CI Linters (cont.)
# Lint GitHub Actions workflows locally using official container
actionlint:
	@docker run --rm \
		--user "$(shell id -u):$(shell id -g)" \
		-v "$(CURDIR)":/repo \
		-w /repo \
		rhysd/actionlint:latest -color && echo "Actionlint: no issues found"

# Run Semgrep locally using uvx, mirroring the local workflow
semgrep-local:
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

# =========================
# CI Helpers & Git
# =========================
uv-sync-test:
	uv sync --group test --frozen
	uv pip check

# Run the same checks as the Git pre-push hook, forcing all SKIP flags to 0
pre-push:
	SKIP_LOCAL_SEC_SCANS=0 SKIP_LINT=0 SKIP_PYRIGHT=0 SKIP_TESTS=0 scripts/git-hooks/pre-push

# Convenience: push, then run local integration tests, then create/show PR
push-pr:
	@bash scripts/dev/pushpr.sh ${ARGS}
