#!/bin/bash
# Build the app image and always write logs to logs/build.log

set -Eeuo pipefail

# Source centralized config (ensures we run from project root and logs dir exists)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../common.sh"

mkdir -p "$LOGS_DIR"
SCRIPT_NAME="build_app"
BUILD_LOG_TS=$(init_script_logging "$SCRIPT_NAME")
enable_error_trap "$BUILD_LOG_TS" "$SCRIPT_NAME"
enable_debug_trace "$BUILD_LOG_TS"

# Maintain stable symlink logs/build.log → latest timestamped build log
ln -sf "$(basename "$BUILD_LOG_TS")" "$LOGS_DIR/build.log"

log INFO "Writing build output to $BUILD_LOG_TS"

# Pass through any extra flags to docker compose build (e.g., --no-cache)
# Always build the canonical app service defined in docker/docker-compose.yml
docker compose -f "$DOCKER_COMPOSE_FILE" build --progress=plain "$APP_SERVICE" "$@" 2>&1 | tee -a "$BUILD_LOG_TS"

log INFO "Build finished. Log saved at $BUILD_LOG_TS"


