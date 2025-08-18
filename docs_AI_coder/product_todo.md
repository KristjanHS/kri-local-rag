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

#### P0 — Migrate Integration Tests to Target Approach (Solve P4 MagicMock Detection)

- **Why**: Integration tests currently use `@patch` decorators that can leak MagicMock instances into normal app usage, causing the P4 torch.compile optimization issue. Migrating to pytest-native fixtures will provide better isolation and solve the MagicMock detection problem.

- **Context**: Current integration tests in `tests/integration/` use `unittest.mock.patch` decorators that patch module-level functions like `backend.retriever._get_embedding_model`. These patches can persist beyond test boundaries and cause MagicMock instances to leak into the `_embedding_model` cache, triggering the "Skipping torch.compile optimization (tests or MagicMock instance)" debug message during normal app usage.

- **Target Approach**: Follow the testing strategy document's recommendation to use pytest-native fixtures instead of `@patch` decorators for better test isolation and state management.

- [x] **Task 0 — Run Linters and Type Checkers**
  - **Action**: Run `pyright` and `ruff` to ensure the current codebase passes static analysis checks before making changes. This establishes a clean baseline.
  - **Verify**: The commands `pyright` and `ruff check .` complete without reporting any errors.

- [x] **Task 1 — Run Integration Tests to Confirm Current Failures**
  - **Action**: Run the integration test suite using `bash scripts/test_integration.sh`.
  - **Verify**: Observe the specific test failures related to the `MagicMock` detection or other issues that the migration is intended to solve. This confirms the problem exists before attempting a fix.

- [x] **Task 2 — Create managed_embedding_model Fixture**
  - **Action**: Add a `managed_embedding_model` fixture to `tests/integration/conftest.py` similar to the `managed_cross_encoder` fixture in unit tests.
  - **Action**: The fixture should mock `backend.retriever._get_embedding_model` and return a MagicMock instance with proper cleanup.
  - **Verify**: The fixture works correctly and provides the same functionality as the current `@patch` decorators.

- [x] **Task 3 — Migrate test_startup_validation_integration.py**
  - **Action**: Replace `@patch("backend.retriever._get_embedding_model")` decorators with the new `managed_embedding_model` fixture.
  - **Action**: Update test methods to use the fixture parameter instead of the patched mock.
  - **Verify**: All tests in this file pass with the new fixture approach.

- [x] **Task 4 — Migrate test_qa_pipeline.py**
  - **Action**: Replace `@patch("backend.qa_loop.generate_response")` and `@patch("backend.qa_loop.get_top_k")` decorators with appropriate fixtures.
  - **Action**: Create a `managed_qa_functions` fixture if needed for multiple QA-related mocks.
  - **Verify**: All tests in this file pass with the new fixture approach.

- [x] **Task 5 — Migrate test_answer_streaming_integration.py**
  - **Action**: Replace the `@patch` decorators with appropriate fixtures.
  - **Action**: Ensure streaming functionality is properly mocked.
  - **Verify**: All tests in this file pass with the new fixture approach.

- [x] **Task 6 — Migrate test_ingest_pipeline.py**
  - **Action**: Replace `@patch("backend.ingest.get_embedding_model")` with the `managed_embedding_model` fixture.
  - **Action**: Update test logic to work with the fixture approach.
  - **Verify**: All tests in this file pass with the new fixture approach.

- [x] **Task 7 — Migrate test_qa_real_ollama.py**
  - **Action**: Replace `@patch("backend.qa_loop.get_top_k")` with appropriate fixture.
  - **Verify**: All tests in this file pass with the new fixture approach.

- [x] **Task 8 — Verify P4 Problem Resolution**
  - **Action**: Run normal CLI commands (e.g., `./scripts/cli.sh python -m backend.qa_loop --question "test"`) to check if the MagicMock detection debug message still appears.
  - **Action**: Run integration tests to ensure they still pass and don't interfere with normal app usage.
  - **Verify**: The "Skipping torch.compile optimization (tests or MagicMock instance)" debug message no longer appears during normal CLI usage.

- [x] **Task 9 — Update Testing Strategy Documentation**
  - **Action**: Update `docs/testing_strategy.md` to reflect that integration tests now follow the target approach.
  - **Action**: Add examples of the new fixture usage for integration tests.
  - **Verify**: Documentation accurately reflects the current testing approach and provides clear guidance for future development.

#### P1 — Refactor Core Logic to Use Dependency Injection

- **Why**: The current application logic relies on global, module-level caches for heavy objects like embedding models. This forces tests to use monkeypatching (`@patch` or fixtures that patch) to isolate components. Refactoring to a Dependency Injection (DI) pattern will make the code more modular, easier to test without patching, and eliminate the root cause of mock leakage issues.
- **Target Approach**: Modify key functions and classes to accept dependencies (like the embedding model or the Weaviate client) as explicit arguments. The application's entry point (e.g., the CLI or UI) will be responsible for creating these objects and "injecting" them into the functions that need them.

- [x] **Task 1 — Refactor `qa_loop.py`**
  - **Action**: Modify the `answer` function to accept `embedding_model` and `cross_encoder` objects as optional arguments.
  - **Action**: Update the CLI entry point to create these models once and pass them into the `qa_loop`.
  - **Verify**: The CLI functionality remains unchanged. Unit and integration tests are updated to pass the models directly instead of using fixtures that patch.

- [x] **Task 2 — Refactor `ingest.py`**
  - **Action**: Modify the `ingest` function to accept the `embedding_model` and `weaviate_client` as arguments.
  - **Action**: Update the `ingest.sh` script and any other callers to create and pass these dependencies.
  - **Verify**: The ingestion process works as before. Tests are updated to inject mock dependencies directly.

- [x] **Task 3 — Remove Patching from Tests**
  - **Action**: With DI in place, review all tests in `tests/integration` and `tests/unit`.
  - **Action**: Remove any remaining `pytest.mark.patch` or `mocker.patch` calls that are no longer necessary. Fixtures should now be used to *create* mock objects, not to patch them into the application's namespace.
  - **Verify**: The test suite passes, and the use of patching is significantly reduced or eliminated.

#### P3 — Containerized CLI E2E copies (Partial Completion) ✅ PARTIALLY COMPLETED

- **Why**: Host-run E2E miss packaging/runtime issues (entrypoint, PATH, env, OS libs). Twins validate the real image without replacing fast host tests.
- **Current Approach**: Used the existing `app` container which can run both Streamlit (web UI) and CLI commands via `docker compose exec app`. This leveraged the project's existing architecture where the `app` service is designed to handle multiple entry points.
- **Key Insight**: The project already supports CLI commands in the app container (see README.md: `./scripts/cli.sh python -m backend.qa_loop --question "What is in my docs?"`). This pattern was extended for automated testing rather than creating a separate `cli` service.
- **Benefits**: Simpler architecture, fewer services to maintain, aligns with existing project patterns, and leverages the same container that users interact with.

- [x] **Task: Resolve Flaky Unit Tests with Improved Mocking Strategy** ✅ **COMPLETED**
  - **Overall Problem Description:** The unit tests for the cross-encoder logic in `backend/qa_loop.py` were flaky. Specifically, `test_rerank_cross_encoder_success` and `test_cross_encoder_enables_heavy_optimizations_when_allowed` failed when run as part of the full test suite, but succeeded when run in isolation. This indicated a state leakage problem, where the cached global `_cross_encoder` object was being modified by one test and not properly reset before the next, causing unexpected failures. The current mocking strategy, which relied on `unittest.mock.patch`, was proving difficult to debug and was not robust enough to prevent this state pollution. The goal was to implement a more reliable, `pytest`-native mocking and state management strategy to ensure all unit tests were deterministic and isolated.
  - **Action Plan:**
    1.  **Install `pytest-mock`:** Ensured the `pytest-mock` plugin was included in the project's development dependencies.
        -   **Verify:** The command `.venv/bin/python -m pip show pytest-mock` confirmed the package was installed.
    2.  **Create a `managed_cross_encoder` Fixture:** In `tests/unit/conftest.py`, created a new `pytest` fixture named `managed_cross_encoder`. This fixture used the `mocker` fixture to patch `backend.qa_loop._get_cross_encoder`. It was function-scoped to ensure cleanup after every test.
        -   **Verify:** The new fixture was available to the test suite without causing errors.
    3.  **Refactor `test_qa_loop_logic.py`:** Updated the failing tests in this file to use the new `managed_cross_encoder` fixture instead of the `@patch` decorator.
        -   **Verify:** The tests in `tests/unit/test_qa_loop_logic.py` passed consistently, both when run in isolation and as part of the full suite.
    4.  **Refactor `test_cross_encoder_optimizations.py`:** Updated this test to use the `managed_cross_encoder` fixture as well, removing any direct patching.
        -   **Verify:** The test in `tests/unit/test_cross_encoder_optimizations.py` passed consistently.
    5.  **Long-Term Consideration (No Immediate Action):** Evaluated the feasibility of refactoring `backend/qa_loop.py` to use dependency injection. This would involve passing the cross-encoder as an explicit argument to the functions that need it, which would make the code more testable and reduce the need for mocking. This is a larger architectural change and should be considered for future development.

- [x] Step 1 — Identify candidates ✅ **COMPLETED**
  - Action: Listed E2E tests invoking CLI in-process (e.g., `backend.qa_loop`) such as `tests/e2e/test_qa_real_end_to_end.py`.
  - Verify: Confirmed they don't already run via container.

- [x] Step 2 — Use existing app container for CLI testing ✅ **COMPLETED**
  - Action: Leveraged the existing `app` service which can run both Streamlit and CLI commands via `docker compose exec`.
  - Verify: `docker compose exec app python -m backend.qa_loop --help` exited 0.

- [x] Step 3 — Test helper ✅ **COMPLETED**
  - Action: In `tests/e2e/conftest.py`, added `run_cli_in_container(args, env=None)` that uses `docker compose exec app ...`, returns `returncode/stdout/stderr`.
  - Verify: `--help` smoke passed.

- [x] Step 3.1 — Review and validate implementation ✅ **COMPLETED**
  - Action: Reviewed the implementation against best practices and simplified to use existing app container.
  - Verify: Confirmed that the simplified approach was correct and aligned with project structure.

- [x] Step 3.2 — Clean up old complexity ✅ **COMPLETED**
  - Action: Removed the separate `cli` service from `docker/docker-compose.yml` since we're using the existing `app` container.
  - Action: Updated `run_cli_in_container` fixture in `tests/e2e/conftest.py` to use `docker compose exec app`
- [x] Step 4 — Readiness and URLs ✅ **COMPLETED**
  - Action: Used existing `weaviate_compose_up`/`ollama_compose_up`; ensured ingestion uses compose-internal URLs.
  - Verify: Readiness checks passed before CLI twin runs.

- [x] Step 5 — Create test twins ✅ **COMPLETED**
  - Action: Added `_container_e2e.py` twins that call `run_cli_in_container([...])` with equivalent CLI subcommands; optionally marked with `@pytest.mark.docker`.
  - Verify: Single twin passed via `.venv/bin/python -m pytest -q tests/e2e/test_qa_real_end_to_end_container_e2e.py` after compose `--wait`.

- [ ] Step 6 — Build outside tests (PENDING)
  - Action: Ensure scripts/CI build `kri-local-rag-app` once; helper should raise `pytest.UsageError` if image missing.
  - Verify: Second run is faster due to image reuse.

- [ ] Step 7 — Diagnostics and isolation (PENDING)
  - Action: On failure, print exit code, last 200 lines of app logs, and tails of `weaviate`/`ollama` logs; use ephemeral dirs/volumes.
  - Verify: Failures are actionable; runs are deterministic and isolated.

- [ ] Step 8 — Wire into scripts/docs/CI (PENDING)
  - Action: Document commands in `docs/DEVELOPMENT.md` and `AI_instructions.md`; mention in `scripts/test.sh e2e` help; add a CI job for the containerized CLI subset.
  - Verify: Fresh env runs `tests/e2e/*_container_e2e.py` green; CI job passes locally under `act` and on hosted runners.

#### P4 — Align Testcontainer Weaviate Version with Docker Compose
- **Why**: An integration test (`test_weaviate_integration.py`) uses the `testcontainers` library, which defaults to an older Weaviate version (`1.24.5`) than the one specified in `docker-compose.yml` (`1.32.0`). This discrepancy can lead to tests passing with an old version but the app failing with the new one, or vice-versa.
- **Best Practice**: Test environments should match the application's environment as closely as possible to ensure test results are reliable.
- **Action**: [ ] Modify `tests/integration/test_weaviate_integration.py` to explicitly configure the `WeaviateContainer` with the same image tag used in `docker/docker-compose.yml`.
- **Verify**: [ ] When the test runs, the logs show it is pulling and starting the correct Weaviate version (`1.32.0`).

#### P5 — E2E retrieval failure: QA test returns no context (Weaviate)

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

#### P6 — Minimalist Scripts Directory Cleanup

- **Goal**: Reorganize the `scripts/` directory for better clarity with minimal effort. Group related scripts into subdirectories. Avoid complex refactoring or new patterns like dispatchers.

- [ ] **Phase 1: Create Grouping Directories and a `common.sh`**
  - Action: Create the new directory structure: `scripts/test/`, `scripts/lint/`, `scripts/docker/`, `scripts/ci/`, `scripts/dev/`.
  - Action: Create a single `scripts/common.sh` file. Initially, it will only contain `set -euo pipefail` and basic color variables for logging.
  - Verify: The new directories and the `common.sh` file exist and are accessible.

#### P7 — Torch.compile Optimization Debugging and Performance

- **Context**: During CLI usage, torch.compile optimization messages appear every time the script runs, and there's a suspicious debug message about "Skipping torch.compile optimization (tests or MagicMock instance)" appearing during normal app usage.

- **Root Cause Analysis**:
  - **torch.compile is not persistent**: Optimizations are lost when Python processes restart (expected behavior)
  - **CLI script starts new process**: Each `./scripts/cli.sh` run creates a fresh Python process, resetting global caches
  - **MagicMock detection issue**: Debug message suggests test-related mocking is active during normal app usage
  - **Environment configuration**: `.env` file had Docker service URLs instead of localhost URLs for local development

- **Current Status**: 
  - ✅ Fixed `.env` configuration (localhost URLs for local CLI, Docker service URLs for containers)
  - ✅ Reduced torch.compile verbosity to DEBUG level in `qa_loop.py`
  - ✅ Added re-compilation prevention check within same process
  - 🔍 **PENDING**: Investigate why MagicMock detection triggers during normal app usage

- **Key Learnings so far**:
  - torch.compile optimizations are process-local and cannot be persisted across restarts
  - CLI script architecture (new process per run) inherently requires re-optimization
  - Test mocking infrastructure can leak into normal app usage if not properly isolated
  - Environment configuration needs to distinguish between local development and containerized usage

- [ ] **Task 1 — Investigate MagicMock Detection in Normal Usage**
  - **Action**: Add detailed logging to `backend/retriever.py` to trace the exact condition that triggers the "Skipping torch.compile optimization (tests or MagicMock instance)" message.
  - **Action**: Check if any test configuration or environment variables are leaking into normal app usage.
  - **Verify**: The debug message only appears during actual test runs, not during normal CLI usage.

- [ ] **Task 2 — Optimize torch.compile Application Strategy**
  - **Action**: Review if torch.compile should be applied to both embedding model and cross-encoder, or if one is sufficient.
  - **Action**: Consider adding environment variable to control torch.compile application (e.g., `TORCH_COMPILE_ENABLED=false` for development).
  - **Verify**: Performance is maintained while reducing unnecessary re-compilation overhead.

- [ ] **Task 3 — Add Performance Monitoring**
  - **Action**: Add timing measurements around torch.compile operations to quantify the optimization overhead.
  - **Action**: Create a simple benchmark to measure the impact of torch.compile on inference speed.
  - **Verify**: Clear metrics showing the trade-off between compilation time and inference performance.

- [ ] **Task 4 — Improve Error Handling and User Experience**
  - **Action**: Add more informative messages about torch.compile status (e.g., "Model optimization in progress..." with progress indicators).
  - **Action**: Consider caching compiled models to disk if possible to avoid re-compilation across process restarts.
  - **Verify**: Users understand what's happening during model optimization and the process feels responsive.
