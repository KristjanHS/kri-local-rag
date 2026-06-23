---
paths:
  - "**/*.py"
last_verified: 2026-06-23
---
## Linting, Formatting & Types

- **Ruff** is the single tool for Python lint + format (config in `pyproject.toml`: line length 120, double quotes). Runs on save and on commit. Headless: `ruff check . --fix` then `ruff format .`.
- **No `print`** in app or test code — Ruff `T201` enforces this. Use `logging` (see `logging.md`).
- **Pyright** for type checking (`pyrightconfig.json`). Headless: `make pyright` or `pyright .`. Use `# type: ignore[...]` sparingly, always with a justifying comment.
