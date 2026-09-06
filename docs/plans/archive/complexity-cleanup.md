# Complexity Cleanup Plan — Tiers 1 & 2

**Status:** ✅ Closed (archived 2026-06-25 — Tiers 1–2 shipped; §2.6 resolved as *keep hooks*) · **Branch:** `dev` · **Scope:** `backend/`, `frontend/`
**Source:** Whole-repo complexity survey (parallel reviewers, Ousterhout/Linus lens), all dead-code claims grep-verified before inclusion.

## Goal

Remove verified dead code and unwind test-driven complexity in the Python core,
**without changing runtime behavior**. Tier 1 is mechanical deletion; Tier 2 is
small targeted refactors. Findings the survey got wrong (e.g. swapping the
`threading.Event` stop signal for a bool) are explicitly excluded — see
[Out of scope](#out-of-scope).

## Working rules

- Run from repo root; use `.venv/bin/python`. Never set `PYTHONPATH`.
- After each tier: `make pre-commit` + `.venv/bin/python -m pytest tests/unit` (add `tests/integration` for Tier 2). Surface failures, don't paper over them.
- Conventional Commits on `dev`. One commit per tier (or per Tier 2 item).
- Delete the tests that exist *only* to pin deleted code — do not keep code alive for tests (`_KEEP_FOR_TESTS` is the anti-pattern we're removing).

---

## Tier 1 — Confirmed dead code (mechanical deletion)

Each symbol below has **zero production callers** (grep-verified: only the
definition, the `_KEEP_FOR_TESTS` marker, or test-only references). ~90 lines.

### 1.1 `backend/config.py`
- [ ] `HF_CACHE_DIR` (line ~175) — unused; HF reads `HF_HOME` directly.
- [ ] `EMBED_COMMIT`, `RERANK_COMMIT` (lines ~182-183) — unused.
- [ ] `TRANSFORMERS_OFFLINE` block (lines ~186-190, incl. comment + `transformers_offline_env` parse) — all references are inside `config.py`; never consumed.
- [ ] `is_running_in_docker()` (lines ~231-244) — never called.

### 1.2 `backend/models.py`
- [ ] `get_embedder()`, `get_cross_encoder()` (lines ~268-275) — legacy aliases, no callers.
- [ ] `get_model_status()` (lines ~224-229) — no callers.
- [ ] `clear_model_cache()` (lines ~216-221) — no callers (not even tests).
- [ ] Keep `preload_models()` — used by `tests/integration/test_model_loading_integration.py`.

### 1.3 `backend/ollama_client.py`
- [ ] `_verify_model_download()` (lines ~114-132) — referenced only by `_KEEP_FOR_TESTS`; never executed.
- [ ] `_KEEP_FOR_TESTS` tuple (line ~383) — the dead-code-retention marker itself.
- [ ] `ensure_model_available()` (lines ~135-142) — test-only wrapper; production calls `pull_if_missing()` directly.
- [ ] `_detect_ollama_model()` (lines ~31-45) — test-only; no production caller.

### 1.4 Orphaned tests
- [ ] Remove/adjust tests that exist solely to exercise the symbols above:
  - `tests/unit/test_ollama_client_unit.py` — `ensure_model_available`, `_detect_ollama_model` cases.
  - `tests/unit/test_startup_model_check_unit.py`, `test_startup_validation_unit.py`, `test_frontend_smoke.py`, `tests/integration/test_startup_validation_integration.py` — audit each `ensure_model_available` reference; repoint to `pull_if_missing` or delete if the assertion only validated the wrapper.

### Tier 1 verification
- [ ] `make pre-commit`
- [ ] `.venv/bin/python -m pytest tests/unit tests/integration`
- [ ] `grep -rn` each deleted symbol → 0 hits remaining.
- [ ] Commit: `refactor(backend): remove verified dead code and test-only shims`

---

## Tier 2 — Real complexity smells (targeted refactors)

Ordered by confidence/payoff. Each is a behavior-preserving change; verify with
existing tests.

### 2.1 Remove test-injection function params from `answer()` — HIGH
- **File:** `backend/qa_loop.py:118-132`
- **Problem:** `answer()` takes `get_top_k_func` / `generate_response_func` defaulting to the real functions, overridden only in two integration tests. Production never overrides them.
- **Fix:** Drop both params. In the tests, replace injection with `unittest.mock.patch("backend.qa_loop.get_top_k", ...)` / `patch("backend.qa_loop.generate_response", ...)`.
- **Touch:** `tests/integration/test_qa_pipeline.py`, `tests/integration/test_answer_streaming_integration.py`.
- **Verify:** both integration tests pass.

### 2.2 Delete the fake `stats` dict in ingestion — HIGH
- **File:** `backend/ingest.py:195,237,252` (+ call site ~310)
- **Problem:** `stats = {"inserts":0,"updates":0,"skipped":0}` but only `inserts` is incremented ("count all as inserts for simplicity") and the return is discarded.
- **Fix:** Remove the dict and its `return`; keep useful per-batch progress logging. Drop the unused return capture at the call site.
- **Verify:** ingest unit/integration tests; manual `make ingest` smoke optional.

### 2.3 Collapse doubled debug output in `generate_response()` — MEDIUM
- **File:** `backend/ollama_client.py:252-284`
- **Problem:** 18× `logger.debug(x)` immediately followed by `if on_debug: on_debug(x)` — a hand-maintained parallel channel feeding the Streamlit debug panel.
- **Fix:** Route the UI panel through a `logging.Handler` (attach in `rag_app.py`, capture into `session_state["debug_lines"]`) and drop the inline `on_debug` duplication. Keep `on_token` (data, not diagnostics).
- **Touch:** `frontend/rag_app.py` debug-capture wiring.
- **Risk:** Medium — changes how the UI debug panel is fed; verify the panel still populates. Defer if not worth it.

### 2.4 Simplify defensive exception handling — MEDIUM
- **File:** `backend/qa_loop.py:254-342` (`ensure_weaviate_ready_and_populated`)
- **Problem:** `except WeaviateConnectionError: raise WeaviateConnectionError(...) from None` re-raises same type, no added context; generic `except Exception` re-wraps everything.
- **Fix:** Remove no-value re-raises; let exceptions propagate. Keep the `finally` client-close but guard against `client is None`.
- **Verify:** startup/connection error-path tests still pass.

### 2.5 Drop the cache-bypass branch in `_get_embedding_model()` — MEDIUM
- **File:** `backend/retriever.py:46-71`
- **Problem:** `model_name` param exists solely for a test path; production always calls it argument-less.
- **Fix:** Remove the param and the bypass branch; tests mock `load_embedder()` if they need a specific model.
- **Verify:** retriever tests pass.

### 2.6 ✅ RESOLVED (keep hooks) — `RAG_FAKE_ANSWER` / `RAG_SKIP_STARTUP_CHECKS` in UI
- **File:** `frontend/rag_app.py` (fake-answer + skip-startup-checks env reads)
- **Problem:** Test hooks live in production UI code.
- **Resolution (2026-06-25 user decision):** Keep the hooks. They are a legitimate seam for the
  subprocess-launched smoke tests (`test_app_smoke.py`), where in-process `mock.patch` cannot reach
  across the fork; the "split into a separate test app" reviewer suggestion is worse than the disease.
  No code change. (Same decision as `architectural-simplification.md` §A1.)

### Tier 2 verification
- [ ] `make pre-commit`
- [ ] `.venv/bin/python -m pytest tests/unit tests/integration`
- [ ] Commit per item, e.g. `refactor(qa_loop): drop test-injection params from answer()`

---

## Out of scope (survey claims rejected on verification)

- **`rag_app.py:132` `stop_event` → bool.** Rejected. The backend interrupt
  contract is `stop_event.is_set()` (`ollama_client.py:305`, `qa_loop.py:145`).
  A bool breaks the interface. `threading.Event` is correct — leave it.
- **`rag_app.py:151` `_ThreadLogFilter`.** Keep. It isolates logs per
  ScriptRunner thread across concurrent Streamlit sessions — not speculative.
- **`vector_utils.to_float_list` narrowing to torch/numpy only.** Skip. The
  defensive conversion is cheap; narrowing risks breaking if `encode()` returns
  a list.

## Rollout

1. Tier 1 (one commit) → verify → ready to merge.
2. Tier 2 items 2.1, 2.2 (highest confidence) → separate commits.
3. Tier 2 items 2.3–2.5 as capacity allows; 2.6 only after a decision.
4. Archive this plan to `docs/plans/archive/` once Tiers 1–2 land.
