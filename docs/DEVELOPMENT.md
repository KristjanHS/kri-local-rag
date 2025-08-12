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

## Dependency resolution with uv (while keeping the app pip-only)

This project remains pip-only for application installs and CI. We use `tools/uv_sandbox/` as an isolated, reproducible sandbox to resolve tricky dependency sets and validate compatibility before updating `requirements*.txt`.

When to use the sandbox:
- Testing new pins or resolving conflicts (e.g., Protobuf 5.x + gRPC + torch + sentence-transformers).
- Verifying a coherent graph without changing the main venv.

Steps:
1) Run the sandbox resolver
```bash
cd tools/uv_sandbox
./run.sh
```
This will:
- Create a local venv (`tools/uv_sandbox/.venv`)
- Use CPU-only wheels via `PIP_EXTRA_INDEX_URL`/`UV_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu`
- Check lockfile state (`uv lock --check`), sync without mutation (`uv sync --frozen`)
- Validate with `uv pip check` and display `uv tree`

2) Inspect results
```bash
uv tree | less
```
Key targets we monitor: `protobuf` (5.x), `grpcio` (1.63.x), `torch` (2.7.x CPU), `sentence-transformers` (5.x), `weaviate-client`, `langchain`, `streamlit`.

3) Propagate pins to pip
- Copy the confirmed versions for direct dependencies into `requirements.txt` (runtime) and `requirements-dev.txt` (tooling). Keep transitive pins in `constraints.txt` if needed.
- Reinstall locally and re-check:
```bash
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pip check
.venv/bin/python -m pytest --test-core
```

4) CI and Docker
- Torch wheels index (CPU vs GPU):
  - Default (recommended for smaller images and faster builds): CPU wheels
    - Set `PIP_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu`
    - Or pass `--extra-index-url https://download.pytorch.org/whl/cpu` to pip
  - GPU (if you need CUDA-enabled Torch): choose the CUDA channel matching your system (example: CUDA 12.6)
    - Set `PIP_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cu121`
    - See the official PyTorch wheel indices list at [PyTorch wheels index](https://download.pytorch.org/whl/) and the install selector at [PyTorch Get Started](https://pytorch.org/get-started/locally/).
- Build the Docker image and verify runtime imports (CPU-only torch expected by default):
```bash
DOCKER_BUILDKIT=1 docker build -f docker/app.Dockerfile -t kri-local-rag:local .
docker run --rm kri-local-rag:local python -c 'import torch,google.protobuf,grpc; print(torch.__version__, torch.cuda.is_available())'
```

Guardrails:
- Do not add `uv` to application install paths or CI envs; it is a tooling-only sandbox.
- Avoid `--locked --frozen` together; use `uv lock --check` + `uv sync --frozen`.
- Keep `.venv` under `tools/uv_sandbox/` untracked; commit `pyproject.toml` and `uv.lock` when relevant.
- You can delete `tools/uv_sandbox/.venv/` anytime; `run.sh` will recreate it. Keep `pyproject.toml` and `uv.lock` for reproducibility (delete `uv.lock` only if you want a fresh resolve).

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
- Pre-push hook runs automatically: first `lint`, then `fast_tests`
- Manual CI: `./scripts/ci_act.sh`
- Cleanup: `./scripts/cleanup_docker_and_ci_cache.sh`
