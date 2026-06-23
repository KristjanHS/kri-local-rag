# Development, Testing & CI/CD

Reference for dev setup, the test suites, and the CI/release pipeline. Run commands from repo root; see `make help` for all targets.

## Setup

- Prerequisites: Python 3.12+, Docker (optional, for the full stack).
- Full dev environment (venv, deps, system tools): `make dev-setup`, then `source .venv/bin/activate`.
- Shared git hooks: `make setup-hooks` points git at `scripts/git-hooks/` (the `pre-commit` and `pre-push` hooks). Local `.git/hooks/` still take precedence.
- Import strategy (editable install, never `PYTHONPATH`): see `.claude/rules/python-imports-and-deps.md`. `kri_local_rag.egg-info/` carries the package metadata that drives editable installs and module discovery.

## Running tests

Suites map to folders (`tests/unit|integration|e2e|ui`; defined in `.claude/rules/testing.md`).

```bash
make unit                                    # fast, sockets blocked
make e2e                                     # full stack via Docker Compose
.venv/bin/python -m pytest tests/ui --no-cov -q   # Playwright/Streamlit
make pre-push                                # unit bundle; respects SKIP_TESTS=1
```

Integration tests need real services — see `## Integration tests` below.

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

## Test markers

- `slow` — long-running (>30s).
- `docker` — needs the Docker daemon.
- `requires_weaviate` / `requires_ollama` — needs that service up.

## Test utilities & service URLs

Integration helpers live in `tests/integration/conftest.py` — import, never reimplement (see `.claude/rules/testing.md`): `get_service_url`, `is_service_healthy`, `get_available_services`. `get_service_url` is defined in `backend/config.py`; endpoints/timeouts come from `pyproject.toml` `[tool.integration]`.

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

Offline-first loading, all settings in `backend/config.py`:

- Env overrides: `EMBED_REPO`, `RERANK_REPO`, `EMBED_COMMIT`, `RERANK_COMMIT`.
- Defaults: `all-MiniLM-L6-v2` (embed), `ms-marco-MiniLM-L-6-v2` (rerank).
- Dev downloads models at pinned commits; prod bakes them into the image and sets `TRANSFORMERS_OFFLINE=1`.
- API: `load_embedder()` / `load_reranker()` from `backend.models` (cached).

## Docker & wheels

Start the stack with `make stack-up` (builds, starts, waits for health). Service operations and reset: `docs/operate/docker-management.md`.

**Torch variant (GPU default / CPU extra).** torch + torchvision are base deps
that resolve from PyPI by default → GPU-capable CUDA wheels on Linux. A single
`cpu` extra re-pins both to the pytorch-cpu index for slim CPU-only installs (see
`pyproject.toml` `[tool.uv]` and
`docs/plans/archive/2026-06-23-cpu-gpu-variant-simplification-design.md`). The
otherwise-redundant `gpu` extra exists only to satisfy uv's ≥2-members-per-conflict
rule — it is source-less, so it resolves from PyPI just like the no-extra default.

```bash
make sync                            # local/bare-metal dev → PyPI/CUDA torch (default)
make sync SYNC_EXTRA="--extra cpu"   # CPU-only box → slim +cpu wheels
./run_uv.sh --extra cpu              # equivalent direct invocation
```

CI passes `SYNC_EXTRA="--extra cpu"` (CPU-only runners). A bare `uv sync` with no
extra is now the *intended* GPU path, not a footgun. To switch an existing checkout
between variants, recreate the venv clean (`rm -rf .venv` then re-sync) — swapping
CUDA wheel families in place can corrupt the shared PEP-420 `nvidia/` namespace dir.

The **Docker app image stays CPU** (slim runtime; only Ollama uses the GPU). Its
`uv sync` lines hardcode `--extra cpu`, so no build arg is needed:

```bash
DOCKER_BUILDKIT=1 docker build -f docker/app.Dockerfile -t kri-local-rag:local .
```

## Helper scripts

- `scripts/docker/docker-setup.sh` — one-time Docker bootstrap.
- `scripts/docker/docker-reset.sh` — full cleanup (containers, images, volumes).
- `scripts/docker/build_app.sh` — build the `app` image (`--no-cache` accepted).
- `scripts/cli.sh` — run the CLI inside Docker.

## CI workflows

GitHub Actions; canonical local gate is `make pre-commit` before pushing.

- `python-lint-test.yml` — lint -> fast_tests, plus pyright and docker_smoke_tests. PR to main/dev. 5–15 min.
- `codeql.yml` — static security analysis. Push/PR to main, weekly. Up to 6h.
- `semgrep.yml` — pattern security scan. Push/PR to main. Up to 30 min.

Security workflows run only on GitHub, not under Act.

## Pre-push sequence (Act)

`git push` runs this gate locally via Act, in order — all blocking except CodeQL:

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

`make setup-hooks` installs it; hooks fire on `git commit`. Run all with `make pre-commit`, or one via `pre-commit run ruff`. Tools: Ruff, YAMLfmt, Actionlint, Hadolint, Bandit, Pyright, Detect-secrets. Config: `.pre-commit-config.yaml`, `.secrets.baseline`.

```bash
pre-commit autoupdate                # refresh hook versions
make ruff-fix                         # autofix lint
# yamlfmt needs Go: go install github.com/google/yamlfmt/cmd/yamlfmt@latest (or drop it from config)
```

## Release process

`./scripts/ci/promote_dev_to_main.sh` promotes `dev` -> `main` (flags: `--dry-run`, `--prefer-dev-all`). It checks a clean tree, runs ruff + fast pytest on `dev`, fast-forwards/merges `main`, re-checks, pushes `origin/main`, returns to `dev`. Needs a local venv and push rights.

Failures: merge conflicts -> resolve or `--prefer-dev-all`; CI failures -> `logs/pre-push.log` then the cleanup script; branch protection "PRs only" -> open the PR manually.
