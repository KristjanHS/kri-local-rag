# AI Agent Instructions

Action-first cheatsheet for automations.

### Golden Commands

- **Start services**: `make stack-up`
- **Stop services**: `make stack-down`
- **Run E2E tests**: `make e2e`
- **Quick dev setup**: `make dev-setup`
- **CLI Q&A**: `make cli` (pass `ARGS='--question "..."'`)

Ports: app `http://localhost:8501`, Weaviate `http://localhost:8080`, Ollama `http://localhost:11434`.

### Core Policies

- **No PYTHONPATH**: Use editable install and `-m` execution
- **Absolute imports**: `from backend.config import get_logger`
- **Module execution**: `.venv/bin/python -m backend.qa_loop`
- **Renovate validation**: `npx --package renovate renovate-config-validator renovate.json`
- **YAML formatting**: `make yamlfmt`

### Project Structure

- **Backend**: `qa_loop.py` (RAG loop), `weaviate_client.py` (DB), `ollama_client.py` (LLM)
- **Key Directories**: `backend/`, `frontend/`, `tests/`, `docker/`, `scripts/`
- **Data Ingestion**: Streamlit upload, `scripts/ingest.sh`, or compose `ingest` profile

### ML Strategy

Client-side vectorization and reranking with centralized model loading:
- Models configured in `backend/config.py` with environment overrides
- Uses `backend.models.load_embedder()` and `backend.models.load_reranker()`
- Offline-first with fallback to pinned downloads

## Testing (Quick)

- Unit: `make unit`
- Integration (local): `make integration`
- E2E: `make e2e`

Details (markers, health checks, TEST_DOCKER): see `docs/dev_test_CI/testing_approach.md`.

Markers
- `slow`: Long-running tests (>30s)
- `docker`: Requires Docker daemon
- `requires_weaviate`: Needs Weaviate service
- `requires_ollama`: Needs Ollama service
Note: the generic `external` marker was removed in favor of the specific service markers above.

## Development Environment

**Dependencies (uv)**:
- Dependency groups live in `pyproject.toml` under `[dependency-groups]` (e.g., `dev`, `test`).
- Quick install: `make uv-sync-test` (syncs test deps; uv manages env).
- Full dev/test install: `uv venv --seed && make uv-sync-test`.
- Use `.venv/bin/python -m <module>` for execution; editable install handled by uv.

**Quick Commands**:
- Setup dev env: `make dev-setup`
- Local gate: `make pre-commit`
- CLI Q&A: `make cli` or `make ask Q='...'`

## Docker Workflow

**Quick Commands**:
- Start/stop: `make stack-up` / `make stack-down` (non-destructive)
- Reset (destructive): `make stack-reset`
- Logs: `make app-logs LINES=200` (add `FOLLOW=1` to tail)

Advanced operations: see `docs/operate/docker-management.md`.

## Quick Reference

**Key Files**:
- `backend/qa_loop.py` - Main RAG loop
- `backend/weaviate_client.py` - Vector DB client
- `backend/ollama_client.py` - LLM client
- `backend/config.py` - Model configuration
- `backend/models.py` - Model loading utilities

## See Also
- Development Guide: `docs/dev_test_CI/DEVELOPMENT.md`
- Testing Approach: `docs/dev_test_CI/testing_approach.md`
- Docker Management: `docs/operate/docker-management.md`
- Make targets: `make help`
