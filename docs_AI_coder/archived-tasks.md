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



## Archived on 2025-08-12

### P0.0a — Validating the Dependency Compatibility and Versions (completed subgroups)

#### Skepticism checks
- Verify `torch==2.7.x` support with `sentence-transformers==5.x` on Python 3.12 — monitored; unresolved in docs but sandbox OK.
- Confirm plain pip installs under WSL2 + act — stable.
- Re-check Semgrep opentelemetry requirement — not required by default; keep Semgrep containerized.
- Validate one pinned set of `requirements*.txt` across contexts — workable; remain flexible if divergence appears.

#### Modified plan steps
1) UV diagnostic sandbox for compatibility resolution
   - `tools/uv_sandbox/pyproject.toml` created with target versions; `run.sh` added and later corrected to use `uv lock --check` and `uv sync --frozen`, unset `VIRTUAL_ENV`, and use CPU wheels via `PIP_EXTRA_INDEX_URL`/`UV_EXTRA_INDEX_URL`.
   - Stable `uv.lock` committed. Notes: `protobuf==5.29.5`, `grpcio==1.63.0`, `torch==2.7.1` (CPU), `sentence-transformers==5.0.0`, `weaviate-client==4.16.6`, `langchain==0.3.27`. OTel excluded.

2) Pin propagation to pip requirements
   - Analyzed `uv.lock`/`uv tree`; propagated direct pins to `requirements*.txt`.
   - Verified with `pip check`; core tests pass.

3) CI integration (GitHub Actions + act)
   - Standardized installs from `requirements*.txt`, ensured CPU torch wheel index available, added caching, isolated Semgrep, excluded OTel until compatible.

4) Docker integration
   - Multi-stage build using `requirements.txt`; copied only runtime artifacts; validated image size and cold-start.

5) Validation and rollout
   - Dry-run results: pip check OK; core tests: 79 passed, 1 skipped, 9 deselected, 1 xpassed; versions: protobuf 5.29.5, grpcio 1.63.0, torch 2.7.1+cpu, sentence-transformers 5.0.0.
   - Docker smoke: torch 2.7.1+cpu cuda False; protobuf 5.29.5; grpcio 1.63.0.

6) Automation and upgrades
   - Renovate configured for `requirements*.txt` and actions; added concise UV/upgrade guidance to `docs/DEVELOPMENT.md` and `.cursor/rules/uv-sandbox.mdc`.

### P0.0d — ignoring call-arg ?

- Replace `# type: ignore[call-arg]` in `backend/ingest.py` with a typed helper
  - Change: Introduced `backend/vector_utils.py` with `to_float_list()` and updated `backend/ingest.py` to use it.
  - Verify: Lints clean; embedding conversion uses explicit typing without ignores.
- Audit remaining vector conversions and remove ignores where possible
  - Targets:
    - `backend/retriever.py`: Refactored to use `to_float_list` and removed ignore.
    - Tests under `tests/integration/test_vectorizer_enabled_integration.py` use `# type: ignore[attr-defined]` for `.tolist()`; consider using `to_float_list` or dedicated test helpers for clarity.

### P0 — Corrections from best-practice review (this session)

- Docker wheel index scoping
  - Action: Keep `TORCH_WHEEL_INDEX` only as a build-arg and avoid persisting `PIP_EXTRA_INDEX_URL` in the final image. Ensures build-only knobs do not leak to runtime.
  - Status: Done (builder keeps `ARG TORCH_WHEEL_INDEX`; final stage no longer sets `PIP_EXTRA_INDEX_URL`).

- Make wheels guidance concise
  - Action: Replace verbose wheel instructions with short, variable-based snippets for Docker and local venv.
  - Status: Done in `docs/DEVELOPMENT.md`.
 
- Vector conversion helper clarity and robustness
  - Action: Refine `backend/vector_utils.py::to_float_list` to:
    - Prefer straightforward `torch is not None and isinstance(x, torch.Tensor)`/`isinstance(x, np.ndarray)` checks over `locals()` tricks
    - Exclude `str`/`bytes`/`bytearray` from generic `Sequence` handling
    - Handle numeric scalars via `numbers.Real`
  - Verify: Lints clean; `.venv/bin/python -m pytest --test-core` passes.

## Archived on 2025-08-13

### P2.9 — Enforce no-network in unit tests (completed)

- Add `pytest-socket` to `pyproject.toml` test extras and document usage — done
- Add an `autouse=True` session fixture to call `disable_socket(allow_unix_socket=True)` — done
- Replace connection-based self-check in session fixture with a lightweight assert — done
- Drop per-test re-disable once the offender was disproven — done
- Provide `allow_network` opt-in fixture (function scope) for rare cases; ensure any such tests are moved to `tests/integration/` or marked `@pytest.mark.integration` — done
- Keep root guards against real Weaviate/Ollama calls; reconciled with pytest-socket to avoid duplicate/confusing messages — done

- Verify: a unit test attempting `httpx.get("http://example.com")` fails with a clear error — `tests/unit/test_network_block_httpx_unit.py` covers this; passes in isolation and in suite.

- Unit networking flake (investigated and resolved)
  - Added per-test logging in `tests/unit/conftest.py` to record socket-blocking status and test `nodeid` — done
  - Added early/late canaries `tests/unit/test__network_canary_first.py` and `tests/unit/test__network_canary_last.py` — added then removed after stability
  - Implemented a fail-fast diagnostic to immediately surface the first victim when sockets were detected enabled — gated via `UNITNETGUARD_FAIL_FAST` and kept as a toggle
  - Bisection and inspection found no offender locally; validated stability with randomized orders; canaries removed and a sentinel test kept

- Fail-fast and localization steps (summary)
  1) Fail-fast diagnostic enabled via env flag; active check asserts `SocketBlockedError`
  2) Bisection with `-k` and randomized order; no offender reproduced locally
  3) Fixture/library inspection; no state leaks identified; continued monitoring strategy adopted
  4) Full suite re-run green; fail-fast left as optional toggle
  5) Cleanup: removed canaries; kept session guard and `allow_network` fixture
  6) Hardening: added sentinel test and `weaviate.connect_to_custom` guard; docs updated

- Follow-up corrections (best-practice alignment)
      - [x] Update unit tests to assert `pytest_socket.SocketBlockedError` explicitly instead of generic `Exception`
      - [x] Reduce `UnitNetGuard` diagnostic log level from WARNING to INFO to avoid noisy test output
- Skeptic checks considered: ensured detection isn’t masked by OS errors; reviewed shared fixtures; verified serial vs. parallel behavior

#### P1 — Stabilization and Finalization
 
- [x] Finalize: Full suite green
  - Action: Run the full suite locally; then update CI if needed.
  - Verify: `.venv/bin/python -m pytest -q -m "not environment" --disable-warnings` passes with 0 failures.

#### P2 — CI pipeline separation and test architecture tasks

- [x] P2.1 — Split test suites and defaults (unit/integration with coverage vs. UI/E2E without coverage)
  - Action: Adjusted `addopts` in `pyproject.toml` to exclude UI/E2E tests by default. Added `pytest` options (`--test-core`, `--test-ui`) in `tests/conftest.py` to run specific suites.
  - Verify: `pytest --test-core` runs the core suite with coverage. `pytest --test-ui --no-cov` runs the UI suite without coverage.

- [x] P2.2 — Prefer marker selection over runtime skip hooks
  - Action: Added a `pytest_collection_modifyitems` hook in `tests/e2e_streamlit/conftest.py` that raises a `pytest.UsageError` if UI tests are run with coverage enabled. Marked Playwright tests with `@pytest.mark.ui`.
  - Verify: Running UI tests with coverage fails early with a clear error message.

- [x] P2.3 — Simplify logging; drop per-test file handlers
  - Action: Removed `pytest_runtest_setup/teardown/logreport` hooks from `tests/conftest.py`.
  - Verify: Logging now relies entirely on the centralized `log_cli`/`log_file` configuration in `pyproject.toml`.

- [x] P2.4 — Standardize Docker management via pytest-docker
  - Action: Removed the custom `docker_services` and `test_log_file` fixtures from `tests/conftest.py`, relying on the `pytest-docker` plugin.
  - Verify: Integration tests still pass, with service management handled by the plugin.

- [x] P2.5 — Normalize markers and directories
  - Action: Added a `ui` marker and ensured test selection commands work correctly.
  - Verify: `pytest --test-ui` selects only Playwright tests; `pytest --test-core` excludes them.

- [x] P2.6 — Coverage configuration hardening
  - Action: Configured `.coveragerc` and `pyproject.toml` to store coverage data in `reports/coverage/`. The UI test suite guard ensures it is run with `--no-cov`.
  - Verify: `.coverage` files no longer appear in the project root.

 - [x] P2.7 — CI pipeline separation
  - Action: Split CI into two jobs: `tests-core` (coverage) and `tests-ui` (no coverage). Publish coverage from core job only.
  - Verify: CI runs green; core job uploads coverage HTML; Playwright browsers cached for UI job.

- [x] P2.8 — Developer docs and DX commands
  - Action: Updated `docs/DEVELOPMENT.md` and `docs_AI_coder/AI_instructions.md` with new `pytest` options.
  - Verify: Documentation reflects the new testing commands.

 - [x] P2.9 — Optional hardening for unit/fast test suites
    - Post-cleanup follow-ups (keep unit suite fast and deterministic)
      - [x] Make per-test diagnostic fixture a no-op by default
        - Action: Update `tests/unit/conftest.py::_log_socket_block_status` to return immediately unless `UNITNETGUARD_FAIL_FAST=1` is set; avoid doing any socket probe/logging on the default path.
        - Verify: `.venv/bin/python -m pytest -q tests/unit` remains green; wall time improves vs current.
      - [x] Keep fail-fast as an opt-in toggle only
        - Action: Document in `docs_AI_coder/AI_instructions.md` that setting `UNITNETGUARD_FAIL_FAST=1` enables the per-test probe and immediate failure on first detection.
        - Verify: With `UNITNETGUARD_FAIL_FAST=1`, the first victim is reported; without it, suite runs with no per-test probe.
      - Rationale: Best practice with `pytest-socket` is to rely on a session-level block plus targeted opt-in allowances. A default per-test network probe adds overhead and can mask offenders; keeping it behind an env flag provides rapid diagnosis without slowing normal runs.
    - Speed up feedback
      - [x] Add `pytest-xdist` and run fast tests with `-n auto` in CI for quicker PR feedback
        - [x] Add dependency to test extras and local env; verify `pytest -q -n auto tests/unit` passes
        - [x] Update CI workflow to use `-n auto` for the fast/core job
  - Guard against accidental real clients in unit tests
    - [x] Add a unit-scope fixture that monkeypatches `weaviate.connect_to_custom` to raise if called (unless explicitly patched in a test)
    - [x] Verify: a unit test calling real `connect_to_custom` fails; patched tests still pass