Necessary context: docs/testing_strategy.md, cursor_rules/AI_instructions.md

# Migration Plan: Testcontainers → Compose-only (Minimal, Incremental, Verifiable)

> Goal: remove Testcontainers with **small, reversible steps**, keeping tests reliable via Compose
> healthchecks, startup ordering, isolation, and diagnostics.

# Migration Progress Tracker: Testcontainers → Compose-only

This document tracks the progress of the migration from Testcontainers to a Docker Compose-based testing setup.

## Migration Steps

- [x] **Step 1 — Add Healthchecks to Every Service**
  - **Action**: Add `healthcheck` for `weaviate`, `ollama`, and `app`. Example:
    ```yaml
    services:
      weaviate:
        image: semitechnologies/weaviate:1.32.0
        healthcheck:
          test: ["CMD-SHELL", "wget -q --spider http://localhost:8080/v1/.well-known/ready || exit 1"]
          interval: 5s
          timeout: 3s
          retries: 30
          start_period: 30s
    ```
    Use `depends_on: { <svc>: { condition: service_healthy } }` for any dependent service.
    **Rationale**: Compose can wait on **health** of dependencies; healthchecks define "ready."
  - **Verification**: `docker compose up -d --wait --wait-timeout 120` returns success and `docker ps` shows services as **healthy**.

- [x] **Step 2 — Introduce a Test Overlay File**
  - **Action**: Create `compose.test.yml` for test-specific tweaks (pinned images, ephemeral volumes, fewer exposed ports). Merge with:
    ```bash
    docker compose -f compose.yml -f compose.test.yml config
    ```
    Ensure paths are correct (paths are resolved relative to the **first** `-f` file).
  - **Verification**: `docker compose -f compose.yml -f compose.test.yml config --images` lists the expected tags.

- [x] **Step 3 — Add "Up/Down/Logs" Test Harness Scripts**
  - **Action**: Create tiny scripts (or Make targets):
    - **Up**: `docker compose -f compose.yml -f compose.test.yml -p "$RUN_ID" up -d --wait --wait-timeout 120`
    - **Down**: `docker compose -p "$RUN_ID" down -v`
    - **Logs (on failure)**: `docker compose -p "$RUN_ID" logs -n 200 app weaviate ollama`
    Use a **unique project name** (`-p`) per run to isolate networks/volumes.
  - **Verification**: Running **Up** returns only after services are healthy; **Down** removes volumes; **Logs** show tailed output (-n).

- [x] **Step 4 — Convert One TC Test (The Smallest) to Compose**
  - **Action**: 
    - Remove its Testcontainers fixture.
    - Ensure the test targets the **Compose** services (use service DNS names; avoid host ports for internal deps).
    - For CLI-style tests, run through the **app container**: `docker compose -p "$RUN_ID" exec -T app ./scripts/cli.sh …`
  - **Verification**: ✅ Test passes when run inside the container. Created dedicated test file `tests/integration/test_weaviate_compose.py`.
  - **Improvements Made**:
    - Created dedicated test Dockerfile: `app.test.Dockerfile` for isolated test environment
    - Updated test Compose file: `compose.test.yml` uses the new test Dockerfile
    - Improved Makefile: Enhanced with unique RUN_ID and reliable lifecycle management
    - Added volume mounts: Live code changes without rebuilds
    - Implemented per-Dockerfile ignore: `app.test.Dockerfile.dockerignore` for clean builds

- [x] **Step 5 — Spread Readiness & Race-proofing**
  - **Action**: For any test that previously had "sleep" or fragile waits, rely on:
    - `up --wait` + healthchecks (Step 1/3).
    - If a *first call* can still race (e.g., model warmup), add a tiny retry loop in the test helper.
  - **Verification**: ✅ Tests pass consistently without race conditions. Fixed API compatibility issues in `test_weaviate_compose.py`:
    - Updated Weaviate client API calls (`get_all()` → `list_all()`)
    - Fixed property creation syntax (`dataType` → `data_type`, using `Property` class)
    - Added case-insensitive collection name comparison
    - Tests run reliably with healthchecks and `up --wait`

- [x] **Step 5.5 — Enhance Test Harness Robustness**
  - **Action**: Improve `make test-up` to prevent duplicate test environments:
    - Check if containers are already running with existing RUN_ID before starting new ones
    - Automatically clean up stale `.run_id` files when containers aren't running
    - Provide clear user guidance when containers are already running
  - **Verification**: ✅ Prevents resource conflicts and improves developer experience:
    - No more port binding errors from duplicate environments
    - Intelligent state management handles stale files automatically
    - Clear feedback and guidance for users
    - All existing functionality (`test-down`, `test-logs`) continues to work seamlessly

- [x] **Step 5.6 — Infrastructure Improvements & Optimization**
  - **Action**: Enhanced the Compose-based testing infrastructure with production-ready improvements:
    - **Hash-based rebuild detection**: Uses SHA-256 hash instead of file modification times for more reliable rebuilds
    - **Optimized Docker build**: Removed unnecessary file copying, optimized `.dockerignore`, and proper version pinning
    - **Improved Makefile**: Fixed missing targets, automatic logs directory creation, and COMPOSE variable for DRY principle
    - **Pre-commit compliance**: All checks pass including Hadolint with proper version pinning
    - **Removed redundant files**: Eliminated unnecessary `app.test.Dockerfile.dockerignore`
  - **Verification**: ✅ All infrastructure improvements working correctly:
    - Hash-based rebuild logic detects actual changes and prevents unnecessary rebuilds
    - Docker builds are faster and more reliable
    - All pre-commit checks pass consistently
    - Existing tests continue to work with improved infrastructure

- [🔄] **Step 6 — Batch-Convert the Remaining TC Tests**
  - **Action**: Move the rest of the Testcontainers specs in **small batches** (2–3 at a time):
    - Point them to the Compose services.
    - Remove per-test containers; reuse the single stack from Step 3.
  - **Current Status**: 🔄 **IN PROGRESS** - Testing completed, issues identified:
    - **✅ Working Compose Tests**: 
      - `test_weaviate_compose.py` (2/2 tests pass)
      - `test_vectorizer_enabled_compose.py` (1/1 test pass)
    - **❌ Issues Found in Existing Compose Tests**:
      - `test_ingest_pipeline_compose.py`: Uses `localhost:8080` instead of `weaviate:8080`, NLTK data corruption
      - `test_qa_real_ollama_compose.py`: Uses `localhost:11434` instead of `ollama:11434`
    - **❌ Docker-in-Docker Issues**:
      - `test_backend_import_in_container.py`: Tries to run `docker` commands inside container
      - `test_frontend_requirements_in_container.py`: Tries to run `docker` commands inside container
    - **📋 Remaining Testcontainers Tests to Convert**:
      - `test_qa_real_ollama.py`, `test_cli_output.py`, `test_ml_environment.py`, `test_qa_pipeline.py`
      - `test_startup_validation_integration.py`, `test_answer_streaming_integration.py`, `test_ingest_pipeline.py`
      - `test_cross_encoder_environment.py`, `test_vectorizer_enabled_integration.py`, `test_python_setup.py`
      - `test_weaviate_debug.py`, `test_weaviate_integration.py` (marked for deletion in Step 11)
  - **Next Actions Required**:
    1. Fix connection issues in existing Compose tests (localhost → service names)
    2. Resolve NLTK data issues in `test_ingest_pipeline_compose.py`
    3. Update or remove Docker-in-Docker tests that won't work in Compose
    4. Convert remaining Testcontainers tests in small batches
  - **Verify**: After each batch, run just that batch; keep failures contained and fix before moving on.

- [ ] **Step 7 — Wire CI for Compose-only (Minimal)**
  - **Action**:
    - Keep **unit tests** on every PR.
    - Add a **manual/scheduled** job that runs the Compose test lane with unique `-p` names, `up --wait`, and `down -v`, dumping tailed logs on failure.
  - **Verify**:
    - Local `act` run is green.
    - The scheduled job is green and produces useful logs on failure.

- [ ] **Step 8 — Remove Testcontainers Code & Dependency**
  - **Action**: Delete TC fixtures/helpers and the TC package from `pyproject.toml`/`requirements`.
  - **Verify**: A full test run passes; repo search shows **no** TC imports left.

- [ ] **Step 9 — Lock Parity & Document**
  - **Action**:
    - Pin image **tags** (or output a digest-locked overlay via `config --lock-image-digests`).
    - Add a short **README** note: use `up --wait`, healthchecks, unique `-p`, and `down -v`.
  - **Verify**: New developers can clone → run the scripts → get green tests without extra steps.

- [ ] **Step 10 — (Optional) Modularize Compose**
  - **Action**: If your stack grows, consider Compose **include** (2.20.3+) to split files cleanly, or keep the simple `-f` merge flow you already use.
  - **Verify**: `docker compose config` shows the expected merged model; relative paths remain correct.

- [ ] **Step 11 — Finalize Migration Cleanup**
  - **Action**: Remove obsolete test files and artifacts from the old Testcontainers approach:
    - Delete `tests/integration/test_weaviate_integration.py` (replaced by `test_weaviate_compose.py`)
    - Remove any other obsolete test files that were part of the old approach
  - **Verify**: The test suite runs successfully without any failures related to missing files.

---

### Why these steps work

* **Healthchecks + `depends_on: condition: service_healthy`** express readiness, and **`up --wait`** blocks until services are healthy; this removes most race conditions.
* **Project names (`-p`)** isolate networks/volumes per run—critical when tests run in parallel or on CI.
* **`down -v` + tailed `logs`** give deterministic cleanup and actionable diagnostics.

> Keep each step tiny: convert **one** test, prove it, then proceed. This keeps risk low and momentum high.
