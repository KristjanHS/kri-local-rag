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
source "$(dirname "${BASH_SOURCE[0]}")/config.sh"

# Setup logging (timestamped file + stable symlink) and traps
SCRIPT_NAME=$(get_script_name "${BASH_SOURCE[0]}")
LOG_FILE=$(init_script_logging "$SCRIPT_NAME")
enable_error_trap "$LOG_FILE" "$SCRIPT_NAME"
enable_debug_trace "$LOG_FILE"
log INFO "Starting $SCRIPT_NAME" | tee -a "$LOG_FILE"

# Ensure helper scripts are executable
chmod +x scripts/cli.sh scripts/ingest.sh scripts/docker-reset.sh scripts/build_app.sh || true

# --- Step 1: Build Docker Images ---
echo ""
log INFO "Starting Docker image build process" | tee -a "$LOG_FILE"
echo -e "${BOLD}--- Step 1: Building custom Docker images... ---${NC}"
echo "This may take a few minutes. Detailed output is being saved to '$LOG_FILE'."
run_step "Build app image" "$LOG_FILE" ./scripts/build_app.sh
echo -e "${GREEN}✓ Build complete.${NC}"


# --- Step 2: Start Services ---
echo ""
log INFO "Starting Docker services" | tee -a "$LOG_FILE"
echo -e "${BOLD}--- Step 2: Starting all Docker services... ---${NC}"
echo "This can take a long time on the first run as models are downloaded."
echo "The script will wait for all services to report a 'healthy' status."
echo "Detailed output is being saved to '$LOG_FILE'."
run_step "Compose up services: ${SERVICES_UP[*]}" "$LOG_FILE" docker compose --file "$DOCKER_COMPOSE_FILE" up --detach --wait "${SERVICES_UP[@]}"
echo -e "${GREEN}✓ All services are up and healthy.${NC}"


# --- Step 2b: Pre-pull default Ollama model to reduce first-answer latency ---
ensure_ollama_model() {
  local model_to_pull
  model_to_pull="${OLLAMA_MODEL:-cas/mistral-7b-instruct-v0.3}"
  log INFO "Checking if Ollama model is present: ${model_to_pull}" | tee -a "$LOG_FILE"
  # If already present, exit quickly
  if docker compose -f "$DOCKER_COMPOSE_FILE" exec -T "$OLLAMA_SERVICE" ollama list | grep -q "$model_to_pull"; then
    log INFO "Model '${model_to_pull}' already available." | tee -a "$LOG_FILE"
    return 0
  fi
  log INFO "Pulling Ollama model '${model_to_pull}' (this may take a long time on first run)…" | tee -a "$LOG_FILE"
  # Try to pull; do not fail the setup if the pull is unavailable or fails.
  if docker compose -f "$DOCKER_COMPOSE_FILE" exec -T "$OLLAMA_SERVICE" ollama pull "$model_to_pull"; then
    log INFO "Model '${model_to_pull}' pulled successfully." | tee -a "$LOG_FILE"
  else
    log WARN "Failed to pre-pull Ollama model '${model_to_pull}'. The app will attempt to download it on first use." | tee -a "$LOG_FILE"
  fi
  return 0
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
echo "To open an interactive RAG CLI shell, run: ./scripts/cli.sh (starts qa_loop.py by default)"
echo ""
echo "To stop all services, run: docker compose --file $DOCKER_COMPOSE_FILE down"
echo "To completely reset the environment, run: ./scripts/docker-reset.sh"
echo "" 