# Product TODO List

This file tracks **outstanding / undone** tasks for the project. Completed work
(verified during the 2026-06-23 done-ness audit) lives in
[`archive/product_todo-completed.md`](archive/product_todo-completed.md).

## Context

- **App**: Local RAG using Weaviate (8080), Ollama (11434), Streamlit UI (8501)
- **Security**: Only Streamlit should be user-visible. Other services should be local-only (loopback or compose-internal)
- **Python execution**: Avoid `PYTHONPATH`; run modules with `python -m` from project root to ensure imports work
- **Environment**: Prefer the project venv (`.venv/bin/python`) or an equivalent Python environment
- **Vectorization**: Uses a local `SentenceTransformer` model for client-side embeddings. Weaviate is configured for manually provided vectors.
- **Reranking**: A separate, local `CrossEncoder` model is used to re-score initial search results for relevance.

## Common Pitfalls and Solutions

### Docker Compose Path Resolution
- **Issue**: `docker compose -f docker/docker-compose.yml` resolves paths relative to compose file location, not working directory
- **Fix**: Use `.env.docker` (not `./docker/.env.docker`) in compose files
- **Verify**: `docker compose -f docker/docker-compose.yml config`

### CI Test Execution Strategy
- **Issue**: Integration and E2E tests require the full Docker stack (Weaviate, Ollama) which cannot run reliably on GitHub CI runners
- **Fix**: Integration and E2E tests are excluded from GitHub CI entirely and only execute locally via act (nektos/act) on manual `workflow_dispatch` or scheduled runs
- **Verify**: Fast tests (unit tests only) run on every PR, while integration/E2E tests run only locally via act

### Task Verification
- **Issue**: File existence ≠ functional working
- **Fix**: Test actual commands that were failing, not just file presence

## Conventions

- **Commands are examples**: Any equivalent approach that achieves the same outcome is acceptable
- **Paths, ports, and model names**: Adapt to your environment as needed
- Each step has Action and Verify. Aim for one change per step to allow quick fix-and-retry.
- On any Verify failure: stop and create a focused debugging plan before proceeding (assume even these TODO instructions may be stale or mistaken). The plan should:
  - Summarize expected vs. actual behavior
  - Re-check key assumptions
  - Consider that the step description might be wrong; cross-check code for the source of truth.
  - Propose 1–3 small, reversible next actions with a clear Verify for each. Apply the smallest change first.
  - After a change, re-run the same Verify command from the failed step. Only then continue.
  - If blocked, mark the step as `[BLOCKED: <short reason/date>]` in this todo file and proceed to the smallest independent next step if any; otherwise stop and request help.

## Quick References

- **AI agent cheatsheet and E2E commands**: [`docs/AI_coder/AI_instructions.md`](AI_instructions.md)
- **Dev, testing & CI/CD**: [`docs/dev_test_CI/README.md`](../dev_test_CI/README.md)

## Prioritized Backlog

> **Execution order (set 2026-06-23).** Work the items in *phase* order (A→D), not
> P-number order. P-numbers are retained as stable IDs. Dependency spine: **P5 is the
> root-cause keystone** — fixing the Weaviate collection/schema mismatch unblocks the P3
> blockers and removes most P2 E2E failures. P5/P3/P2 overlap heavily; treat them as one
> effort, not three.
>
> | Phase | Item(s) | Why here |
> |-------|---------|----------|
> | **A** | P5 **(+ P3 Step 7 folded in)** | Fix the Weaviate collection/schema root cause. Pull P3 Step 7 (diagnostics & isolation) forward as the instrumentation that makes P5 debugging actionable. |
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

- [ ] **Step 7 — Diagnostics and isolation** *(PULLED INTO PHASE A — build first, then use it to debug P5)*
  - Action: on failure, print exit code, last 200 lines of app logs, and tails of
    `weaviate`/`ollama` logs; use ephemeral dirs/volumes.
  - Verify: failures are actionable; runs are deterministic and isolated.

- [ ] **Step 8 — Wire into scripts/docs/CI**
  - Action: document commands in `docs/dev_test_CI/README.md` and `AI_instructions.md`;
    mention in `scripts/dev/test.sh e2e` help; add a CI job for the containerized CLI subset.
  - Verify: fresh env runs `tests/e2e/*_container_e2e.py` green; CI job passes locally under
    `act` and on hosted runners.

**Blockers / Next Steps** (overlaps P5 — same root cause):

- **Weaviate connection** — `test_e2e_ingest_with_heavy_optimizations_into_real_weaviate`
  fails with `WeaviateConnectionError ... [Errno 111] Connection refused`. Uses
  `testcontainers`; container may not be ready/accessible. Pinned image to
  `cr.weaviate.io/semitechnologies/weaviate:1.32.0` in
  `tests/e2e/test_heavy_optimizations_weaviate_e2e.py`; re-run to confirm.
- **Weaviate schema** — `test_e2e_answer_with_real_services` fails with
  `could not find class Document in schema` (falls back to bm25). Confirm
  `COLLECTION_NAME` (`backend/config.py` default `Document`) and that
  `ensure_weaviate_ready_and_populated()` creates the schema + populates data before the test.

---

#### P5 — E2E retrieval failure: QA test returns no context (Weaviate) — **PHASE A — DO FIRST (keystone)**

> **Note**: same root cause as the P3 blockers above (collection/schema mismatch). Resolve
> together. Likely mismatch between the collection name used by retrieval vs. ingestion, or
> ingestion not executed.
>
> **Phase A folds in P3 Step 7.** Build the P3 Step 7 diagnostics/isolation harness (exit
> code + app/`weaviate`/`ollama` log tails on failure, ephemeral volumes) *before* cracking
> P5 — it turns the "no context returned" failure into an actionable trace. The load-bearing
> fix in this phase is **Task 5: standardize on one E2E collection name** across tests,
> fixtures, and config; the other tasks are diagnosis around it.

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
