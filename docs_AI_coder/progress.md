# Migration Progress: Testcontainers → Compose-only

This document tracks the progress of the migration from Testcontainers to a Docker Compose-based testing setup.

## Completed Steps

### Step 1 — Add Healthchecks to Every Service
- **Action**: Added `healthcheck` for `weaviate`, `ollama`, and `app` in `docker-compose.yml`.
- **Verification**: `docker compose up -d --wait` successfully brings up all services to a healthy state.

### Step 2 — Introduce a Test Overlay File
- **Action**: Created `compose.test.yml` for test-specific configurations.
- **Verification**: `docker compose -f docker-compose.yml -f compose.test.yml config --images` lists the correct images.

### Step 3 — Add “Up/Down/Logs” Test Harness Scripts
- **Action**: Created `test-up`, `test-down`, and `test-logs` targets in the `Makefile`.
- **Verification**: The Makefile targets successfully manage the test environment's lifecycle.

### Step 4 — Convert One TC Test (The Smallest) to Compose
- **Action**: Converted `tests/integration/test_weaviate_integration.py` to use the Docker Compose setup.
- **Verification**: In progress. The test is failing because `pytest` is not found in the `app` container's `PATH`.
