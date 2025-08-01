#!/bin/bash
# This script automates the full first-time setup for the kri-local-rag project.
# It builds the necessary Docker images and starts all services.

# Exit immediately if a command exits with a non-zero status.
# The -o pipefail ensures that a pipeline command is treated as failed if any of its components fail.
set -e -o pipefail

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

# Setup logging
SCRIPT_NAME=$(get_script_name "${BASH_SOURCE[0]}")
LOG_FILE=$(get_log_file "$SCRIPT_NAME")
setup_logging "$SCRIPT_NAME"

# Ensure helper scripts are executable
chmod +x scripts/cli.sh scripts/ingest.sh scripts/docker-reset.sh || true

# --- Step 1: Build Docker Images ---
echo ""
log_message "INFO" "Starting Docker image build process"
echo -e "${BOLD}--- Step 1: Building custom Docker images... ---${NC}"
echo "This may take a few minutes. Detailed output is being saved to '$LOG_FILE'."
docker compose --file "$DOCKER_COMPOSE_FILE" build --progress=plain "${SERVICES_BUILD[@]}" 2>&1 | tee -a "$LOG_FILE"
echo -e "${GREEN}✓ Build complete.${NC}"


# --- Step 2: Start Services ---
echo ""
log_message "INFO" "Starting Docker services"
echo -e "${BOLD}--- Step 2: Starting all Docker services... ---${NC}"
echo "This can take a long time on the first run as models are downloaded."
echo "The script will wait for all services to report a 'healthy' status."
echo "Detailed output is being saved to '$LOG_FILE'."
docker compose --file "$DOCKER_COMPOSE_FILE" up --detach --wait "${SERVICES_UP[@]}" 2>&1 | tee -a "$LOG_FILE"
echo -e "${GREEN}✓ All services are up and healthy.${NC}"


# --- Step 3: Verify Final Status ---
echo ""
log_message "INFO" "Verifying final service status"
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