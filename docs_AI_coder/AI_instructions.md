# AI Agent Instructions

Action-first cheatsheet for automations.

### Golden commands (copy-paste)

- Start services (build + up + wait):

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
.venv/bin/python -m pytest -q -m e2e --disable-warnings --maxfail=1
```

- All-in-one (build + wait + tests):

```bash
docker compose -f docker/docker-compose.yml up -d --build && \
for i in {1..60}; do curl -fsS http://localhost:8501 >/dev/null 2>&1 && echo ready && break || sleep 1; done && \
.venv/bin/python -m pytest -q -m e2e --disable-warnings --maxfail=1
```

- Stop services:

```bash
docker compose -f docker/docker-compose.yml down
```

Ports: app `http://localhost:8501`, Weaviate `http://localhost:8080`, Ollama `http://localhost:11434`.

### Local dev quick setup

```bash
python -m venv .venv
source .venv/bin/activate
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pip install -e .
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

See below for Testing and Docker. For human-oriented docs, see `docs/DEVELOPMENT.md`.

---

## Orientation

- Directories: `backend/`, `frontend/`, `data/`, `docker/`, `scripts/`, `tests/`, `docs/`, `docs_AI_coder/`.
- Backend: `qa_loop.py` (RAG loop), `weaviate_client.py` (DB), `ollama_client.py` (LLM).
- Ingestion: Streamlit upload, `scripts/ingest.sh`, or compose `ingest` profile.

### Vectorization and Reranking Strategy

This project uses a client-side approach for both embedding and reranking, using local models.

- **Vectorization**: A `SentenceTransformer` (bi-encoder) model creates vectors locally. Data is then ingested into Weaviate with manually provided vectors (`vectorizer: 'none'`).
- **Reranking**: A `CrossEncoder` model re-scores the top search results locally for better relevance.

Server-side Weaviate modules like `text2vec-huggingface` or `reranker-huggingface` are not used.

## Testing

### Test Suites

The test suite is organized with markers to control scope and speed:

- **Unit Tests** (`@pytest.mark.unit`): Fast, isolated tests for individual functions/classes using mocking.
- **Integration Tests** (`@pytest.mark.integration`): Validate interactions, sometimes with Testcontainers.
- **End-to-End (E2E) Tests** (`@pytest.mark.e2e`): Full workflow; requires Docker stack.
- **Docker-Dependent Tests** (`@pytest.mark.docker`): Require a running Docker daemon.
- **Slow Tests** (`@pytest.mark.slow`): Long-running tests.
- **Environment Tests** (`@pytest.mark.environment`): Validate local dev environment.

### Running Tests

- **Core test suite** (fast, with coverage):
  - Runs unit and integration tests. Excludes UI/E2E tests.
  - Generates a coverage report.

```bash
.venv/bin/python -m pytest --test-core
```

- **UI test suite** (Playwright/Streamlit, no coverage):
  - Runs only the UI and Playwright browser tests.
  - Must be run with `--no-cov`.

```bash
.venv/bin/python -m pytest --test-ui --no-cov
```

- Run all tests (including slow and E2E):

```bash
.venv/bin/python -m pytest -v -m "not environment"
```

- E2E and Docker only (slowest):

```bash
.venv/bin/python -m pytest -v -m "e2e or docker"
```

- Environment sanity checks:

```bash
.venv/bin/python -m pytest -v -m "environment"
```

### Notes




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
docker compose -f docker/docker-compose.yml up -d --build

# Wait for the app to be reachable
for i in {1..60}; do
  if curl -fsS http://localhost:8501 >/dev/null 2>&1; then echo ready; break; fi
  sleep 1
done

# Tail app logs if needed
docker compose -f docker/docker-compose.yml logs -f app | cat
```

### Run end-to-end (E2E) tests

Notes:
- Pytest default in `pytest.ini` excludes `slow`; selecting `-m e2e` overrides this.
- Tests use env hooks to stay fast/deterministic:
  - `RAG_SKIP_STARTUP_CHECKS=1`
  - `RAG_FAKE_ANSWER=...`
  - `RAG_VERBOSE_TEST=1`

Command (from project root):

```bash
.venv/bin/python -m pytest -q -m e2e --disable-warnings --maxfail=1
```

All-in-one (start + wait + tests):

```bash
docker compose -f docker/docker-compose.yml up -d --build && \
for i in {1..60}; do curl -fsS http://localhost:8501 >/dev/null 2>&1 && echo ready && break || sleep 1; done && \
.venv/bin/python -m pytest -q -m e2e --disable-warnings --maxfail=1
```

Stop services:

```bash
docker compose -f docker/docker-compose.yml down
```
