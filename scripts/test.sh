#!/usr/bin/env bash
set -euo pipefail

# Always run from repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

PY=".venv/bin/python"
COMPOSE_FILE="$REPO_ROOT/docker/docker-compose.yml"

usage() {
  echo "Usage: $0 {unit|integration|e2e|ui} [pytest args...]" >&2
  exit 1
}

if [[ $# -lt 1 ]]; then
  usage
fi

bundle="$1"; shift || true

case "$bundle" in
  unit)
    exec "$PY" -m pytest tests/unit -q "$@"
    ;;
  integration)
    exec "$PY" -m pytest tests/integration -q "$@"
    ;;
  e2e)
    # Bring up full stack, run e2e, then tear down. Honor TEARDOWN_DOCKER/KEEP_DOCKER_UP envs.
    set -x
    docker compose -f "$COMPOSE_FILE" up -d --wait
    set +x
    # Ensure cleanup on exit unless KEEP_DOCKER_UP=1
    cleanup() {
      if [[ -n "${KEEP_DOCKER_UP:-}" && "$KEEP_DOCKER_UP" != "0" && "$KEEP_DOCKER_UP" != "false" ]]; then
        echo "[test.sh] Leaving Docker stack up (KEEP_DOCKER_UP set)."
        return 0
      fi
      echo "[test.sh] Tearing down Docker stack (down, preserving volumes)…"
      docker compose -f "$COMPOSE_FILE" down || true
    }
    trap cleanup EXIT INT TERM
    "$PY" -m pytest tests/e2e -q "$@"
    ;;
  ui)
    # UI suite requires no coverage and Playwright browsers installed
    exec "$PY" -m pytest tests/ui --no-cov -q "$@"
    ;;
  *)
    usage
    ;;
esac


