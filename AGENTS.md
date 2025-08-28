# Repository Guidelines

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

## Coding Style & Naming
- Python 3.12; 4‑space indent; max line length 120; prefer double quotes.
- Lint/format: Ruff (`ruff`, `ruff format`) and type check with Pyright.
- Names: modules/functions/vars `snake_case`; classes `PascalCase`; constants `UPPER_SNAKE`.
- Hooks: `make setup-hooks` to enable pre‑commit (ruff, pyright, bandit, detect‑secrets, hadolint, actionlint, yamlfmt).

## Testing Guidelines
- Framework: Pytest with markers: `slow`, `docker`, `external`, `requires_weaviate`, `requires_ollama`, `integration`.
- File naming: `tests/**/test_*.py`; keep unit tests fast and isolated; integration/e2e may target running compose.
- Useful env for tests/dev: `RAG_SKIP_STARTUP_CHECKS=1`, `RAG_FAKE_ANSWER="..."`.
- Run subsets: `pytest tests/unit -q`, `pytest -m "integration and not slow"`.

## Commit & Pull Request Guidelines
- Commits: concise, imperative subject; group related changes; no secrets. Run pre‑commit before pushing.
- PRs: describe intent, key changes, and test coverage; link issues; include run instructions and UI screenshots if relevant.
- Requirements: CI must pass (lint, type, tests); update docs (`README.md`, `docs/**`) when behavior changes.

## Security & Configuration
- Copy `.env.example` → `.env`; set `WEAVIATE_URL`, `OLLAMA_URL`, optional `OLLAMA_IMAGE`.
- Do not commit secrets; baseline in `.secrets.baseline` is enforced by pre‑commit.
- First run downloads models; allow time or pre‑pull via setup script.

## Codex CLI Alignment
- Codex sessions follow `docs/CODEX_RULES.md`, which mirrors `.cursor/rules/*` for consistent behavior across tools.
