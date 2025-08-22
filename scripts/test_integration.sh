#!/bin/bash
set -euo pipefail

# Always run from repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

# Convenience wrapper for integration test bundle
# Usage: bash scripts/test_integration.sh

echo "Running integration test bundle..."

# Check if test environment is running
if [[ ! -f .run_id ]]; then
  echo "Error: Test environment not running. Run 'make test-up' first." >&2
  exit 1
fi

RUN_ID=$(cat .run_id)
echo "Running integration tests in Compose environment (RUN_ID=$RUN_ID)..."

# Run tests inside the app container
docker compose -f docker/docker-compose.yml -f docker/compose.test.yml -p "$RUN_ID" exec -T app /opt/venv/bin/python3 -m pytest tests/integration -q
