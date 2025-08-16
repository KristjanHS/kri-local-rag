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

#### P0a — Epic: Refactor Mocking Strategy and Test Isolation to Follow Best Practices

- **High-Level Goal**: Eliminate the current anti-patterns in mocking and test isolation that cause intermittent failures, complex state management, and maintenance burden. Replace with clean dependency injection and proper test boundaries.

- **Context**: The current test suite uses multiple anti-patterns that violate testing best practices:
  - **Module-level mocking**: `sys.modules["sentence_transformers"] = MagicMock()` pollutes global state
  - **Direct state manipulation**: `retriever._embedding_model = None` depends on implementation details
  - **Complex setup/teardown**: Multiple layers of mocking and state reset create race conditions
  - **Test interference**: Tests fail when run in suite but pass individually due to shared state
  - **Over-engineering**: Multiple redundant mocking strategies for the same functionality

- **Current Anti-Patterns Identified**:
  - **Module-Level Mocking**: Tests mock `sys.modules` before imports, affecting all subsequent tests
  - **Global State Pollution**: Direct manipulation of module-level variables like `_cross_encoder` and `_embedding_model`
  - **Complex Mocking Layers**: Multiple `@patch` decorators and manual state resets for the same functionality
  - **Import Order Dependencies**: Tests must be structured to avoid real imports during collection
  - **Brittle State Management**: Tests manually reset state that could change with implementation

- **Target Architecture**:
  - **Dependency Injection**: Functions accept dependencies as parameters rather than importing them
  - **Clean Test Boundaries**: Each test is isolated and doesn't affect others
  - **Simple Mocking**: Single, clear mocking strategy per test
  - **Behavior Testing**: Tests focus on what functions do, not how they do it
  - **Proper Fixtures**: Reusable, isolated test setup using pytest fixtures

- **Phase 1: Refactor Code to Support Dependency Injection**
  - **Context**: The current code uses lazy imports and global state, making it difficult to test properly. This phase refactors the code to accept dependencies as parameters, enabling clean testing.
  - [ ] **Task 1.1: Refactor `_get_cross_encoder` for Dependency Injection.**
    - Action: Modify `_get_cross_encoder()` in `backend/qa_loop.py` to accept an optional `cross_encoder_constructor` parameter.
    - Action: Update the function to use the injected constructor if provided, otherwise fall back to lazy import.
    - Action: Add type hints and documentation for the new parameter.
    - Verify: The function works identically when called without the parameter, but can accept a mock constructor for testing.
  - [ ] **Task 1.2: Refactor `_get_embedding_model` for Dependency Injection.**
    - Action: Modify `_get_embedding_model()` in `backend/retriever.py` to accept an optional `sentence_transformer_constructor` parameter.
    - Action: Update the function to use the injected constructor if provided, otherwise fall back to lazy import.
    - Action: Add type hints and documentation for the new parameter.
    - Verify: The function works identically when called without the parameter, but can accept a mock constructor for testing.
  - [ ] **Task 1.3: Update Calling Functions to Support Injection.**
    - Action: Modify `_score_chunks()` and `_rerank()` in `backend/qa_loop.py` to accept and pass through the constructor parameter.
    - Action: Modify `get_top_k()` in `backend/retriever.py` to accept and pass through the constructor parameter.
    - Action: Ensure all public APIs maintain backward compatibility.
    - Verify: All existing functionality works unchanged, but functions can now accept injected dependencies.

- **Phase 2: Simplify Test Infrastructure**
  - **Context**: The current test setup is overly complex with multiple mocking layers and state management. This phase simplifies the test infrastructure to use clean, isolated tests.
  - [ ] **Task 2.1: Remove Module-Level Mocking.**
    - Action: Remove all `sys.modules` mocking from test files.
    - Action: Remove module-level `MagicMock()` assignments.
    - Action: Update imports to happen normally without special handling.
    - Verify: Tests can import modules normally without side effects.
  - [ ] **Task 2.2: Create Clean Test Fixtures.**
    - Action: Create `mock_cross_encoder` fixture in `tests/unit/conftest.py` that provides a properly configured mock.
    - Action: Create `mock_sentence_transformer` fixture in `tests/unit/conftest.py` that provides a properly configured mock.
    - Action: Ensure fixtures are isolated and don't affect other tests.
    - Verify: Tests can use these fixtures to get clean, isolated mocks.
  - [ ] **Task 2.3: Simplify Test Classes.**
    - Action: Remove complex `setup_method()` functions that manipulate global state.
    - Action: Remove redundant state reset logic from individual tests.
    - Action: Simplify test methods to focus on behavior testing.
    - Verify: Tests are simpler, more readable, and less prone to interference.

- **Phase 3: Rewrite Tests with Clean Architecture**
  - **Context**: The current tests are complex and brittle due to the anti-patterns. This phase rewrites the tests to use the new dependency injection and clean fixtures.
  - [ ] **Task 3.1: Rewrite QA Loop Tests.**
    - Action: Rewrite `tests/unit/test_qa_loop_logic.py` to use dependency injection instead of complex mocking.
    - Action: Use the `mock_cross_encoder` fixture for tests that need a cross-encoder mock.
    - Action: Focus tests on behavior (e.g., "rerank returns sorted results") rather than implementation details.
    - Action: Remove tests that verify internal state or mocking behavior.
    - Verify: Tests are simpler, more reliable, and test actual functionality.
  - [ ] **Task 3.2: Rewrite Search Logic Tests.**
    - Action: Rewrite `tests/unit/test_search_logic.py` to use dependency injection instead of complex mocking.
    - Action: Use the `mock_sentence_transformer` fixture for tests that need an embedding model mock.
    - Action: Focus tests on behavior (e.g., "search returns relevant results") rather than implementation details.
    - Action: Remove tests that verify internal state or mocking behavior.
    - Verify: Tests are simpler, more reliable, and test actual functionality.
  - [ ] **Task 3.3: Update Integration Tests.**
    - Action: Update integration tests to use the new dependency injection parameters where appropriate.
    - Action: Ensure integration tests still test real functionality with actual models.
    - Action: Remove any complex mocking from integration tests that should use real dependencies.
    - Verify: Integration tests work with both real and mocked dependencies as appropriate.

- **Phase 4: Validation and Cleanup**
  - **Context**: After refactoring, we need to ensure everything works correctly and clean up any remaining anti-patterns.
  - [ ] **Task 4.1: Run Full Test Suite.**
    - Action: Run the entire test suite to ensure no regressions.
    - Action: Verify that tests run consistently (no more "passes individually but fails in suite").
    - Action: Check that test execution time is reasonable.
    - Verify: All tests pass consistently and performance is acceptable.
  - [ ] **Task 4.2: Remove Dead Code and Anti-Patterns.**
    - Action: Remove any remaining module-level mocking code.
    - Action: Remove any remaining direct state manipulation in tests.
    - Action: Clean up any unused imports or variables related to the old mocking strategy.
    - Verify: Codebase is clean and follows best practices.
  - [ ] **Task 4.3: Update Documentation.**
    - Action: Update test documentation to reflect the new clean architecture.
    - Action: Add examples of how to write new tests using the dependency injection pattern.
    - Action: Document the fixtures available for common testing scenarios.
    - Verify: Documentation is clear and helpful for future development.

- **Benefits of This Refactoring**:
  - **Reliability**: Tests will no longer have intermittent failures due to shared state
  - **Maintainability**: Simpler test code that's easier to understand and modify
  - **Performance**: Faster test execution due to reduced setup/teardown complexity
  - **Best Practices**: Code follows established testing patterns and principles
  - **Future-Proof**: New tests can be written easily using the established patterns

#### P0b — Epic: Harden CrossEncoder and Centralize Model Cache

- **High-Level Goal**: Refactor the CrossEncoder integration to be more resilient by removing the scoring fallback logic, and centralize the model cache to be shared between local tests and the containerized application.

- **Context**: The current implementation in `backend/qa_loop.py` has a fallback mechanism in `_score_chunks()` if the 
`CrossEncoder` fails to load or score. This was likely added to handle cases where the model isn't downloaded, especially in 
network-restricted environments like unit tests. The goal is to remove this fallback, making the `CrossEncoder` a hard 
dependency. This requires ensuring it can be loaded reliably without network access during tests (using a local cache) and 
fails explicitly if the model is missing.
- **Project Architecture & CrossEncoder Integration**:
  - **Core Implementation**: `backend/qa_loop.py` - Contains `_get_cross_encoder()`, `_score_chunks()`, and `_rerank()` 
  functions
  - **CrossEncoder Model**: Uses `sentence-transformers.CrossEncoder` with model `"cross-encoder/ms-marco-MiniLM-L-6-v2"` for 
  re-ranking search results
  - **Lazy Loading Pattern**: `CrossEncoder = None` at module level, imported lazily in `_get_cross_encoder()` to avoid 
  startup overhead
  - **Caching Strategy**: `_cross_encoder` global variable caches the instance after first load for performance
  - **Current Fallback Logic**: `_score_chunks()` has 3 strategies: 1) CrossEncoder scoring, 2) Keyword overlap scoring, 3) 
  Neutral scores (0.0) as final fallback
  - **Dependencies**: `sentence-transformers==5.0.0` in `requirements.txt` (required for CrossEncoder functionality)

- **Test Infrastructure & Current Issues**:
  - **Unit Tests**: `tests/unit/test_qa_loop_logic.py` - Contains tests with complex mock context managers for 
  `_get_cross_encoder`
  - **Cross-Encoder Specific Tests**: `tests/unit/test_cross_encoder_optimizations.py` - Tests PyTorch optimizations and model 
  loading
  - **Integration Tests**: `tests/integration/test_cross_encoder_environment.py` - Tests real CrossEncoder loading in various 
  environments
  - **Test Configuration**: `tests/unit/conftest.py` - Disables network access for unit tests (`@pytest.fixture(autouse=True)`)
  - **Global Test Config**: `tests/conftest.py` - Sets up logging and test environment
  - **Environment Variables**: `RERANKER_CROSS_ENCODER_OPTIMIZATIONS=false` in test environment to disable PyTorch 
  optimizations
  - **Current Mock Strategy**: Tests use `patch("backend.qa_loop._get_cross_encoder")` and reset `qa_loop._cross_encoder = 
  None`

- **Related Components & Dependencies**:
  - **Vector Search**: `backend/vector_search.py` - Handles Weaviate queries and chunk retrieval
  - **Chunk Processing**: `backend/chunking.py` - Text chunking and preprocessing
  - **Configuration**: `backend/config.py` - Environment variables and settings
  - **Logging**: `backend/logging_config.py` - Logging setup and configuration
  - **Model Cache**: `~/.cache/huggingface/hub/` - Default location for sentence-transformers model cache
  - **Docker Environment**: `docker/docker-compose.yml` - Container orchestration for Weaviate, Ollama, and app services

- **Current Problem Areas**:
  - **Intermittent Test Failures**: `test_rerank_cross_encoder_success` fails with `AssertionError: assert 0.0 == 0.0` 
  indicating fallback to neutral scores
  - **Mock Complexity**: Complex patching and state management in tests leads to race conditions
  - **Fallback Reliability**: The fallback mechanism sometimes triggers when CrossEncoder should work
  - **Network Dependencies**: Tests require network access for model download, conflicting with network restrictions

- **Target Architecture**:
  - **Single Scoring Path**: Only CrossEncoder scoring, no fallbacks
  - **Explicit Failures**: Clear exceptions when CrossEncoder cannot load or score
  - **Local Model Cache**: Pre-cached models for offline test environments
  - **Simplified Tests**: A clear separation between mocked unit tests and integration tests that use a real `CrossEncoder` 
  instance.
  - **Robust Loading**: Reliable model loading in all environments (dev, test, production)

- **Phase 1: Centralize and Configure the Model Cache**
  - **Context**: The model cache is currently located in `tests/model_cache`, which prevents the Docker container from using it. This phase moves the cache to the project root and configures both the test suite and Docker workflow to use the shared location.
  - [x] **Task 1.1: Relocate `model_cache` to Project Root.**
    - Action: Move the `tests/model_cache` directory to `model_cache` at the project root.
    - Verify: The `model_cache` directory is located at the project root and no longer exists in `tests/`.
  - [x] **Task 1.2: Update `.gitignore` and `.dockerignore`.**
    - Action: Modify the `.gitignore` file to add `model_cache/` to the list of ignored directories, and add a `.gitkeep` file to the directory.
    - Action: Remove `model_cache` from `.dockerignore` to ensure it's included in the build context.
    - Verify: The `model_cache` is ignored by Git but included in the Docker build.
  - [x] **Task 1.3: Reconfigure Scripts and Tests.**
    - Action: Modify `scripts/setup/download_model.py` to use the new root-level `model_cache` path.
    - Action: Update the `cross_encoder_cache_dir` fixture in `tests/conftest.py` to point to the new location.
    - Verify: The download script and tests use the new path.
  - [x] **Task 1.4: Update Dockerfile.**
    - Action: Add a `COPY` instruction to the `Dockerfile` to copy the `model_cache` into the container.
    - Action: Set the `SENTENCE_TRANSFORMERS_HOME` environment variable in the `Dockerfile` to the new cache path.
    - Verify: The container builds successfully and uses the cached model.

- **Phase 2: Refactor CrossEncoder Implementation and Remove Fallback Logic**
  - **Context**: The current implementation in `backend/qa_loop.py` includes a fallback mechanism if the CrossEncoder fails. This phase will remove the fallback, making the CrossEncoder a hard dependency and simplifying the codebase.
  - [x] **Task 2.1: Refactor `qa_loop.py`.**
    - Action: Modify `_score_chunks()` in `backend/qa_loop.py` to remove the keyword-based and neutral-score fallbacks.
    - Action: Ensure that if `_get_cross_encoder()` fails to load the model, it raises a clear `RuntimeError`.
    - Verify: The code in `_score_chunks()` is simpler and contains only the `CrossEncoder` scoring path.
  - [ ] **Task 2.2: Update Tests for New Behavior.**
    - Action: In `tests/unit/test_qa_loop_logic.py`, remove the tests for fallback behavior.
    - Action: Add a new unit test that mocks `_get_cross_encoder` to raise an exception and verifies that `_score_chunks` propagates it.
    - Action: Update the integration test in `tests/integration/test_cross_encoder_environment.py` to confirm it works with the refactored code.
    - Verify: Both unit and integration tests pass after the refactoring.

- **Phase 3: Final Validation**
  - [ ] **Task 3.1: Run Full Test Suite.**
    - Action: Run the entire test suite (unit, integration, e2e) to ensure the refactoring hasn't caused regressions.
    - Verify: All tests pass (`.venv/bin/python -m pytest`).


#### P1 — Containerized CLI E2E copies (keep host-run E2E; add container-run twins)

- **Why**: Host-run E2E miss packaging/runtime issues (entrypoint, PATH, env, OS libs). Twins validate the real image without replacing fast host tests.
- **Current Approach**: Use the existing `app` container which can run both Streamlit (web UI) and CLI commands via `docker compose exec app`. This leverages the project's existing architecture where the `app` service is designed to handle multiple entry points.
- **Key Insight**: The project already supports CLI commands in the app container (see README.md: `./scripts/cli.sh python -m backend.qa_loop --question "What is in my docs?"`). We extend this pattern for automated testing rather than creating a separate `cli` service.
- **Benefits**: Simpler architecture, fewer services to maintain, aligns with existing project patterns, and leverages the same container that users interact with.

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



#### P3 — Minimalist Scripts Directory Cleanup

- **Goal**: Reorganize the `scripts/` directory for better clarity with minimal effort. Group related scripts into subdirectories. Avoid complex refactoring or new patterns like dispatchers.

- [ ] **Phase 1: Create Grouping Directories and a `common.sh`**
  - Action: Create the new directory structure: `scripts/test/`, `scripts/lint/`, `scripts/docker/`, `scripts/ci/`, `scripts/dev/`.
  - Action: Create a single `scripts/common.sh` file. Initially, it will only contain `set -euo pipefail` and basic color variables for logging.
  - Verify: The new directories and the `