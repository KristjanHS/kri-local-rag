# Project TODO List

This file tracks outstanding tasks and planned improvements for the project.

## Context

- **App**: Local RAG using Weaviate (8080), Ollama (11434), Streamlit UI (8501)
- **Security**: Only Streamlit should be user-visible. Other services should be local-only (loopback or compose-internal)
- **Python execution**: Avoid `PYTHONPATH`; run modules with `python -m` from project root to ensure imports work
- **Environment**: Prefer the project venv (`.venv/bin/python`) or an equivalent Python environment
- **Vectorization**: Uses a local `SentenceTransformer` model for client-side embeddings. Weaviate is configured for manually provided vectors.
- **Reranking**: A separate, local `CrossEncoder` model is used to re-score initial search results for relevance.

## Conventions

- **Commands are examples**: Any equivalent approach that achieves the same outcome is acceptable
- **Paths, ports, and model names**: Adapt to your environment as needed
- **Host vs container URLs**:
  - From host: use `http://localhost:8080` (Weaviate) and `http://localhost:11434` (Ollama)
  - From containers: use `http://weaviate:8080` and `http://ollama:11434`
- Each step has Action and Verify. Aim for one change per step to allow quick fix-and-retry.
- On any Verify failure: stop and create a focused debugging plan before proceeding (assume even these TODO instructions may be stale or mistaken). The plan should:
   - Summarize expected vs. actual behavior and include the exact command/output/exit code.
   - Gather quick signals (only the minimum needed): relevant service logs, port bindings, container status, environment variables, and config diffs.
   - Re-check key assumptions (host vs container URLs, credentials, network bindings, versions, availability of external services).
   - Consider that the step description might be wrong; cross-check code, `DEVELOPMENT.md`, and `docker/` for the source of truth.
   - Propose 1–3 small, reversible next actions with a clear Verify for each. Apply the smallest change first.
   - After a change, re-run the same Verify command from the failed step. Only then continue.
   - If blocked, mark the step as `[BLOCKED: <short reason/date>]` in this todo file and proceed to the smallest independent next step if any; otherwise stop and request help.


## Quick References

- **AI agent cheatsheet and E2E commands**: [`docs_AI_coder/AI_instructions.md`](AI_instructions.md) (sections: "Golden commands" and "AI Agent Hints: Docker startup and E2E tests")
- **Test suites and markers**: [`docs_AI_coder/AI_instructions.md`](AI_instructions.md) (section: "Testing")
- **Human dev quickstart**: [`docs/DEVELOPMENT.md`](../docs/DEVELOPMENT.md)
- **MVP runbook**: [`docs_AI_coder/mvp_deployment.md`](mvp_deployment.md)
- **Archived tasks**: [`docs_AI_coder/archived-tasks.md`](archived-tasks.md)

 

## Prioritized Backlog

Reference: See [TEST_REFACTORING_SUMMARY.md](TEST_REFACTORING_SUMMARY.md) for context on completed Phase 1 testing work.

#### P0.1 Immediate — Local dev checks (pre-push)

- [x] Re-enable local security scans in pre-push
  - Action: Run push with `SKIP_LOCAL_SEC_SCANS=0` to include Semgrep/CodeQL locally: `SKIP_LOCAL_SEC_SCANS=0 git push -n` (dry run) or actual push.
  - Verify: Pre-push log shows Semgrep/CodeQL steps executed without schema errors and exits 0.

- [ ] Install pyright in `.venv` so type checks run in pre-push
  - Action: `.venv/bin/pip install pyright` (optionally pin to CI version) and commit if adding to `requirements-dev.txt`.
  - Verify: `.venv/bin/pyright --version` succeeds and pre-push no longer warns about missing pyright.

#### P0.2 — Test suite bundling into four bundles (unit, integration, e2e, ui) — simplified

- Context and goal
  - Current situation: tests are split across `tests/unit`, `tests/integration`, `tests/e2e`, `tests/e2e_streamlit`, plus `tests/environment` and `tests/docker`. There are custom pytest flags/hooks and some global marker-based exclusions (e.g., `-m "not ui"`). Unit socket blocking exists but enforcement paths are a bit complex.
  - Goal: simplify to directory-as-bundle as the single source of truth; remove custom flags and most hooks; rename `e2e_streamlit` → `ui`; migrate `environment` and `docker` tests into `integration` or `e2e`; run UI explicitly without coverage; select suites by path in dev and CI; keep only cross-cutting markers (`slow`, `docker` if needed, `external`).

- [x] Step 1 — Use directory-as-bundle; keep tagging minimal
  - Action: Treat each folder under `tests/` as the bundle source of truth; select suites by directory paths only:
    - `tests/unit/` (sockets blocked; fully mocked)
    - `tests/integration/` (one real component; network allowed)
    - `tests/e2e/` (full stack via Docker Compose)
    - `tests/ui/` (UI; Playwright/Streamlit; coverage disabled; run only when targeted)
    - Keep only cross-cutting markers like `slow`, `docker`, or `external` when needed.
  - Verify: `.venv/bin/python -m pytest --co -q tests/unit tests/integration tests/e2e tests/ui` lists items by directory; no reliance on `-m`.

- [x] Step 1.0 — Remove custom suite flags and collection hooks; keep one simple unit guard
  - Action: Delete custom options `--test-fast`, `--test-core`, `--test-ui` and related `pytest_collection_modifyitems` logic from `tests/conftest.py`.
  - Action: Keep a minimal autouse fixture in `tests/unit/conftest.py` that calls `pytest_socket.disable_socket(allow_unix_socket=True)`; remove redundant double-guards and diagnostics unless actively needed.
  - Verify: Unit runs block sockets; selecting by directory runs the expected tests without any custom flags or mark expressions.

- [x] Step 1.1 — Unit bundle (fast, fully mocked, sockets blocked)
  - Action: Standardize command alias: `.venv/bin/python -m pytest tests/unit -n auto -q`. Keep `UNIT_ONLY_TESTS=1` behavior and socket guards from `tests/unit/conftest.py`.
  - Verify: Command runs only `tests/unit/*`, exits green, and any real socket attempt fails fast with `SocketBlockedError`.

- [x] Step 1.2 — Audit and migrate tests to correct bundles
  - Action: Move any heavy or external-service-touching tests out of `tests/unit/` into `tests/integration/` (or `e2e` if they require the full stack). Remove redundant `unit/integration/e2e/ui` markers where the directory already defines the type; keep only cross-cutting tags like `slow`, `docker`, `external`.
  - Verify: `.venv/bin/python -m pytest tests/unit -q` remains green and fast; directory-scoped runs cover the moved tests.

- [x] Step 1.2.1 — Pre-push and docs
  - Action: Update pre-push hook to run only unit bundle by default: `.venv/bin/python -m pytest tests/unit --maxfail=1 -q` (respect `SKIP_TESTS=1`).
  - Action: Update `docs/DEVELOPMENT.md` with bundle definitions, directory-based commands, and expectations (mocking policy, network rules, and when to promote a test to a heavier bundle).
  - Verify: Fresh clone dev can follow docs to run each bundle successfully; pre-push remains quick.

- [x] Step 1.3 — Deprecate `tests/environment/` by migrating tests
  - Action: Audit each test in `tests/environment/` and move to:
    - `tests/integration/` if it validates local/python/ML setup without full compose or cross-service orchestration.
    - `tests/e2e/` if it depends on the full Docker stack or multiple real services.
  - Action: Remove redundant `environment` markers once migrated; keep only cross-cutting tags if needed.
  - Action: Delete `tests/environment/` after migration.
  - Verify: Directory-scoped runs for integration and e2e remain green; CI no longer references `environment`.

- [x] Step 1.4 — Deprecate `tests/docker/` by migrating tests
  - Action: Audit each test in `tests/docker/` and move to:
    - `tests/integration/` if it validates packaging/imports, app image build, or a single service without orchestrating the full stack during the test run.
    - `tests/e2e/` if it requires bringing up the full Compose stack or exercises cross-service interactions as part of the test.
  - Action: Remove redundant `docker` markers once migrated; keep only cross-cutting tags like `slow` when applicable.
  - Action: Delete `tests/docker/` after migration.
  - Verify: Directory-scoped integration and e2e runs are green; CI no longer references the `tests/docker/` directory (optional `-m docker` marker usage remains only if still needed).

- [x] Step 1.5 — Rename UI directory and update configs
  - Action: Rename `tests/e2e_streamlit/` → `tests/ui/`.
  - Action: Update references in configs and docs:
    - `pyproject.toml` → `[tool.pytest.ini_options].testpaths` updated to include `tests/ui`.
    - `pyproject.toml` → `[tool.coverage.run].omit` updated to `tests/ui/*`.
    - `tests/ui/conftest.py` contains a guard: raise a `pytest.UsageError` if coverage is enabled (UI requires `--no-cov`).
    - `tests/conftest.py` path filters updated to `tests/ui/`.
    - CI workflow jobs and any scripts to point to `tests/ui`.
    - Docs (`DEVELOPMENT.md`, README, any references) to use `tests/ui` nomenclature.
  - Verify: `.venv/bin/python -m pytest tests/ui --no-cov -q` collects and runs the UI tests; coverage omit still skips UI as expected.

- [x] Step 1.6 — Normalize project config to new folder layout
  - Action: In `pyproject.toml` `[tool.pytest.ini_options].testpaths`, remove `tests/ui` so default runs exclude UI entirely; developers and CI must target `tests/ui` explicitly.
  - Action: Replace any `tests/e2e_streamlit` references with `tests/ui`; remove `tests/environment` and `tests/docker` after migration.
  - Action: In `pyproject.toml` `[tool.pytest.ini_options].markers`, trim to cross-cutting only: keep `slow`, `docker` (if still used post-migration), and `external`; remove `unit`, `integration`, `e2e`, `ui`, and `environment` to avoid marker drift.
  - Action: Update docs (`DEVELOPMENT.md`) to state that directories determine bundles; markers are for cross-cutting semantics only.
  - Verify: `pytest --markers | cat` shows only the minimal cross-cutting markers; `pytest --co -q` lists items from the expected directories.

- [x] Step 1.7 — Remove unused pytest-docker config and prefer explicit Compose in scripts
  - Action: If not using `pytest-docker` plugin features directly, delete `[tool.pytest.docker]*` sections from `pyproject.toml` to reduce confusion.
  - Action: Prefer e2e orchestration via `scripts/test.sh e2e` that wraps `docker compose up -d --build && pytest tests/e2e -q && docker compose down -v`.
  - Verify: No plugin warnings on run; e2e orchestration flows through the script.

- [x] Step 3 — Integration bundle (one real component; network allowed)
  - Action: Standardize command: `.venv/bin/python -m pytest tests/integration -q`.
  - Action: Document policy: prefer Testcontainers or a single real dependency; for multi-service needs, move test to `e2e`.
  - Verify: Typical tests (e.g., `tests/integration/test_weaviate_integration.py`) pass without requiring the full compose stack; logs show no socket-block enforcement.

  - [x] Fix: Reset cached globals to avoid cross-test state (best practices)
    - Action: Add autouse fixture in `tests/integration/conftest.py` that clears `RAG_FAKE_ANSWER` and resets caches only if respective modules are already imported: `backend.qa_loop._cross_encoder`, `backend.qa_loop._ollama_context`, and `backend.retriever._embedding_model` via `sys.modules`.
    - Rationale: Aligns with `docs_AI_coder/AI_instructions.md` guidance to prevent flaky tests caused by cached globals and to not import modules inside fixtures (keeps patch decorators effective).
    - Verify: `.venv/bin/python -m pytest tests/integration -q` shows deterministic results; streaming test passes in isolation and alongside others.
    - Validation: All integration tests pass (28/28); flaky-tests guidance updated and condensed in `docs_AI_coder/AI_instructions.md`.

- [ ] Step 4 — E2E bundle (all real components; network allowed)
  - Action: Provide a single dispatcher script `scripts/test.sh` with usage: `test.sh [unit|integration|e2e|ui]` that runs the standardized directory-based commands; for e2e it does `docker compose up -d --build && pytest tests/e2e -q && docker compose down -v` with `set -euo pipefail`.
  - Verify: `bash scripts/test.sh unit|integration|e2e|ui` runs the intended bundle with minimal flags.
  
  ##### Hotfix Log — 2025-08-14
- [x] Ensure real QA e2e test uses ingestion fixture
  - **Action**: Explicitly import `docker_services_ready` from `tests/e2e/fixtures_ingestion.py` in `tests/e2e/test_qa_real_end_to_end.py` so Weaviate is bootstrapped and populated before calling `answer()`.
  - **Rationale**: Tests should prepare their environment; `answer()` should not implicitly bootstrap databases. This aligns with best practices of explicit test setup and isolation.
  - **Verify**: `bash scripts/test.sh e2e` runs green.

- [x] Preserve volumes during e2e teardown and clean up only test data
  - **Action**: Change `scripts/test.sh` e2e teardown to `docker compose down` (without `-v`) to avoid removing persistent volumes.
  - **Action**: Add session autouse fixture in `tests/e2e/conftest.py` to delete only the `TestCollection` at the end of the e2e session.
  - **Rationale**: Prevent accidental production data loss while ensuring ephemeral test data does not persist.
  - **Verify**: After e2e, volumes remain; `TestCollection` is removed.

- [x] Make bootstrap e2e use compose Weaviate (no app rebuild), not Testcontainers
  - **Action**: Add `weaviate_compose_up` fixture in `tests/e2e/conftest.py` to start only the `weaviate` service via docker compose (`up -d --wait weaviate`).
  - **Action**: Update `tests/e2e/test_weaviate_bootstrap_missing_collection_e2e.py` to use this fixture and connect to `http://localhost:8080` with gRPC 50051.
  - **Rationale**: Mirrors production networking (HTTP + gRPC) and avoids gRPC port mismatch issues seen with Testcontainers defaults.
  - **Verify**: Running the single test passes; e2e suite remains green.

- [x] Ensure e2e tests that need real Ollama start that container too
  - **Action**: Add `ollama_compose_up` fixture in `tests/e2e/conftest.py` to start only the `ollama` service via docker compose (`up -d --wait ollama`).
  - **Action**: Update `tests/e2e/test_qa_real_end_to_end.py` to depend on both `weaviate_compose_up` and `ollama_compose_up` (and register `tests/e2e/fixtures_ingestion` via `pytest_plugins`).
  - **Rationale**: Makes tests explicitly start real services they need and aligns with the production stack; avoids hidden dependencies.
  - **Verify**: Test runs with real Weaviate + Ollama and returns a non-empty answer without "I found no relevant context".
  
- [ ] Step 5 — UI bundle (frontend/UI only; network allowed; coverage disabled)
  - Action: Require `-e .[ui]` and browsers; standardize command: `.venv/bin/python -m pytest tests/ui --no-cov -q`.
  - Verify: Without `--no-cov`, the run errors with clear usage as enforced by `tests/ui/conftest.py`. With `--no-cov`, only `tests/ui/*` are collected and run.

- [ ] Step 6 — CI wiring: dedicated jobs per bundle
  - Action: In `.github/workflows/python-lint-test.yml`, keep `fast_tests` for Unit; add (or adjust existing) manual/scheduled jobs:
    - Integration: run `pytest tests/integration -q` with caching; avoid Playwright and full compose.
    - E2E: manual or scheduled; bring up compose, run `pytest tests/e2e -q`, then tear down.
    - UI: keep existing `ui_tests_act` flow; ensure it installs `-e .[ui]` and `playwright install`, then run `pytest tests/ui --no-cov -q`.
  - Verify: `act pull_request -j fast_tests` remains green. Manual `act workflow_dispatch -j ui_tests_act` runs UI. Integration/E2E jobs run only when triggered and pass locally under `act`.

- [ ] Step 6.1 — Simplify default pytest options to avoid marker drift
  - Action: In `pyproject.toml` `[tool.pytest.ini_options].addopts`, remove `-m "not ui"` (directory selection and UI testpaths exclusion handle UI). Keep coverage args.
  - Action: Keep marker declarations only for cross-cutting categories (`slow`, `docker`, `external`) to document intent; do not require `unit/integration/e2e/ui` markers.
  - Verify: `pytest -q` on a fresh env collects all non-UI tests due to UI's own conftest coverage gating and directory-based commands in CI/scripts.

- [ ] Step 7 — Developer UX: top-level scripts/Make targets
  - Action: Add convenience wrappers: `scripts/test_unit.sh`, `scripts/test_integration.sh`, `scripts/test_e2e.sh`, `scripts/test_ui.sh` with the standardized directory-based commands and minimal flags.
  - Verify: `bash scripts/test_unit.sh` runs the unit bundle; similar for other scripts.


#### P1 — CLI/QA Loop UX and Logging Cleanup (reduce clutter, keep essentials)

- Context and goal
  - Current situation: The CLI prints duplicate and overly verbose INFO logs (e.g., both plain and rich formats), shows non-actionable boot warnings, and surfaces low-level retrieval details (candidate counts, chunk heads) at INFO. This clutters the UX and hides the actual answer stream.
  - Goal: Provide a clean, minimal default console that shows only essential status and the streamed answer, while keeping rich diagnostic detail in rotating file logs and behind an explicit `--debug` mode. Ensure there is a single logger initialization path and predictable verbosity controls.

- [ ] Step 1 — Centralize logging (root-only, minimal console)
  - Action: Make `backend.config.get_logger` the only logger factory. Remove or delegate `backend.console.get_logger` to avoid handler duplication.
  - Action: Initialize once in `backend.config`:
    - RichHandler to stderr for console (message-only), level from `LOG_LEVEL` (default INFO).
    - RotatingFileHandler at DEBUG to `logs/rag_system.log` with full format.
    - Set noisy third-party loggers (`httpx`, `urllib3`, `requests`, `transformers`, `torch`, `sentence_transformers`, `pypdf`) to WARNING/ERROR.
    - Enable `logging.captureWarnings(True)`.
  - Verify: `.venv/bin/python -m backend.qa_loop --question "ping"` prints each message once; DEBUG appears only in the file log.

- [ ] Step 2 — Simplify console UX (show essentials only)
  - Action: Replace multi-line readiness/info banners with `Console().status(...)` spinners; show at most two lines before the input prompt.
  - Action: Stream the answer prefixed with a single "Answer: "; use `rich.rule.Rule` for separators as needed.
  - Action: Downgrade retrieval details and step-by-step readiness logs from INFO → DEBUG; keep user-facing guidance at INFO.
  - Verify: Default run shows a clean prompt, concise status, and the streamed answer; detailed steps are only in `logs/rag_system.log`.

- [ ] Step 3 — Predictable verbosity controls (CLI > env > default)
  - Action: Support `-q/--quiet` and `-v/--verbose` (repeatable) plus `--log-level LEVEL` in `backend.qa_loop`. Apply level early.
  - Action: Precedence: `--log-level` > `-q/-v` > `LOG_LEVEL` env > default INFO. Keep file handler at DEBUG regardless.
  - Action: Simplify `scripts/cli.sh` to pass flags through; avoid exporting `LOG_LEVEL` when `--debug/-v` is provided to prevent conflicts.
  - Verify: `-q` shows only warnings/errors; default shows minimal INFO; `-vv` shows DEBUG.

- [ ] Step 4 — Targeted warning handling (no blanket ignores)
  - Action: Add selective `warnings.filterwarnings` for known noisy imports (e.g., specific SWIG deprecations). Do not globally ignore `DeprecationWarning`.
  - Action: Keep filtered warnings recorded in file logs via `captureWarnings`; suppress them from console by default.
  - Verify: Boot-time SWIG warnings disappear from console; remain visible in `logs/rag_system.log`.

- [ ] Step 5 — Guardrails and docs
  - Action: Add a unit test asserting a single Rich console handler and no duplicate stream handlers after importing `backend.retriever`, `backend.qa_loop`, etc.
  - Action: Add a CLI output test asserting default/quiet/verbose behaviors using `capsys`.
  - Action: Update `README.md` and `docs/DEVELOPMENT.md` to document flags, precedence, and log file location.
  - Verify: `.venv/bin/python -m pytest -q tests/unit/test_logging_config.py tests/integration/test_cli_output.py` passes.

#### P2 — Containerized CLI E2E copies (keep host-run E2E; add container-run twins)

- Why: Host-run E2E miss packaging/runtime issues (entrypoint, PATH, env, OS libs). Twins validate the real image without replacing fast host tests.

- [ ] Step 1 — Identify candidates
  - Action: List E2E tests invoking CLI in-process (e.g., `backend.qa_loop`) such as `tests/e2e/test_qa_real_end_to_end.py`.
  - Verify: Confirm they don’t already run via container.

- [ ] Step 2 — Compose runner for CLI (no bind mounts)
  - Action: Add `cli` service (profile `cli`) in `docker/docker-compose.yml` using `kri-local-rag-app`, no `volumes`, `working_dir: /app`, and env:
    - `WEAVIATE_URL=http://weaviate:8080`, `OLLAMA_URL=http://ollama:11434`.
  - Verify: `docker compose --profile cli run --rm cli python -m backend.qa_loop --help | cat` exits 0.

- [ ] Step 3 — Test helper
  - Action: In `tests/e2e/conftest.py`, add `run_cli_in_container(args, env=None)` that runs `docker compose --profile cli run --rm cli ...`, returns `returncode/stdout/stderr`.
  - Verify: `--help` smoke passes.

- [ ] Step 4 — Readiness and URLs
  - Action: Use existing `weaviate_compose_up`/`ollama_compose_up`; ensure ingestion uses compose-internal URLs.
  - Verify: Readiness checks pass before CLI twin runs.

- [ ] Step 5 — Create test twins
  - Action: Add `_container_e2e.py` twins that call `run_cli_in_container([...])` with equivalent CLI subcommands; optionally mark with `@pytest.mark.docker`.
  - Verify: Single twin passes via `.venv/bin/python -m pytest -q tests/e2e/test_qa_real_end_to_end_container_e2e.py` after compose `--wait`.

- [ ] Step 6 — Build outside tests
  - Action: Ensure scripts/CI build `kri-local-rag-app` once; helper should raise `pytest.UsageError` if image missing.
  - Verify: Second run is faster due to image reuse.

- [ ] Step 7 — Diagnostics and isolation
  - Action: On failure, print exit code, last 200 lines of app logs, and tails of `weaviate`/`ollama` logs; use ephemeral dirs/volumes.
  - Verify: Failures are actionable; runs are deterministic and isolated.

- [ ] Step 8 — Wire into scripts/docs/CI
  - Action: Document commands in `docs/DEVELOPMENT.md` and `AI_instructions.md`; mention in `scripts/test.sh e2e` help; add a CI job for the containerized CLI subset.
  - Verify: Fresh env runs `tests/e2e/*_container_e2e.py` green; CI job passes locally under `act` and on hosted runners.

#### P3 — E2E retrieval failure: QA test returns no context (Weaviate)

 - Context and goal
   - Failing test returns no context from Weaviate. Likely mismatch between collection name used by retrieval and the one populated by ingestion, or ingestion not executed.

 - [ ] Task 1 — Reproduce quickly
   - Run only the failing test to confirm the symptom.

 - [ ] Task 2 — Check config and schema
   - Confirm effective `COLLECTION_NAME` and that the corresponding collection exists in Weaviate.

 - [ ] Task 3 — Confirm data population
   - Ensure the ingestion fixture ran and that the target collection contains objects.

 - [ ] Task 4 — Probe retrieval directly
   - Call the retriever to verify it returns non-empty results when data is present.

 - [ ] Task 5 — Standardize collection naming
   - Decide one collection name for E2E and apply consistently (tests, fixtures, and config).

 - [ ] Task 6 — Implement and verify
   - Apply the change, re-run E2E, and confirm the QA test passes.

 - [ ] Task 7 — Add minimal guardrails
   - Log the active collection name in the e2e fixture and add a small test ensuring graceful behavior when empty.

#### P4 — ...

New Tasks/Topic can be added here.

#### P5 — Pre-push performance optimizations (local DX)

- [x] Switch lint/typecheck to native venv (faster than act)
  - [x] Replace `act ... -j lint` in the pre-push hook with native calls: `.venv/bin/ruff check .` and `.venv/bin/ruff format --check .`
  - [x] Replace `act ... -j pyright` with `.venv/bin/pyright`
- [x] Keep tests via `act` for parity; native fast path runs the unit bundle: `.venv/bin/python -m pytest tests/unit --maxfail=1 -q`

- [x] Add pre-push skip toggles (env-driven)
  - [x] Support `SKIP_LINT=1`, `SKIP_PYRIGHT=1`, `SKIP_TESTS=1` to selectively skip steps locally
  - [x] Default heavy scans to opt-in (CodeQL already defaults to skip via `SKIP_LOCAL_SEC_SCANS=1`)

- [x] Fail-fast for local tests
  - [x] Update pre-push fast tests invocation to include `--maxfail=1 -q` for quicker feedback on first failure

- [ ] Pre-commit integration for changed-files speedups
  - [ ] Add `.pre-commit-config.yaml` with `ruff` (lint + format) and optional `pyright` hooks
  - [ ] Install hooks (`pre-commit install`) and document usage
  - [ ] Configure to run only on changed files to keep local runs snappy

- [ ] Documentation updates
  - [ ] Document all local toggles in `docs/DEVELOPMENT.md` (e.g., `SKIP_LINT`, `SKIP_PYRIGHT`, `SKIP_TESTS`, and `SKIP_LOCAL_SEC_SCANS`)
  - [ ] Provide a "fast push" recipe, e.g.: ``SKIP_PYRIGHT=1 SKIP_LOCAL_SEC_SCANS=1 git push``
  - [ ] Note how to opt-in to CodeQL locally: ``SKIP_LOCAL_SEC_SCANS=0 git push``

- [ ] Version alignment and consistency
  - [ ] Pin the local `pyright` version (e.g., in `requirements-dev.txt`) to match CI
  - [ ] Ensure `ruff` version in pre-commit matches the CI action version (`0.5.3` today)
  
 - [x] Pre-push alignment
   - [x] Replace any `--test-fast` references with `tests/unit` for pre-push context and update `scripts/pre_push.sh` accordingly

#### P5.1 — Docker build cache and context optimizations

- [ ] Add a root `.dockerignore` to shrink build context and improve cache hits
  - Action: Create `.dockerignore` at repo root including at minimum: `.git`, `.venv`, `__pycache__/`, `*.pyc`, `logs/`, `data/`, `node_modules/`, `dist/`, `build/`, `*.ipynb_checkpoints`.
  - Verify: Run a build and confirm the "Sending build context" size drops and cache hit rate increases on subsequent builds.

- [ ] Use BuildKit apt cache for OS package installs
  - Action: In `docker/app.Dockerfile`, change the apt layer to use a cache mount:
    - Replace the apt RUN with `RUN --mount=type=cache,target=/var/cache/apt apt-get update && apt-get install -y --no-install-recommends ... && apt-get clean && rm -rf /var/lib/apt/lists/*`.
  - Verify: Second build is faster with cache hits on apt downloads.

- [ ] Document BuildKit and cache guidance
  - Action: In `docs/DEVELOPMENT.md` (Docker section), note that BuildKit is on by default; prefer cached builds. Use `--no-cache` only when intentionally refreshing. Mention `scripts/build_app.sh` passes through extra flags (e.g., `--no-cache`).
  - Verify: Doc updated and referenced from README as appropriate.

- [ ] Pin remote image tags for reproducibility (where reasonable)
  - Action: Audit image tags in `docker/docker-compose.yml` and `docker/app.Dockerfile`.
    - Keep `weaviate` pinned (already pinned).
    - Consider pinning `OLLAMA_IMAGE` default from `latest` to a known-good version; document override via env var.
    - Python base images are already pinned; keep that practice.
  - Verify: `docker compose up` uses the pinned versions; builds remain reproducible.

- [ ] Optional: Add opt-in image refresh step while defaulting to cache usage
  - Action: In `scripts/docker-setup.sh`, honor an env flag `FORCE_PULL=1` to run `docker compose pull` before build/up; default to not pulling.
  - Verify: With `FORCE_PULL=1`, images are updated; without it, local cache is used.

- [ ] Optional: Avoid dependency-layer cache busting
  - Action: Keep `requirements.txt` stable and separate dev/runtime dependencies (`requirements-dev.txt` vs runtime). Ensure `docker/app.Dockerfile` installs only runtime deps to preserve cache.
  - Verify: Code-only changes do not invalidate the dependency install layer; rebuilds are fast.

#### P5.2 — NLTK data setup - to make .md ingestion work (deterministic and reproducible)

- [ ] Replace brittle inline NLTK downloads in Docker with official downloader CLI
  - Action: In `docker/app.Dockerfile`, replace the current `python -c "import nltk; ..."` with:
    ```Dockerfile
    RUN mkdir -p /opt/venv/nltk_data \
        && ${VENV_PATH}/bin/python -m nltk.downloader -d /opt/venv/nltk_data punkt punkt_tab
    ```
  - Action: Remove any `|| true` so the build fails fast if downloads fail.
  - Verify: A fresh build succeeds and the layer contains `tokenizers/punkt` and `tokenizers/punkt_tab` under `/opt/venv/nltk_data`.

- [ ] Establish a single data path via `NLTK_DATA`
  - Action: Keep `ENV NLTK_DATA=/opt/venv/nltk_data` in Docker. For local dev, document using `export NLTK_DATA="$(pwd)/.venv/nltk_data"`.
  - Verify: `python -c "import nltk.data; print(nltk.data.path)"` includes the expected path in both envs.

- [ ] Local dev parity: documented bootstrap
  - Action: In `docs/DEVELOPMENT.md`, add a snippet for devs:
    ```bash
    export NLTK_DATA="$(pwd)/.venv/nltk_data"
    mkdir -p "$NLTK_DATA"
    .venv/bin/python -m nltk.downloader -d "$NLTK_DATA" punkt punkt_tab
    ```
  - Verify: On a clean venv, the commands complete and `nltk.data.find('tokenizers/punkt')` succeeds.

- [ ] Startup verification with clear error
  - Action: Add a lightweight check at app startup (or first-use path) to assert NLTK resources exist, e.g. `nltk.data.find('tokenizers/punkt')`, and raise a helpful message if missing.
  - Verify: When the data is removed/absent, the app fails fast with a clear remediation hint referencing the dev/Docker steps above.

- [ ] Pin library version for stability
  - Action: Pin `nltk` to a known-working version in `requirements.txt` (runtime) and `requirements-dev.txt` if needed.
  - Verify: Rebuild/install resolves the pinned version; tokenization works as before.

- [ ] Optional: Offline/CI artifacts for corpora
  - Action: For fully offline or hermetic builds, package the required subset of `nltk_data` as a build artifact (e.g., tarball) and add a Docker build step to extract it to `/opt/venv/nltk_data` with checksum verification.
  - Verify: Docker build succeeds without network when the artifact is provided; app runs and passes the startup verification.

#### P6 — E2E testing Tasks (CLI and Streamlit)

  - [ ] Create dedicated UI dependency extra (isolate Playwright)
    - [ ] Action: In `pyproject.toml`, move `pytest-playwright==0.4.4` and `playwright>=1.45,<2` out of the `test` extra and define a new extra: `[project.optional-dependencies].ui = ["pytest-playwright==0.4.4", "playwright>=1.45,<2"]`.
    - [ ] Action: Ensure default local/dev installs do NOT include `ui` (e.g., keep `-e .[test,docs,cli]`).
    - [ ] Verify: A fresh `pip install -e .[test,docs,cli]` does not install Playwright; `python -m playwright` is not available until `-e .[ui]` is installed.

  - [ ] CI dependency isolation for UI suite
    - [ ] Action: In `.github/workflows/python-lint-test.yml`, ensure only the UI job installs the UI extra (e.g., `pip install -e .[ui]` or `-e .[test,docs,cli,ui]` if those are needed there).
    - [ ] Action: In the same UI job, run `python -m playwright install --with-deps` before executing tests; remove any Playwright installs from non-UI jobs.
    - [ ] Verify: `act pull_request -j ui_tests_act` shows the UI extra being installed and browsers installed; `-j fast_tests`/`-j core_suite` do not install Playwright nor browsers.

  - [ ] Document isolated UI workflow for developers
    - [ ] Action: Update `docs/DEVELOPMENT.md` to show two paths:
      - Regular dev: `pip install -e .[test,docs,cli]` (no Playwright)
      - UI run: `pip install -e .[ui] && python -m playwright install --with-deps && pytest --test-ui --no-cov`
    - [ ] Verify: Follow the doc steps on a clean venv; UI tests only run after installing the `ui` extra and browsers.

  - [ ] Playwright dependency explicit pin (stability)
    - [ ] Action: In `pyproject.toml` add `"playwright>=1.45,<2"` to `[project.optional-dependencies].test` next to `pytest-playwright==0.4.4`, then reinstall dev deps.
    - [ ] Verify: `.venv/bin/python -m playwright --version` succeeds; `.venv/bin/python -m pytest --test-ui --no-cov -q` collects and runs UI tests.

  - [ ] Trim CI Playwright browser installs to UI jobs only (simplify CI)
    - [ ] Action: In `.github/workflows/python-lint-test.yml`, remove Playwright browser install steps from non-UI jobs (e.g., `core_suite`). Keep them only where `--test-ui` (or other Playwright tests) actually run.
    - [ ] Verify: `act pull_request -j fast_tests` and `-j core_suite` show no Playwright install step; `-j ui_tests_act` still installs browsers and runs UI tests.

  - [ ] Simplify UI coverage gating (reduce custom logic)
    - [ ] Action: In `tests/e2e_streamlit/conftest.py`, simplify the collection hook to only enforce: if `--test-ui` is used while coverage is enabled, raise a clear `pytest.UsageError`. Rely on default `-m "not ui"` from `pyproject.toml` to exclude UI tests in normal runs; drop verbose coverage detection/deselect logic if not needed.
    - [ ] Verify: `.venv/bin/python -m pytest -q` runs green with UI tests deselected; `.venv/bin/python -m pytest --test-ui --no-cov -q` runs UI tests; `.venv/bin/python -m pytest --test-ui -q` errors with the expected usage message.

  - [ ] Streamlit E2E: Improve locator resilience (only if still flaky)
    - Action: Switch input selection to `get_by_label("Ask a question:")`, keep `[data-testid]` for answers, and if needed add `page.wait_for_function` to await `TEST_ANSWER` text.
    - Verify: Re-run the single test; expect pass without diagnostic waits.

  - [ ] **Task 1: Isolate and Reproduce the Failure Reliably.**
    - **Goal:** Create a minimal, fast command that reliably demonstrates the failure, so we don't have to run the full 1-minute test suite to verify our fix.
    - **Action:** Use the simplest Playwright test we have (`test_browser_launch_only.py`) and run it with `pytest-cov` enabled.
    - **Verify:** Confirm this single test fails with the known `AttributeError`. Then, run it with `--no-cov` and confirm it passes. This gives us a clear baseline.

  - [ ] **Task 2: Implement a Conditional Skip.**
    - **Goal:** Ensure the default, coverage-enabled full suite runs green by not executing Playwright tests.
    - **Action:** In `tests/e2e_streamlit/conftest.py`, add a `pytest_collection_modifyitems` hook that unconditionally skips all tests in this directory whenever `--no-cov` is not present (i.e., default coverage runs). Keep a guard that raises if `--test-ui` is used without `--no-cov`.
    - **Verify:** Re-run the failing command from Task 1. All UI tests should now report as `SKIPPED` instead of `ERROR`.

  - [ ] Correction plan: Make UI skip unconditional under coverage
    - [ ] Simplify detection to: if not `--no-cov`, fully deselect items in `tests/e2e_streamlit` to avoid fixture setup
    - [ ] Re-run full suite: `.venv/bin/python -m pytest -q -m "not environment" --disable-warnings` should pass with 0 errors
    - [ ] Run UI-only suite without coverage: `.venv/bin/python -m pytest --test-ui --no-cov -q` should pass or at least run without coverage-related errors

  - [ ] **Task 3: Achieve a "Green" Full Suite Run.**
    - **Goal:** Ensure the main test suite can now run to completion and generate a coverage report without any errors.
    - **Action:** Run the full test suite command (`pytest -m "not environment"`).
    - **Verify:** The command should complete with all tests either passing or being skipped (specifically the Playwright tests). There should be zero errors, and a coverage report should be generated for the rest of the codebase.

  - [ ] **Task 4: Create a Separate, Coverage-Free E2E Test Run.**
    - **Goal:** Make sure our important Playwright E2E tests are still executed somewhere.
    - **Action:** Define a new, separate command that runs *only* the Playwright tests and explicitly disables coverage (`--no-cov`). This command will be used in our CI pipeline and for local E2E checks.
    - **Verify:** Run this new command and confirm that all Playwright tests pass.

#### P7 — Dependencies management last tasks: Compatibility monitors and guardrails

- Goal: Stabilize on Protobuf 5.x lane, keep sentence-transformers 5.x, and address dependency compatibility to minimize future surprises.
- Proposed Approach: Use `uv` as a diagnostic tool to find compatible pinned versions for `pip`, simplifying requirements management and isolating tooling.

#### Skepticism checks (archived; see `docs_AI_coder/archived-tasks.md`)
#### Modified plan steps (archived; see `docs_AI_coder/archived-tasks.md`)

**Compatibility monitors and guardrails (integrate into workflow)**
    - [ ] Active monitoring: Actively track the status of `opentelemetry-proto` support for Protobuf ≥5. If opentelemetry becomes a requirement later, and compatibility is confirmed, update the sandbox and re-pin. Until then, strictly avoid including opentelemetry in the application's main environment.
    - [ ] Weaviate-client integration: Confirm the tested version range for gRPC compatibility with the current Weaviate server version used. Add specific integration tests that target gRPC paths within the application if not already present.
    - [ ] Rollback strategy: Define clear rollback procedures. If updates introduced regressions, revert the pins in `requirements*.txt` and iterate in the `uv` sandbox to find a stable, compatible set before re-attempting the upgrade.

#### P7.3 — Renovate configuration best practices alignment

- [ ] Validate current Renovate config against best practices
  - Action: Run config validator locally to confirm schema and detect deprecations:
    - `npx --yes --package renovate -- renovate-config-validator`
  - Verify: Command exits 0; no errors; note any warnings for follow-up.

- [ ] Consider adopting Renovate `config:best-practices` (or add equivalent presets explicitly)
  - Action: Evaluate replacing `extends` with `config:best-practices`. If unavailable in your Renovate runner version, add the nearest equivalents explicitly:
    - Keep `config:recommended`
    - Add `helpers:pinGitHubActionDigests` (pin Actions to commit SHAs)
    - Add `:configMigration` (auto-migrate deprecated options)
    - Keep `docker:pinDigests` (already present)
  - Verify: Re-run validator; open a Renovate onboarding PR reflecting the new extends; confirm Actions are pinned to SHAs in subsequent PRs.

- [ ] Enable and verify GitHub vulnerability alerts integration
  - Action: Add/verify `"vulnerabilityAlerts": true` so Renovate opens PRs for GH advisories when supported by the platform/repo permissions.
  - Verify: After next run, security alert PRs appear when applicable; Renovate log shows the vulnerability alerts step enabled.

- [ ] Keep PR noise low while maintaining safety
  - Action: Review/update limits and schedule:
    - Confirm `prConcurrentLimit: 10`, `prHourlyLimit: 2` fit team capacity
    - Keep off-hours schedule (currently `before 6am on monday`) or consider `schedule:nonOfficeHours`
  - Verify: Next cycle keeps PR volume manageable; no daytime bursts.

- [ ] CI guardrail: validate Renovate config on PRs that touch it
  - Action: Add a lightweight CI job that runs the validator when `renovate.json` changes:
    - `npx --yes --package renovate -- renovate-config-validator`
  - Verify: Open a dummy PR modifying `renovate.json`; job runs and passes/fails appropriately.

- [ ] Python updates: confirm pinning and grouping strategy
  - Action: Keep `rangeStrategy: "replace"` for `pip_requirements` to update pins in `requirements*.txt`.
  - Action: Audit `pip_requirements.fileMatch` patterns cover all requirement files (e.g., `requirements.txt`, `requirements-dev.txt`, any `requirements-*.txt`). Expand if needed.
  - Action: Keep/adjust grouping rules (pytest/ruff/mypy/sphinx) and patch-only automerge for Python for safe, low-risk merges.
  - Verify: Sample cycle shows grouped PRs as expected; patch PRs for Python auto-merge cleanly.

- [ ] GitHub Actions updates: safety and automation
  - Action: Keep minor/patch automerge for Actions; ensure digest pinning is enabled via `helpers:pinGitHubActionDigests` (or `config:best-practices`).
  - Verify: New Actions PRs use commit SHAs and auto-merge when minor/patch.

- [ ] Docker updates: digest safety and auto-merge
  - Action: Keep `docker:pinDigests` extend and the packageRule that auto-merges `digest` updates on branch.
  - Verify: Digest-only PRs auto-merge and images remain pinned by digest.

#### P8 Next up (maintainability, observability)
- [ ] Refactor Weaviate connection logic into a single reusable function.
- [ ] Replace fragile relative paths with robust absolute paths where appropriate.
- [ ] Configure centralized file logging (e.g., `logs/app.log`) across CLI and services.
- [ ] Enhance progress logging for long-running ingestion (progress bar or granular steps).
- [ ] Review integration suite Docker autostart
  - [ ] Action: Measure runtime impact of `tests/integration/conftest.py::_start_docker_services_session` autouse startup.
  - [ ] Action: If overhead is significant and not broadly needed, scope compose startup to tests that require it (explicit `docker_services` usage) or guard autostart behind an env flag (e.g., `INTEGRATION_AUTOSTART_COMPOSE=1`).
  - [ ] Verify: Integration tests that need compose still pass; testcontainers-only tests remain unaffected and faster.

#### P8.1 — Socket handling simplification (follow-up)

Archived on 2025-08-13

#### P8.2 — Test path trust and tagging simplification

- Goal: Make test type derive from path (source of truth) and simplify markers to align with best practices.
- Plan (small, incremental steps)
  1) Enforce path-derived default markers
     - [ ] Action: Add/adjust a `pytest_collection_modifyitems` hook in `tests/conftest.py` to auto-apply markers by path:
       - `tests/unit/` → `unit`
       - `tests/integration/` → `integration`
       - `tests/environment/` → `environment`
       - `tests/e2e/` → `e2e`
       - `tests/e2e_streamlit/` → `ui`
       - `tests/docker/` → `docker`
     - [ ] Verify: `pytest --co -q` shows sample items with expected markers.
  2) Tighten fast suite selection
     - [x] Action: Ensure `--test-fast` collects only from `tests/unit/` and sets `UNIT_ONLY_TESTS=1` to enforce early socket block.
     - [ ] Verify: `.venv/bin/python -m pytest --test-fast -q` is green; no external network attempts appear in logs.
  3) Audit and relocate miscategorized tests
     - [ ] Action: Scan for tests under `tests/unit/` importing heavy/external services or carrying non-unit markers; move them to the correct directory (usually `tests/integration/`).
     - [ ] Verify: Re-run `--test-fast`; confirm it remains green and faster. Run `-m integration` to ensure moved tests are collected there.
  4) Simplify explicit markers
     - [ ] Action: Remove redundant `@pytest.mark.<type>` where the path already determines the type; keep only additional markers like `slow`, `ui`, or `docker` when needed.
     - [ ] Verify: `pytest -q` collects the same tests as before; diffs show only marker removals.
  5) Guardrail: reject mismatched path/marker
     - [ ] Action: In `pytest_collection_modifyitems`, error if a test under `tests/unit/` has markers `integration`, `e2e`, `docker`, or `environment` (and vice versa when appropriate).
     - [ ] Verify: Introduce a deliberate mismatch in a temporary branch; confirm collection fails with a clear message; revert.
  6) Documentation
     - [ ] Action: Update `docs/DEVELOPMENT.md` to document that path determines test type; markers are optional for extra semantics only. Document `--test-fast`, `--test-core`, `--test-ui` behavior.
     - [ ] Verify: Follow the doc to run each suite locally; results match expectations.
  7) CI alignment
     - [ ] Action: Keep the CI "Fast Tests" job on `--test-fast`. Add a lightweight job or step to run `pytest --check-test-paths` (via env/flag) to enforce the guardrail in PRs.
     - [ ] Verify: Open a draft PR with an intentional mismatch; CI step fails with a helpful message; revert.

#### P9 — Soon (quality, CI structure, performance)
- [ ] Expand unit test coverage, focusing on core logic and error paths.
- [ ] Improve test assertions and edge case testing across existing tests.
- [ ] Implement test data management fixtures for consistent, reliable tests.
- [ ] Review all integration tests for isolation and resource cleanup.
- [ ] Improve overall test isolation to ensure tests do not interfere with each other.
- [ ] Separate test jobs by type in GitHub Actions and update workflow/service deps.
- [ ] Add test quality gates (coverage thresholds, basic performance checks).
- [ ] Add performance benchmarks for critical paths (embedding generation, retrieval).
- [ ] Add further test categories/organization (logic, utils, mocks, etc.).

#### P10 — Later (docs, standards, templates, metrics)
- [ ] Update `DEVELOPMENT.md` with dependency management guidelines.
- [ ] Document logging and monitoring strategy in `DEVELOPMENT.md`.
- [ ] Create testing standards document.
- [ ] Add test templates for consistency and performance benchmarking.
- [ ] Improve test documentation and add test quality metrics tracking over time.



 