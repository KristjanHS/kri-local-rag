# Product TODO — Completed / Archived Work

Archived from `docs/plans/product_todo.md` on 2026-06-23. This file records work that
was **verified complete** during a done-ness audit (not merely checkbox-marked).
Open/undone tasks remain in `docs/plans/product_todo.md`.

> **Audit method**: each "done" claim was checked against the codebase, not trusted
> from its checkmark (per the project convention: *file existence ≠ functional working*).
> Verification evidence is recorded inline below.

---

## P2 — Application Validation After Model Changes (completed portions)

The model-handling refactor and its lower validation layers are done:

- ✅ Single source of truth for model configs (`backend/config.py`)
- ✅ Removed duplicate model download scripts
- ✅ Centralized config imports across the codebase
- ✅ Environment-variable override support retained
- ✅ Modern mocking patterns across test code

**Completed validation layers:**

- [x] **Basic Configuration & Imports** — config imports (`DEFAULT_EMBEDDING_MODEL`,
  `DEFAULT_RERANKER_MODEL`, `DEFAULT_OLLAMA_MODEL`), models module imports, env-var
  overrides, and logging all functional.
- [x] **Model Loading Functionality** — `load_embedder` / `load_reranker` available,
  centralized config usage, env-var fallbacks work.
- [x] **Unit Test Suite** — **VERIFIED 2026-06-23**: `pytest tests/unit/` → **65 passed**
  in 8.54s, 53% coverage. (Original note said "53/53, 52%"; the suite has since grown
  and still passes green.)

> The remaining P2 validation layers (Integration through Documentation & Scripts)
> require live services and are still open — see `product_todo.md`.

### Established patterns for AI Coder (reference)

- **Modern Mocking**: `mocker` fixture from `pytest-mock` instead of `unittest.mock.patch`.
- **Autouse Cache Reset**: `reset_embedding_model_cache()` fixture cleans global state.
- **Fixture Pattern**: `mock_embedding_model` / `managed_cross_encoder` for DI.
- **Pre-commit Gates**: Ruff, Pyright, Bandit, Hadolint all pass.
- **Caching**: `_get_embedding_model()` uses the global `_embedding_model` cache.

```python
# Modern approach for mocking
def test_something(mocker, mock_embedding_model):
    mocker.patch("module.function", return_value=mock_value)
    # No manual cache cleanup — autouse fixtures handle it
```

---

## P2.2 — Integration Tests Logic Simplification (Steps 1–8) — SHIPPED

Shipped in commit `8e56248` ("simplification of integr tests and testing docs"),
planned in `dab3678`.

**VERIFIED 2026-06-23:**

- ✅ pytest markers `requires_weaviate` / `requires_ollama` registered in `pyproject.toml`.
- ✅ `TEST_DOCKER` env var drives Docker-vs-local URLs (`backend/config.py`,
  `tests/integration/conftest.py`).
- ✅ Legacy artifacts removed (`integration_config.toml`, `conftest.py.backup` — confirmed absent).
- ✅ Single source of truth: `[tool.integration]` in `pyproject.toml`.
- ✅ HTTP health checks against official endpoints (`/v1/.well-known/ready`, `/api/version`).

**Caveats noted at archive time (did not block shipping):**

- ⚠️ `tests/integration/conftest.py` is **318 lines**, not the "<200" success criterion.
  The original notes claimed both "773→184" and "773→333" — both inconsistent with reality.
  The simplification is real and large, but the specific line target was not met.
- ℹ️ Step 7's standalone doc files (`TEST_DOCKER_GUIDE.md`, `MIGRATION_GUIDE.md`,
  `README_integration.md`, `test_integration_examples.py`, `DEVELOPMENT.md`) no longer
  exist. They were **created as part of Step 7 and later intentionally removed during a
  de-bloating pass** (testing docs now live consolidated in `docs/dev_test_CI/README.md`).
  This is expected cleanup, not a regression — the Step 7 work was done, then deliberately
  pruned.
- ⚠️ One residual verification remained open: *"verify all integration tests pass when
  docker containers are running."* This is a live-service run, folded into the open
  P2 integration validation rather than tracked here.

### Working patterns (reference)

```python
@pytest.mark.requires_weaviate
@pytest.mark.requires_ollama
def test_my_feature(integration):
    weaviate_url = integration["get_service_url"]("weaviate")  # Docker vs local
    is_healthy   = integration["check_service_health"]("ollama")  # HTTP health check
```

- `TEST_DOCKER=true` → services at `weaviate:8080`, `ollama:11434`.
- `TEST_DOCKER=false` (default) → `localhost:8080`, `localhost:11434`.

---

## P3 — Containerized CLI E2E copies (Steps 1–5) — COMPLETED

Approach: reused the existing `app` container (runs both Streamlit and CLI via
`docker compose exec app`) instead of a separate `cli` service.

**VERIFIED 2026-06-23:**

- [x] **Step 1 — Identify candidates** — listed in-process CLI E2E tests (e.g.
  `tests/e2e/test_qa_real_end_to_end.py`).
- [x] **Step 2 — Use existing app container** — `docker compose exec app python -m
  backend.qa_loop --help` exits 0.
- [x] **Step 3 — Test helper** — `run_cli_in_container(...)` exists in
  `tests/e2e/conftest.py` (confirmed present, line ~162).
- [x] **Step 3.1 — Review & validate** — simplified to existing app container.
- [x] **Step 3.2 — Clean up old complexity** — separate `cli` service removed from
  `docker/docker-compose.yml` (confirmed: no `cli:` block present).
- [x] **Step 4 — Readiness & URLs** — reused `weaviate_compose_up` / `ollama_compose_up`,
  compose-internal URLs for ingestion.
- [x] **Step 5 — Create test twins** — `tests/e2e/test_qa_real_end_to_end_container_e2e.py`
  exists (confirmed).

> Steps 6–8 (build-outside-tests, diagnostics, CI wiring) plus the Weaviate connection /
> schema blockers remain open — see `product_todo.md`.

---

## P7 — Torch.compile (completed portions)

- ✅ Fixed `.env` configuration (localhost URLs for local CLI vs Docker service URLs).
- ✅ Reduced torch.compile verbosity (DEBUG level) and added re-compilation prevention
  within a single process.
- ✅ **Task 1 effectively resolved by refactor** — **VERIFIED 2026-06-23**: the
  torch.compile logic now lives in `backend/ingest.py` with an idempotent
  `_is_torch_compiled` guard and proper log levels. The suspicious
  *"Skipping torch.compile optimization (tests or MagicMock instance)"* message no longer
  exists anywhere in `backend/`, so the original symptom is no longer reproducible.

**Key learnings (reference):**

- torch.compile optimizations are process-local; cannot persist across restarts.
- The CLI script (new process per run) inherently re-optimizes each invocation.
- Test mocking infra can leak into normal usage if not isolated (now mitigated).

> Tasks 2–4 (env-var toggle, perf monitoring, UX/disk caching) remain open as low-value
> enhancements — see `product_todo.md`.
