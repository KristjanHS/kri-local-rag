#!/usr/bin/env bash
set -euo pipefail

# Always run from repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

PY=".venv/bin/python"
COMPOSE_FILE="$REPO_ROOT/docker/docker-compose.yml"

# Default behavior: keep containers up for fast iterations
KEEP_UP=true
TEARDOWN=false
for arg in "$@"; do
  if [[ "$arg" == "--keep-docker-up" ]]; then
    KEEP_UP=true
    break
  elif [[ "$arg" == "--teardown-docker" ]]; then
    TEARDOWN=true
  fi
done

# Env overrides
if [[ -n "${TEARDOWN_DOCKER:-}" ]] && [[ "$TEARDOWN_DOCKER" != "0" ]] && [[ "$TEARDOWN_DOCKER" != "false" ]]; then
  TEARDOWN=true
fi
if [[ -n "${KEEP_DOCKER_UP:-}" ]] && [[ "$KEEP_DOCKER_UP" != "0" ]] && [[ "$KEEP_DOCKER_UP" != "false" ]]; then
  KEEP_UP=true
fi

cleanup() {
  # Skip cleanup unless teardown explicitly requested
  if [[ "$TEARDOWN" != true ]] && [[ "$KEEP_UP" == true ]]; then
    echo "[pytest_with_cleanup] Skipping cleanup (keep requested)."
    return 0
  fi

  echo "[pytest_with_cleanup] Cleaning up docker compose services (down -v)…"
  docker compose -f "$COMPOSE_FILE" down -v || true

  echo "[pytest_with_cleanup] Cleaning up Testcontainers leftovers (containers, networks)…"
  # Remove Testcontainers-managed containers
  mapfile -t TC_CONTAINERS < <(docker ps -aq -f "label=org.testcontainers") || true
  if [[ ${#TC_CONTAINERS[@]} -gt 0 ]]; then
    docker rm -f "${TC_CONTAINERS[@]}" || true
  fi

  # Remove Testcontainers-managed networks
  mapfile -t TC_NETWORKS < <(docker network ls -q -f "label=org.testcontainers") || true
  if [[ ${#TC_NETWORKS[@]} -gt 0 ]]; then
    docker network rm "${TC_NETWORKS[@]}" || true
  fi
}

trap cleanup EXIT INT TERM

# Ensure pytest uses our virtualenv Python
exec "$PY" -m pytest "$@"


