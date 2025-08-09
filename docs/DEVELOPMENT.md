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

- Quick/quiet fast tests (recommended for local iteration):
```bash
.venv/bin/python -m pytest -q tests/
```

- Full verbose test output:
```bash
.venv/bin/python -m pytest -v
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

## CI: GitHub Actions and Act Cli for local CI

- Workflow file: `.github/workflows/python-lint-test.yml`
- Act runner images pinned in `.actrc`

Pre-push hook (runs automatically if installed):
```bash
act pull_request -j lint_and_fast_tests --pull=false --log-prefix-job-id
```

Manually simulate pull_reqest + run CI job locally
```bash
./scripts/ci_act.sh

```

Manual fast tests only:
```bash
act workflow_dispatch -j lint_and_fast_tests
```

Manual Pyright only:
```bash
act workflow_dispatch -j pyright
```

Troubleshooting flaky local CI:
```bash
./scripts/cleanup_docker_and_ci_cache.sh
# optional aggressive cleanup/restart
./scripts/cleanup_docker_and_ci_cache.sh --restart-docker --builder-prune
```
On WSL2, you may also need to restart Docker Desktop and/or run `wsl --shutdown`.
