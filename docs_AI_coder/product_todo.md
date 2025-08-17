# Product TODO List

This file tracks outstanding tasks and planned improvements for the project.

## Context

- **App**: Local RAG using Weaviate (8080), Ollama (11434), Streamlit UI (8501)
- **Security**: Only Streamlit should be user-visible. Other services should be local-only (loopback or compose-internal)
- **Python execution**: Avoid `PYTHONPATH`; run modules with `python -m` from project root to ensure imports work
- **Environment**: Prefer the project venv (`.venv/bin/python`) or an equivalent Python environment
- **Vectorization**: Uses a local `SentenceTransformer` model for client-side embeddings. Weaviate is configured for manually provided vectors.
- **Reranking**: A separate, local `CrossEncoder` model is used to re-score initial search results for relevance.

## Common Pitfalls and Solutions

### Docker Compose Path Resolution
- **Issue**: `docker compose -f docker/docker-compose.yml` resolves paths relative to compose file location, not working directory
- **Fix**: Use `.env.docker` (not `./docker/.env.docker`) in compose files
- **Verify**: `docker compose -f docker/docker-compose.yml config`

### CI Test Execution Strategy
- **Issue**: Integration and E2E tests require the full Docker stack (Weaviate, Ollama) which cannot run reliably on GitHub CI runners
- **Fix**: Integration and E2E tests are excluded from GitHub CI entirely and only execute locally via act (nektos/act) on manual `workflow_dispatch` or scheduled runs
- **Verify**: Fast tests (unit tests only) run on every PR, while integration/E2E tests run only locally via act

### Task Verification
- **Issue**: File existence ≠ functional working
- **Fix**: Test actual commands that were failing, not just file presence

## Conventions

- **Commands are examples**: Any equivalent approach that achieves the same outcome is acceptable
- **Paths, ports, and model names**: Adapt to your environment as needed
- Each step has Action and Verify. Aim for one change per step to allow quick fix-and-retry.
- On any Verify failure: stop and create a focused debugging plan before proceeding (assume even these TODO instructions may be stale or mistaken). The plan should:
   - Summarize expected vs. actual behavior
   - Re-check key assumptions
   - Consider that the step description might be wrong; cross-check code for the source of truth.
   - Propose 1–3 small, reversible next actions with a clear Verify for each. Apply the smallest change first.
   - After a change, re-run the same Verify command from the failed step. Only then continue.
   - If blocked, mark the step as `[BLOCKED: <short reason/date>]` in this todo file and proceed to the smallest independent next step if any; otherwise stop and request help.

## Quick References

- **AI agent cheatsheet and E2E commands**: [`docs_AI_coder/AI_instructions.md`](AI_instructions.md)
- **Human dev quickstart**: [`docs/DEVELOPMENT.md`](../docs/DEVELOPMENT.md)
- **Archived tasks**: [`docs_AI_coder/archived-tasks.md`](archived-tasks.md)

## Prioritized Backlog

#### P0 — Epic: Refactor Testing Strategy for Robustness and Simplicity

- **High-Level Goal**: Overhaul the testing strategy to align with modern best practices. This involves centralizing the model cache for reliable offline testing, hardening the application's model-loading logic, and replacing fragile, module-level mocks with clean, scoped pytest fixtures.

- **Benefits**:
  - **Simplicity & Readability**: Tests become much easier to read, understand, and maintain.
  - **Reliability**: `monkeypatch` and fixtures provide robust test isolation, preventing tests from interfering with each other.
  - **Robustness**: Application logic is hardened by removing silent fallbacks in favor of explicit, predictable errors.
  - **Maintainability**: Follows standard pytest patterns, making it easier for new developers to contribute.

- **Phase 1: Harden Application Code and Centralize Model Cache**
  - **Context**: Before refactoring the tests, we must ensure the application itself is robust and the testing environment is stable. This involves making the CrossEncoder a hard dependency and ensuring models are cached for offline use.
  - [x] **Task 1.1: Centralize and Configure the Model Cache.**
    - **Action**: Ensure the `model_cache` directory is at the project root, ignored by Git, included in the Docker build context, and copied into the container with the `SENTENCE_TRANSFORMERS_HOME` environment variable correctly set.
    - **Verify**: The command `./scripts/test.sh integration` passes without requiring network access to download models.
  - [x] **Task 1.2: Remove Cross-Encoder Fallback Logic.**
    - **Action**: Modify `_score_chunks()` in `backend/qa_loop.py` to remove the keyword-based and neutral-score fallbacks. If the CrossEncoder model fails to load, the function should raise a clear `RuntimeError`.
    - **Verify**: The code in `_score_chunks()` is simplified, containing only the CrossEncoder scoring path. The test suite will likely have failures that the next phase will address.

- **Phase 2: Refactor Unit Tests with Pytest Fixtures** ✅ **COMPLETED**
  - **Context**: With a hardened application and stable environment, we refactored the unit tests to use modern, simple mocking patterns. This phase replaced all global, stateful mocking with scoped pytest fixtures.
  - **Target Approach**: Modern pytest fixtures (`managed_cross_encoder`, `mock_embedding_model`) are now the preferred method for unit tests.
  - [x] **Task 2.1: Create Mocking Fixtures in `conftest.py`.**
    - **Action**: Created `managed_cross_encoder` fixture that patches `backend.qa_loop._get_cross_encoder` (TARGET APPROACH).
    - **Action**: Created `mock_embedding_model` fixture that patches `backend.retriever.SentenceTransformer` (TARGET APPROACH).
    - **Action**: Created `reset_cross_encoder_cache` autouse fixture for state management.
    - **Verify**: The fixtures are available and working in the test suite.
  - [x] **Task 2.2: Refactor QA Loop Unit Tests.**
    - **Action**: Updated `tests/unit/test_qa_loop_logic.py` to use `managed_cross_encoder` fixture (TARGET APPROACH).
    - **Action**: Removed old setup/teardown logic and manual state manipulation.
    - **Action**: Tests now use modern pytest-native mocking patterns.
    - **Verify**: QA loop unit tests are stable and use the new fixture-based approach.
  - [x] **Task 2.3: Refactor Search Logic Unit Tests.**
    - **Action**: Updated `tests/unit/test_search_logic.py` to use `mock_embedding_model` fixture (TARGET APPROACH).
    - **Action**: Removed manual state manipulation.
    - **Verify**: Search logic unit tests pass using the new fixture-based mocking.

- **Phase 3: Full Suite Validation and Cleanup**
  - **Context**: After refactoring, ensure the entire suite is stable, clean, and that no regressions were introduced.
  - [x] **Task 3.1: Run Full Test Suite.**
    - **Action**: Run the entire test suite, including unit, integration, and E2E tests.
    - **Verify**: All tests pass (`.venv/bin/python -m pytest`).
  - [x] **Task 3.2: Remove Dead Code.**
    - **Action**: Remove any unused imports, variables, or helper functions related to the old mocking strategy from the test files.
    - **Verify**: The test codebase is clean, simpler, and follows a consistent, modern pattern.


#### P1 — Containerized CLI E2E copies (keep host-run E2E; add container-run twins)

- **Why**: Host-run E2E miss packaging/runtime issues (entrypoint, PATH, env, OS libs). Twins validate the real image without replacing fast host tests.
- **Current Approach**: Use the existing `app` container which can run both Streamlit (web UI) and CLI commands via `docker compose exec app`. This leverages the project's existing architecture where the `app` service is designed to handle multiple entry points.
- **Key Insight**: The project already supports CLI commands in the app container (see README.md: `./scripts/cli.sh python -m backend.qa_loop --question "What is in my docs?"`). We extend this pattern for automated testing rather than creating a separate `cli` service.
- **Benefits**: Simpler architecture, fewer services to maintain, aligns with existing project patterns, and leverages the same container that users interact with.

- [x] **Task: Resolve Flaky Unit Tests with Improved Mocking Strategy**
  - **Overall Problem Description:** The unit tests for the cross-encoder logic in `backend/qa_loop.py` are flaky. Specifically, `test_rerank_cross_encoder_success` and `test_cross_encoder_enables_heavy_optimizations_when_allowed` fail when run as part of the full test suite, but succeed when run in isolation. This indicates a state leakage problem, where the cached global `_cross_encoder` object is being modified by one test and not properly reset before the next, causing unexpected failures. The current mocking strategy, which relies on `unittest.mock.patch`, is proving difficult to debug and is not robust enough to prevent this state pollution. The goal is to implement a more reliable, `pytest`-native mocking and state management strategy to ensure all unit tests are deterministic and isolated.
  - **Action Plan:**
    1.  **Install `pytest-mock`:** Ensure the `pytest-mock` plugin is included in the project's development dependencies.
        -   **Verify:** The command `.venv/bin/python -m pip show pytest-mock` confirms the package is installed.
    2.  **Create a `managed_cross_encoder` Fixture:** In `tests/unit/conftest.py`, create a new `pytest` fixture named `managed_cross_encoder`. This fixture will use the `mocker` fixture to patch `backend.qa_loop._get_cross_encoder`. It will be function-scoped to ensure cleanup after every test.
        -   **Verify:** The new fixture is available to the test suite without causing errors.
    3.  **Refactor `test_qa_loop_logic.py`:** Update the failing tests in this file to use the new `managed_cross_encoder` fixture instead of the `@patch` decorator.
        -   **Verify:** The tests in `tests/unit/test_qa_loop_logic.py` pass consistently, both when run in isolation and as part of the full suite.
    4.  **Refactor `test_cross_encoder_optimizations.py`:** Update this test to use the `managed_cross_encoder` fixture as well, removing any direct patching.
        -   **Verify:** The test in `tests/unit/test_cross_encoder_optimizations.py` passes consistently.
    5.  **Long-Term Consideration (No Immediate Action):** Evaluate the feasibility of refactoring `backend/qa_loop.py` to use dependency injection. This would involve passing the cross-encoder as an explicit argument to the functions that need it, which would make the code more testable and reduce the need for mocking. This is a larger architectural change and should be considered for future development.

- [x] Step 1 — Identify candidates
  - Action: List E2E tests invoking CLI in-process (e.g., `backend.qa_loop`) such as `tests/e2e/test_qa_real_end_to_end.py`.
  - Verify: Confirm they don't already run via container.

- [x] Step 2 — Use existing app container for CLI testing
  - Action: Leverage the existing `app` service which can run both Streamlit and CLI commands via `docker compose exec`.
  - Verify: `docker compose exec app python -m backend.qa_loop --help` exits 0.

- [x] Step 3 — Test helper
  - Action: In `tests/e2e/conftest.py`, add `run_cli_in_container(args, env=None)` that uses `docker compose exec app ...`, returns `returncode/stdout/stderr`.
  - Verify: `--help` smoke passes.

- [x] Step 3.1 — Review and validate implementation
  - Action: Review the implementation against best practices and simplify to use existing app container.
  - Verify: Confirm that the simplified approach is correct and aligns with project structure.

- [x] Step 3.2 — Clean up old complexity
  - Action: Remove the separate `cli` service from `docker/docker-compose.yml` since we're using the existing `app` container.
  - Action: Update `run_cli_in_container` fixture in `tests/e2e/conftest.py` to use `docker compose exec app`
- [x] Step 4 — Readiness and URLs
  - Action: Use existing `weaviate_compose_up`/`ollama_compose_up`; ensure ingestion uses compose-internal URLs.
  - Verify: Readiness checks pass before CLI twin runs.

- [x] Step 5 — Create test twins
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

#### P2 — E2E retrieval failure: QA test returns no context (Weaviate)

 - Context and goal
   - Failing test returns no context from Weaviate. Likely mismatch between collection name used by retrieval and the one populated by ingestion, or ingestion not executed.

 - [ ] **Task 1 — Reproduce quickly**
   - **Action**: Run only the failing test to confirm the symptom (e.g., `pytest tests/e2e/test_qa_real_end_to_end.py`).
   - **Verify**: The test fails with an assertion related to empty context, confirming the issue is reproducible.

 - [ ] **Task 2 — Check config and schema**
   - **Action**: Inspect `docker-compose.yml`, `.env` files, and test fixtures to find the `COLLECTION_NAME` being used. Connect to the Weaviate console and list collections.
   - **Verify**: The collection name used in the test exists in Weaviate, and its schema is as expected.

 - [ ] **Task 3 — Confirm data population**
   - **Action**: Add a breakpoint or logging in the ingestion fixture (`tests/e2e/fixtures_ingestion.py`) to confirm it runs. Query the collection in Weaviate to count its objects.
   - **Verify**: The ingestion fixture executes successfully, and the target collection in Weaviate contains more than zero objects.

 - [ ] **Task 4 — Probe retrieval directly**
   - **Action**: Add a temporary test case that directly calls the `retrieve_chunks` function against the populated collection.
   - **Verify**: The direct call to the retriever returns a non-empty list of documents, proving the retrieval logic is functional.

 - [ ] **Task 5 — Standardize collection naming**
   - **Action**: Choose a single collection name for all E2E tests (e.g., `TestCollectionE2E`) and apply it consistently across tests, fixtures, and configurations.
   - **Verify**: A global search for the old collection name in the `tests/` directory yields no results.

 - [ ] **Task 6 — Implement and verify**
   - **Action**: With the standardized name in place, re-run the full E2E test suite.
   - **Verify**: The originally failing QA test now passes successfully.

 - [ ] **Task 7 — Add minimal guardrails**
   - **Action**: In the E2E setup fixture, add a log statement for the collection name being used. Create a new, small test that intentionally queries a non-existent collection.
   - **Verify**: The test logs show the correct collection name, and the new test confirms that querying an empty/non-existent collection returns an empty list rather than crashing.



#### P3 — Minimalist Scripts Directory Cleanup

- **Goal**: Reorganize the `scripts/` directory for better clarity with minimal effort. Group related scripts into subdirectories. Avoid complex refactoring or new patterns like dispatchers.

- [ ] **Phase 1: Create Grouping Directories and a `common.sh`**
  - Action: Create the new directory structure: `scripts/test/`, `scripts/lint/`, `scripts/docker/`, `scripts/ci/`, `scripts/dev/`.
  - Action: Create a single `scripts/common.sh` file. Initially, it will only contain `set -euo pipefail` and basic color variables for logging.
  - Verify: The new directories and the `