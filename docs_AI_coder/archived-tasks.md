# Archived Tasks

This file records tasks that have been completed and moved out of the active TODO backlog.

## Archived on 2025-01-27

### P0.1b — Local dev checks (pre-push) ✅ COMPLETED

- [x] Re-enable local security scans in pre-push
  - Action: Run push with `SKIP_LOCAL_SEC_SCANS=0` to include Semgrep/CodeQL locally: `SKIP_LOCAL_SEC_SCANS=0 git push -n` (dry run) or actual push.
  - Verify: Pre-push log shows Semgrep/CodeQL steps executed without schema errors and exits 0.

- [x] Install pyright in `.venv` so type checks run in pre-push
  - Action: `.venv/bin/pip install pyright` (optionally pin to CI version) and commit if adding to `requirements-dev.txt`.
  - Verify: `.venv/bin/pyright --version` succeeds and pre-push no longer warns about missing pyright.

**Status**: All steps completed. Local security scans are re-enabled in pre-push, and pyright is installed in the local venv for type checking.

### P0.2 — Test suite bundling into four bundles (unit, integration, e2e, ui) — simplified ✅ COMPLETED

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

- [x] Step 4 — E2E bundle (all real components; network allowed)
  - Action: Provide a single dispatcher script `scripts/test.sh` with usage: `test.sh [unit|integration|e2e|ui]` that runs the standardized directory-based commands; for e2e it does `docker compose up -d --wait && pytest tests/e2e -q && docker compose down` with `set -euo pipefail`.
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
  
- [x] Step 5 — UI bundle (frontend/UI only; network allowed; coverage disabled)
  - Action: Require `-e .[ui]` and browsers; standardize command: `.venv/bin/python -m pytest tests/ui --no-cov -q`.
  - Verify: Without `--no-cov`, the run errors with clear usage as enforced by `tests/ui/conftest.py`. With `--no-cov`, only `tests/ui/*` are collected and run.

- [x] Step 6 — CI wiring: dedicated jobs per bundle
  - Action: In `.github/workflows/python-lint-test.yml`, keep `fast_tests` for Unit; add (or adjust existing) manual/scheduled jobs:
    - Integration: run `pytest tests/integration -q` with caching; avoid Playwright and full compose.
    - E2E: manual or scheduled; bring up compose, run `pytest tests/e2e -q`, then tear down.
    - UI: keep existing `ui_tests_act` flow; ensure it installs `-e .[ui]` and `playwright install`, then run `pytest tests/ui --no-cov -q`.
  - Verify: `act pull_request -j fast_tests` remains green. Manual `act workflow_dispatch -j ui_tests_act` runs UI. Integration/E2E jobs run only when triggered and pass locally under `act`.

- [x] Step 6.1 — Simplify default pytest options to avoid marker drift
  - Action: In `pyproject.toml` `[tool.pytest.ini_options].addopts`, remove `-m "not ui"` (directory selection and UI testpaths exclusion handle UI). Keep coverage args.
  - Action: Keep marker declarations only for cross-cutting categories (`slow`, `docker`, `external`) to document intent; do not require `unit/integration/e2e/ui` markers.
  - Verify: `pytest -q` on a fresh env collects all non-UI tests due to UI's own conftest coverage gating and directory-based commands in CI/scripts.

- [x] Step 7 — Developer UX: top-level scripts/Make targets
  - Action: Add convenience wrappers: `scripts/test_unit.sh`, `scripts/test_integration.sh`, `scripts/test_e2e.sh`, `scripts/test_ui.sh` with the standardized directory-based commands and minimal flags.
  - Verify: `bash scripts/test_unit.sh` runs the unit bundle; similar for other scripts.

**Status**: All steps completed. Test suite has been successfully reorganized into four clear bundles (unit, integration, e2e, ui) with directory-based organization, simplified configuration, and proper CI integration.

### P5 — Pre-push performance optimizations (local DX) ✅ MOSTLY COMPLETED

- [x] Switch lint/typecheck to native venv (faster than act)
  - [x] Replace `act ... -j lint` in the pre-push hook with native calls: `.venv/bin/ruff check .` and `.venv/bin/ruff format --check .`
  - [x] Replace `act ... -j pyright` with `.venv/bin/pyright`
- [x] Keep tests via `act` for parity; native fast path runs the unit bundle: `.venv/bin/python -m pytest tests/unit --maxfail=1 -q`

- [x] Add pre-push skip toggles (env-driven)
  - [x] Support `SKIP_LINT=1`, `SKIP_PYRIGHT=1`, `SKIP_TESTS=1` to selectively skip steps locally
  - [x] Default heavy scans to opt-in (CodeQL already defaults to skip via `SKIP_LOCAL_SEC_SCANS=1`)

- [x] Fail-fast for local tests
  - [x] Update pre-push fast tests invocation to include `--maxfail=1 -q` for quicker feedback on first failure

- [x] Pre-push alignment
   - [x] Replace any `--test-fast` references with `tests/unit` for pre-push context and update `scripts/pre_push.sh` accordingly

**Status**: Core performance optimizations completed. Pre-push now uses native venv tools for faster execution, includes skip toggles for flexibility, and implements fail-fast behavior. Remaining tasks are documentation updates and pre-commit integration.

## Archived on 2025-08-15

### P0.1a — Git Hooks Management (Best Practices) ✅ COMPLETED

- [x] Step 1 — Centralize Git Hooks in a Versioned Directory
  - Action: Create a new directory `scripts/git-hooks/`.
  - Action: Move the existing `.git/hooks/pre-commit` and `.git/hooks/pre-push` scripts to `scripts/git-hooks/`.
  - Action: Ensure the new `scripts/git-hooks/` directory is tracked by git.
  - Verify: `ls scripts/git-hooks` shows `pre-commit` and `pre-push`. The files are added in `git status`.

- [x] Step 2 — Configure Git to Use the Centralized Hooks Directory
  - Action: In `docs/DEVELOPMENT.md`, instruct developers to run `git config core.hooksPath scripts/git-hooks` once after cloning.
  - Action: Add a small script or a make target (e.g., `make setup-hooks`) to automate this configuration.
  - Verify: Running `git config --get core.hooksPath` returns `scripts/git-hooks`. Committing triggers the centralized hook.

- [x] Step 3 — Clean Up and Document
  - Action: Document the purpose of the shared hooks and the setup command in `docs/DEVELOPMENT.md`.
  - Action: Remind developers they can still have local, untracked hooks in `.git/hooks/` if they need to override something for their own workflow, but the shared hooks should be the default.
  - Verify: The documentation is clear and easy for a new developer to follow.

**Status**: All steps completed. Git hooks are centralized in `scripts/git-hooks/`, git is configured to use the centralized path, and documentation is complete in `docs/DEVELOPMENT.md`.

## Archived on 2025-08-10

### Test Refactoring Status

- Unit tests properly isolated (17 tests, ~9s runtime)
- Integration tests properly categorized (13 tests, ~33s runtime)
- All tests run by default (59 tests, ~21s runtime)
- 58.68% test coverage achieved
- Python testing best practices implemented

### P0.1 — Weaviate API Migration

- Weaviate API Migration: Server Upgrade — Upgraded Weaviate server to v1.32.0 in local and CI compose.
- Weaviate API Migration: Client Version Pinning — `weaviate-client==4.16.6` pinned in `requirements.txt`.
- Weaviate API Migration: Remove Deprecated Fallbacks — Removed `vectorizer_config` fallbacks; code uses modern `vector_config` API.
- Weaviate API Migration: Update Integration Test — Integration tests use modern API without fallbacks.
- Weaviate API Migration: Verify Full System — Full system validated via integration tests (ingestion, retrieval, search).

### P1.1 — Other tasks

- Add CI environment validation — Implemented (e.g., `pip check`).
- Add unit test for CLI error handling — Added; asserts stderr and exit code on error.
- Add unit test verifying startup calls `ensure_model_available` — Added; startup path validated.

### P0.2 — E2E Tasks (CLI and Streamlit)

- CLI E2E: Interactive mode times out — Fixed. Interactive path robust to piped stdin, immediate flush, graceful EOF.
- CLI E2E: Single-question mode times out — Fixed. Single-question path prints promptly and exits 0.
- Streamlit E2E: Fake answer not visible after click — Fixed. App renders `[data-testid='answer']` and immediate fake-answer when `RAG_FAKE_ANSWER` is set; `RAG_SKIP_STARTUP_CHECKS=1` honored.
- Streamlit E2E: Strengthen assertion to wait for content — Implemented `to_contain_text("TEST_ANSWER", timeout=20000)`.
- Streamlit E2E: Add tiny diagnostic wait behind env flag — Implemented `RAG_E2E_DIAG_WAIT` optional wait.
- Streamlit E2E: Add explicit fake-mode marker and env echo — Added `[data-testid='fake-mode']`; app logs `RAG_SKIP_STARTUP_CHECKS` and `RAG_FAKE_ANSWER` at startup.
- Streamlit E2E: Ensure fake-answer path fully bypasses backend and runs first — Submit handler renders fake answer immediately.
- Streamlit E2E: Confirm server flags and isolate coverage — Launch with `--server.headless true` and `--server.fileWatcherType none`; E2E runs with `--no-cov`.

### P0.3 — Stabilization and Finalization

- Deflake: modest timeout bump after fixes — Timeouts bumped where needed; tests stable.

### P1.1 — Other tasks

- Add CI environment validation — Implemented (e.g., `pip check`).
- Add unit test for CLI error handling — Added; asserts stderr and exit code on error.
- Add unit test verifying startup calls `ensure_model_available` — Added; startup path validated.



## Archived on 2025-08-12

### P0.0a — Validating the Dependency Compatibility and Versions (completed subgroups)

#### Skepticism checks
- Verify `torch==2.7.x` support with `sentence-transformers==5.x` on Python 3.12 — monitored; unresolved in docs but sandbox OK.
- Confirm plain pip installs under WSL2 + act — stable.
- Re-check Semgrep opentelemetry requirement — not required by default; keep Semgrep containerized.
- Validate one pinned set of `requirements*.txt` across contexts — workable; remain flexible if divergence appears.

#### Modified plan steps
1) UV diagnostic sandbox for compatibility resolution
   - `tools/uv_sandbox/pyproject.toml` created with target versions; `run.sh` added and later corrected to use `uv lock --check` and `uv sync --frozen`, unset `VIRTUAL_ENV`, and use CPU wheels via `PIP_EXTRA_INDEX_URL`/`UV_EXTRA_INDEX_URL`.
   - Stable `uv.lock` committed. Notes: `protobuf==5.29.5`, `grpcio==1.63.0`, `torch==2.7.1` (CPU), `sentence-transformers==5.0.0`, `weaviate-client==4.16.6`, `langchain==0.3.27`. OTel excluded.

2) Pin propagation to pip requirements
   - Analyzed `uv.lock`/`uv tree`; propagated direct pins to `requirements*.txt`.
   - Verified with `pip check`; core tests pass.

3) CI integration (GitHub Actions + act)
   - Standardized installs from `requirements*.txt`, ensured CPU torch wheel index available, added caching, isolated Semgrep, excluded OTel until compatible.

4) Docker integration
   - Multi-stage build using `requirements.txt`; copied only runtime artifacts; validated image size and cold-start.

5) Validation and rollout
   - Dry-run results: pip check OK; core tests: 79 passed, 1 skipped, 9 deselected, 1 xpassed; versions: protobuf 5.29.5, grpcio 1.63.0, torch 2.7.1+cpu, sentence-transformers 5.0.0.
   - Docker smoke: torch 2.7.1+cpu cuda False; protobuf 5.29.5; grpcio 1.63.0.

6) Automation and upgrades
   - Renovate configured for `requirements*.txt` and actions; added concise UV/upgrade guidance to `docs/DEVELOPMENT.md` and `.cursor/rules/uv-sandbox.mdc`.

### P0.0d — ignoring call-arg ?

- Replace `# type: ignore[call-arg]` in `backend/ingest.py` with a typed helper
  - Change: Introduced `backend/vector_utils.py` with `to_float_list()` and updated `backend/ingest.py` to use it.
  - Verify: Lints clean; embedding conversion uses explicit typing without ignores.
- Audit remaining vector conversions and remove ignores where possible
  - Targets:
    - `backend/retriever.py`: Refactored to use `to_float_list` and removed ignore.
    - Tests under `tests/integration/test_vectorizer_enabled_integration.py` use `# type: ignore[attr-defined]` for `.tolist()`; consider using `to_float_list` or dedicated test helpers for clarity.

### P0 — Corrections from best-practice review (this session)

- Docker wheel index scoping
  - Action: Keep `TORCH_WHEEL_INDEX` only as a build-arg and avoid persisting `PIP_EXTRA_INDEX_URL` in the final image. Ensures build-only knobs do not leak to runtime.
  - Status: Done (builder keeps `ARG TORCH_WHEEL_INDEX`; final stage no longer sets `PIP_EXTRA_INDEX_URL`).

- Make wheels guidance concise
  - Action: Replace verbose wheel instructions with short, variable-based snippets for Docker and local venv.
  - Status: Done in `docs/DEVELOPMENT.md`.
 
- Vector conversion helper clarity and robustness
  - Action: Refine `backend/vector_utils.py::to_float_list` to:
    - Prefer straightforward `torch is not None and isinstance(x, torch.Tensor)`/`isinstance(x, np.ndarray)` checks over `locals()` tricks
    - Exclude `str`/`bytes`/`bytearray` from generic `Sequence` handling
    - Handle numeric scalars via `numbers.Real`
  - Verify: Lints clean; `.venv/bin/python -m pytest --test-core` passes.

## Archived on 2025-08-13

### P2.9 — Enforce no-network in unit tests (completed)

- Add `pytest-socket` to `pyproject.toml` test extras and document usage — done
- Add an `autouse=True` session fixture to call `disable_socket(allow_unix_socket=True)` — done
- Replace connection-based self-check in session fixture with a lightweight assert — done
- Drop per-test re-disable once the offender was disproven — done
- Provide `allow_network` opt-in fixture (function scope) for rare cases; ensure any such tests are moved to `tests/integration/` or marked `@pytest.mark.integration` — done
- Keep root guards against real Weaviate/Ollama calls; reconciled with pytest-socket to avoid duplicate/confusing messages — done

- Verify: a unit test attempting `httpx.get("http://example.com")` fails with a clear error — `tests/unit/test_network_block_httpx_unit.py` covers this; passes in isolation and in suite.

- Unit networking flake (investigated and resolved)
  - Added per-test logging in `tests/unit/conftest.py` to record socket-blocking status and test `nodeid` — done
  - Added early/late canaries `tests/unit/test__network_canary_first.py` and `tests/unit/test__network_canary_last.py` — added then removed after stability
  - Implemented a fail-fast diagnostic to immediately surface the first victim when sockets were detected enabled — gated via `UNITNETGUARD_FAIL_FAST` and kept as a toggle
  - Bisection and inspection found no offender locally; validated stability with randomized orders; canaries removed and a sentinel test kept

- Fail-fast and localization steps (summary)
  1) Fail-fast diagnostic enabled via env flag; active check asserts `SocketBlockedError`
  2) Bisection with `-k` and randomized order; no offender reproduced locally
  3) Fixture/library inspection; no state leaks identified; continued monitoring strategy adopted
  4) Full suite re-run green; fail-fast left as optional toggle
  5) Cleanup: removed canaries; kept session guard and `allow_network` fixture
  6) Hardening: added sentinel test and `weaviate.connect_to_custom` guard; docs updated

- Follow-up corrections (best-practice alignment)
      - [x] Update unit tests to assert `pytest_socket.SocketBlockedError` explicitly instead of generic `Exception`
      - [x] Reduce `UnitNetGuard` diagnostic log level from WARNING to INFO to avoid noisy test output
- Skeptic checks considered: ensured detection isn’t masked by OS errors; reviewed shared fixtures; verified serial vs. parallel behavior

#### P1 — Stabilization and Finalization
 
- [x] Finalize: Full suite green
  - Action: Run the full suite locally; then update CI if needed.
  - Verify: `.venv/bin/python -m pytest -q -m "not environment" --disable-warnings` passes with 0 failures.

#### P2 — CI pipeline separation and test architecture tasks

- [x] P2.1 — Split test suites and defaults (unit/integration with coverage vs. UI/E2E without coverage)
  - Action: Adjusted `addopts` in `pyproject.toml` to exclude UI/E2E tests by default. Added `pytest` options (`--test-core`, `--test-ui`) in `tests/conftest.py` to run specific suites.
  - Verify: `pytest --test-core` runs the core suite with coverage. `pytest --test-ui --no-cov` runs the UI suite without coverage.

- [x] P2.2 — Prefer marker selection over runtime skip hooks
  - Action: Added a `pytest_collection_modifyitems` hook in `tests/e2e_streamlit/conftest.py` that raises a `pytest.UsageError` if UI tests are run with coverage enabled. Marked Playwright tests with `@pytest.mark.ui`.
  - Verify: Running UI tests with coverage fails early with a clear error message.

- [x] P2.3 — Simplify logging; drop per-test file handlers
  - Action: Removed `pytest_runtest_setup/teardown/logreport` hooks from `tests/conftest.py`.
  - Verify: Logging now relies entirely on the centralized `log_cli`/`log_file` configuration in `pyproject.toml`.

- [x] P2.4 — Standardize Docker management via pytest-docker
  - Action: Removed the custom `docker_services` and `test_log_file` fixtures from `tests/conftest.py`, relying on the `pytest-docker` plugin.
  - Verify: Integration tests still pass, with service management handled by the plugin.

- [x] P2.5 — Normalize markers and directories
  - Action: Added a `ui` marker and ensured test selection commands work correctly.
  - Verify: `pytest --test-ui` selects only Playwright tests; `pytest --test-core` excludes them.

- [x] P2.6 — Coverage configuration hardening
  - Action: Configured `.coveragerc` and `pyproject.toml` to store coverage data in `reports/coverage/`. The UI test suite guard ensures it is run with `--no-cov`.
  - Verify: `.coverage` files no longer appear in the project root.

 - [x] P2.7 — CI pipeline separation
  - Action: Split CI into two jobs: `tests-core` (coverage) and `tests-ui` (no coverage). Publish coverage from core job only.
  - Verify: CI runs green; core job uploads coverage HTML; Playwright browsers cached for UI job.

- [x] P2.8 — Developer docs and DX commands
  - Action: Updated `docs/DEVELOPMENT.md` and `docs_AI_coder/AI_instructions.md` with new `pytest` options.
  - Verify: Documentation reflects the new testing commands.

 - [x] P2.9 — Optional hardening for unit/fast test suites
    - Post-cleanup follow-ups (keep unit suite fast and deterministic)
      - [x] Make per-test diagnostic fixture a no-op by default
        - Action: Update `tests/unit/conftest.py::_log_socket_block_status` to return immediately unless `UNITNETGUARD_FAIL_FAST=1` is set; avoid doing any socket probe/logging on the default path.
        - Verify: `.venv/bin/python -m pytest -q tests/unit` remains green; wall time improves vs current.
      - [x] Keep fail-fast as an opt-in toggle only
        - Action: Document in `docs_AI_coder/AI_instructions.md` that setting `UNITNETGUARD_FAIL_FAST=1` enables the per-test probe and immediate failure on first detection.
        - Verify: With `UNITNETGUARD_FAIL_FAST=1`, the first victim is reported; without it, suite runs with no per-test probe.
      - Rationale: Best practice with `pytest-socket` is to rely on a session-level block plus targeted opt-in allowances. A default per-test network probe adds overhead and can mask offenders; keeping it behind an env flag provides rapid diagnosis without slowing normal runs.
    - Speed up feedback
      - [x] Add `pytest-xdist` and run fast tests with `-n auto` in CI for quicker PR feedback
        - [x] Add dependency to test extras and local env; verify `pytest -q -n auto tests/unit` passes
        - [x] Update CI workflow to use `-n auto` for the fast/core job
  - Guard against accidental real clients in unit tests
    - [x] Add a unit-scope fixture that monkeypatches `weaviate.connect_to_custom` to raise if called (unless explicitly patched in a test)
    - [x] Verify: a unit test calling real `connect_to_custom` fails; patched tests still pass

### P0 — Must do now (stability, forward-compat, fast feedback)

- **Fix 5 failing tests (network blocking and heavyweight model downloads)**
  - Plan (small, incremental steps)
    - [x] Enable sockets per-test for all non-unit suites (integration, environment, e2e, docker)
      - [x] Action: Add/update autouse fixtures in each suite's `conftest.py` to enable sockets at test start and restore blocking at test end. Update root guard in `tests/conftest.py` to also allow `e2e` (currently allows only integration/slow/docker).
      - [x] Verify: Run a representative test from each suite; confirm no `SocketBlockedError` and real connections are attempted.
    - [x] Use real models in non-unit tests where applicable
      - [x] Action: Ensure integration/environment tests instantiate real `SentenceTransformer`/`CrossEncoder` as written; do not use dummy embedders.
      - [x] Verify: `tests/integration/test_ingest_pipeline.py::{test_ingest_pipeline_loads_and_embeds_data,test_ingest_pipeline_is_idempotent}` now use the real model.
    - [x] Do not skip non-unit tests on missing external components
      - [x] Action: Remove graceful skips everywhere (fixtures and tests). Specifically:
        - [x] Drop skip logic from `tests/integration/test_ingest_pipeline.py::weaviate_client`.
        - [x] Remove Docker pre-check skip from `tests/integration/test_weaviate_integration.py`.
      - [x] Verify: When external components are unavailable, these tests fail, surfacing the issue.
    - [x] Use real external components in non-unit tests
      - [x] Action: Ensure integration/env/e2e/docker tests target real services and models; no dummy stand-ins. Keep only mocks where a test explicitly verifies mocked behavior.
      - [x] Verify: `tests/integration/test_vectorizer_enabled_integration.py` uses live Weaviate; ingestion tests use real `SentenceTransformer`; environment tests download required models. The container lifecycle test should pass when Docker is available; if not available, it should fail clearly.
    - [x] Re-run the 5 previously failing tests
      - [x] Action: `pytest -q` targeted to those tests only.
      - [x] Verify: All five pass; failures should point to missing externals rather than being skipped.

  - **Container lifecycle and network policy corrections (from recent changes)**
    - [x] Align non-unit test behavior with "no graceful skip" policy
      - [x] Action: Update `tests/conftest.py::docker_services` to FAIL if Docker/daemon is unavailable instead of calling `pytest.skip` (only for non-unit suites). Keep the in-container CI guard (`/.dockerenv`) as-is.
      - [x] Verify: Run an integration test with Docker stopped; expect a clear failure explaining Docker is required (not a skip).
    - [x] Enforce teardown in CI; keep-up only for local iterations
      - [x] Action: In CI workflows, set `TEARDOWN_DOCKER=1` (or pass `--teardown-docker`) so the session fixture tears down services. Keep local default as keep-up for fast iterations.
      - [x] Verify: CI logs show `docker compose down -v` after tests; no leftover CI containers/volumes.
    - [x] Document fast-iteration defaults and the wrapper script
      - [x] Action: Add a short section to `docs/DEVELOPMENT.md` describing: default keep-up policy, `--teardown-docker` and env toggles (`KEEP_DOCKER_UP`, `TEARDOWN_DOCKER`), and usage of `scripts/pytest_with_cleanup.sh`.
      - [x] Verify: Follow the doc steps locally to run `scripts/pytest_with_cleanup.sh -m integration` (keeps up by default) and with `--teardown-docker` (cleans up compose and Testcontainers).
    - [x] Ensure sockets are enabled per-suite for all non-unit tests
      - [x] Action: Confirm we have autouse fixtures that temporarily `enable_socket()` in `tests/integration/`, `tests/environment/`, and `tests/e2e/` (added). No suite should rely on global allow-all.
      - [x] Verify: Representative tests in each suite can reach real services without `SocketBlockedError` while unit tests remain blocked by default.

### P8.1 — Socket handling simplification (follow-up)

- [x] Simplify unit-only socket blocking configuration
  - [x] Action: In `tests/unit/conftest.py`, remove the `markexpr` heuristic from `_disable_network_for_unit_tests` (unit scope already limits it to unit tests).
  - [x] Action: Remove stack-based exceptions in `_guard_against_enable_socket_misuse`; keep a simple guard that allows `allow_network` only.
  - [x] Verify: `pytest -q -k network_block_unit` shows unit blocking still enforced; `-m integration` remains green.

- [x] Remove unnecessary socket toggles in non-unit fixtures
  - [x] Action: In `tests/conftest.py::docker_services`, drop temporary `enable_socket()/disable_socket()` — sockets are allowed by default now.
  - [x] Action: Remove no-op network fixtures/comments in `tests/integration/`, `tests/environment/`, and `tests/e2e/` where not needed.
  - [x] Verify: `pytest -q -m integration`, `-m environment`, and E2E single tests still pass locally.

### P3 — Semgrep blocking findings visibility and triage (local)

- Objective: Make blocking findings clearly visible locally and fix at least the top one.
- Plan (small, incremental steps)
   1) Ensure findings are shown even when the scan fails locally
      - [x] Update Semgrep workflow to run the summary step unconditionally (always) while keeping PRs failing on findings in CI
  2) Surface findings in terminal during pre-push
     - [x] Run the pre-push hook and verify the Semgrep findings summary shows rule, file:line, and message
  3) Triage and fix the top finding
     - [x] Identify the most critical/simple-to-fix finding from the summary
     - [x] Implement a minimal, safe fix in code
      - [x] Add/adjust a unit test if applicable — Added timeout assertions for Ollama HTTP calls in `tests/unit/test_ollama_client_unit.py`
  4) Verify locally
     - [x] Re-run pre-push; confirm Semgrep has no blocking findings
       - [BLOCKED: pre-push stops at lint due to protobuf constraint mismatch; Semgrep job run directly reports 0 blocking findings]

### P4 — CI/SAST enforcement

- CodeQL workflow
  - [x] Disable Default CodeQL setup in GitHub repo settings (to avoid advanced-config conflict)
  - [x] Broaden PR trigger (run on all PRs): remove `branches: ["main"]` under `on.pull_request`
  - [x] Validate `analyze@v3` inputs against official docs; if `output` is unsupported, remove it and adjust the local summary step accordingly
  - [x] Keep uploads enabled only on GitHub (skip on forks and under Act), and enforce via branch protection rather than hard-fail
- Semgrep workflow
  - [x] Ensure robust baseline: add a step to unshallow history before scan (`git fetch --prune --unshallow || true`), or fetch base commit for PRs
  - [x] Switch to official Semgrep Docker action; do not run under local act
  - [x] Keep SARIF upload skipped for forked PRs; consider two-job upload pattern if uploads are needed for forks
- Pre-push (local)
  - [x] Make pre-push resilient if `act` is missing: detect and skip with a clear message
  - [x] Add `SKIP_LOCAL_SEC_SCANS=1` guard to optionally skip Semgrep/CodeQL locally when needed
  - [x] Document the guard and prerequisites in `docs/DEVELOPMENT.md`
- Repo protection
  - [x] Configure branch protection to require "Code scanning results / CodeQL" and Semgrep check on PRs