# AI Agent Instructions

Action-first cheatsheet for automations.

### Golden commands (copy-paste)

- Start services (recommended, includes build + health-wait):

```bash
./scripts/docker-setup.sh
```

- Start services (manual alternative):

```bash
docker compose -f docker/docker-compose.yml up -d --build
for i in {1..60}; do
  if curl -fsS http://localhost:8501 >/dev/null 2>&1; then echo ready; break; fi
  sleep 1
done
```

- Tail app logs (optional):

```bash
docker compose -f docker/docker-compose.yml logs -f app | cat
```

- Run E2E tests (quiet, fail fast):

```bash
.venv/bin/python -m pytest -q tests/e2e --disable-warnings --maxfail=1
```

- All-in-one (build + wait + tests):

```bash
./scripts/docker-setup.sh && \
.venv/bin/python -m pytest -q tests/e2e --disable-warnings --maxfail=1
```

- Stop services:

```bash
docker compose -f docker/docker-compose.yml down
```

Ports: app `http://localhost:8501`, Weaviate `http://localhost:8080`, Ollama `http://localhost:11434`.

### Local dev quick setup
To set up your local development environment, including the Python virtualenv, all dependencies, and system tools, run the unified setup script:
```bash
bash scripts/setup-dev-env.sh
```

After setup is complete, activate the virtual environment:
```bash
source .venv/bin/activate
```

Run the CLI QA loop:

```bash
.venv/bin/python -m backend.qa_loop
```

### Policies: imports and execution

- Do not set `PYTHONPATH`. Use editable install and module execution.
- Use absolute imports from project root.
  - Correct: `from backend.config import get_logger`
  - Incorrect: `from config import get_logger`
- Execute package modules with `-m`.
  - Correct: `.venv/bin/python -m backend.qa_loop`
  - Incorrect: `.venv/bin/python backend/qa_loop.py`

### Policies: Renovate configuration validation

- Always validate Renovate configuration changes before committing:
  ```bash
  npx --package renovate renovate-config-validator renovate.json
  npx --package renovate renovate-config-validator --strict renovate.json
  ```
- Use `npx` approach (not global installation) to avoid security vulnerabilities
- Validate locally before committing (CI focuses on code quality)

See below for Testing and Docker. For human-oriented docs, see `docs/DEVELOPMENT.md`.

### Policies: Linters

- **`yamlfmt`**: All YAML files are formatted by `yamlfmt`. The rules are in `.yamlfmt`.
  - **Check**: `yamlfmt --lint "**/*.yaml" "**/*.yml"`
  - **Fix**: `yamlfmt "**/*.yaml" "**/*.yml"`

---

## Orientation

- Directories: `backend/`, `frontend/`, `data/`, `docker/`, `scripts/`, `tests/`, `docs/`, `docs_AI_coder/`.
- Backend: `qa_loop.py` (RAG loop), `weaviate_client.py` (DB), `ollama_client.py` (LLM).
- Ingestion: Streamlit upload, `scripts/ingest.sh`, or compose `ingest` profile.

### Vectorization and Reranking Strategy

This project uses a client-side approach for both embedding and reranking with a centralized, offline-first model loading system.

- **Model Configuration**: All model settings are centralized in `backend/config.py` with `DEFAULT_*` constants and environment variable overrides
- **Vectorization**: Uses `backend.models.load_embedder()` with offline-first logic - checks for baked models locally, falls back to downloading with pinned commits
- **Reranking**: Uses `backend.models.load_reranker()` with the same offline-first approach for the `CrossEncoder` model
- **Environment Support**: Configurable for both development (with downloads) and production (offline with pre-baked models)

Server-side Weaviate modules like `text2vec-huggingface` or `reranker-huggingface` are not used. All vectorization happens client-side with local models.

## Testing

### Test Suites

The test suite is organized by folder structure to control scope and speed:

- **Unit Tests** (`tests/unit/`): Fast, isolated tests for individual functions/classes using mocking.
- **Integration Tests** (`tests/integration/`): Validate interactions, sometimes with Testcontainers.
- **End-to-End (E2E) Tests** (`tests/e2e/`): Full workflow; requires Docker stack.
- **UI Tests** (`tests/ui/`): Streamlit UI and Playwright browser tests.

Additional markers for specific behaviors:
- **Docker-Dependent Tests** (`@pytest.mark.docker`): Require a running Docker daemon.
- **Slow Tests** (`@pytest.mark.slow`): Long-running tests.
- **External Tests** (`@pytest.mark.external`): Require external services (Weaviate, Ollama).
- **Environment Tests** (`@pytest.mark.environment`): Validate local dev environment.

### Running Tests

- **Core test suite** (fast, with coverage):
  - Runs unit and integration tests. Excludes UI/E2E tests.
  - Generates a coverage report.

```bash
.venv/bin/python -m pytest -q tests/unit tests/integration
```

- **Integration tests with real services** (Compose-based):
  - Uses Docker Compose for Weaviate/Ollama services
  - Optimized build detection (only rebuilds when dependencies change)
  - Live code mounting for instant updates

```bash
# Start test environment
make test-up

# Run tests in container (use /opt/venv/bin/python, not .venv/bin/python)
docker compose -f docker/docker-compose.yml -f docker/compose.test.yml -p "$(cat .run_id)" exec -T app /opt/venv/bin/python -m pytest tests/integration/

# Stop environment
make test-down
```

- **UI test suite** (Playwright/Streamlit, no coverage):
  - Runs only the UI and Playwright browser tests.
  - Must be run with `--no-cov`.

```bash
.venv/bin/python -m pytest tests/ui --no-cov
```

- Run all tests (including slow and E2E):

```bash
.venv/bin/python -m pytest -v -m "not environment" --cov-fail-under=60
```

- E2E and Docker only (slowest):

```bash
.venv/bin/python -m pytest -v tests/e2e -m "docker"
```

- Environment sanity checks:

```bash
.venv/bin/python -m pytest -v -m "environment"
```

### Notes

Coverage policy:
- Coverage is collected by default, but the fail-under threshold is only enforced on full runs (e.g., CI or the command above with `--cov-fail-under=60`).
- On partial runs (using `-k`, `-m`, or explicit test paths), a safety in `tests/conftest.py` relaxes `--cov-fail-under` to 0 to avoid false failures. To disable coverage entirely, add `--no-cov`.

### Network policy in unit tests (for agents)

- Enforcement (always on)
  - Global flag: `--disable-socket` in `pyproject.toml` addopts
  - Session fixture: `disable_socket(allow_unix_socket=True)`
  - Guards: sentinel test asserts `SocketBlockedError`; `weaviate.connect_to_custom` is blocked in unit runs
  - Fail-fast diagnostic (opt-in): set `UNITNETGUARD_FAIL_FAST=1` to enable a per-test socket probe and immediate failure on first detection (default off to keep runs fast)

- Allowing network in one test
  - Use the opt-in fixture on that test only: `def test_x(allow_network): ...`
  - Prefer moving real-network tests to `tests/integration/` (folder-based organization)

- Quick verify
  - `.venv/bin/python -m pytest -q tests/unit/test_network_block_sentinel_unit.py` should pass
  - `.venv/bin/python -m pytest -q tests/unit` should show no OS-level network errors

- When things fail late in the suite
  - Cause: sockets re-enabled mid-run or a subprocess/library bypassed `pytest-socket`
  - Debug: set `UNITNETGUARD_FAIL_FAST=1`, re-run to pinpoint the first victim; use `-k` to bisect; try randomized order (pytest-randomly)
  - Fix: mock clients (e.g., `httpx.MockTransport`); avoid `enable_socket`/socket monkeypatches; move real-network tests to integration

### Flaky tests: cached globals/env

- Symptoms: order-dependent failures, real LLM text instead of mocked tokens, mocks not taking effect.
- Likely causes: cached globals (`qa_loop._cross_encoder`, `qa_loop._ollama_context`, `models._embedding_model`, `models._cross_encoder`), leftover `RAG_FAKE_ANSWER`, importing target modules inside fixtures before patches run, or using old model loading patterns instead of centralized `backend.models.load_embedder()`/`load_reranker()`.

- Fix quickly:
  1) **Unit tests (TARGET APPROACH)**: Use the modern fixtures in `tests/unit/conftest.py`:
     - `managed_cross_encoder` for cross-encoder mocking (preferred)
     - `mock_embedding_model` for embedding model mocking (preferred)
     - `reset_cross_encoder_cache` (autouse) handles cache cleanup

  2) **Integration tests (TARGET APPROACH)**: Use the established fixtures in `tests/unit/conftest.py`:
  ```python
  def test_with_mocked_models(mock_embedding_model: MagicMock):
      """Example using the project's mock_embedding_model fixture."""
      from backend.retriever import _get_embedding_model

      # The fixture automatically mocks backend.models.load_embedder
      model = _get_embedding_model()
      assert model is not None  # Returns the mock instance
  ```

  3) Don’t import target modules in fixtures that run before patches; prefer `sys.modules.get(...)`.
  4) Reproduce fast: run the failing test alone, then the suite; enable `pytest-randomly`.
  5) Env hygiene: set `RAG_FAKE_ANSWER` per-test via `monkeypatch.setenv`; let the autouse fixture clear it.


## Development Environment and Dependencies

### Avoid PYTHONPATH

Do not set `PYTHONPATH`. It can break virtual environment detection in tools. Use editable installs and module execution with `-m`.

### Dependency Strategy

- `requirements.txt`: production dependencies
- `requirements-dev.txt`: development/testing dependencies (includes `requirements.txt`)

Install for development:

```bash
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pip install -e .
```

Quick run: `.venv/bin/python -m backend.qa_loop`

### UV sandbox — ultra-short (for agents)

- Policy: pip-only for app/CI. Use `tools/uv_sandbox/` only to validate pins for major upgrades or conflicts.
- Run and verify:
```bash
cd tools/uv_sandbox
./run.sh
uv pip check && uv tree | head -200 | cat
```
- If clean, copy direct pins to `requirements.txt`/`requirements-dev.txt`, then verify locally (CPU wheels by default):
```bash
export PIP_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pip check
.venv/bin/python -m pytest -q tests/unit tests/integration
```
- Guardrails: no `uv` in app/CI; use `uv lock --check` + `uv sync --frozen`; do not track `tools/uv_sandbox/.venv/`; commit `pyproject.toml`/`uv.lock`; prefer CPU wheels unless CUDA/ROCm needed.


## Python Module and Import Strategy

1. Treat code directories like `backend/` as packages (have `__init__.py`).
2. Use absolute imports from project root.
   - Correct: `from backend.config import get_logger`
   - Incorrect: `from config import get_logger`
3. Execute package scripts as modules.
   - Correct: `.venv/bin/python -m backend.qa_loop`
   - Incorrect: `.venv/bin/python backend/qa_loop.py`

## Troubleshooting

### ModuleNotFoundError: No module named 'backend'

Ensure the project is installed in editable mode in the active venv:

```bash
.venv/bin/python -m pip install -e .
```

## Docker Workflow Details

Build images using `requirements.txt`, then install the project in editable mode:

```dockerfile
# Copy only production requirements first
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Copy project and install it
COPY backend/ ./backend
COPY pyproject.toml .
RUN pip install -e .
```

Rebuild app image cleanly and restart:

```bash
./scripts/build_app.sh --no-cache
docker compose -f docker/docker-compose.yml up -d --force-recreate app
```

## Quick Launcher (optional, WSL/VS Code)

Add to `~/.bashrc` or `~/.zshrc` for quick project entry:

```bash
llm () {
    local project=~/projects/kri-local-rag
    local ws="$project/kri-local-rag.code-workspace"
    cd "$project" || return 1
    [ -f .venv/bin/activate ] && source .venv/bin/activate
    code "$ws" >/dev/null 2>&1 &
}
```


## AI Agent Hints: Docker startup and E2E tests

Use these minimal, reliable commands when automating tasks.

### Start services (Docker)

Paths and ports:
- Compose: `docker/docker-compose.yml`
- App (Streamlit): `http://localhost:8501`
- Weaviate: `http://localhost:8080`
- Ollama: `http://localhost:11434`

Commands:

```bash
# Preferred
./scripts/docker-setup.sh

# Tail app logs if needed
docker compose -f docker/docker-compose.yml logs -f app | cat
```

### Docker Compose Troubleshooting

**Path Issues**: `docker compose -f docker/docker-compose.yml` resolves paths relative to compose file location
- Fix: Use `.env.docker` (not `./docker/.env.docker`) in compose files
- Validate: `docker compose -f docker/docker-compose.yml config`

**Env File Errors**: If "env file not found":
1. `ls -la docker/.env.docker` (check exists)
2. Fix path in docker-compose.yml (relative to compose file)
3. `docker compose -f docker/docker-compose.yml config` (validate)

### Run end-to-end (E2E) tests

Notes:
- Tests use env hooks to stay fast/deterministic:
  - `RAG_SKIP_STARTUP_CHECKS=1`
  - `RAG_FAKE_ANSWER=...`
  - `RAG_VERBOSE_TEST=1`

Command (from project root):

```bash
.venv/bin/python -m pytest -q tests/e2e --disable-warnings --maxfail=1
```

All-in-one (start + wait + tests):

```bash
docker compose -f docker/docker-compose.yml up -d --build && \
for i in {1..60}; do curl -fsS http://localhost:8501 >/dev/null 2>&1 && echo ready && break || sleep 1; done && \
.venv/bin/python -m pytest -q tests/e2e --disable-warnings --maxfail=1
```

Stop services:

```bash
docker compose -f docker/docker-compose.yml down
```
