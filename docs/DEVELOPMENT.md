# Development Quickstart

Concise setup for human developers. For detailed, AI-automation-focused guidance, see `docs_AI_coder/AI_instructions.md`.

## Prerequisites
- Python 3.12+ recommended (matches project requirement)
- Docker (optional, for running full stack)

## Setup Dev Env
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt
pip install -e .
# Install Semgrep in a separate, tool-managed environment (isolated from .venv)
# pipx is recommended for best performance and isolation
python -m pip install --user pipx || true
python -m pipx ensurepath || true
pipx install --force semgrep
```

## Run the app (CLI / Web UI)
For basic usage and quick-start commands, see the root README. This document focuses on development workflows and advanced topics.

## Run tests (directory-based bundles)

- Unit (fast, sockets blocked):
```bash
.venv/bin/python -m pytest tests/unit -n auto -q
```

- Integration (one real component; network allowed):
```bash
.venv/bin/python -m pytest tests/integration -q
```

Integration policy:
- Prefer a single real dependency or Testcontainers per test. If multiple real services are required, move the test to `tests/e2e/`.
- Network is allowed. Do not auto-start Docker Compose in this suite; tests that truly need the full stack belong in E2E.
- Keep tests deterministic: avoid importing heavy target modules in fixtures; if needed, reset module caches via `sys.modules`.

- E2E (full stack via Docker Compose):
```bash
docker compose -f docker/docker-compose.yml up -d --build
.venv/bin/python -m pytest tests/e2e -q
docker compose -f docker/docker-compose.yml down -v
```

- UI (Playwright/Streamlit; coverage disabled):
```bash
.venv/bin/python -m pytest tests/ui --no-cov -q
```

- Pre-push fast path (runs unit bundle by default; respects SKIP_TESTS=1):
```bash
scripts/pre_push.sh
```


## Docker (optional)
Preferred startup: use the automated setup script which builds the image, starts services, and waits for health checks.
```bash
./scripts/docker-setup.sh
```
See the root README for starting/stopping the stack and simple day-to-day commands. For deeper service operations and troubleshooting, see `docs/docker-management.md`.

## Wheels (CPU/GPU) — concise
- Docker build (choose one channel):
```bash
export TORCH_WHEEL_INDEX=https://download.pytorch.org/whl/cpu      # default
# export TORCH_WHEEL_INDEX=https://download.pytorch.org/whl/cu121   # CUDA 12.1
# export TORCH_WHEEL_INDEX=https://download.pytorch.org/whl/rocm6.1 # ROCm 6.1

DOCKER_BUILDKIT=1 docker build \
  --build-arg TORCH_WHEEL_INDEX=$TORCH_WHEEL_INDEX \
  -f docker/app.Dockerfile -t kri-local-rag:local .
```

- Local venv install (choose one channel):
```bash
export PIP_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu      # default
# export PIP_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cu121   # CUDA 12.1
# export PIP_EXTRA_INDEX_URL=https://download.pytorch.org/whl/rocm6.1 # ROCm 6.1

.venv/bin/python -m pip install -r requirements.txt
```

- Quick smoke test of image:
```bash
docker run --rm kri-local-rag:local python -c "import torch,google.protobuf as gp,grpc; print('torch', torch.__version__, 'cuda', torch.cuda.is_available()); print('protobuf', gp.__version__); print('grpcio', grpc.__version__)"
```

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


## Ingest documents

Run all checks locally without pushing:
```bash
./scripts/promote_dev_to_main.sh --dry-run
```

Promote (push), or create PR if main is protected:
```bash
./scripts/promote_dev_to_main.sh
./scripts/promote_dev_to_main.sh --create-pr
```

Optional allow-list file for auto conflict resolution (`.promotion-rules.conf`):
```text
# Lines are path prefixes or file names that can be auto-resolved by
# preferring the source branch during conflict resolution
README.md
docs/
docs_AI_coder/
```

## CI: GitHub Actions and Act CLI for local CI

For comprehensive information about GitHub Actions, Act CLI, and local CI testing, see [GitHub Workflows Documentation](github-workflows.md).

**Quick reference:**
- Workflow file: `.github/workflows/python-lint-test.yml`
- Act runner images pinned in `.actrc`
- Pre-push hook (optional): link to `scripts/pre_push.sh` to run pyright, lint, and fast tests locally before pushing
  ```bash
  ln -sf ../../scripts/pre_push.sh .git/hooks/pre-push
  ```
- Skip local security scans in pre-push when needed:
  ```bash
  SKIP_LOCAL_SEC_SCANS=1 git push
  ```
- Local Semgrep (isolated from .venv):
  ```bash
  # Using pipx-managed Semgrep
  pipx run semgrep ci --config auto --metrics off --sarif --output semgrep_local.sarif
  ```
- Manual CI: `./scripts/ci_act.sh`
- Cleanup: `./scripts/cleanup_docker_and_ci_cache.sh`
 
## Branch protection (main)

- Required status checks to merge into `main`:
  - Code scanning results / CodeQL
  - Semgrep / Sec Scan
- Direct pushes to `main` are blocked unless these checks pass on the PR.
- View current protection settings:
```bash
gh api -H "Accept: application/vnd.github+json" repos/KristjanHS/kri-local-rag/branches/main/protection | jq .
```