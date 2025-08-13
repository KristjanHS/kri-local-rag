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
