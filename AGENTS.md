# Repository Guidelines

## Standards & Rules
- **Run commands from the project root.**
- **Run Pytest as a module:** `.venv/bin/python -m pytest tests/unit -q` and  `.venv/bin/python -m pytest tests/integration -q`
- **Run pre-commit checks locally:** `cd /home/kristjans/projects/kri-local-rag && pre-commit run --all-files`
- **Use `.venv/bin/python` for Python execution** to ensure consistent virtual environment usage.
- See `docs/CODEX_RULES.md` for linting/formatting, typing, testing policy, imports/deps, Docker safety, logging, and after‑edits guidance.

## Project Structure & Modules
- `backend/`: ingestion (`ingest.py`), retrieval/QA (`qa_loop.py`), Weaviate/Ollama clients, config.
- `frontend/`: Streamlit UI (`rag_app.py`).
- `scripts/`: Docker and developer helpers (`docker/docker-setup.sh`, `ingest.sh`, `cli.sh`).
- `tests/`: `unit/`, `integration/`, `e2e/`, `ui/` with `conftest.py` fixtures.
- `docker/`: compose and Dockerfiles. Artifacts/coverage in `reports/`, sample data in `data/`, `example_data/`.

## Build, Test, and Dev Commands
- Start stack (recommended): `./scripts/docker/docker-setup.sh` — builds app and starts Weaviate, Ollama, Streamlit.
- Web UI: visit `http://localhost:8501` (dev run: `streamlit run frontend/rag_app.py`).
- Ingest docs: `./scripts/ingest.sh ./data` — runs ingestion in the app container.
- CLI Q&A: `./scripts/cli.sh` or `python -m backend.qa_loop --question "..."`.
- Test harness: `make test-up` → `make test-run-integration` → `make test-down`.
- Pytest locally: `pytest -q` (coverage outputs to `reports/coverage`).

## Commit & Pull Request Guidelines
- Commits: concise, imperative subject; group related changes; no secrets. Run pre‑commit before pushing.
- Requirements: CI must pass (lint, type, tests); update docs (`README.md`, `docs/**`) when behavior changes.

## Security & Configuration
- Do not commit secrets; baseline in `.secrets.baseline` is enforced by pre‑commit.