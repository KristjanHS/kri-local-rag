# Development Quickstart

Concise setup for human developers. For detailed, AI-automation-focused guidance, see `docs/AI_coder/AI_instructions.md`.

## Prerequisites
- Python 3.12+ recommended (matches project requirement)
- Docker (optional, for running full stack)

## Setup
This project uses a unified script to set up a complete development environment, including a Python virtualenv, all dependencies, and required system tools.

```bash
make dev-setup
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
make unit
```

- Integration (real services with simplified patterns):
```bash
# Docker environment (recommended)
export TEST_DOCKER=true
make test-up
make test-integration
make test-down

# Local environment
export TEST_DOCKER=false
make integration
```

For testing patterns, see `docs/dev_test_CI/testing_approach.md`.

- E2E (full stack via Docker Compose):
```bash
make e2e
```

- UI (Playwright/Streamlit; coverage disabled):
```bash
.venv/bin/python -m pytest tests/ui --no-cov -q
```

- Pre-push fast path (runs unit bundle by default; respects SKIP_TESTS=1):
```bash
make pre-push
```

## Model System

The project uses a centralized, offline-first model loading system:

### Configuration
- **Central location**: All model settings in `backend/config.py`
- **Environment overrides**: Use `EMBED_REPO`, `RERANK_REPO`, `EMBED_COMMIT`, `RERANK_COMMIT`
- **Default models**: `sentence-transformers/all-MiniLM-L6-v2` (embedding), `cross-encoder/ms-marco-MiniLM-L-6-v2` (reranking)

### Usage
```python
from backend.models import load_embedder, load_reranker

# Load models (with automatic caching)
embedder = load_embedder()
reranker = load_reranker()
```

### Development vs Production
- **Development**: Models download automatically with pinned commits
- **Production**: Models are pre-baked into Docker images for offline operation
- **Offline mode**: Set `TRANSFORMERS_OFFLINE=1` for production deployments

## Docker (optional)
Preferred startup: use the Make target which builds the image, starts services, and waits for health checks.
```bash
make stack-up
```
See the root README for starting/stopping the stack and simple day-to-day commands. For deeper service operations and troubleshooting, see `docs/operate/docker-management.md`.

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

- Local venv install (uv):
```bash
# CPU wheels are configured in pyproject via [tool.uv.index]/[tool.uv.sources]
uv venv --seed && make uv-sync-test
```

- Quick smoke test of image:
```bash
docker run --rm kri-local-rag:local python -c "import torch,google.protobuf as gp,grpc; print('torch', torch.__version__, 'cuda', torch.cuda.is_available()); print('protobuf', gp.__version__); print('grpcio', grpc.__version__)"
```

## Notes
- Avoid setting `PYTHONPATH`. Install dependencies via `make uv-sync-test` and use module execution with `-m`.
 - `kri_local_rag.egg-info/` provides package metadata that enables editable installs, dependency resolution, and discovery of modules/entry points by tooling.


## More docs
- Detailed guidance used mostly by AI coder: `docs/AI_coder/AI_instructions.md`
- Docker management and troubleshooting: `docs/operate/docker-management.md`
- **Testing strategy**: `docs/dev_test_CI/testing_approach.md` - Complete guide to testing patterns, integration tests, and model management


## Helper scripts

- `scripts/docker/docker-setup.sh`: one-time Docker environment bootstrap.
- `scripts/docker/docker-reset.sh`: full Docker cleanup (containers, images, volumes).
- `scripts/docker/build_app.sh`: build the `app` image; accepts `--no-cache`.
- `scripts/cli.sh`: convenience wrapper to run the CLI inside Docker.

**Note**: Scripts that need integration test utilities should import them from `tests/integration/conftest.py` rather than duplicating the logic. See `docs/dev_test_CI/testing_approach.md` for details.

## See Also
- Make targets: run `make help`
- AI Agent Instructions: `docs/AI_coder/AI_instructions.md`
- Docker Management: `docs/operate/docker-management.md`
