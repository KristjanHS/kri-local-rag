## Context: why stabilization comes first

Recent refactors introduced a centralized Weaviate client wrapper and partially migrated call sites and tests to use it. Early unit runs showed multiple failures because:
- Some unit tests still patched `weaviate.connect_to_custom` instead of the new wrapper.
- The unit test guard blocks real Weaviate connections, causing wrapper calls to fail when not patched.
- The wrapper maintains a module-level client cache that can leak between tests without explicit teardown.

To avoid compounding errors, we’ll first stabilize the test environment and mocking strategy (unit-only) before resuming the broader migration (integration/e2e). The stabilization plan below documents the exact order and verifications to regain green tests safely, then the original refactor plan follows.

## Stabilization plan to regain green tests (execute in order)

- [x] 0) Lint and type baseline
  - [x] `.venv/bin/python -m ruff check . --fix && .venv/bin/python -m ruff format .`
  - [x] `.venv/bin/python -m pyright .`

- [x] 1) Stabilize unit tests first
  - [x] In `tests/unit/conftest.py`, return a fake Weaviate client by default for unit tests; fake supports `collections.get().query.hybrid(...)`, `collections.exists(...)`.
  - [x] Add an autouse fixture to call `close_weaviate_client()` before/after each unit test to clear wrapper cache.
  - [x] Verify:
    - [x] `.venv/bin/python -m pytest tests/unit/test_search_logic.py -q`
    - [x] `.venv/bin/python -m pytest tests/unit -q`

- [x] 2) Ensure all unit tests patch the wrapper
  - [x] Sweep unit tests for `weaviate.connect_to_custom` patches; replace with `backend.weaviate_client.get_weaviate_client`.
  - [x] Verify: `.venv/bin/python -m pytest tests/unit -q`

- [x] 4) Simplify URL resolution in wrapper
  - [x] Use `backend.config.get_service_url("weaviate")` in `backend/weaviate_client.py`; removed bespoke hostname normalization helper.
  - [x] Replaced normalization test with minimal config test: `tests/unit/test_config_get_service_url_unit.py` (asserts default and env override behavior; no network).
  - [x] Verified: `.venv/bin/python -m ruff check . --fix && .venv/bin/python -m ruff format .`, `.venv/bin/python -m pyright .`, `.venv/bin/python -m pytest tests/unit/test_config_get_service_url_unit.py -q`

- [ ] 5) Bring integration tests back (light set)
  - [ ] Replace any remaining direct client creations in integration fixtures with `get_weaviate_client()` and ensure teardown calls `close_weaviate_client()`.
  - [ ] Verify: `.venv/bin/python -m pytest tests/integration -q -m 'not slow'`

- [ ] 6) Run e2e tests
  - [ ] Ensure `tests/e2e/*` use the wrapper and close it in teardown.
  - [ ] Verify: `.venv/bin/python -m pytest tests/e2e -q`

- [ ] 7) Cleanups and final checks
  - [ ] Remove `ingest._get_weaviate_url` once wrapper normalization is in place.
  - [ ] Verify:
    - [ ] `.venv/bin/python -m ruff check . --fix && .venv/bin/python -m ruff format .`
    - [ ] `.venv/bin/python -m pyright .`
    - [ ] `.venv/bin/python -m pytest tests/unit -q`
    - [ ] `.venv/bin/python -m pytest tests/integration -q`
    - [ ] `.venv/bin/python -m pytest tests/e2e -q`

## Weaviate wrapper refactor plan (incremental with test checkpoints)

- [ ] 1) Create centralized client wrapper
  - Files: `backend/weaviate_client.py`
  - [x] Add `get_weaviate_client()` and `close_weaviate_client()`
  - [ ] Include hostname normalization for Docker vs local
  - Tests to run:
    - `.venv/bin/python -m ruff check . --fix && .venv/bin/python -m ruff format .`
    - `.venv/bin/python -m pyright .`
    - `.venv/bin/python -m pytest tests/unit/test_weaviate_guard.py -q`

- [ ] 2) Migrate retriever to use wrapper
  - Files: `backend/retriever.py`
  - [x] Replace direct `weaviate.connect_to_custom(...)` with `from backend.weaviate_client import get_weaviate_client` and use it.
  - Update unit tests to mock wrapper instead of direct Weaviate:
    - [x] `tests/unit/test_search_logic.py`: replace `mocker.patch("backend.retriever.weaviate.connect_to_custom")` with `mocker.patch("backend.weaviate_client.get_weaviate_client", return_value=mock_client)`.
    - [x] Remove assertions expecting `client.close()`; wrapper manages lifecycle.
  - Tests to run:
    - `.venv/bin/python -m pytest tests/unit/test_search_logic.py -q`

- [ ] 3) Migrate delete_collection to wrapper
  - Files: `backend/delete_collection.py`
  - [x] Use `get_weaviate_client()` and `close_weaviate_client()`.
  - Tests to run:
    - `.venv/bin/python -m pytest tests/unit/test_weaviate_client_close.py -q`
    - `.venv/bin/python -m pytest tests/unit/test_weaviate_guard.py -q`

- [ ] 4) Migrate ingest helper to wrapper (keep shim)
  - Files: `backend/ingest.py`
  - [x] Make `connect_to_weaviate()` return `get_weaviate_client()` for backward compatibility.
  - [ ] Later cleanup: remove `_get_weaviate_url()` when all call sites are wrapper-based.
  - Tests to run:
    - `.venv/bin/python -m pytest tests/unit/test_ingest_logic.py -q`
    - `.venv/bin/python -m pytest tests/integration/test_ingest_pipeline_compose.py -q -m 'not slow'`

- [ ] 5) Migrate qa_loop readiness to wrapper
  - Files: `backend/qa_loop.py`
  - [x] Replace direct connection with `get_weaviate_client()` and `close_weaviate_client()` in `ensure_weaviate_ready_and_populated()`.
  - Update unit tests to mock wrapper instead of `weaviate.connect_to_custom`:
    - [x] `tests/unit/test_weaviate_client_close.py`: monkeypatch `backend.weaviate_client.get_weaviate_client` to return a fake client; optionally spy on `close_weaviate_client`.
  - Tests to run:
    - `.venv/bin/python -m pytest tests/unit/test_weaviate_client_close.py -q`
    - `.venv/bin/python -m pytest tests/unit/test_debug.py::test_cli_debug_paths -q`

- [ ] 6) Update test safety guard and shared fixtures
  - Files: `tests/conftest.py`
  - [x] Keep guard blocking `weaviate.connect_to_custom` in unit tests; add guard for `backend.weaviate_client.get_weaviate_client`.
  - Update e2e/integration fixtures that create direct clients to use wrapper:
    - [x] `tests/e2e/conftest.py` teardown: use `get_weaviate_client()` and `close_weaviate_client()`.
  - Tests to run:
    - `.venv/bin/python -m pytest tests/unit -q`
    - `.venv/bin/python -m pytest tests/e2e/conftest.py -q` (teardown-only check; may skip if Docker unavailable)

- [ ] 7) Sweep remaining call sites and tests
  - Files: `backend/qa_loop.py` (any missed), `tests/integration/test_weaviate_compose.py`, `tests/integration/conftest.py`, `tests/e2e/*`.
  - Replace direct `weaviate.connect_to_custom` with wrapper usage or adjust mocks to patch wrapper only.
  - Tests to run:
    - `.venv/bin/python -m pytest tests/integration -q -m 'not slow'`
    - `.venv/bin/python -m pytest tests/e2e -q` (optional; requires Docker)

- [ ] 8) Cleanups and hardening
  - Remove now-unused helpers (e.g., `ingest._get_weaviate_url` if fully superseded).
  - Add a reusable fake-client fixture for unit tests to reduce per-test mocking.
  - Final checks:
    - `.venv/bin/python -m ruff check . --fix && .venv/bin/python -m ruff format .`
    - `.venv/bin/python -m pyright .`
    - `.venv/bin/python -m pytest tests/unit -q`
    - `.venv/bin/python -m pytest tests/integration -q -m 'not slow'`

### Notes

- Prefer patching `backend.weaviate_client.get_weaviate_client` in tests rather than patching `weaviate.connect_to_custom` in multiple places.
- If existing tests asserted direct `client.close()` calls, either assert the wrapper `close_weaviate_client()` is invoked, or keep asserting on a fake client’s `closed` flag when the wrapper closes it.

