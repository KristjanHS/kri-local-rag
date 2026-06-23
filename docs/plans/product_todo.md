# Product TODO List

This file tracks **outstanding / undone** tasks for the project. Completed work
(verified during the 2026-06-23 done-ness audit) lives in
[`archive/product_todo-completed.md`](archive/product_todo-completed.md).

## Context

- **App**: Local RAG — Weaviate (8080), Ollama (11434), Streamlit UI (8501); only Streamlit is user-visible.
- **Vectorization / reranking**: local `SentenceTransformer` for client-side embeddings (Weaviate stores manually provided vectors); a local `CrossEncoder` re-scores results.
- Repo-root / `.venv/bin/python` / no-`PYTHONPATH` execution and commit conventions live in `CLAUDE.md` and `.claude/rules/`.

## Working method

Each item has Action + Verify; make one change per step. On a Verify failure, stop and create a focused debugging plan before proceeding (per `CLAUDE.md` rule 6) — assume even these instructions may be stale. Mark a stuck item `[BLOCKED: <reason/date>]` and move to the next independent step. Gotchas worth recalling: Docker Compose resolves paths relative to the compose-file location (use `.env.docker`, not `./docker/.env.docker`); integration/E2E tests run only locally via `act`, never on GitHub CI (see `docs/operate/auto-merge.md`).

## Quick References

- **Dev, testing & CI/CD**: [`docs/dev_test_CI/README.md`](../dev_test_CI/README.md)
- **Run commands / Makefile targets**: root `README.md`, `make help`, `CLAUDE.md`

## Prioritized Backlog

> **Execution order (set 2026-06-23).** Work the items in *phase* order (A→D), not
> P-number order. P-numbers are retained as stable IDs. Dependency spine: **P5 is the
> root-cause keystone** — fixing the Weaviate collection/schema mismatch unblocks the P3
> blockers and removes most P2 E2E failures. P5/P3/P2 overlap heavily; treat them as one
> effort, not three.
>
> | Phase | Item(s) | Why here |
> |-------|---------|----------|
> | **A** | ~~P5 + P3 Step 7~~ ✅ **DONE 2026-06-23** | P5 (Weaviate collection/schema root cause) found already-resolved on live triage — QA retrieval E2E passes. P3 Step 7 diagnostics shipped (`_dump_container_diagnostics`); isolation half deferred to `e2e_container.md`. |
> | **B** | P3 Steps 6, 8 | With P5 green, verify build-reuse (Step 6) and wire the containerized CLI subset into scripts/docs/CI (Step 8). Also satisfies P2's Integration-Suite / Docker-Env / Docs sub-items. |
> | **C** | P2 (remaining gaps) | Full app-validation sweep as *confirmation*, skipping what A+B already covered. Model-loading layers (Integration Suite, Real Model Ops) are independent of P5 and can run anytime. |
> | **D** | P7 | Low-value / partly moot — **defer** unless Phase C surfaces a concrete compile-time pain point. |

#### P2 — Complete Application Validation After Model Changes (PHASE C — confirmation sweep, IN PROGRESS)

**Goal**: Validate that the entire RAG application works correctly after the comprehensive
model handling refactoring, ensuring no regressions were introduced.

**Already done** (see archive): config/imports, model loading, and the unit test suite
(65 passing, 53% coverage) are verified complete. The remaining layers below all require
**live services** (Weaviate + Ollama) and real models.

- [ ] **Integration Test Suite**
  - Test real model loading (with timeout protection)
  - Validate caching behavior
  - Test error scenarios (missing models, network issues)
  - Verify offline mode functionality
  - Verify: all integration tests pass when docker containers are running (carried over from P2.2 Step 8)

- [ ] **Core RAG Pipeline Components**
  - Test retriever module with real models
  - Test vectorization pipeline with real models
  - Test reranking functionality with real models
  - Test hybrid search logic with real models

- [ ] **Ollama Integration**
  - Test Ollama client connectivity
  - Test model availability checking
  - Test model download via Ollama
  - Test generation with real Ollama model

- [ ] **End-to-End QA Pipeline**
  - Test complete QA workflow with mock services and real models
  - Test error handling in QA pipeline
  - Validate context retrieval and answer generation with real models
  - Test different model configurations

- [ ] **Docker Environment**
  - Test Docker build process
  - Validate container startup
  - Test service health checks
  - Verify volume mounts work correctly

- [ ] **Real Model Operations**
  - Test with actual embedding model (small/fast one)
  - Test with actual reranker model (small/fast one)
  - Validate model caching and reuse with real models
  - Test model switching via environment variables

- [ ] **Performance & Memory**
  - Test memory usage with real model loading
  - Validate real model unloading/caching works
  - Test concurrent real model access
  - Monitor for memory leaks

- [ ] **Error Handling & Edge Cases**
  - Test behavior with missing real models
  - Test network failure scenarios
  - Test disk space issues
  - Test corrupted model files

- [ ] **Documentation & Scripts**
  - Validate all scripts use correct imports
  - Test docker-setup.sh with new configuration
  - Update any outdated documentation
  - Verify environment variable documentation

**Success Criteria**: all integration tests pass · core RAG works end-to-end · Docker env
operates correctly · real models load and function · no performance regressions · error
handling works · documentation up to date.

**Risks to Monitor**: model loading performance · memory usage with multiple models ·
network dependency for downloads · Docker build time · test flakiness from real models.

---

#### P3 — Containerized CLI E2E copies (PHASE B — Steps 6 & 8; Step 7 pulled into Phase A)

**Already done** (see archive): Steps 1–5 — the CLI-twin infrastructure using the existing
`app` container (`run_cli_in_container` helper, removed separate `cli` service, one passing
twin `test_qa_real_end_to_end_container_e2e.py`).

- [ ] **Step 6 — Build outside tests**
  - Action: ensure scripts/CI build `kri-local-rag-app` once; helper raises
    `pytest.UsageError` if image missing.
    - Status: implemented — `app_compose_up` checks for `kri-local-rag-app:latest` and
      raises `pytest.UsageError` if missing; `docker/app.Dockerfile` adds
      `COPY frontend/ /app/frontend/` before `pip install .` in the builder stage.
  - Verify: second run is faster due to image reuse. *(Partially verified — build works,
    but tests fail on the Weaviate blockers below.)*

- [x] **Step 7 — Diagnostics and isolation** *(diagnostics DONE 2026-06-23; isolation deferred)*
  - Action: on failure, print exit code, last 200 lines of app logs, and tails of
    `weaviate`/`ollama` logs; use ephemeral dirs/volumes.
  - **Done:** `tests/e2e/conftest.py::_dump_container_diagnostics` — `run_cli_in_container`
    now dumps exit code + CLI stdout/stderr tails + `docker compose logs --tail 200` for
    `app`/`weaviate`/`ollama` whenever a containerized CLI call returns non-zero
    (best-effort, never raises). Covered by `tests/unit/test_e2e_diagnostics_unit.py`
    (service-list + never-raise contract, subprocess mocked → fast unit tier).
  - **Deferred:** the "ephemeral dirs/volumes" isolation half belongs to the compose-fixture
    redesign (`e2e_container.md`); the current fixtures intentionally reuse the shared
    `make test-up` stack and preserve volumes.

- [ ] **Step 8 — Wire into scripts/docs/CI**
  - Action: document commands in `docs/dev_test_CI/README.md`;
    mention in `scripts/dev/test.sh e2e` help; add a CI job for the containerized CLI subset.
  - Verify: fresh env runs `tests/e2e/*_container_e2e.py` green; CI job passes locally under
    `act` and on hosted runners.

**Blockers / Next Steps** — **reframed 2026-06-23 after live triage** (the original
"schema mismatch" framing was stale; see P5 RESOLVED below):

- **~~Weaviate schema~~ — RESOLVED.** `test_e2e_answer_with_real_services` now **passes**;
  no `could not find class Document in schema`. See P5.
- **Compose-fixture project conflict** (the real cause of the 3 e2e SKIPs) — the e2e
  compose fixtures (`weaviate_compose_up`/`ollama_compose_up`/`app_compose_up` in
  `tests/e2e/conftest.py`) run `docker compose -f docker/docker-compose.yml up -d --wait
  <svc>` under the **default** project name (`kri-local-rag`), which spawns a *second*
  Weaviate alongside the already-running `make test-up` stack (run-id project). The second
  container dies on cluster init (`Failed to get final advertise address: No private IP
  address found … could not init cluster state`) and the fixture `pytest.skip`s. Fix
  belongs to `e2e_container.md`: make the fixtures detect an already-healthy service and
  reuse it instead of starting a conflicting project, **and** make `run_cli_in_container`
  target the active compose project (env-aware helper) rather than the default name.
- **Weaviate connection (heavy-optimizations test)** — `test_heavy_optimizations_weaviate_e2e.py`
  uses `testcontainers` (its own ephemeral Weaviate, image pinned
  `cr.weaviate.io/semitechnologies/weaviate:1.32.0`); re-run standalone (no competing stack)
  to confirm. Not the same path as the compose-fixture conflict above.

---

#### P5 — E2E retrieval failure: QA test returns no context (Weaviate) — **PHASE A — ✅ RESOLVED (verified live 2026-06-23)**

> **RESOLVED 2026-06-23 (live verification against the `make test-up` stack).** The
> `Document`/`TestCollection` schema-mismatch this section was built around **no longer
> exists**. `tests/e2e/test_qa_real_end_to_end.py::test_e2e_answer_with_real_services`
> **passes** end-to-end against real Weaviate + Ollama: it ingests into `TestCollection`
> and queries `TestCollection` (both sides pass `collection_name=TEST_COLLECTION_NAME`),
> retrieval returns context, no "could not find class Document in schema". Full host E2E
> run: **4 passed, 3 skipped** (the 3 skips are a compose-fixture infra conflict, not P5 —
> see the reframed P3 blockers below). Tasks 1–7 are obsolete diagnosis for an
> already-fixed bug; left for history.
>
> **Residual nuance (not a retrieval bug):** two collection names still coexist in the e2e
> layer — `fixtures_ingestion.py::docker_services_ready` populates `COLLECTION_NAME`
> (`Document`) via `ensure_weaviate_ready_and_populated()`, while `test_qa_real_end_to_end.py`
> and conftest cleanup use `TestCollection`. Harmless today (each test queries the name it
> populated), but worth standardizing — folded into the `e2e_container.md` "simplify compose
> fixtures" work.

- [ ] **Task 1 — Reproduce quickly**
  - Action: run only the failing test (e.g. `pytest tests/e2e/test_qa_real_end_to_end.py`).
  - Verify: test fails with an empty-context assertion, confirming reproducibility.

- [ ] **Task 2 — Check config and schema**
  - Action: inspect `docker-compose.yml`, `.env` files, and fixtures for the
    `COLLECTION_NAME` in use. Connect to Weaviate and list collections.
  - Verify: the collection used in the test exists with the expected schema.

- [ ] **Task 3 — Confirm data population**
  - Action: log/breakpoint in the ingestion fixture (`tests/e2e/fixtures_ingestion.py`) to
    confirm it runs; query the collection's object count.
  - Verify: fixture executes and the target collection has > 0 objects.

- [ ] **Task 4 — Probe retrieval directly**
  - Action: add a temporary test that calls `retrieve_chunks` directly against the populated
    collection.
  - Verify: direct call returns a non-empty list, proving retrieval logic works.

- [ ] **Task 5 — Standardize collection naming**
  - Action: choose one collection name for all E2E tests (e.g. `TestCollectionE2E`) and
    apply it across tests, fixtures, and config.
  - Verify: global search for the old name in `tests/` yields no results.

- [ ] **Task 6 — Implement and verify**
  - Action: with the standardized name, re-run the full E2E suite.
  - Verify: the originally failing QA test passes.

- [ ] **Task 7 — Add minimal guardrails**
  - Action: log the collection name in the E2E setup fixture; add a small test that queries
    a non-existent collection.
  - Verify: logs show the correct name; querying an empty/non-existent collection returns an
    empty list rather than crashing.

---

#### P7 — Torch.compile Optimization (PHASE D — DEFERRED; Tasks 2–4 remaining, low priority)

**Already done** (see archive): `.env` fix, reduced verbosity, in-process re-compile guard,
and **Task 1 is moot** — the torch.compile logic was refactored into `backend/ingest.py`
with an idempotent `_is_torch_compiled` guard; the "Skipping torch.compile (tests or
MagicMock)" message no longer exists.

> These remaining tasks are low-value enhancements. Confirm they are still worth doing
> before picking them up.

- [ ] **Task 2 — Optimize torch.compile application strategy**
  - Action: decide whether torch.compile should apply to both embedding model and
    cross-encoder, or just one.
  - Action: consider an env var to control it (e.g. `TORCH_COMPILE_ENABLED=false` for dev).
  - Verify: performance maintained while reducing unnecessary re-compilation overhead.

- [ ] **Task 3 — Add performance monitoring**
  - Action: add timing around torch.compile operations; create a simple inference benchmark.
  - Verify: clear metrics on the compilation-time vs. inference-speed trade-off.

- [ ] **Task 4 — Improve error handling and UX**
  - Action: more informative optimization-status messages; consider caching compiled models
    to disk to avoid re-compilation across process restarts.
  - Verify: users understand what's happening and the process feels responsive.

---

#### Post-MVP — Launch hardening (DEFERRED)

Carried over from the archived `docs/plans/archive/launch_prep_todo.md` bring-up checklist
(the bring-up steps themselves shipped; these were its open "Post-MVP (defer)" items). The
deploy runbook is `docs/operate/mvp_deployment.md`.

- [ ] Add app healthcheck / readiness probe for the Streamlit container.
- [ ] Produce a lean production image (drop dev deps, avoid the editable install).
- [ ] Enable Weaviate auth; front with a reverse proxy / SSO; terminate HTTPS.
- [ ] Define container resource limits and a GPU scheduling policy.
- [ ] Pin model/versions and warm an offline model cache at build time.
- [ ] Add metrics, tracing, and alerts.
