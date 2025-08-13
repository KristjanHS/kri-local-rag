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

#### P1 — ...

No tasks here at the moment

#### P2 — ...

No tasks here at the moment

#### P3 — Semgrep blocking findings visibility and triage (local)

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
     - [ ] Re-run pre-push; confirm Semgrep has no blocking findings
       - [BLOCKED: pre-push stops at lint due to protobuf constraint mismatch; Semgrep job run directly reports 0 blocking findings]

#### P4 — CI/SAST enforcement

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

#### P5 — Pre-push performance optimizations (local DX)

- [ ] Switch lint/typecheck to native venv (faster than act)
  - [ ] Replace `act ... -j lint` in the pre-push hook with native calls: `.venv/bin/ruff check .` and `.venv/bin/ruff format --check .`
  - [ ] Replace `act ... -j pyright` with `.venv/bin/pyright`
  - [ ] Keep tests via `act` for parity, or add a native fast path: `.venv/bin/python -m pytest --test-fast --maxfail=1 -q`

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

- [ ] Simplify unit-only socket blocking configuration
  - [ ] Action: In `tests/unit/conftest.py`, remove the `markexpr` heuristic from `_disable_network_for_unit_tests` (unit scope already limits it to unit tests).
  - [ ] Action: Remove stack-based exceptions in `_guard_against_enable_socket_misuse`; keep a simple guard that allows `allow_network` only.
  - [ ] Verify: `pytest -q -k network_block_unit` shows unit blocking still enforced; `-m integration` remains green.

- [ ] Remove unnecessary socket toggles in non-unit fixtures
  - [ ] Action: In `tests/conftest.py::docker_services`, drop temporary `enable_socket()/disable_socket()` — sockets are allowed by default now.
  - [ ] Action: Remove no-op network fixtures/comments in `tests/integration/`, `tests/environment/`, and `tests/e2e/` where not needed.
  - [ ] Verify: `pytest -q -m integration`, `-m environment`, and E2E single tests still pass locally.

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

 