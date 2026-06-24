#!/usr/bin/env bash
set -euo pipefail

# Orchestrates the docker-compose based test environment.

RUN_ID_FILE=${RUN_ID_FILE:-.run_id}
LOG_DIR=${LOG_DIR:-logs}
BUILD_HASH_FILE=${BUILD_HASH_FILE:-.test-build.hash}
COMPOSE_FILE=${COMPOSE_FILE:-docker/docker-compose.yml}
PROFILE=${PROFILE:-test}
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
  build-if-needed        Rebuild image if deps changed [--run-id ID]
  clean                  Remove test volumes and run/build metadata
EOF
}

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
  if [[ "$new_hash" != "$old_hash" ]] || ! docker image inspect "$TEST_IMAGE" >/dev/null 2>&1; then
    log "Build deps changed or image missing; rebuilding images..."
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

  local run_id=""
  if [[ -f "$RUN_ID_FILE" ]]; then
    local existing_id
    existing_id=$(<"$RUN_ID_FILE")
    if is_env_running "$existing_id"; then
      if (( force == 0 )); then
        log "Test env RUN_ID=$existing_id already running."
        log "Use 'make test-down' to stop it, or 'make test-logs' to view logs."
        return 0
      fi
      run_id="$existing_id"
    else
      # Env stopped but RUN_ID preserved by 'down' — reuse it so preserved
      # volumes are reattached instead of orphaned.
      log "Reusing preserved RUN_ID=$existing_id (volumes from previous run)."
      run_id="$existing_id"
    fi
  fi

  if [[ -z "$run_id" ]]; then
    run_id=$(date +%s)
  fi
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
    log "Stopping test environment with RUN_ID=$run_id (preserving volumes) ..."
    # Plain 'down' keeps named volumes so the next 'up' can reuse them.
    # Keep the RUN_ID file so 'make test-clean' can still target this project
    # to remove its volumes.
    dc "$run_id" down
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
    # Set TEST_DOCKER=true to indicate we're running in Docker test environment
    dc "$run_id" exec -T -e TEST_DOCKER=true app-test /opt/venv/bin/python3 -m pytest tests/integration -q --junitxml=reports/junit_compose_integration.xml
  else
    err "No active test environment found. Run 'make test-up' first."
    exit 1
  fi
}

cmd_run_e2e() {
  if [[ -f "$RUN_ID_FILE" ]]; then
    local run_id
    run_id=$(<"$RUN_ID_FILE")
    mkdir -p reports
    # Set TEST_DOCKER=true to indicate we're running in Docker test environment
    dc "$run_id" exec -T -e TEST_DOCKER=true app-test /opt/venv/bin/python3 -m pytest tests/e2e -q --junitxml=reports/junit_compose_e2e.xml
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
  if [[ -f "$RUN_ID_FILE" ]]; then
    local run_id
    run_id=$(<"$RUN_ID_FILE")
    log "Removing test environment with RUN_ID=$run_id and its volumes ..."
    dc "$run_id" down -v
  fi
  rm -f "$BUILD_HASH_FILE" "$RUN_ID_FILE" || true

  # Prune orphaned test projects left by earlier runs. A fresh run-id mints a new
  # "<run_id>" project (its own containers + "<run_id>_weaviate_db" volume); a plain
  # `down` preserves them, so old ones orphan across sessions. Test projects always use
  # a numeric run-id as COMPOSE_PROJECT_NAME, so this never touches the live stack
  # ("kri-local-rag"). Collect ids from both leftover containers and volumes, then tear
  # each down with -v (removes its containers and volume together).
  local ids
  ids=$( { docker volume ls -q 2>/dev/null | grep -E '^[0-9]+_weaviate_db$' | sed 's/_weaviate_db$//';
           docker ps -a --format '{{.Names}}' 2>/dev/null | grep -E '^[0-9]+-' | sed -E 's/-[a-z].*$//'; } \
         | sort -u || true)
  local id
  for id in $ids; do
    log "Pruning orphaned test project: $id"
    dc "$id" down -v --remove-orphans >/dev/null 2>&1 || true
  done
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
