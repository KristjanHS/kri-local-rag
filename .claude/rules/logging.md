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
- Test logging config lives in `pyproject.toml` (`[tool.pytest.ini_options]`): console at INFO, `reports/test_session.log` at DEBUG.
