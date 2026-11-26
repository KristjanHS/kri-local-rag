# Development, Testing & CI/CD

Reference for dev setup, the test suites, and the CI/release pipeline. Run commands from repo root; see `make help` for all targets.

## Setup

- Prerequisites: Python 3.14, Docker (optional, for the full stack).
- Full dev environment (venv, deps, system tools): `make dev-setup`, then `source .venv/bin/activate`.
- Host Python against the Docker services: `make uv-sync-test` syncs the test group into `.venv`. On the host, `OLLAMA_URL` and `WEAVIATE_URL` default to `http://localhost:11434` and `http://localhost:8080`. Compose sets the container hostnames.
- Shared git hooks: `make setup-hooks` sets `core.hooksPath` to `scripts/git-hooks/`, so git runs that folder's `pre-commit` and `pre-push` hooks and ignores `.git/hooks/`.
- Import strategy (editable install, never `PYTHONPATH`): see `.claude/rules/python-imports-and-deps.md`. `kri_local_rag.egg-info/` carries the package metadata that drives editable installs and module discovery.

## Running tests

Suites map to folders (`tests/unit|integration|e2e|ui`; defined in `.claude/rules/testing.md`).

```bash
make unit                                    # fast, sockets blocked
make e2e                                     # host pytest vs localhost services (see ## E2E tests)
.venv/bin/python -m pytest tests/ui --no-cov -q   # Playwright/Streamlit
make pre-push                                # the pre-push hook with every step on
```

Integration tests need real services. E2E tests run the full stack in two modes.

## Test notifications

Color/bell/log wrappers around the suites:

```bash
make push-pr                                          # push -> test -> PR
./scripts/dev/test-notification.sh [integration|unit|e2e|all]
PYTEST_ARGS="-x --tb=short" ./scripts/dev/test-notification.sh integration
```

VS Code: Ctrl+Shift+P -> "Tasks: Run Task" -> "Run Tests with Notifications". Logs to `logs/test-notification.log`.

## Integration tests

Real local models with mocked external services. Two ways to run:

```bash
# Docker (recommended)
export TEST_DOCKER=true
make test-up && make test-integration && make test-down

# Local
export TEST_DOCKER=false
make integration PYTEST_ARGS='-v'
```

Service-specific runs via markers:

```bash
make integration PYTEST_ARGS='-m "requires_weaviate"'
make integration PYTEST_ARGS='-m "requires_ollama"'
make integration PYTEST_ARGS='-m "requires_weaviate and requires_ollama"'
```

## E2E tests

End-to-end tests exercise the real stack (Weaviate + Ollama + the packaged app
image) and run in **two modes**. Both resolve service URLs through
`get_service_url`, so the same test code works either way. Never hardcode a URL
in a test.

```bash
# Mode 1, host: pytest runs on the host against localhost services.
make e2e                 # targets whichever stack is up (live OR test); auto-
                         # starts the live stack if none. PRESERVE=0 to stack-down after.

# Mode 2, in-container: pytest runs inside the app-test container (hermetic, CI-faithful).
make test-up && make test-e2e && make test-down
```

Because the test stack reuses the live host ports (`8080/50051/11434/8501`), the
two stacks can't run at once. `make e2e` hits `http://localhost:8080`, while
`make test-e2e` hits the compose hostname `http://weaviate:8080` from inside the
container. `make e2e`
needs the `kri-local-rag-app:latest` image or it skips; `make test-e2e` needs a
running test stack (`make test-up`).

## Test markers

- `slow`: long-running (>30s).
- `docker`: needs the Docker daemon.
- `requires_weaviate` / `requires_ollama`: needs that service up.

## Test utilities & service URLs

Integration helpers live in `tests/integration/conftest.py`; import them, never reimplement (see `.claude/rules/testing.md`): `get_service_url`, `is_service_healthy`, `get_available_services`. `get_service_url` is defined in `backend/config.py`; endpoints/timeouts come from `pyproject.toml` `[tool.integration]`.

Service URLs default to localhost and are overridden by env var; Docker Compose sets the container-network values:

| Var | Local default | In Compose | Health endpoint |
|---|---|---|---|
| `OLLAMA_URL` | `http://localhost:11434` | `http://ollama:11434` | `/api/version` |
| `WEAVIATE_URL` | `http://localhost:8080` | `http://weaviate:8080` | `/v1/.well-known/ready` |

## Test strategy & troubleshooting

Use real local models for ML components (SentenceTransformer, CrossEncoder); mock external services, DB, file I/O, and network. The offline smoke test loads the baked `EMBED_MODEL_PATH`/`RERANK_MODEL_PATH` inside the Docker image and skips locally.

```bash
echo "OLLAMA_URL=$OLLAMA_URL WEAVIATE_URL=$WEAVIATE_URL"   # confirm env
curl -i $WEAVIATE_URL/v1/.well-known/ready                 # Weaviate up?
curl -i $OLLAMA_URL/api/version                            # Ollama up?
```

Connection refused usually means a URL mismatch (localhost vs container name) or a service still starting.

## Model system

Model settings live in `backend/config.py`:

- Env overrides: `EMBEDDING_MODEL`, `RERANK_MODEL`, `OLLAMA_MODEL`.
- Defaults: `all-MiniLM-L6-v2` (embed), `ms-marco-MiniLM-L-6-v2` (rerank).
- HuggingFace caches under `HF_HOME`; prod bakes the models into the image so loading needs no network.
- API: `load_embedder()` / `load_reranker()` from `backend.models` (cached).

## Docker & wheels

Start the stack with `make stack-up` (builds, starts, waits for health). Service operations and reset: `docs/operate/docker-management.md`.

**Torch variant (GPU default / CPU extra).** torch + torchvision are base deps
that resolve from PyPI by default → GPU-capable CUDA wheels on Linux. A single
`cpu` extra re-pins both to the pytorch-cpu index for slim CPU-only installs (see
`pyproject.toml` `[tool.uv]` and
`docs/plans/archive/2026-06-23-cpu-gpu-variant-simplification-design.md`). The
otherwise-redundant `gpu` extra exists only to satisfy uv's ≥2-members-per-conflict
rule. It is source-less, so it resolves from PyPI just like the no-extra default.

```bash
make sync                            # local/bare-metal dev → PyPI/CUDA torch (default)
make sync SYNC_EXTRA="--extra cpu"   # CPU-only box → slim +cpu wheels
./run_uv.sh --extra cpu              # equivalent direct invocation
```

CI passes `SYNC_EXTRA="--extra cpu"` (CPU-only runners). A bare `uv sync` with no
extra is now the *intended* GPU path, not a footgun. To switch an existing checkout
between variants, recreate the venv clean (`rm -rf .venv` then re-sync). Swapping
CUDA wheel families in place can corrupt the shared PEP-420 `nvidia/` namespace dir.

The **Docker app image stays CPU** (slim runtime; only Ollama uses the GPU). Its
`uv sync` lines hardcode `--extra cpu`, so no build arg is needed:

```bash
DOCKER_BUILDKIT=1 docker build -f docker/app.Dockerfile -t kri-local-rag:local .
```

## Helper scripts

- `scripts/docker/docker-setup.sh`: one-time Docker bootstrap.
- `scripts/docker/docker-reset.sh`: full cleanup (containers, images, volumes).
- `scripts/docker/build_app.sh`: build the `app` image (`--no-cache` accepted).
- `scripts/cli.sh`: run the CLI with the host `.venv` (behind `make cli` and `make ask`). `make cli-docker` runs it inside the app container instead.

## CI workflows

GitHub Actions; canonical local gate is `make pre-commit` before pushing.

- `python-lint-test.yml`: Lint, Deptry, Unit Tests, Pyright. PR to main/dev, push to main, weekly, manual. Integration, E2E and UI jobs run only under Act.
- `codeql.yml`: static security analysis. Every PR, weekly, manual. Up to 6h.
- `semgrep.yml`: pattern security scan. Every PR, manual. Up to 30 min.
- `security_scans.yml`: uv audit and Trivy filesystem scan. PRs touching `uv.lock`, `pyproject.toml` or Docker files, weekly, manual.
- `meta-linters.yml`: Actionlint, Yamlfmt, Hadolint. PRs touching YAML or Docker files, manual.
- `enable-automerge.yml`: turns on auto-merge. PRs to main opened or marked ready.
- `auto-pr.yml`: opens a pull request. Manual.
- `codeql_local.yml`: CodeQL in an isolated env for Act. Manual.

CodeQL and Semgrep have separate local jobs for Act; their GitHub jobs skip under Act.

## Pre-push sequence (Act)

`git push` runs this gate locally via Act, in order. All steps block except CodeQL:

1. Pyright (types) 2. Lint (`ruff check` + `ruff format --check`) 3. Fast tests 4. Semgrep 5. CodeQL (informational locally).

## Act CLI

`.actrc` pins optimized images and auto-removes containers/volumes per run.

```bash
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash
act -l                                                   # list
act workflow_dispatch -W .github/workflows/python-lint-test.yml
act workflow_dispatch -j lint                            # single job
./scripts/docker/cleanup_docker_and_ci_cache.sh [--restart-docker --builder-prune]
```

## Pre-commit framework

After `make setup-hooks`, the `scripts/git-hooks/pre-commit` hook runs the framework on the staged files at every `git commit`. Skip `pre-commit install`: it refuses to run while `core.hooksPath` is set. Run all hooks on all files with `make pre-commit`, or one via `pre-commit run ruff`. Tools: Ruff, YAMLfmt, Actionlint, Hadolint, Bandit, Pyright, Detect-secrets. Config: `.pre-commit-config.yaml`, `.secrets.baseline`.

```bash
pre-commit autoupdate                # refresh hook versions
make ruff-fix                         # autofix lint
# yamlfmt needs Go: go install github.com/google/yamlfmt/cmd/yamlfmt@latest (or drop it from config)
```

## Release process

`./scripts/ci/promote_dev_to_main.sh` promotes `dev` -> `main` (flags: `--dry-run`, `--prefer-dev-all`). It checks a clean tree, runs ruff + fast pytest on `dev`, fast-forwards/merges `main`, re-checks, pushes `origin/main`, returns to `dev`. Needs a local venv and push rights.

Failures: merge conflicts -> resolve or `--prefer-dev-all`; CI failures -> `logs/pre-push.log` then the cleanup script; branch protection "PRs only" -> open the PR manually.
