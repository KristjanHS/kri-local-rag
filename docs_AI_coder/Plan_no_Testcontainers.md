# Product TODO List (Compose-Only, No Testcontainers)

This file tracks outstanding tasks and planned improvements for the project, rewritten to use **Docker
Compose only** with robust guardrails for **readiness**, **isolation**, **parity**, and **diagnostics**.

---

## Context

* **App**: Local RAG using Weaviate (8080), Ollama (11434), Streamlit UI (8501)
* **Security**: Only Streamlit is user-visible. All other services should be reachable only via the Compose
  network (no host port mapping unless strictly required). Compose gives service-to-service DNS by name on the
  app’s default network. ([Docker Documentation](https://docs.docker.com/compose/how-tos/networking/?utm_source=chatgpt.com))
* **Python execution**: Avoid `PYTHONPATH`; run modules with `python -m` from project root to ensure imports work.
* **Environment**: Prefer the project venv (`.venv/bin/python`) or an equivalent Python environment.
* **Vectorization**: Local `SentenceTransformer` for embeddings; Weaviate is configured for manually provided vectors.
* **Reranking**: Local `CrossEncoder` model re-scores initial search results.

---

## Compose Guardrails (replaces Testcontainers)

1. **Readiness you can trust**

   * Add **`healthcheck`** to every dependency (Weaviate, Ollama, app).
   * Use **`depends_on` with `condition: service_healthy`** so dependents start only after deps are healthy.
   * Bring up stacks with **`docker compose up -d --wait --wait-timeout <sec>`** to block until running/healthy.
     See: Compose `healthcheck`, startup order, and `up --wait`. ([Docker Documentation](https://docs.docker.com/reference/compose-file/services/?utm_source=chatgpt.com))

2. **Isolation per run**

   * In CI or when running multiple stacks locally, set a unique **project name**
     (e.g., `-p "$GITHUB_RUN_ID"` or `-p "rag-$USER-$(date +%s)"`). This isolates container, network, and volume names.
   * Default service-to-service traffic should stay on the Compose network; **avoid mapping host ports** unless
     you need user access (e.g., Streamlit). ([Docker Documentation](https://docs.docker.com/compose/project-name/?utm_source=chatgpt.com))

3. **Parity and repeatability**

   * **Pin image tags** (avoid `:latest`). Consider digest pinning for strict immutability if needed.
   * Verify merged config with `docker compose config` during CI. ([Snyk](https://snyk.io/blog/10-docker-image-security-best-practices/?utm_source=chatgpt.com), [Docker Documentation](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/?utm_source=chatgpt.com))

4. **Multiple Compose files, clean pathing**

   * Keep a base `compose.yml` and a test overlay `compose.test.yml`.
   * Paths in overlays resolve **relative to the first file** given with `-f`; validate with
     `docker compose -f compose.yml -f compose.test.yml config`.
   * Optionally use modern **`include:`** for modularization. ([Docker Documentation](https://docs.docker.com/compose/how-tos/multiple-compose-files/merge/?utm_source=chatgpt.com))

5. **Logs and cleanup**

   * On failure, dump focused logs (e.g., last 200 lines) with `docker compose logs -n 200 <svc>`.
   * Always **`docker compose down -v`** for deterministic cleanup of networks and volumes. ([Docker Documentation](https://docs.docker.com/reference/cli/docker/compose/logs/?utm_source=chatgpt.com))

---

## Common Pitfalls and Solutions

### Docker Compose Path Resolution

* **Issue**: `docker compose -f docker/docker-compose.yml` resolves relative paths against the **first file** you
  pass with `-f`, not your working directory.
* **Fix**: Keep paths in the overlay relative to the **base** compose file; validate with
  `docker compose -f docker/docker-compose.yml -f docker/docker-compose.test.yml config`.
* **Verify**: `docker compose config` prints fully resolved paths so you can spot mistakes. ([Docker Documentation](https://docs.docker.com/compose/how-tos/multiple-compose-files/merge/?utm_source=chatgpt.com))

### CI Test Execution Strategy (Compose-Only)

* **Constraint**: Full stack (Weaviate, Ollama) is heavy on hosted runners; long model pulls and GPU constraints.
* **Decision**: Keep **unit tests** on every PR. Run **integration + E2E** behind a manual trigger (and locally via
  `act`) or on a scheduled lane, using all guardrails below.
* **Guardrails to apply**:

  * Unique **project name** per run (`-p "$GITHUB_RUN_ID"`). ([Docker Documentation](https://docs.docker.com/compose/project-name/?utm_source=chatgpt.com))
  * Bring up with **`--wait`** and **healthchecks** to avoid race conditions. ([Docker Documentation](https://docs.docker.com/reference/cli/docker/compose/up/?utm_source=chatgpt.com))
  * **No host ports** for internal deps; only expose Streamlit. ([Docker Documentation](https://docs.docker.com/compose/how-tos/networking/?utm_source=chatgpt.com))
  * Pin images and/or digests in the test overlay. ([Docker Documentation](https://docs.docker.com/develop/develop-images/dockerfile_best-practices/?utm_source=chatgpt.com))
  * Tear down with **`down -v`** and collect logs with `compose logs`. ([Docker Documentation](https://docs.docker.com/reference/cli/docker/compose/down/?utm_source=chatgpt.com))
* **Local runs**: `act` can execute workflows locally; be aware runner images differ from GitHub’s, so pick the
  correct image and supply secrets as needed. ([GitHub](https://github.com/nektos/act?utm_source=chatgpt.com))

### Task Verification

* **Issue**: File existence ≠ functional working.
* **Fix**: Test the **actual CLI and HTTP behaviors** (e.g., `/v1/.well-known/ready`) rather than static checks.

---

## Conventions

* **Commands are examples**: Any equivalent approach that achieves the same outcome is acceptable.
* **Ports and model names**: Adapt to your environment as needed.
* Each step has **Action** and **Verify**. Keep changes small and reversible. If a Verify fails, stop and write a
  debugging mini-plan before proceeding (assume even these docs can be wrong).

---

## Quick References

* **AI agent cheatsheet and E2E commands**: [`docs_AI_coder/AI_instructions.md`](AI_instructions.md)
* **Human dev quickstart**: [`docs/DEVELOPMENT.md`](../docs/DEVELOPMENT.md)
* **Archived tasks**: [`docs_AI_coder/archived-tasks.md`](archived-tasks.md)

---

## Prioritized Backlog

### P3 — Containerized CLI E2E copies (Partial Completion) ✅ PARTIALLY COMPLETED

* **Why**: Host-run E2E can miss image/entrypoint/env issues. Running the CLI **inside the `app` container**
  validates the real image while keeping host tests fast.

* **Approach (unchanged, Compose-only)**: Use `docker compose exec app` for CLI and keep Streamlit in same image.

* **Benefits**: Simpler architecture, fewer services, consistent with user workflow.

* [x] Step 6 — Build outside tests (PENDING)

  * **Action**: Ensure scripts/CI build `kri-local-rag-app` once; raise `pytest.UsageError` if image missing.
    Update `scripts/build_app_if_missing.sh` and call it from `scripts/test_e2e.sh`.
  * **Verify**: Second run is faster via image reuse. If failures occur, use logs + healthchecks before code changes.

**Current Blockers / Next Steps (Compose-only):**

* **Weaviate readiness / schema**

  * **Symptom**: `Connection refused` or “class not in schema”.
  * **Actions**:

    1. Add a **healthcheck** for Weaviate (e.g., `GET /v1/.well-known/ready`) with retries/start\_period.
    2. Use `depends_on: { weaviate: { condition: service_healthy } }` for the app.
    3. Bring stack up with `up -d --wait --wait-timeout 120`.
    4. In the app init, **create/verify schema** on boot; fail fast with clear logs if absent.
  * **Verify**: `docker compose logs -n 200 weaviate app` show ready/healthy; the E2E that previously fell back to
    BM25 now completes with hybrid results. ([Docker Documentation](https://docs.docker.com/reference/compose-file/services/?utm_source=chatgpt.com))

* **CLI race on first run**

  * **Symptom**: CLI starts before deps are ready.
  * **Actions**: Ensure CLI steps run **after** `compose up -d --wait` and health is green; if needed, add a small
    retry loop around first connection.
  * **Verify**: First CLI command succeeds without manual sleeps. ([Docker Documentation](https://docs.docker.com/compose/how-tos/startup-order/?utm_source=chatgpt.com))

* [ ] Step 7 — Diagnostics and isolation (PENDING)

  * **Action**: On failure, print exit codes and **last 200 lines** of `app`, `weaviate`, and `ollama` logs; run each
    job with a unique **project name** (`-p "$GITHUB_RUN_ID"`); use **ephemeral named volumes** for tests.
  * **Verify**: Failures are actionable; runs don’t collide. ([Docker Documentation](https://docs.docker.com/reference/cli/docker/compose/logs/?utm_source=chatgpt.com))

* [ ] Step 8 — Wire into scripts/docs/CI (PENDING)

  * **Action**: Document commands in `docs/DEVELOPMENT.md` and `AI_instructions.md`; mention in `scripts/test.sh e2e`
    help; add a CI job for the containerized CLI subset using **`--wait`**, **pinned images**, and **down -v**.
  * **Verify**: Fresh env runs `tests/e2e/*_container_e2e.py` green locally (and under `act`); scheduled job passes.
    ([Docker Documentation](https://docs.docker.com/reference/cli/docker/compose/up/?utm_source=chatgpt.com))

---

### P5 — E2E retrieval failure: QA test returns no context (Weaviate)

* **Context & goal**: E2E returns no context; likely ingestion vs retrieval collection mismatch or ingestion not run.

* [ ] **Task 1 — Reproduce quickly**

  * **Action**: Run only the failing test: `pytest tests/e2e/test_qa_real_end_to_end.py`.
  * **Verify**: Confirm assertion shows empty context.

* [ ] **Task 2 — Check config and schema**

  * **Action**: Inspect `compose.yml`, `.env`, and test fixtures for `COLLECTION_NAME`.
    List Weaviate classes via API.
  * **Verify**: Expected collection exists with expected schema.

* [ ] **Task 3 — Confirm data population**

  * **Action**: Add logging/breakpoint in ingestion fixture; count objects after ingestion.
  * **Verify**: Count > 0.

* [ ] **Task 4 — Probe retrieval directly**

  * **Action**: Temporary test calling `retrieve_chunks` against the populated collection.
  * **Verify**: Non-empty results.

* [ ] **Task 5 — Standardize collection naming**

  * **Action**: Adopt a single E2E collection name, e.g., `TestCollectionE2E`, across tests and configs.
  * **Verify**: Global search shows no stray names.

* [ ] **Task 6 — Implement and verify**

  * **Action**: Re-run full E2E suite after standardization.
  * **Verify**: QA test passes.

* [ ] **Task 7 — Minimal guardrails**

  * **Action**: Log the collection name at setup; add a small test that queries a non-existent collection to confirm a
    clean empty result rather than a crash.
  * **Verify**: Logs show the correct name; negative test passes.

---

### P6 — Minimalist Scripts Directory Cleanup

* **Goal**: Reorganize `scripts/` for clarity with minimal effort.

* [ ] **Phase 1: Create grouping directories and `common.sh`**

  * **Action**: Create `scripts/test/`, `scripts/lint/`, `scripts/docker/`, `scripts/ci/`, `scripts/dev/`.
  * **Action**: Create `scripts/common.sh` with `set -euo pipefail` and basic color logging.
  * **Verify**: Directories and `common.sh` exist and are used by entry scripts.

---

### P7 — `torch.compile` noise & perf

* **Status**:

  * ✅ Local `.env` fixed (localhost for CLI; Docker URLs in containers).
  * ✅ `qa_loop.py` verbosity reduced to DEBUG; re-compile avoidance in-process.
  * 🔍 Still seeing “Skipping torch.compile optimization (tests or MagicMock instance)” in normal usage.

* [ ] **Task 1 — Investigate MagicMock detection**

  * **Action**: Add detailed logging in `backend/retriever.py`; audit env leaks from test config into app runs.
  * **Verify**: Message appears only during tests.

* [ ] **Task 2 — Compile strategy**

  * **Action**: Decide whether to compile embeddings, cross-encoder, or both; add `TORCH_COMPILE_ENABLED` env.
  * **Verify**: Maintain perf while reducing unnecessary compilation.

* [ ] **Task 3 — Perf monitoring**

  * **Action**: Add timing around compile + inference; simple benchmark target in `scripts/test/bench.sh`.
  * **Verify**: Clear numbers for trade-offs.

* [ ] **Task 4 — UX improvements**

  * **Action**: Friendlier messages during initial optimization; consider caching strategies if feasible.
  * **Verify**: Users understand optimization phases; app remains responsive.

---

## Reference snippets (drop-in)

* **Bring up isolated test stack**

  ```bash
  docker compose -f compose.yml -f compose.test.yml \
    -p "rag-${USER}-$(date +%s)" up -d --wait --wait-timeout 120
  ```
* **Tear down and clean**

  ```bash
  docker compose -p "rag-${USER}-$(date +%s)" down -v
  ```
* **Focused logs when a test fails**

  ```bash
  docker compose logs -n 200 app weaviate ollama
  ```

> Rationale for these patterns: Compose `--wait` honors service **healthchecks** and prevents racey starts; unique
> **project names** prevent collisions; and `down -v` plus targeted `logs` make failures actionable. ([Docker Documentation](https://docs.docker.com/reference/cli/docker/compose/up/?utm_source=chatgpt.com))

---

*This plan removes Testcontainers entirely and codifies readiness, isolation, parity, and diagnostics using native
Compose features. Where practicality conflicts with purity, prefer reliability and clarity over cleverness.*
