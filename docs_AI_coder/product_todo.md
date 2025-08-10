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
   - Consider that the step description might be wrong; cross-check code, `README.md`, and `docker/` for the source of truth.
   - Propose 1–3 small, reversible next actions with a clear Verify for each. Apply the smallest change first.
   - After a change, re-run the same Verify command from the failed step. Only then continue.
   - If blocked, mark the step as `[BLOCKED: <short reason/date>]` in this todo file and proceed to the smallest independent next step if any; otherwise stop and request help.


## Quick References

- **AI agent cheatsheet and E2E commands**: [`docs_AI_coder/AI_instructions.md`](AI_instructions.md) (sections: "Golden commands" and "AI Agent Hints: Docker startup and E2E tests")
- **Test suites and markers**: [`docs_AI_coder/AI_instructions.md`](AI_instructions.md) (section: "Testing")
- **Human dev quickstart**: [`docs/DEVELOPMENT.md`](../docs/DEVELOPMENT.md)
- **MVP runbook**: [`docs_AI_coder/mvp_deployment.md`](mvp_deployment.md)

## Test Refactoring Status

**Test Refactoring Complete**: See [TEST_REFACTORING_SUMMARY.md](TEST_REFACTORING_SUMMARY.md) for details on completed test isolation and classification improvements.

**Current Status**: 
- [x] Unit tests properly isolated (17 tests, ~9s runtime)
- [x] Integration tests properly categorized (13 tests, ~33s runtime)  
- [x] All tests run by default (59 tests, ~21s runtime)
- [x] 58.68% test coverage achieved
- [x] Python testing best practices implemented

## Prioritized Backlog

Reference: See [TEST_REFACTORING_SUMMARY.md](TEST_REFACTORING_SUMMARY.md) for context on completed Phase 1 testing work.

### P0 — Must do now (stability, forward-compat, fast feedback)

#### P0.1 — Weaviate API Migration
**Phase 1: Current State Assessment** 🔄 IN PROGRESS
- [x] Check current Weaviate server version in docker-compose — Found: local compose `1.32.0` in `docker/docker-compose.yml`; CI compose `1.25.4` in `docker/docker-compose.ci.yml`
- [x] Verify current client version and any existing issues — `weaviate-client==4.16.6` pinned in `requirements.txt`; known v4.16.0–4.16.3 "Invalid properties" bugs avoided; some code still contains deprecated fallbacks to `vectorizer_config` (to be handled in migration tasks)
- [x] Test current API patterns to understand what's working vs. deprecated — Modern API paths validated via `tests/integration/test_vectorizer_enabled_integration.py`; ingestion (`backend/ingest.py`) uses `vector_config=Configure.Vectors.self_provided()`; deprecated fallbacks still exist in `_test_support.py` and `backend/delete_collection.py` (to be removed in migration tasks)

**Phase 2: Incremental Migration** 🔄 IN PROGRESS
- [x] Pin to specific stable version (v4.16.6) in requirements.txt — Confirmed in `requirements.txt`
- [x] Update collection creation to use modern API in backend/ingest.py — Uses `vector_config=Configure.Vectors.self_provided()`
- [x] Update integration test to use modern API without fallbacks — Confirmed in `tests/integration/test_vectorizer_enabled_integration.py`
- [x] Test each change before proceeding — Targeted integration test passed locally

**Phase 3: Server Compatibility** 🔄 IN PROGRESS  
- [x] Upgrade Weaviate server from v1.25.1 to v1.32.0 for client compatibility — Local compose already at `1.32.0`; CI compose upgraded to `1.32.0`

**Migration Tasks:**
 - [x] **Weaviate API Migration: Server Upgrade** - Upgrade Weaviate server from v1.25.1 to v1.32.0 in `docker/docker-compose.yml` and CI compose. **Context**: Current server version is incompatible with weaviate-client v4.16+ (requires v1.23.7+). **Result**: Local compose already at `1.32.0`; CI compose upgraded to `1.32.0`.
- [x] **Weaviate API Migration: Client Version Pinning** - `weaviate-client==4.16.6` pinned in `requirements.txt`. **Context**: Avoids v4.16.0–4.16.3 "Invalid properties" bugs and version drift.
- [x] **Weaviate API Migration: Remove Deprecated Fallbacks** - Removed `vectorizer_config` fallbacks from `backend/_test_support.py` and `backend/delete_collection.py`; `backend/ingest.py` already uses modern `vector_config` API.
- [x] **Weaviate API Migration: Update Integration Test** - Confirmed `tests/integration/test_vectorizer_enabled_integration.py` uses modern API without fallbacks.
 - [BLOCKED: Streamlit E2E depends on Playwright browser launch — 2025-08-10] **Weaviate API Migration: Verify Full System** - Test complete system after migration to ensure no regressions. **Context**: Major version changes could introduce subtle compatibility issues. **Approach**: Run full test suite and verify core functionality (ingestion, retrieval, search).

#### P0.2 — E2E Tasks (CLI and Streamlit)

- [x] CLI E2E: Interactive mode times out — FIXED
  - Action: Make interactive mode robust to piped stdin and non-TTY. Ensure prompts and phase banners flush immediately; handle EOF by printing `Goodbye!` and exiting. If needed, guard test path with `RAG_TEST_MODE=1` to process one Q then exit.
  - Verify: `.venv/bin/python -m pytest -q tests/e2e/test_cli_script_e2e.py::test_cli_interactive_mode --disable-warnings` passes; `reports/logs/e2e_cli_interactive.out` contains: `PHASE: interactive`, `RAG System CLI - Interactive Mode`, `Mocked answer.`, `Goodbye!`.

- [x] CLI E2E: Single-question mode times out — FIXED
  - Action: Ensure single-question path prints promptly (unbuffered) and exits with code 0. In fake-answer path, print once and exit; avoid waiting for extra input.
  - Verify: `.venv/bin/python -m pytest -q tests/e2e/test_cli_script_e2e.py::test_cli_single_question_mode --disable-warnings` passes; `reports/logs/e2e_cli_single.out` contains: `PHASE: single_question`, `Question: ...`, `Answer: Mocked answer for a single question.`

- [BLOCKED: Playwright browser launch error — 2025-08-10] Streamlit E2E: Fake answer not visible after click
  - Action (app-side): Implemented stable locator (`data-testid='answer'`) and immediate fake-answer render when `RAG_FAKE_ANSWER` is set. `RAG_SKIP_STARTUP_CHECKS=1` honored.
  - Current status: App renders correctly; test now fails earlier due to Playwright browser `launch()` error (inspect/endswith). Environment/tooling issue, not app logic.
  - Verify: After unblocking the Playwright launcher, `.venv/bin/python -m pytest -q tests/e2e_streamlit/test_app_smoke.py::test_interaction_basic --disable-warnings` should find `Answer` and `TEST_ANSWER` within 10s.

  ##### Next steps to unblock Streamlit E2E (Playwright)
  - [x] Ensure Playwright browsers are installed and up-to-date in the test environment; run `python -m playwright install --with-deps` in CI bootstrap.
  - [x] Force headless minimal launch via plugin config or env (e.g., `PLAYWRIGHT_HEADLESS=1`), and disable coverage for Playwright sessions if coverage hooks interfere.
  - [ ] If the inspect-related error persists, pin `pytest-playwright` to a known-good version and/or upgrade `playwright` to the latest compatible.
  - [x] Add a retry wrapper or increase launch timeout for the browser fixture.

#### P0.3 — Stabilization and Finalization
 - [x] Deflake: modest timeout bump after fixes
  - Action: If still flaky under CI load, bump timeouts: CLI tests from 10s → 20s; Playwright `to_be_visible` from 10s → 15s.
  - Verify: All three tests pass reliably across two consecutive runs.

- [ ] Finalize P0: Full suite green
  - Action: Run the full suite locally; then update CI if needed.
  - Verify: `.venv/bin/python -m pytest -q -m "not environment" --disable-warnings` passes with 0 failures.


### P1.1 other tasks
- [x] Add CI environment validation (e.g., `pip check`) to prevent dependency conflicts.
- [ ] Add unit test for CLI error handling (assert messages go to `stderr` and exit code is correct).
- [ ] Add unit test verifying startup calls `ensure_model_available`.

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

