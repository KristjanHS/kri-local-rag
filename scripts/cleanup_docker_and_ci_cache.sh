#!/usr/bin/env bash
# scripts/cleanup_docker_and_ci_cache.sh – Clean Docker resources and local CI (act) cache
#
# What it does
# - Shows Docker disk usage before/after
# - Prunes unused Docker data (containers, images, networks, build cache)
# - Optionally prunes builder cache (buildx)
# - Prunes dangling volumes
# - Clears local act cache (~/.cache/act)
# - Optional: restart Docker daemon (best-effort)
#
# Usage
#   ./scripts/cleanup_docker_and_ci_cache.sh                # run cleanup
#   ./scripts/cleanup_docker_and_ci_cache.sh --dry-run      # print actions without executing
#   ./scripts/cleanup_docker_and_ci_cache.sh --restart-docker
#   ./scripts/cleanup_docker_and_ci_cache.sh --skip-act-cache
#   ./scripts/cleanup_docker_and_ci_cache.sh --builder-prune
#
# Notes
# - This is safe but destructive for UNUSED Docker resources. Running containers are untouched.
# - On WSL2, restarting Docker may require restarting Docker Desktop and/or `wsl --shutdown` manually.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "${SCRIPT_DIR}/config.sh"

SCRIPT_NAME="$(get_script_name "$0")"
setup_logging "$SCRIPT_NAME"

LOG_FILE="$(get_log_file "$SCRIPT_NAME")"

DRY_RUN=0
RESTART_DOCKER=0
SKIP_ACT_CACHE=0
DO_BUILDER_PRUNE=0

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --restart-docker) RESTART_DOCKER=1 ;;
    --skip-act-cache) SKIP_ACT_CACHE=1 ;;
    --builder-prune) DO_BUILDER_PRUNE=1 ;;
    *) log WARN "Unknown argument: $arg" | tee -a "$LOG_FILE" ;;
  esac
done

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    log ERROR "Required tool '$1' not found in PATH" | tee -a "$LOG_FILE"
    exit 1
  fi
}

run_cmd() {
  local cmd=("$@")
  if [[ "$DRY_RUN" -eq 1 ]]; then
    log INFO "[dry-run] ${cmd[*]}" | tee -a "$LOG_FILE"
  else
    log INFO "$ ${cmd[*]}" | tee -a "$LOG_FILE"
    "${cmd[@]}" | tee -a "$LOG_FILE"
  fi
}

show_pre_state() {
  log INFO "▶ Docker disk usage BEFORE"
  run_cmd docker system df
  log INFO "Mounted filesystems (df -h)"
  run_cmd df -h
}

show_post_state() {
  log INFO "▶ Docker disk usage AFTER"
  run_cmd docker system df
  log INFO "Mounted filesystems (df -h)"
  run_cmd df -h
}

restart_docker_daemon() {
  log INFO "Attempting to restart Docker daemon (best-effort)…"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    log INFO "[dry-run] sudo systemctl restart docker || sudo service docker restart" | tee -a "$LOG_FILE"
    return 0
  fi
  if command -v systemctl >/dev/null 2>&1; then
    if sudo systemctl restart docker; then
      log INFO "Docker restarted via systemd" | tee -a "$LOG_FILE"
      return 0
    fi
  fi
  if command -v service >/dev/null 2>&1; then
    if sudo service docker restart; then
      log INFO "Docker restarted via service" | tee -a "$LOG_FILE"
      return 0
    fi
  fi
  log WARN "Could not automatically restart Docker. If on WSL2, consider restarting Docker Desktop and 'wsl --shutdown' manually." | tee -a "$LOG_FILE"
}

perform_cleanup() {
  # Core cleanups
  run_cmd docker system prune -af
  if [[ "$DO_BUILDER_PRUNE" -eq 1 ]]; then
    run_cmd docker builder prune -af
  fi
  run_cmd docker volume prune -f

  if [[ "$SKIP_ACT_CACHE" -eq 0 ]]; then
    # Clear local act cache
    run_cmd rm -rf "$HOME/.cache/act"
  else
    log INFO "Skipping act cache cleanup as requested" | tee -a "$LOG_FILE"
  fi
}

main() {
  need docker
  show_pre_state

  if [[ "$RESTART_DOCKER" -eq 1 ]]; then
    restart_docker_daemon
  fi

  log INFO "▶ Performing Docker and CI cache cleanup…" | tee -a "$LOG_FILE"
  perform_cleanup

  if [[ "$RESTART_DOCKER" -eq 1 ]]; then
    restart_docker_daemon
  fi

  show_post_state
  log INFO "✔ Cleanup complete" | tee -a "$LOG_FILE"
}

main "$@"


