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

#### P0 — Must do now (stability, forward-compat, fast feedback)

Reserved for new urgent topic/tasks

#### P1 — ...

Reserved for new almost-urgent topic/tasks

#### P2 — ...

Reserved for new topic/tasks

#### P3 — ...

Reserved for new topic/tasks

#### P4 — ...

Reserved for new topic/tasks

#### P5 — Pre-push performance optimizations (local DX)

- [x] Switch lint/typecheck to native venv (faster than act)
  - [x] Replace `act ... -j lint` in the pre-push hook with native calls: `.venv/bin/ruff check .` and `.venv/bin/ruff format --check .`
  - [x] Replace `act ... -j pyright` with `.venv/bin/pyright`
  - [x] Keep tests via `act` for parity, or add a native fast path: `.venv/bin/python -m pytest --test-fast --maxfail=1 -q`

- [ ] Add pre-push skip toggles (env-driven)
  - [ ] Support `SKIP_LINT=1`, `SKIP_PYRIGHT=1`, `SKIP_TESTS=1` to selectively skip steps locally
  - [ ] Default heavy scans to opt-in (CodeQL already defaults to skip via `SKIP_LOCAL_SEC_SCANS=1`)

- [ ] Fail-fast for local tests
  - [ ] Update pre-push fast tests invocation to include `--maxfail=1 -q` for quicker feedback on first failure

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

 