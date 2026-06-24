# Test Suite Value Cleanup

Status: **in progress** (started 2026-06-23). Goal: delete or fix low-value unit/integration/e2e
tests per the 5-check value gate (`.claude/rules/testing.md`) and the testing anti-patterns skill.

Audit covered all 56 test files (~5,570 lines) via four parallel review agents (unit-infra, unit-logic,
integration, e2e/ui). Each verdict cites the gate check or anti-pattern violated.

## ✅ Done (Pass 1 — staged/committed)

- **Deleted 16 zero-value files** (no real coverage lost):
  - Scaffolding/language tests: `unit/test_imports.py`, `unit/test_python_setup.py`, `unit/test_env_example.py`
  - Plugin/library tests: `unit/test_network_block_unit.py`, `…_sentinel_unit.py`, `…_httpx_unit.py` (all test `pytest-socket`/`httpx`, not our code)
  - Already-`--ignore`'d dead files: `unit/test_debug.py`, `unit/test_logging.py`, `unit/test_search_logic_archived.py`
  - Harness-testing files: `unit/test_weaviate_guard.py` (tests the conftest guard), `e2e/test_container_helper.py` (`--help` banner), `ui/test_browser_launch_only.py` (tests Playwright works)
  - Vendor smoke / diagnostics: `integration/test_weaviate_compose.py` (Weaviate connect+CRUD), `integration/test_weaviate_debug.py` (print-driven)
  - Weaker dup: `e2e/test_qa_real_end_to_end.py` (in-process, strictly weaker than `integration/test_qa_real_ollama_compose.py`); `e2e/test_heavy_optimizations_weaviate_e2e.py` (claims to verify `torch.compile` but only asserts `count>=2`)
- **Moved 3 fully-mocked "integration" tests → `tests/unit/`** (no real component, misfiled):
  `test_answer_streaming_integration.py`→`unit/test_answer_streaming.py`, `test_cli_output.py`, `test_qa_pipeline.py`
- **Fixed `unit/test_compose_security.py`** — removed broken `compute_str()` forward-reference (a `# type: ignore[name-defined]` was masking it); the loopback-binding security assertions are kept.
- **Removed 3 stale `--ignore` lines** from `pyproject.toml` (pointed at now-deleted files).

## ⏸️ Open question — needs a decision

### test_model_loading_integration.py (546 lines, 9 tests) — how aggressively to trim?

All options drop tests 6–9 (pure dups of 1–3), the ~70-line `_is_network_connectivity_error` /
`_is_model_availability_error` / `_should_skip_on_model_error` skip-helper trio, and the flaky timing
assertions (`second_load_time < 1.0` — tests performance, not correctness).

- **Pragmatic (4 tests, ~120 lines, recommended):** embedder-load, reranker-load (caching folded into each), `preload_models()`, invalid-model error path.
- **Minimal (2 tests, ~55 lines):** only embedder-load + reranker-load (caching folded in).
- **Conservative (5 tests, ~180 lines):** keep tests 1–5 separate (adds standalone `test_model_caching_behavior`).

Note: tests 7–9 are the only consumers of the `real_model_loader` / `model_health_checker` /
`real_embedding_model` / `real_reranker_model` fixtures in `integration/conftest.py` — once dropped,
those fixtures are dead and can be removed too.

## ⏸️ Pending FIX/TRIM work (not yet touched)

Verdicts from the audit. Each is "real value buried in waste" — fix, don't delete wholesale.

### Unit tier
- **`test_cross_encoder_optimizations.py`** — mocks `load_reranker`, asserts the mock came back (`assert cross_encoder is mock_encoder_instance`); the only real branch (`except → None`) is untested. Rewrite to assert the exception→None path, or delete.
- **`test_search_logic.py`** — ~4 near-identical "hybrid raises → RuntimeError, bm25 not called" tests + `assert model is mock_embedding_model` (testing the fixture). Collapse to one parametrized failure test + one empty-collection test. `test_embedding_model_unavailable` ≡ `test_vectorization_error_scenario`.
- **`test_ingest_logic.py`** — keep PDF-magic / `load_and_split` / `deterministic_uuid` / `object_properties`; drop `assert batch.fixed_size.call_count == 1` and `assert first_call_kwargs["vector"] == [...]` (mock-behavior).
- **`test_ingest_unit.py` + `test_markdown_ingestion_end_to_end_unit.py`** — `deterministic_uuid` is tested in 3 files; `load_and_split` over real files in 2. Merge the one unique assertion (`source == "md"` extension normalization) into `test_ingest_logic.py`; delete the rest.
- **`test_startup_validation_unit.py`** — worst offender: `assert os.path.exists(...)`, `assert "OLLAMA_MODEL" in source`, `assert hasattr(qa_loop, "answer")`, `assert mock_ensure_weaviate() is True`. Keep at most the subprocess "config import doesn't hang" test; delete the rest.
- **`test_frontend_smoke.py`** — ~80 lines of stub for one load-bearing `assert_called_once`. Trim the stub or accept as a thin import-smoke test.

### Integration tier
- **`test_startup_validation_integration.py`** — every test is mocked or trivial (`assert hasattr(config, "OLLAMA_MODEL")`, `assert WEAVIATE_URL is not None`). `test_retrieval_with_local_vectorization` is a verbatim dup of `unit/test_search_logic.py::test_retrieval_uses_local_embedding_model`. Gut it.
- **`test_ml_environment.py`** — drop torch-version/MKL/NMS/shape machine checks (`assert hasattr(torch.backends, "mkl")`, `torchvision.ops.nms(...)`); they test the machine + uv, not our code. Relocate the one valuable test (`test_torch_variant_resolution_forks_correctly`, reads `uv export --frozen`) to unit — it's a packaging tripwire.
- **`test_ingest_pipeline_compose.py`** — keep `test_ingest_pipeline_with_real_weaviate_compose` (the 1 real test); the other 3 use a mocked Weaviate behind `@requires_weaviate` and assert mock call counts. Drop or move.

### E2E / UI tier
- **`test_cli_script_e2e.py`** — runs `cli.py` in a subprocess but with `RAG_SKIP_STARTUP_CHECKS=1` + `RAG_FAKE_ANSWER`, then `assert "Mocked answer." in out` (asserts its own injected string). Exercises only argparse + the fake hook. Downgrade to integration, or make it use the real path.
- **`ui/test_app_smoke.py`** — 8 tests over a faked backend; `test_server_is_fully_responsive` is byte-identical to `test_root_health`; locator-only tests check Streamlit/Playwright, not our code. Prune to ~1 real interaction test.

## ⏸️ Verification (not yet run)
- Run full suite at end (`make unit` + `make integration`) once the FIX work lands. Per testing rule, verify the 3 moved tests pass under the unit tier's socket-blocking.
- Nothing committed yet for Pass 1 — review the staged diff before committing.

## KEEP (the genuinely valuable tests — do not touch)
`test_model_import_chain`, `test_qa_loop_logic`, `test_ollama_client_unit`, `test_cli_error_handling_unit`,
`test_supports_encode_protocol_unit`, `test_logging_config`, `test_e2e_diagnostics_unit`, `test_ingest_pdf_unit`,
`test_weaviate_client_close`, `test_config_get_service_url_unit`, `test_startup_model_check_unit` (borderline),
`integration/test_cross_encoder_environment`, `integration/test_qa_real_ollama_compose`,
`integration/test_vectorizer_enabled_compose`, `e2e/test_qa_real_end_to_end_container_e2e`,
`e2e/test_weaviate_bootstrap_missing_collection_e2e`.
