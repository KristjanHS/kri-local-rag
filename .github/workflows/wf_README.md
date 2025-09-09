# GitHub Workflows Overview

This repo uses two security workflows. Edit their YAML files directly for changes.

## CodeQL
- Purpose: Code scanning for security and quality.
- File: `.github/workflows/codeql.yml` (includes a local/isolated job).
- Triggers: Push, PR, and manual (`workflow_dispatch`).
- Output: SARIF uploaded to GitHub Code Scanning.

## Semgrep
- Purpose: Static analysis with rules from Semgrep.
- File: `.github/workflows/semgrep.yml` (includes a local/isolated job).
- Triggers: Push, PR, and manual (`workflow_dispatch`).
- Output: SARIF and optional PR summary; metrics disabled.

## Run / Test
- GitHub UI: Actions → select workflow → Run workflow.
- Local (act):
  - `act workflow_dispatch -W .github/workflows/codeql.yml`
  - `act workflow_dispatch -W .github/workflows/semgrep.yml`

## Tips
- Concurrency, timeouts, and shallow fetch are set in YAML.
- For failures, check permissions, required secrets, and YAML syntax.
