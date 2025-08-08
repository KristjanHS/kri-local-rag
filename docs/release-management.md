# Release & Branch Promotion

## Promote `dev` to `main`

Use the helper script to safely promote changes from `dev` to `main` with live progress, logging, and guardrails.

### Script

```bash
./scripts/promote_dev_to_main.sh
```

### What it does
- Ensures a clean working tree
- Fetches remotes and updates `dev`
- Installs dev dependencies (if needed)
- Runs checks on `dev`:
  - Ruff lint
  - Ruff format --check
  - Pytest (fast suite per project config)
- Updates `main` and attempts fast-forward. If not possible:
  - Performs a merge from `dev` into `main`
  - Auto-resolves safe conflicts (e.g., `README.md`, `docs/`, `docs_AI_coder/`)
  - If conflicts remain, aborts and reports unresolved files
- Re-runs the same checks on `main`
- Pushes `main` to `origin`
- Switches back to `dev` at the end to continue development

### Options

- Dry run (no push):
  ```bash
  ./scripts/promote_dev_to_main.sh --dry-run
  ```
- Prefer `dev` for all conflicts (auto-resolve everything):
  ```bash
  ./scripts/promote_dev_to_main.sh --prefer-dev-all
  ```

### Output & Logs
- Live progress is printed to the terminal
- A full log is saved to `logs/promote_dev_to_main.log`

### Requirements
- Local virtual environment exists with dependencies (see `requirements-dev.txt`)
- Working tree is clean (no uncommitted changes)
- Push permissions to `origin/main`

### Notes on Branch Protection
If your repository enforces “PRs only” for `main`, a direct push may be rejected. The script will display the server message. In that case, open a PR from `dev` → `main` instead, or adjust branch protection settings.

### Troubleshooting
- Merge conflicts not auto-resolved:
  - Resolve manually and continue the merge, or re-run with `--prefer-dev-all`
- Pre-push hook runs local CI (via `act`). Failures will block the push; check the terminal and `logs/pre-push.log`
- Fast tests failing locally:
  - Run `ruff check .` and `ruff format --check .`
  - Run tests locally: `./.venv/bin/python -m pytest -q tests/`

### Exit Behavior
- On any error, the script stops and prints a clear message
- On success (or dry run), the script switches back to `dev`
