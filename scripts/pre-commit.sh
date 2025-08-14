#!/usr/bin/env bash
# Git pre-commit hook for running local CI (with act)
if [[ "$SKIP_LOCAL_SEC_SCANS" != "1" ]]; then
  if [[ -x ".venv/bin/detect-secrets" ]]; then
    echo "INFO: Running detect-secrets scan …"
    .venv/bin/detect-secrets scan .
  else
    if command -v detect-secrets >/dev/null 2>&1; then
      echo "INFO: Running detect-secrets scan (system install) …"
      detect-secrets scan .
    else
      echo "WARN: 'detect-secrets' not found in venv or system. Skipping secrets scan. Install with: pip install detect-secrets"
    fi
  fi
else
  echo "INFO: Skipping detect-secrets due to SKIP_LOCAL_SEC_SCANS=1"
fi