# Archived Tasks

This file records tasks that have been completed and moved out of the active TODO backlog.

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


