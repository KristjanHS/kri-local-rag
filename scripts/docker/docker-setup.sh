#!/bin/bash
# This script automates the full first-time setup for the kri-local-rag project.
# It builds the necessary Docker images and starts all services.

# Exit immediately if a command exits with a non-zero status.
# The -o pipefail ensures that a pipeline command is treated as failed if any of its components fail.
set -Eeuo pipefail

# --- ANSI Color Codes for beautiful output ---
GREEN='\033[0;32m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# --- Prerequisite Check ---
command -v docker >/dev/null 2>&1 || { echo >&2 "Docker is not installed. Please install it to continue."; exit 1; }
# Check for 'docker compose' subcommand
docker compose version >/dev/null 2>&1 || { echo >&2 "'docker compose' command not found. Please ensure you have a recent version of Docker with Compose V2."; exit 1; }


# --- Confirmation Prompt ---
echo -e "${BOLD}Welcome to the automated RAG project setup!${NC}"
echo ""
echo "This script will perform a full, first-time setup by:"
echo "  1. Building the necessary Docker images for the part(s) you select (cli, app, or both)."
echo "  2. Starting all services (Weaviate, Ollama, Transformers, etc.)."
echo ""
echo -e "${BOLD}IMPORTANT:${NC} The first run can be very slow (10-20 minutes or more on a fast connection) as it needs to download several gigabytes of models and dependencies. Subsequent runs will be much faster."
echo ""
read -p "Are you ready to begin? Type 'yes' to continue: " confirmation

if [ "$confirmation" != "yes" ]; then
    echo "Setup cancelled by user."
    exit 0
fi

echo ""
echo -e "${GREEN}--- Confirmation received. Starting setup... ---${NC}"


# --- Build Mode Selection ---
echo ""
echo -e "${BOLD}The APP container now supports both web app and CLI functionality.${NC}"
echo "This will build and start the unified APP service that provides:"
echo "  • Streamlit web interface at http://localhost:8501"
echo "  • CLI access via ./cli.sh"
echo "  • Live code changes (no rebuilds needed)"

SERVICES_BUILD=(app)
SERVICES_UP=(weaviate ollama app)

echo ""
echo -e "${BOLD}Services that will be started: ${SERVICES_UP[*]}${NC}"


# --- Script Start ---
echo -e "${BOLD}Starting the automatic setup for the RAG project...${NC}"

# Source centralized configuration
source "$(dirname "${BASH_SOURCE[0]}")/../common.sh"

# Setup logging (timestamped file + stable symlink) and traps early
SCRIPT_NAME=$(get_script_name "${BASH_SOURCE[0]}")
LOG_FILE=$(init_script_logging "$SCRIPT_NAME")
enable_error_trap "$LOG_FILE" "$SCRIPT_NAME"
enable_debug_trace "$LOG_FILE"
log INFO "Starting $SCRIPT_NAME" | tee -a "$LOG_FILE"

# Single source of truth: read the default model from backend/config.py
# (awk parse, no Python import needed). config.py is canonical; .env's
# OLLAMA_MODEL still overrides at runtime via ${OLLAMA_MODEL:-...} below.
DEFAULT_OLLAMA_MODEL=$(awk -F"['\"]" '/^DEFAULT_OLLAMA_MODEL\s*=/ {print $2}' "$PROJECT_ROOT/backend/config.py")
if [ -z "$DEFAULT_OLLAMA_MODEL" ]; then
    log ERROR "Could not read DEFAULT_OLLAMA_MODEL from backend/config.py" | tee -a "$LOG_FILE"
    exit 1
fi

# --- App image build cache (mirrors scripts/dev/test-env.sh) ---
# Rebuilding the app image is cheap when cached, but a cached BuildKit rebuild
# still mints a NEW image ID, which makes `compose up` recreate the app container
# and re-wait its Streamlit healthcheck (~10s). We therefore gate the rebuild on a
# hash of its inputs so the warm path stays fast. Set FORCE=1 to rebuild anyway.
# Derive the app image name from the compose `app` service so a rename there can't
# silently break the gate (a wrong literal would make `docker image inspect` always
# miss → rebuild every run). Falls back to the known literal if parsing turns up empty.
APP_IMAGE=$(awk '/^  [a-zA-Z]/ { in_app = ($1 == "app:") } in_app && $1 == "image:" { print $2; exit }' "$DOCKER_COMPOSE_FILE")
APP_IMAGE="${APP_IMAGE:-kri-local-rag-app}"
APP_BUILD_HASH_FILE="${APP_BUILD_HASH_FILE:-.app-build.hash}"
APP_BUILD_DEPS=(pyproject.toml uv.lock docker/app.Dockerfile docker/docker-compose.yml)
FORCE_BUILD="${FORCE:-0}"

# Emit a sha256 digest of stdin/args, portable across Linux (sha256sum) and macOS (shasum).
sha256() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$@"
    elif command -v shasum >/dev/null 2>&1; then
        shasum -a 256 "$@"
    else
        log ERROR "Neither sha256sum nor shasum is available; cannot hash build inputs." | tee -a "$LOG_FILE"
        return 1
    fi
}

build_app_if_needed() {
    local new_hash old_hash=""
    new_hash=$(sha256 "${APP_BUILD_DEPS[@]}" | sha256 | awk '{print $1}') || return 1
    if [ -f "$APP_BUILD_HASH_FILE" ]; then
        old_hash=$(<"$APP_BUILD_HASH_FILE")
    fi
    if [ "$FORCE_BUILD" != "1" ] && [ "$new_hash" = "$old_hash" ] \
        && docker image inspect "$APP_IMAGE" >/dev/null 2>&1; then
        log INFO "Build inputs unchanged and image present; skipping app rebuild (FORCE=1 to override)." | tee -a "$LOG_FILE"
        return 0
    fi
    ./scripts/docker/build_app.sh
    echo "$new_hash" > "$APP_BUILD_HASH_FILE"
}

# Ensure helper scripts are executable
chmod +x scripts/cli.sh scripts/ingest.sh scripts/docker/docker-reset.sh scripts/docker/build_app.sh || true

# --- Step 1: Build Docker Images ---
echo ""
log INFO "Starting Docker image build process" | tee -a "$LOG_FILE"
echo -e "${BOLD}--- Step 1: Building custom Docker images... ---${NC}"
echo "This may take a few minutes. Detailed output is being saved to '$LOG_FILE'."
run_step "Build app image" "$LOG_FILE" build_app_if_needed
echo -e "${GREEN}✓ Build complete.${NC}"

# --- Step 2: Start Services ---
echo ""
log INFO "Starting Docker services" | tee -a "$LOG_FILE"
echo -e "${BOLD}--- Step 2: Starting all Docker services... ---${NC}"
echo "This can take a long time on the first run as models are downloaded."
echo "The script will wait for all services to report a 'healthy' status."
echo "Detailed output is being saved to '$LOG_FILE'."

compose_up_with_logs() {
    # Plain 'up' reuses already-healthy containers (~2s warm path) instead of cold-starting
    # everything (~17s). The weaviate eth0-IP restart race that previously prompted
    # --force-recreate is handled at the source by `restart: on-failure` on the weaviate service
    # (see compose file): if memberlist dies with "No private IP address found", Docker re-runs
    # the container once eth0 has its IP, and `up --wait` still converges — without taxing every
    # startup with a full teardown + cold start.
    if docker compose --file "$DOCKER_COMPOSE_FILE" up --detach --wait "${SERVICES_UP[@]}"; then
        return 0
    else
        rc=$?
        log ERROR "Compose up failed (exit $rc). Dumping recent app logs and environment…" | tee -a "$LOG_FILE"
        # Dump last 200 lines of app logs if container exists
        docker compose --file "$DOCKER_COMPOSE_FILE" ps app 2>&1 | tee -a "$LOG_FILE" || true
        docker compose --file "$DOCKER_COMPOSE_FILE" logs --no-color --tail=200 app 2>&1 | tee -a "$LOG_FILE" || true
        # Try a one-off debug shell to inspect PATH inside the image
        docker compose -f "$DOCKER_COMPOSE_FILE" run --rm --no-deps --entrypoint bash app -lc '
            echo "=== Debug (post-failure): PATH/which ===";
            echo "PATH=$PATH";
            which python || true; python -V || true;
            which streamlit || true; python -m streamlit --version || true;
        ' 2>&1 | tee -a "$LOG_FILE" || true
        return $rc
    fi
}

run_step "Compose up services: ${SERVICES_UP[*]}" "$LOG_FILE" compose_up_with_logs
echo -e "${GREEN}✓ All services are up and healthy.${NC}"


# --- Step 2b: Pre-pull default Ollama model to reduce first-answer latency ---
ensure_ollama_model() {
    # Use centralized Ollama model default
    model_to_pull="${OLLAMA_MODEL:-$DEFAULT_OLLAMA_MODEL}"
    log INFO "Checking if Ollama model is present: ${model_to_pull}" | tee -a "$LOG_FILE"
    
    if docker compose -f "$DOCKER_COMPOSE_FILE" exec -T "$OLLAMA_SERVICE" ollama list | grep -q "$model_to_pull"; then
        log INFO "Ollama model '${model_to_pull}' already present; skipping pull." | tee -a "$LOG_FILE"
    else
        log INFO "Pulling Ollama model '${model_to_pull}' (this may take a long time on first run)…" | tee -a "$LOG_FILE"
        
        if docker compose -f "$DOCKER_COMPOSE_FILE" exec -T "$OLLAMA_SERVICE" ollama pull "$model_to_pull"; then
            log INFO "Successfully pulled Ollama model '${model_to_pull}'." | tee -a "$LOG_FILE"
        else
            log WARN "Failed to pre-pull Ollama model '${model_to_pull}'. The app will attempt to download it on first use." | tee -a "$LOG_FILE"
        fi
    fi
}

echo "" 
log INFO "Ensuring default Ollama model is downloaded" | tee -a "$LOG_FILE"
echo -e "${BOLD}--- Step 2b: Pre-pulling default Ollama model (optional) ---${NC}"
run_step "Pre-pull Ollama model" "$LOG_FILE" ensure_ollama_model


# --- Step 3: Verify Final Status ---
echo ""
log INFO "Verifying final service status" | tee -a "$LOG_FILE"
echo -e "${BOLD}--- Step 3: Verifying final service status... ---${NC}"
docker compose --file "$DOCKER_COMPOSE_FILE" ps 2>&1 | tee -a "$LOG_FILE"


# --- Success ---
echo ""
log_message "INFO" "Docker setup completed successfully"
echo -e "${GREEN}${BOLD}========================================${NC}"
echo -e "${GREEN}${BOLD}✅ Setup Complete!${NC}"
echo -e "${GREEN}${BOLD}========================================${NC}"
echo ""
echo "The selected services are now running in the background."

# Post-setup hints
echo -e "You can access the Streamlit app at: ${BOLD}http://localhost:8501${NC}"
echo "To open an interactive RAG CLI shell, run: ./scripts/cli.sh (starts cli.py by default)"
echo ""
echo "To stop all services, run: docker compose --file $DOCKER_COMPOSE_FILE down"
echo "To completely reset the environment, run: ./scripts/docker/docker-reset.sh"
echo "" 
