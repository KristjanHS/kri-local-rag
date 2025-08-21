Necessary context: docs/testing_strategy.md, cursor_rules/AI_instructions.md

Important info:
* Tests must be run Inside test docker container, The Python executable is at /opt/venv/bin/python3

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

- [x] **Step 6 — Batch-Convert the Remaining TC Tests**
  - **Action**: Move the rest of the Testcontainers specs in **small batches** (2–3 at a time):
    - Point them to the Compose services.
    - Remove per-test containers; reuse the single stack from Step 3.
  - **Status**: ✅ **COMPLETED** - All Testcontainers tests successfully converted or removed:
    - **✅ Working Compose Tests** (All passing with existing test environment):
      - `test_weaviate_compose.py` (2/2 tests pass) - ✅ Verified
      - `test_vectorizer_enabled_compose.py` (1/1 test pass) - ✅ Verified  
      - `test_ingest_pipeline_compose.py` (4/4 tests pass) - ✅ Verified
      - `test_qa_real_ollama_compose.py` (1/1 test pass) - ✅ Verified
    - **✅ Test Execution Method Verified**:
      - Tests run **inside** the app container using: `docker compose -p <RUN_ID> exec -T app /opt/venv/bin/python3 -m pytest <test_file>`
      - Python executable is at `/opt/venv/bin/python3` inside container (not `.venv/bin/python`)
      - All core functionality tests have working Compose versions
    - **✅ Redundant Tests Removed**:
      - `test_backend_import_in_container.py`: Removed (Docker-in-Docker test, redundant in Compose environment)
      - `test_frontend_requirements_in_container.py`: Removed (Docker-in-Docker test, redundant in Compose environment)
      - `test_weaviate_integration.py`: Removed (redundant with `test_weaviate_compose.py`)
    - **✅ Old Testcontainers Tests Removed**:
      - `test_qa_real_ollama.py`: Removed (replaced by `test_qa_real_ollama_compose.py`)
      - `test_vectorizer_enabled_integration.py`: Removed (replaced by `test_vectorizer_enabled_compose.py`)
      - `test_ingest_pipeline.py`: Removed (replaced by `test_ingest_pipeline_compose.py`)
    - **✅ Environment Tests Moved**:
      - `test_python_setup.py`: Moved to `tests/unit/` (environment validation tests belong in unit tests)
    - **✅ Integration Test Suite Cleaned**:
      - Removed Testcontainers dependency from `tests/integration/conftest.py`
      - Integration tests now collect 26 tests (down from 31)
      - All tests pass without Testcontainers dependencies
  - **Verification**: ✅ All integration tests pass successfully in Compose environment

- [x] **Step 6.5 — Fix Model Cache Logic (Critical)**
  - **Problem**: Environment variables pointed to `/app/model_cache` but volume was mounted at `/root/.cache/huggingface`, causing models to be re-downloaded each time
  - **Root Cause**: Mismatch between `SENTENCE_TRANSFORMERS_HOME=/app/model_cache` and volume mount path `/root/.cache/huggingface`
  - **Solution Applied**:
    1. **Simplified model cache approach**: 
       - **Ollama models**: Mounted to local `model_cache` directory via bind mount (`../model_cache:/root/.ollama`)
       - **Hugging Face models**: Use default container cache location (no volume mount needed for small models)
    2. **Removed environment variables** from both `app.Dockerfile` and `app.test.Dockerfile`:
       - Removed `SENTENCE_TRANSFORMERS_HOME=/root/.cache/huggingface`
       - Removed `CROSS_ENCODER_CACHE_DIR=/root/.cache/huggingface`
    3. **Removed redundant model_cache copying** from Dockerfiles (models now persist appropriately)
    4. **Fixed container permissions** for Ollama cache directory
      - **Benefits**:
    - **Simplified setup**: Only Ollama models (large) are persisted to local directory
    - **Fast startup**: Hugging Face models (small) download quickly on first use
    - **Persistent Ollama cache**: Large Ollama models persist across container restarts
    - **Bandwidth efficient**: Ollama models cached locally in project directory
    - **Clean separation**: Large models (Ollama) vs small models (Hugging Face) handled appropriately
  - **Migration**: Use existing `model_cache/` directory for Ollama models (one-time setup)
  - **Verification**: Test if Simplified cache approach implemented, only Ollama models use local directory


- [ ] **Step 6.6 - NLTK Data Management (IN PROGRESS)** 
  **CURRENT ISSUE**: Integration tests failing due to missing NLTK data packages
  
  **Problem Identified from Test Failures**:
  - Integration tests fail with: `LookupError: Resource averaged_perceptron_tagger_eng not found`
  - Current Dockerfiles only download `punkt_tab` but tests need additional NLTK packages
  - `UnstructuredMarkdownLoader` requires both sentence tokenization AND POS tagging data
  - Error occurs during markdown file processing in ingestion pipeline
  
  **Research Findings**:
  - `punkt_tab` is required for sentence tokenization (already implemented)
  - `averaged_perceptron_tagger_eng` is required for POS tagging in text classification
  - Runtime downloads in containers are unreliable (network, permissions, filesystem issues)
  - **Best practice**: Pre-download ALL required NLTK data during Docker build
  
  **UPDATED PLAN - Complete NLTK Pre-downloading**:
  
  **Sub-task 6.6.1**: ✅ COMPLETED - NLTK environment variable and data directory
  - ✅ `ENV NLTK_DATA=/opt/venv/nltk_data` already in both Dockerfiles
  - ✅ Directory created with proper permissions
  
  **Sub-task 6.6.2**: 🔄 IN PROGRESS - Update pre-download commands in Dockerfiles
  - ✅ Current: `punkt_tab` already downloaded
  - 🔄 **NEEDED**: Add `averaged_perceptron_tagger_eng` to download command
  - **Updated command**: `RUN python -m nltk.downloader -d /opt/venv/nltk_data punkt_tab averaged_perceptron_tagger_eng`
  - Place download after pip install but before USER directive
  
  **Sub-task 6.6.3**: ⏳ PENDING - Verify the fix works
  - Test download command in running container first (without rebuild)
  - Run integration tests that use markdown files
  - Confirm both `punkt_tab` and `averaged_perceptron_tagger_eng` data available
  - Verify `UnstructuredMarkdownLoader` and POS tagging works
  
  **Sub-task 6.6.4**: ⏳ PENDING - Update documentation
  - Document the complete NLTK data requirements in project README
  - Add comments in Dockerfiles explaining why both packages are necessary
  
  **Files to modify**: 
  - ✅ `docker/app.Dockerfile` (punkt_tab + averaged_perceptron_tagger_eng)
  - ✅ `docker/app.test.Dockerfile` (punkt_tab + averaged_perceptron_tagger_eng)
  
  **Debugging Plan** (Test outside Docker first to avoid multiple failed builds):
  1. **Step 1**: ✅ Identified exact error: `averaged_perceptron_tagger_eng` missing
  2. **Step 2**: 🔄 Test NLTK requirements locally outside Docker:
     - Create local Python environment
     - Install required packages: `unstructured`, `nltk`, `sentence-transformers`
     - Test NLTK download: `nltk.download('averaged_perceptron_tagger_eng')`
     - Verify UnstructuredMarkdownLoader works with test markdown file
     - Confirm all required NLTK packages are identified
  3. **Step 3**: ⏳ Test download in running container (if local test succeeds)
  4. **Step 4**: ⏳ Update Dockerfiles with confirmed working download command
  5. **Step 5**: ⏳ Single rebuild and verify all integration tests pass
  
  **Rationale**: 
  - Production reliability > image size optimization
  - Runtime downloads introduce failure points and slower startup
  - Modern NLTK + Unstructured library requires both tokenization AND POS tagging data
  - Container environments are not ideal for runtime downloads

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
