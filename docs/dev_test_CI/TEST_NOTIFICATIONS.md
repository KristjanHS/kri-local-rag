# Test Notifications (Concise)

- Purpose: quick ways to run tests with notifications (color, bell, logs).

## Run

- Push → test → PR: `make push-pr`
- With notifications: `./scripts/dev/test-notification.sh [integration|unit|e2e|all]`
- VS Code: Ctrl+Shift+P → "Tasks: Run Task" → "Run Tests with Notifications"

## Options

- Extra pytest args: `PYTEST_ARGS="-x --tb=short" ./scripts/dev/test-notification.sh integration`

## Requirements

- `.venv/bin/python` must exist
- Logs: `logs/test-notification.log`
