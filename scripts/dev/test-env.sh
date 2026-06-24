#!/usr/bin/env bash
set -euo pipefail

# Orchestrates the docker-compose based test environment.
#
# The test stack uses a single FIXED compose project name (kri-local-rag-test),
# mirroring how the live stack reuses "kri-local-rag". up/down/clean operate on
# that one project; there is no per-run id to mint, persist, or orphan.
#
# Concurrency note: running N isolated test stacks on one host is intentionally
# NOT supported. The fixed host ports below already block it (two stacks collide
# on the same ports regardless of project name). If concurrent stacks are ever
# wanted back, a per-run project name AND per-run ports must return together —
# the two features are coupled; reviving one without the other is a no-op.

LOG_DIR=${LOG_DIR:-logs}
BUILD_HASH_FILE=${BUILD_HASH_FILE:-.test-build.hash}
COMPOSE_FILE=${COMPOSE_FILE:-docker/docker-compose.yml}
PROFILE=${PROFILE:-test}
# Fixed project name (overridable via env as an escape hatch).
PROJECT_NAME=${COMPOSE_PROJECT_NAME:-kri-local-rag-test}
COMPOSE=(docker compose -f "$COMPOSE_FILE" --profile "$PROFILE")
BUILD_DEPS=(pyproject.toml uv.lock docker/app.Dockerfile docker/docker-compose.yml)
TEST_IMAGE=${TEST_IMAGE:-kri-local-rag-app:test}
# Centralized service list used by up/logs
SERVICES=(weaviate ollama app-test)

# Distinct host ports so the test stack can run alongside the live stack (which uses
# the compose defaults 8080/50051/11434). Container-side ports are unchanged, so the
# in-network DNS used by app-test (weaviate:8080, ollama:11434) is unaffected. Override
# if these collide with something else on the host.
export WEAVIATE_HTTP_HOST_PORT=${WEAVIATE_HTTP_HOST_PORT:-18080}
export WEAVIATE_GRPC_HOST_PORT=${WEAVIATE_GRPC_HOST_PORT:-50052}
export OLLAMA_HOST_PORT=${OLLAMA_HOST_PORT:-21434}
# app-test inherits app's port mapping via `extends`; give it a distinct host port
# (it runs `tail -f /dev/null`, so nothing actually serves here — this only avoids a
# bind collision with the live app on 8501).
export APP_HOST_PORT=${APP_HOST_PORT:-18501}

# Minimal logging helpers
log() { echo "$*"; }
warn() { echo "$*" >&2; }
err() { echo "$*" >&2; }

usage() {
  cat <<EOF
Usage: $0 <command> [options]
Commands:
  up [--force|-f]        Start docker test env (rebuild if --force)
  down                   Stop docker test env, preserving volumes
  logs [--lines|-n N]    Show logs from app-test/weaviate/ollama
  run-integration        Run integration tests inside app-test container
  run-e2e                Run E2E tests tests inside app-test container
  build-if-needed        Rebuild image if deps changed
  clean                  Remove test volumes and build metadata
EOF
}

ensure_repo_root() {
  if [[ ! -f "$COMPOSE_FILE" ]]; then
    err "Compose file '$COMPOSE_FILE' not found. Run from repo root."
    exit 1
  fi
}

# Wrapper for docker compose that pins the fixed project name.
dc() {
  COMPOSE_PROJECT_NAME="$PROJECT_NAME" "${COMPOSE[@]}" "$@"
}

# Return 0 if the test compose project has any containers
is_env_running() {
  dc ps -q 2>/dev/null | grep -q .
}

build_if_needed() {
  mkdir -p "$LOG_DIR"
  # Hash the build deps list deterministically
  local new_hash
  new_hash=$(sha256sum "${BUILD_DEPS[@]}" | sha256sum | awk '{print $1}')
  local old_hash=""
  if [[ -f "$BUILD_HASH_FILE" ]]; then
    old_hash=$(<"$BUILD_HASH_FILE")
  fi
  if [[ "$new_hash" != "$old_hash" ]] || ! docker image inspect "$TEST_IMAGE" >/dev/null 2>&1; then
    log "Build deps changed or image missing; rebuilding images..."
    DOCKER_BUILDKIT=1 dc build app-test 2>&1 | tee "$LOG_DIR/test-build.log"
    echo "$new_hash" > "$BUILD_HASH_FILE"
  else
    log "Build deps unchanged; skipping 'docker compose build'."
  fi
}

cmd_up() {
  local force=0
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --force|-f) force=1; shift ;;
      *) break ;;
    esac
  done

  if (( force == 0 )) && is_env_running; then
    log "Test env (project $PROJECT_NAME) already running."
    log "Use 'make test-down' to stop it, or 'make test-logs' to view logs."
    return 0
  fi

  if (( force == 1 )); then
    rm -f "$BUILD_HASH_FILE" || true
  fi

  build_if_needed
  log "Starting test environment (project $PROJECT_NAME)..."
  dc up -d --wait --wait-timeout 120 "${SERVICES[@]}"
  log "Test environment started."
}

cmd_down() {
  log "Stopping test environment (project $PROJECT_NAME, preserving volumes) ..."
  # Plain 'down' keeps named volumes so the next 'up' can reuse them.
  dc down
}

cmd_logs() {
  local lines=${LINES:-200}
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --lines|-n) lines="$2"; shift 2 || true ;;
      *) break ;;
    esac
  done
  log "Fetching logs for test environment (project $PROJECT_NAME) ..."
  dc logs -n "$lines" "${SERVICES[@]}"
}

cmd_run_integration() {
  if ! is_env_running; then
    err "No active test environment found. Run 'make test-up' first."
    exit 1
  fi
  # Set TEST_DOCKER=true to indicate we're running in Docker test environment
  dc exec -T -e TEST_DOCKER=true app-test /opt/venv/bin/python3 -m pytest tests/integration -q --junitxml=reports/junit_compose_integration.xml
}

cmd_run_e2e() {
  if ! is_env_running; then
    err "No active test environment found. Run 'make test-up' first."
    exit 1
  fi
  mkdir -p reports
  # Set TEST_DOCKER=true to indicate we're running in Docker test environment
  dc exec -T -e TEST_DOCKER=true app-test /opt/venv/bin/python3 -m pytest tests/e2e -q --junitxml=reports/junit_compose_e2e.xml
}

cmd_build_if_needed() {
  build_if_needed
}

cmd_clean() {
  log "Removing test environment (project $PROJECT_NAME) and its volumes ..."
  dc down -v
  rm -f "$BUILD_HASH_FILE" || true
  echo "Test volumes and build cache cleaned."
}

main() {
  local cmd=${1:-}
  shift || true
  # Enforce repo root for actionable commands
  case "$cmd" in
    -h|--help|help|"") ;;
    *) ensure_repo_root ;;
  esac
  case "$cmd" in
    up) cmd_up "$@" ;;
    down) cmd_down ;;
    logs) cmd_logs "$@" ;;
    run-integration) cmd_run_integration ;;
    run-e2e) cmd_run_e2e ;;
    build-if-needed) cmd_build_if_needed "$@" ;;
    clean) cmd_clean ;;
    -h|--help|help|"") usage ;;
    *) echo "Unknown command: $cmd"; usage; exit 1 ;;
  esac
}

main "$@"
