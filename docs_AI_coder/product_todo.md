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
   - If blocked, mark the step as `[BLOCKED: <short reason/date>]` in this file and proceed to the smallest independent next step if any; otherwise stop and request help.


## Quick References

- **AI agent cheatsheet and E2E commands**: [`docs_AI_coder/AI_instructions.md`](AI_instructions.md) (sections: "Golden commands" and "AI Agent Hints: Docker startup and E2E tests")
- **Test suites and markers**: [`docs_AI_coder/AI_instructions.md`](AI_instructions.md) (section: "Testing")
- **Human dev quickstart**: [`docs/DEVELOPMENT.md`](../docs/DEVELOPMENT.md)
- **MVP runbook**: [`docs_AI_coder/mvp_deployment.md`](mvp_deployment.md)

## Test Refactoring Status

**Phase 1 Complete**: See [TEST_REFACTORING_SUMMARY.md](TEST_REFACTORING_SUMMARY.md) for details on completed test isolation and classification improvements.

**Current Status**: 
- [x] Unit tests properly isolated (17 tests, ~9s runtime)
- [x] Integration tests properly categorized (13 tests, ~33s runtime)  
- [x] All tests run by default (59 tests, ~21s runtime)
- [x] 58.68% test coverage achieved
- [x] Python testing best practices implemented

## Prioritized Backlog

Reference: See [TEST_REFACTORING_SUMMARY.md](TEST_REFACTORING_SUMMARY.md) for context on completed Phase 1 testing work.

### P0 — Must do now (stability, forward-compat, fast feedback)

**Weaviate API Migration Action Plan:**
**Phase 1: Current State Assessment** ✅ COMPLETED
- [x] Check current Weaviate server version in docker-compose (v1.25.1 - incompatible with v4.16+ client)
- [x] Verify current client version and any existing issues (v4.16.6 - spans breaking changes)
- [x] Test current API patterns to understand what's working vs. deprecated (fallback to deprecated API)

**Phase 2: Incremental Migration** 🔄 IN PROGRESS
- [x] Pin to specific stable version (v4.16.6) in requirements.txt
- [x] Update collection creation to use modern API in backend/ingest.py
- [x] Update integration test to use modern API without fallbacks
- [ ] Test each change before proceeding (pending verification)

**Phase 3: Server Compatibility** 🔄 IN PROGRESS  
- [x] Upgrade Weaviate server from v1.25.1 to v1.32.0 for client compatibility
- [ ] Verify full system functionality (pending full test suite)

**Migration Tasks:**
- [ ] **Weaviate API Migration: Server Upgrade** - Upgrade Weaviate server from v1.25.1 to v1.32.0 in `docker/docker-compose.yml`. **Context**: Current server version is incompatible with weaviate-client v4.16+ (requires v1.23.7+). This explains the API compatibility issues and deprecation warnings. **Approach**: Direct version bump to latest stable to ensure full compatibility.
- [ ] **Weaviate API Migration: Client Version Pinning** - Pin weaviate-client to v4.16.6 in `requirements.txt` (currently `>=4.6,<5`). **Context**: The version range spans breaking changes at v4.16.0, and versions v4.16.0-4.16.3 had "Invalid properties error" bugs. **Approach**: Pin to specific stable version to avoid version drift and known bugs.
- [ ] **Weaviate API Migration: Remove Deprecated Fallbacks** - Update `backend/ingest.py` to use modern `vector_config` API without fallbacks. **Context**: Current code uses deprecated `vectorizer_config` as fallback, causing deprecation warnings. With compatible versions, fallbacks are no longer needed. **Approach**: Remove try/except blocks and use `vector_config=[Configure.Vectors.self_provided()]` directly.
- [ ] **Weaviate API Migration: Update Integration Test** - Update `tests/integration/test_vectorizer_enabled_integration.py` to use modern API without fallbacks. **Context**: Test currently uses deprecated API patterns and fallback logic. **Approach**: Remove fallback logic and use consistent modern API patterns.
- [ ] **Weaviate API Migration: Verify Full System** - Test complete system after migration to ensure no regressions. **Context**: Major version changes could introduce subtle compatibility issues. **Approach**: Run full test suite and verify core functionality (ingestion, retrieval, search).

### P0 other tasks
- [ ] Add CI environment validation (e.g., `pip check`) to prevent dependency conflicts.
- [ ] Add unit test for CLI error handling (assert messages go to `stderr` and exit code is correct).
- [ ] Add unit test verifying startup calls `ensure_model_available`.

### P1 — Next up (maintainability, observability)
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

