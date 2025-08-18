# Development Quickstart

Concise setup for human developers. For detailed, AI-automation-focused guidance, see `docs_AI_coder/AI_instructions.md`.

## Prerequisites
- Python 3.12+ recommended (matches project requirement)
- Docker (optional, for running full stack)

## Setup
This project uses a unified script to set up a complete development environment, including a Python virtualenv, all dependencies, and required system tools.

```bash
bash scripts/setup-dev-env.sh
```

After setup, activate the virtual environment to use the installed tools:
```bash
source .venv/bin/activate
```

## Git Hooks Setup
To ensure code quality and consistency, this project uses shared Git hooks. After cloning, configure your local repository to use them:
```bash
make setup-hooks
```
This command points Git to the `scripts/git-hooks/` directory where the shared `pre-commit` and `pre-push` hooks are located.

You can still use local, untracked hooks in `.git/hooks/` for your own workflows. Git will look for hooks there first before falling back to the shared hooks directory.

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
scripts/git-hooks/pre-push
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
- `