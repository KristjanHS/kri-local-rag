# Development Quickstart

Concise setup for human developers. For detailed, AI-automation-focused guidance, see `docs_AI_coder/AI_instructions.md`.

## Prerequisites
- Python 3.11+ recommended
- Docker (optional, for running full stack)

## Setup Dev Env
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt
pip install -e .
```

## Run the app (CLI QA loop)
```bash
.venv/bin/python -m backend.qa_loop
```

## Run tests

- **Core test suite** (fast, with coverage):
```bash
.venv/bin/python -m pytest --test-core
```

- **UI test suite** (Playwright/Streamlit, no coverage):
```bash
.venv/bin/python -m pytest --test-ui --no-cov
```

## Docker (optional)
```bash
docker compose -f docker/docker-compose.yml up -d --build
```
Then open `http://localhost:8501`.
For logs, rebuilds, service ops, and troubleshooting, see `docs/docker-management.md`.

## Notes
- Avoid setting `PYTHONPATH`. Use editable installs (`pip install -e .`) and module execution with `-m`.
 - `kri_local_rag.egg-info/` provides package metadata that enables editable installs, dependency resolution, and discovery of modules/entry points by tooling.

## More docs
- Detailed guidance used mostly by AI coder: `docs_AI_coder/AI_instructions.md`
 - Docker management and troubleshooting: `docs/docker-management.md`

## Helper scripts

- `scripts/docker-setup.sh`: one-time Docker environment bootstrap.
- `scripts/docker-reset.sh`: full Docker cleanup (containers, images, volumes).
- `scripts/build_app.sh`: build the `app` image; accepts `--no-cache`.
- `scripts/cli.sh`: convenience wrapper to run the CLI inside Docker.
- `scripts/ingest.sh`: ingest local documents into the system.
- `scripts/config.sh`: shared config sourced by the other scripts.

 - ## Ingest documents

- Streamlit UI: open `http://localhost:8501` and upload PDFs (ensure services are running; see `docs/docker-management.md`):
  ```bash
  docker compose -f docker/docker-compose.yml up -d --build
  ```
- Helper script (one-liner ingestion):
  ```bash
  ./scripts/ingest.sh <path-to-pdfs>
  ```
- Compose profile (batch ingestion):
  ```bash
  docker compose -f docker/docker-compose.yml --profile ingest up
  ```

## CI: GitHub Actions and Act CLI for local CI

For comprehensive information about GitHub Actions, Act CLI, and local CI testing, see [GitHub Workflows Documentation](github-workflows.md).

**Quick reference:**
- Workflow file: `.github/workflows/python-lint-test.yml`
- Act runner images pinned in `.actrc`
- Pre-push hook runs automatically: first `lint`, then `fast_tests`
- Manual CI: `./scripts/ci_act.sh`
- Cleanup: `./scripts/cleanup_docker_and_ci_cache.sh`
