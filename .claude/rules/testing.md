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
  - `tests/e2e/` — full stack via Docker Compose.
  - `tests/ui/` — Playwright browser tests.
- Unit tests must do no real network I/O — put network behavior in integration/e2e.
- On a failing test: state what it asserts, then the code's actual behavior, then decide which is wrong before editing. Stop and surface logs after 3 failed attempts.
