#!/usr/bin/env bash
set -euo pipefail

# Orchestrates the docker-compose based test environment.
# Usage:
#   scripts/dev/test-env.sh up [--force]
#   scripts/dev/test-env.sh down
#   scripts/dev/test-env.sh logs [--lines N]
#   scripts/dev/test-env.sh run-integration
#   scripts/dev/test-env.sh build-if-needed [--run-id ID]
#   scripts/dev/test-env.sh clean

RUN_ID_FILE=${RUN_ID_FILE:-.run_id}
LOG_DIR=${LOG_DIR:-logs}
BUILD_HASH_FILE=${BUILD_HASH_FILE:-.test-build.hash}
COMPOSE_FILE=${COMPOSE_FILE:-docker/docker-compose.yml}
PROFILE=${PROFILE:-test}
COMPOSE=(docker compose -f "$COMPOSE_FILE" --profile "$PROFILE")
BUILD_DEPS=(requirements.txt requirements-dev.txt pyproject.toml docker/app.Dockerfile docker/docker-compose.yml)
# Centralized service list used by up/logs
SERVICES=(weaviate ollama app-test)

# Minimal logging helpers
log() { echo "$*"; }
warn() { echo "$*" >&2; }
err() { echo "$*" >&2; }

ensure_repo_root() {
  if [[ ! -f "$COMPOSE_FILE" ]]; then
    err "Compose file '$COMPOSE_FILE' not found. Run from repo root."
    exit 1
  fi
}

write_run_id() {
  local id="$1"
  echo "$id" > "$RUN_ID_FILE"
}

# Return 0 if docker compose project has any containers
is_env_running() {
  local id="$1"
  if COMPOSE_PROJECT_NAME="$id" "${COMPOSE[@]}" ps -q 2>/dev/null | grep -q .; then
    return 0
  fi
  return 1
}

# Wrapper for docker compose that sets project name from arg1
dc() {
  local proj="$1"; shift
  COMPOSE_PROJECT_NAME="$proj" "${COMPOSE[@]}" "$@"
}

# Resolve a run id based on mode:
#  - require: error if no RUN_ID file/env
#  - create: generate new if missing and persist
resolve_run_id() {
  local mode=${1:-require}
  local id=${RUN_ID:-}
  if [[ -z "$id" && -f "$RUN_ID_FILE" ]]; then
    id=$(<"$RUN_ID_FILE")
  fi
  if [[ -z "$id" ]]; then
    if [[ "$mode" == "require" ]]; then
      err "No active test environment found. Run 'make test-up' first."
      return 1
    fi
    id=$(date +%s)
    write_run_id "$id"
  fi
  printf '%s\n' "$id"
}

build_if_needed() {
  local run_id="$1"
  mkdir -p "$LOG_DIR"
  # Hash the build deps list deterministically
  local new_hash
  new_hash=$(sha256sum "${BUILD_DEPS[@]}" | sha256sum | awk '{print $1}')
  local old_hash=""
  if [[ -f "$BUILD_HASH_FILE" ]]; then
    old_hash=$(<"$BUILD_HASH_FILE")
  fi
  if [[ "$new_hash" != "$old_hash" ]]; then
    log "Build deps changed; rebuilding images..."
    DOCKER_BUILDKIT=1 dc "$run_id" build app-test 2>&1 | tee "$LOG_DIR/test-build-$run_id.log"
    ln -sf "test-build-$run_id.log" "$LOG_DIR/test-build.log"
    # Prune older build logs, keep latest 5
    if ls -1t "$LOG_DIR"/test-build-*.log >/dev/null 2>&1; then
      mapfile -t _logs < <(ls -1t "$LOG_DIR"/test-build-*.log 2>/dev/null)
      if (( ${#_logs[@]} > 5 )); then
        for ((i=5; i<${#_logs[@]}; i++)); do rm -f "${_logs[$i]}"; done
      fi
    fi
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

  if [[ -f "$RUN_ID_FILE" ]]; then
    local existing_id
    existing_id=$(<"$RUN_ID_FILE")
    if is_env_running "$existing_id"; then
      if (( force == 0 )); then
        log "Test env RUN_ID=$existing_id already running."
        log "Use 'make test-down' to stop it, or 'make test-logs' to view logs."
        return 0
      fi
    else
      warn "Stale RUN_ID file found, cleaning up..."
      rm -f "$RUN_ID_FILE"
    fi
  fi

  local run_id
  run_id=$(date +%s)
  write_run_id "$run_id"

  if (( force == 1 )); then
    rm -f "$BUILD_HASH_FILE" || true
  fi

  build_if_needed "$run_id"
  log "Starting test environment with RUN_ID=$run_id..."
  dc "$run_id" up -d --wait --wait-timeout 120 "${SERVICES[@]}"
  log "Test environment started."
}

cmd_down() {
  if [[ -f "$RUN_ID_FILE" ]]; then
    local run_id
    run_id=$(<"$RUN_ID_FILE")
    log "Stopping test environment with RUN_ID=$run_id ..."
    dc "$run_id" down -v
    rm -f "$RUN_ID_FILE"
  else
    log "No active test environment found."
  fi
}

cmd_logs() {
  local lines=${LINES:-200}
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --lines|-n) lines="$2"; shift 2 || true ;;
      *) break ;;
    esac
  done
  if [[ -f "$RUN_ID_FILE" ]]; then
    local run_id
    run_id=$(<"$RUN_ID_FILE")
    log "Fetching logs for test environment with RUN_ID=$run_id ..."
    dc "$run_id" logs -n "$lines" "${SERVICES[@]}"
  else
    log "No active test environment found."
  fi
}

cmd_run_integration() {
  if [[ -f "$RUN_ID_FILE" ]]; then
    local run_id
    run_id=$(<"$RUN_ID_FILE")
    dc "$run_id" exec -T app-test /opt/venv/bin/python3 -m pytest tests/integration -q --junitxml=reports/junit_compose_integration.xml
  else
    err "No active test environment found. Run 'make test-up' first."
    exit 1
  fi
}

cmd_build_if_needed() {
  local run_id="${RUN_ID:-}"
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --run-id) run_id="$2"; shift 2 || true ;;
      *) break ;;
    esac
  done
  if [[ -z "$run_id" ]]; then
    run_id=$(resolve_run_id create)
  fi
  build_if_needed "$run_id"
}

cmd_clean() {
  rm -f "$BUILD_HASH_FILE" "$RUN_ID_FILE" || true
  echo "Test build cache cleaned."
}

usage() {
  cat <<EOF
Usage: $0 <command> [options]
Commands:
  up [--force|-f]        Start docker test env (rebuild if --force)
  down                   Stop docker test env and remove volumes
  logs [--lines|-n N]    Show logs from app-test/weaviate/ollama
  run-integration        Run integration tests inside app-test container
  build-if-needed        Rebuild image if deps changed [--run-id ID]
  clean                  Remove run/build metadata files
EOF
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
    build-if-needed) cmd_build_if_needed "$@" ;;
    clean) cmd_clean ;;
    -h|--help|help|"") usage ;;
    *) echo "Unknown command: $cmd"; usage; exit 1 ;;
  esac
}

main "$@"
