---
paths:
  - "**/*.py"
  - "**/*.sh"
  - "**/*.yml"
  - "**/*.yaml"
last_verified: 2026-06-23
---
## Logging

- All log files go under the `logs/` directory at the project root — never elsewhere.
- Use structured logging with appropriate levels (DEBUG, INFO, WARNING, ERROR), not `print`.
- Use descriptive log file names (e.g. `rag_system.log`, `cli.log`).
- Test logging config in `pyproject.toml` (`[tool.pytest.ini_options]`): console INFO, file DEBUG, dated per-run by `tests/conftest.py` (`reports/test_session-<ts>.log` + `test_session.log` symlink). Never `logging.shutdown()` in tests — closes pytest's file handler.
