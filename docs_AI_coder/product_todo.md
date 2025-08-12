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

### P0 — Must do now (stability, forward-compat, fast feedback)

#### P0.0a — Validating the Dependency Compatibility and Versions

- Goal: Stabilize on Protobuf 5.x lane, keep sentence-transformers 5.x, and address dependency compatibility to minimize future surprises.
- Proposed Approach: Use `uv` as a diagnostic tool to find compatible pinned versions for `pip`, simplifying requirements management and isolating tooling.

##### Skepticism checks (verify these before implementation)

- [x] Verify that `torch==2.7.x` is officially supported by `sentence-transformers==5.x` on Python 3.12
  - Finding: sentence-transformers 5.x requires Python >=3.9 and Torch >=1.11. Explicit support for `torch==2.7.x` is not yet documented.
  - Action: Continue monitoring sentence-transformers release notes and dependency pins when `torch==2.7.x` becomes generally available. The `uv` sandbox will be crucial for testing this combination.
- [x] Confirm plain pip installs work reliably under WSL2 + act
  - Finding: `pip install -r requirements*.txt` is stable under WSL2/Act.
- [x] Re-check whether Semgrep actually requires opentelemetry by default; prefer containerized Semgrep regardless
  - Finding: opentelemetry dependencies are not strictly required by Semgrep by default.
  - Action: Containerized Semgrep (or an isolated tool venv) is the preferred method to avoid any potential dependency bleed, regardless of whether opentelemetry is pulled directly or transitively.
- [x] Validate whether a single pinned set of `requirements*.txt` suffices across CI, local dev, and Docker; otherwise adopt per-context requirements files
  - Finding: A single pinned set is generally workable.
  - Action: Maintain this approach, but be prepared to introduce context-specific requirements files if divergence becomes unmanageable, especially around compatibility issues.

##### Modified plan steps

The core strategy remains to leverage `uv` for diagnostics and pinning, but the implementation steps are refined to directly address the compatibility challenges, particularly concerning Protobuf, gRPC, and opentelemetry.

1.  **UV diagnostic sandbox for compatibility resolution (primary focus)**
    - [x] Create `tools/uv_sandbox/` with a minimal `pyproject.toml`.
    - [x] Populate `pyproject.toml` with target versions known to be problematic or desired, specifically including:
        - `sentence-transformers==5.x`
        - `torch==2.7.x`
        - A target Protobuf version (>=5.0)
        - A target gRPC version (latest compatible with Protobuf 5.x)
        - If opentelemetry is intended now or later (or is a dependency of a tool like Semgrep), include a compatible version range or specific versions to test their integration with Protobuf 5.x
        - Other direct dependencies (e.g., `langchain`, `weaviate-client`, `streamlit`)
        - Set `requires-python = ">=3.12"`
    - [x] Add `tools/uv_sandbox/run.sh` that performs: `export PIP_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu && uv lock --frozen-lockfile && uv venv --frozen-lockfile && uv sync --locked --frozen-lockfile && uv run python -m pip check && uv tree`

    - Corrections from review (keep minimal and targeted)
        - [x] Update `tools/uv_sandbox/run.sh` to avoid `||` fallbacks by detecting `uv.lock`:
            - If `uv.lock` exists: `uv lock --frozen-lockfile && uv venv --frozen-lockfile && uv sync --locked --frozen-lockfile`
            - Else: `uv lock && uv venv && uv sync --locked`
        - [x] Keep `PIP_EXTRA_INDEX_URL` export at the top and propagate to all uv steps

    - Focused debug plan: UV sandbox script compatibility
        - [x] Capture current failure modes with exact messages:
            - Invalid flags: `--frozen-lockfile` not recognized by `uv lock`/`uv venv`
            - `VIRTUAL_ENV` mismatch warning when root venv is active
            - `pip check` via `uv run` fails due to missing pip in sandbox venv
        - [x] Update `tools/uv_sandbox/run.sh`:
            - Replace frozen-lockfile flags with: `uv lock --check` (if lock exists) and `uv sync --frozen`
            - Unset `VIRTUAL_ENV` before invoking uv to avoid mismatch
            - Use `uv pip check` for dependency validation
            - Export `UV_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu` for CPU-only wheels
        - [x] Re-run the script to produce a stable `uv.lock`; commit it
        - [x] Add `.gitignore` entries to ignore `tools/uv_sandbox/.venv/` (keep `pyproject.toml` and `uv.lock` tracked)
        - [x] Align with original instruction: also export `PIP_EXTRA_INDEX_URL` in `run.sh` (keep `UV_EXTRA_INDEX_URL` too)
    - [x] Prefer supported flags over deprecated patterns: use `uv lock --check` and `uv sync --frozen` (uv has no `--frozen-lockfile`).
    - [x] Add `.gitignore` entries for sandbox venv/artifacts. Keep `pyproject.toml` in VCS.
    - [x] Commit `uv.lock` from a successful sandbox run. This `uv.lock` will represent the resolved, compatible set of versions. Document any version restrictions or specific package combinations that were necessary to achieve compatibility (e.g., "Protobuf 5.x requires gRPC X.Y and is incompatible with OTel Z.W").
      - Notes:
        - Tooling: `uv 0.8.9`
        - Key resolved versions: `protobuf==5.29.5`, `grpcio==1.63.0`, `torch==2.7.1` (CPU), `sentence-transformers==5.0.0`, `weaviate-client==4.16.6`, `langchain==0.3.27`
        - OTel: Not included in sandbox; keep isolated to avoid protobuf lane conflicts until compatibility is confirmed
        - Wheels: CPU-only via `PIP_EXTRA_INDEX_URL`/`UV_EXTRA_INDEX_URL=https://download.pytorch.org/whl/cpu`
2.  **Pin propagation from UV sandbox to pip requirements**
    - [x] Analyze the `uv.lock` and `uv tree` output from the sandbox run. Identify the exact versions for all direct and transitive dependencies that resulted in a clean `pip check` and a coherent dependency graph.
      - Notes: protobuf=5.29.5, grpcio=1.63.0, torch=2.7.1 (CPU), sentence-transformers=5.0.0, weaviate-client=4.16.6, langchain=0.3.27, streamlit=1.47.0
    - [x] Explicitly address compatibility findings:
        - Findings: Protobuf 5.29.5 with gRPC 1.63.0 resolves cleanly alongside torch 2.7.1 and sentence-transformers 5.0.0; `uv pip check` reports compatibility.
        - Decision: Opentelemetry is excluded from the app environment for now to avoid protobuf lane conflicts; revisit when upstream confirms Protobuf ≥5 support.
        - Verification: `weaviate-client==4.16.6` installs and tests pass in integration suite with the chosen gRPC/Protobuf versions.
    - [x] Update `requirements.txt` and `requirements-dev.txt` by manually pinning the resolved versions from the `uv.lock` for direct dependencies. Ensure `requirements.txt` contains the runtime dependencies, and `requirements-dev.txt` includes development tools.
    - [x] Ensure the PyTorch wheel index options (CPU/GPU) are documented, defaulting to CPU for smaller Docker images. Include example env vars and pip flags in `docs/DEVELOPMENT.md`.
    - [x] Document the pip-only policy and the necessity of running `.venv/bin/python -m pip check` after any dependency changes in `docs/DEVELOPMENT.md`.
3.  **CI integration (GitHub Actions + act)**
    - [x] Standardize all installs to use `pip install -r requirements-dev.txt` (for dev/CI environments) and `pip install -r requirements.txt` (for runtime in CI jobs).
    - [x] Ensure the PyTorch CPU index URL is available for jobs that install PyTorch, either via environment variables or direct pip arguments.
    - [x] Add caching keyed by a hash of `requirements.txt` and `requirements-dev.txt`, combined with the Python version and OS. This ensures efficient cache reuse.
    - [x] Isolate Semgrep: Continue using the official Semgrep Docker image for all Semgrep scans in CI. This inherently prevents any opentelemetry or other tooling dependencies from bleeding into the application's Python environment.
    - [x] Opentelemetry strategy: Exclude OTel from app/dev requirements until compatible with Protobuf ≥5. For local act runs, purge stray OTel packages before installation to avoid resolver bleed.
4.  **Docker integration**
    - [x] Utilize multi-stage builds. In the builder stage, use `pip install -r requirements.txt` (and ensure the PyTorch CPU index is provided if PyTorch is installed).
    - [x] Copy only the necessary runtime artifacts (e.g., site-packages, executable scripts) from the builder stage to the final runtime image. This isolation guarantees the runtime environment uses the clean, pinned dependencies.
    - [x] Validate image size and cold-start performance against the current approach.
      - Notes: Image size ~814 MB (compressed size may differ). Streamlit available in runtime (`streamlit --version`), OCR/PDF tools present (`tesseract-ocr`, `poppler-utils`).
5.  **Validation and rollout**
    - [x] Comprehensive dry-run on a branch:
        - Create a fresh virtual environment.
        - Install dependencies using `pip install -r requirements.txt` and `pip install -r requirements-dev.txt`, ensuring the PyTorch CPU index is used.
         - Run `.venv/bin/python -m pip check` to confirm no conflicts.
         - Execute `pytest --test-core` and any other relevant application tests.
         - Specific compatibility checks: Verify the Protobuf and gRPC versions in the installed environment (`pip freeze | grep protobuf`, `pip freeze | grep grpcio`). If opentelemetry was intended or included in dev, check its version and Protobuf/gRPC interaction.
        
        Results (2025-08-12):
         - pip check: OK (No broken requirements found)
         - pytest core: 79 passed, 1 skipped, 9 deselected, 1 xpassed in ~52s
         - Versions: `protobuf==5.29.5`, `grpcio==1.63.0`, `torch==2.7.1+cpu`, `sentence-transformers==5.0.0`

    - [x] Validate Docker build: Build the Docker image and run a minimal end-to-end smoke test to ensure the application functions correctly within the container.
        
        Results (2025-08-12):
         - Image built: `kri-local-rag:local`
         - Smoke test inside container: `torch 2.7.1+cpu cuda False`, `protobuf 5.29.5`, `grpcio 1.63.0`
    - [x] Merge in stages:
        - Stage 1: Documentation updates (`docs/DEVELOPMENT.md`).
        - Stage 2: CI changes (caching, installation standardization, Semgrep isolation enforcement).
        - Stage 3: Dockerfile changes.
6.  **Automation and upgrades**
    - [x] Configure Renovate to manage `requirements*.txt`.
      - Config: `renovate.json` at repo root; manages `requirements*.txt` and GitHub Actions, scheduled weekly.
    - [ ] For larger upgrades (e.g., major versions of Protobuf, gRPC, sentence-transformers, or if `torch==2.7.x` is released and needs integration): Re-run the `uv` diagnostic sandbox first. Explore compatible version sets within the sandbox before updating the pins in `requirements*.txt`.
    - [x] Ensure CI runs all tests on dependency bump PRs generated by Renovate, blocking merges on failures.
      - CI: `pull_request` runs lint and fast tests for all PRs (including Renovate). Block merges via branch protection requiring these checks.
7.  **Compatibility monitors and guardrails (integrate into workflow)**
    - [ ] Active monitoring: Actively track the status of `opentelemetry-proto` support for Protobuf ≥5. If opentelemetry becomes a requirement later, and compatibility is confirmed, update the sandbox and re-pin. Until then, strictly avoid including opentelemetry in the application's main environment.
    - [ ] Weaviate-client integration: Confirm the tested version range for gRPC compatibility with the current Weaviate server version used. Add specific integration tests that target gRPC paths within the application if not already present.
    - [ ] Rollback strategy: Define clear rollback procedures. If updates introduced regressions, revert the pins in `requirements*.txt` and iterate in the `uv` sandbox to find a stable, compatible set before re-attempting the upgrade.

#### P0.0b — Apply best practices to recent CI/SAST changes

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
  - [ ] Configure branch protection to require "Code scanning results / CodeQL" and Semgrep check on PRs

#### P0.0d — ignoring call-arg ?
     - [ ] in all my code, go through the lines containing # type: ignore[call-arg] and check if the code follows best practices. if not, add tasks to correct the code and test it, into product_todo

#### P0.0c — Semgrep blocking findings visibility and triage (local)

- Objective: Make blocking findings clearly visible locally and fix at least the top one.
- Plan (small, incremental steps)
   1) Ensure findings are shown even when the scan fails locally
      - [x] Update Semgrep workflow to run the summary step unconditionally (always) while keeping PRs failing on findings in CI
  2) Surface findings in terminal during pre-push
     - [x] Run the pre-push hook and verify the Semgrep findings summary shows rule, file:line, and message
  3) Triage and fix the top finding
     - [x] Identify the most critical/simple-to-fix finding from the summary
     - [x] Implement a minimal, safe fix in code
     - [ ] Add/adjust a unit test if applicable
  4) Verify locally
     - [ ] Re-run pre-push; confirm Semgrep has no blocking findings
       - [BLOCKED: pre-push stops at lint due to protobuf constraint mismatch; Semgrep job run directly reports 0 blocking findings]

#### P0.1 — Test Suite Architecture Refactor (align with best practices)

- [x] P0.1.1 — Split test suites and defaults (unit/integration with coverage vs. UI/E2E without coverage)
  - Action: Adjusted `addopts` in `pyproject.toml` to exclude UI/E2E tests by default. Added `pytest` options (`--test-core`, `--test-ui`) in `tests/conftest.py` to run specific suites.
  - Verify: `pytest --test-core` runs the core suite with coverage. `pytest --test-ui --no-cov` runs the UI suite without coverage.

- [x] P0.1.2 — Prefer marker selection over runtime skip hooks
  - Action: Added a `pytest_collection_modifyitems` hook in `tests/e2e_streamlit/conftest.py` that raises a `pytest.UsageError` if UI tests are run with coverage enabled. Marked Playwright tests with `@pytest.mark.ui`.
  - Verify: Running UI tests with coverage fails early with a clear error message.

- [x] P0.1.3 — Simplify logging; drop per-test file handlers
  - Action: Removed `pytest_runtest_setup/teardown/logreport` hooks from `tests/conftest.py`.
  - Verify: Logging now relies entirely on the centralized `log_cli`/`log_file` configuration in `pyproject.toml`.

- [x] P0.1.4 — Standardize Docker management via pytest-docker
  - Action: Removed the custom `docker_services` and `test_log_file` fixtures from `tests/conftest.py`, relying on the `pytest-docker` plugin.
  - Verify: Integration tests still pass, with service management handled by the plugin.

- [x] P0.1.5 — Normalize markers and directories
  - Action: Added a `ui` marker and ensured test selection commands work correctly.
  - Verify: `pytest --test-ui` selects only Playwright tests; `pytest --test-core` excludes them.

- [x] P0.1.6 — Coverage configuration hardening
  - Action: Configured `.coveragerc` and `pyproject.toml` to store coverage data in `reports/coverage/`. The UI test suite guard ensures it is run with `--no-cov`.
  - Verify: `.coverage` files no longer appear in the project root.

- [ ] P0.1.7 — CI pipeline separation
  - Action: Split CI into two jobs: `tests-core` (coverage) and `tests-ui` (no coverage). Publish coverage from core job only.
  - Verify: CI runs green; core job uploads coverage HTML; Playwright browsers cached for UI job.

- [x] P0.1.8 — Developer docs and DX commands
  - Action: Updated `docs/DEVELOPMENT.md` and `docs_AI_coder/AI_instructions.md` with new `pytest` options.
  - Verify: Documentation reflects the new testing commands.


- [ ] P0.1.9 — Optional hardening for unit/fast test suites
  - Enforce no-network in unit tests
    - [ ] Add `pytest-socket` to `requirements-dev.txt` and document usage
    - [ ] Add an `autouse=True` fixture scoped to unit tests to call `disable_socket()` (allow Unix sockets if needed)
    - [ ] Verify: a unit test that attempts `httpx.get("http://example.com")` fails with a clear error
  - Tighten fast selection
    - [ ] Update `tests/conftest.py` so `--test-core` also excludes `slow` (in addition to `ui`, `e2e`, `docker`, `environment`, `integration`)
    - [ ] Align `fast_tests` job to use `--test-core` (or equivalent `-m` expression) and verify it does not start Docker/services under `act`
  - Speed up feedback
    - [ ] Optionally add `pytest-xdist` and run fast tests with `-n auto` in CI for quicker PR feedback
  - Guard against accidental real clients in unit tests
    - [ ] Add a unit-scope fixture that monkeypatches `weaviate.connect_to_custom` to raise if called (unless explicitly patched in a test)
    - [ ] Verify: a unit test calling real `connect_to_custom` fails; patched tests still pass

#### P0.2 — E2E Tasks (CLI and Streamlit)

  - [ ] Streamlit E2E: Improve locator resilience (only if still flaky)
    - Action: Switch input selection to `get_by_label("Ask a question:")`, keep `[data-testid]` for answers, and if needed add `page.wait_for_function` to await `TEST_ANSWER` text.
    - Verify: Re-run the single test; expect pass without diagnostic waits.

  - [ ] **Task 1: Isolate and Reproduce the Failure Reliably.**
    - **Goal:** Create a minimal, fast command that reliably demonstrates the failure, so we don't have to run the full 1-minute test suite to verify our fix.
    - **Action:** Use the simplest Playwright test we have (`test_browser_launch_only.py`) and run it with `pytest-cov` enabled.
    - **Verify:** Confirm this single test fails with the known `AttributeError`. Then, run it with `--no-cov` and confirm it passes. This gives us a clear baseline.

  - [ ] **Task 2: Implement a Conditional Skip.**
    - **Goal:** Since telling coverage to *ignore* the Playwright tests isn't working, we will instead tell `pytest` to *not run* the Playwright tests if and only if the coverage plugin is active.
    - **Action:** I will create a `conftest.py` file within the `tests/e2e_streamlit` directory. Inside this file, I will add a `pytest_collection_modifyitems` hook that programmatically adds a "skip" marker to all Playwright tests if it detects that `pytest-cov` is running.
    - **Verify:** Re-run the failing command from Task 1. The test should now report as `SKIPPED` instead of `ERROR`.

  - [ ] **Task 3: Achieve a "Green" Full Suite Run.**
    - **Goal:** Ensure the main test suite can now run to completion and generate a coverage report without any errors.
    - **Action:** Run the full test suite command (`pytest -m "not environment"`).
    - **Verify:** The command should complete with all tests either passing or being skipped (specifically the Playwright tests). There should be zero errors, and a coverage report should be generated for the rest of the codebase.

  - [ ] **Task 4: Create a Separate, Coverage-Free E2E Test Run.**
    - **Goal:** Make sure our important Playwright E2E tests are still executed somewhere.
    - **Action:** Define a new, separate command that runs *only* the Playwright tests and explicitly disables coverage (`--no-cov`). This command will be used in our CI pipeline and for local E2E checks.
    - **Verify:** Run this new command and confirm that all Playwright tests pass.

#### P0.3 — Stabilization and Finalization
  

- [ ] Finalize P0: Full suite green
  - Action: Run the full suite locally; then update CI if needed.
  - Verify: `.venv/bin/python -m pytest -q -m "not environment" --disable-warnings` passes with 0 failures.


### P1.1 other tasks
- (archived) See `docs_AI_coder/archived-tasks.md`

### P1.2 — Next up (maintainability, observability)
- [ ] Refactor Weaviate connection logic into a single reusable function.
- [ ] Replace fragile relative paths with robust absolute paths where appropriate.
- [ ] Configure centralized file logging (e.g., `logs/app.log`) across CLI and services.
- [ ] Enhance progress logging for long-running ingestion (progress bar or granular steps).

### P2 — Soon (quality, CI structure, performance)
- [ ] Expand unit test coverage, focusing on core logic and error paths.
- [ ] Improve test assertions and edge case testing across existing tests.
- [ ] Implement test data management fixtures for consistent, reliable tests.
- [ ] Review all integration tests for isolation and resource cleanup.
- [ ] Improve overall test isolation to ensure tests do not interfere with each other.
- [ ] Separate test jobs by type in GitHub Actions and update workflow/service deps.
- [ ] Add test quality gates (coverage thresholds, basic performance checks).
- [ ] Add performance benchmarks for critical paths (embedding generation, retrieval).
- [ ] Add further test categories/organization (logic, utils, mocks, etc.).

### P3 — Later (docs, standards, templates, metrics)
- [ ] Update `DEVELOPMENT.md` with dependency management guidelines.
- [ ] Document logging and monitoring strategy in `DEVELOPMENT.md`.
- [ ] Create testing standards document.
- [ ] Add test templates for consistency and performance benchmarking.
- [ ] Improve test documentation and add test quality metrics tracking over time.

### P0 — Corrections from best-practice review (this session)

- [x] Docker wheel index scoping
  - Action: Keep `TORCH_WHEEL_INDEX` only as a build-arg and avoid persisting `PIP_EXTRA_INDEX_URL` in the final image. Ensures build-only knobs do not leak to runtime.
  - Status: Done (builder keeps `ARG TORCH_WHEEL_INDEX`; final stage no longer sets `PIP_EXTRA_INDEX_URL`).

- [x] Make wheels guidance concise
  - Action: Replace verbose wheel instructions with short, variable-based snippets for Docker and local venv.
  - Status: Done in `docs/DEVELOPMENT.md`.