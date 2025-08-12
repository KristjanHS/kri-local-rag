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
