---
paths:
  - "**/*.py"
last_verified: 2026-06-24
---
## Linting, Formatting & Types

- **Ruff** is the single tool for Python lint + format (config in `pyproject.toml`: line length 120, double quotes). Runs on save and on commit. Headless: `ruff check . --fix` then `ruff format .`.
- **No `print`** in app or test code — Ruff `T201` enforces this. Use `logging` (see `logging.md`).
- **Pyright** for type checking (`pyrightconfig.json`). Headless: `make pyright` or `pyright .`. Use `# type: ignore[...]` sparingly, always with a justifying comment.
- Pyright `include`=`[backend]`; underscore helpers used only by `cli.py`/tests trip `reportUnusedFunction` — make cross-module helpers public.
