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

#### P3 — Containerized CLI E2E copies (Partial Completion) ✅ PARTIALLY COMPLETED

- **Why**: Host-run E2E miss packaging/runtime issues (entrypoint, PATH, env, OS libs). Twins validate the real image without replacing fast host tests.
- **Current Approach**: Used the existing `app` container which can run both Streamlit (web UI) and CLI commands via `docker compose exec app`. This leveraged the project's existing architecture where the `app` service is designed to handle multiple entry points.
- **Key Insight**: The project already supports CLI commands in the app container (see README.md: `./scripts/cli.sh python -m backend.qa_loop --question "What is in my docs?"`). This pattern was extended for automated testing rather than creating a separate `cli` service.
- **Benefits**: Simpler architecture, fewer services to maintain, aligns with existing project patterns, and leverages the same container that users interact with.

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
