---
paths:
  - "tests/**/*.py"
  - "**/*_test.py"
last_verified: 2026-06-23
---
## Testing

- Run pytest as a module from repo root: `.venv/bin/python -m pytest tests/unit/`.
- Folder-based suites (see `pyproject.toml` `testpaths`):
  - `tests/unit/` — fast, sockets blocked (`pytest-socket`), parallel via `-n auto` (`pytest-xdist`).
  - `tests/integration/` — one real component, network allowed.
  - `tests/e2e/` — full stack, two modes: `make e2e` (host vs localhost) and `make test-e2e` (in the app-test container). URLs resolve via `get_service_url` — never hardcode in a test.
  - `tests/ui/` — Playwright browser tests.
- Unit tests must do no real network I/O — put network behavior in integration/e2e.
- Import integration helpers (`get_service_url`, `is_service_healthy`) from `tests/integration/conftest.py` — never reimplement.
- On a failing test: state what it asserts, then the code's actual behavior, then decide which is wrong before editing. Stop and surface logs after 3 failed attempts.

## Fixture resolution & e2e assertions

- pytest ranks `conftest.py` fixtures above `pytest_plugins` plugin fixtures regardless of dir depth — a same-named root-conftest fixture silently shadows a plugin one (no logs, no side effects). Confirm which resolves with `pytest <test> --fixtures-per-test`; to override a generic default for a suite, use a closer `conftest.py`, not a plugin module.
- A real-services e2e test must reject the empty-DB / "no relevant context" fallback, not just check `returncode==0` + non-empty output (which passes against the fallback). `make e2e` writes no pytest summary to disk (only `reports/test_session-*` app logs) — read terminal output for pass/fail.
