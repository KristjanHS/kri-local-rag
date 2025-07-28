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
echo -e "${BOLD}Select which part of the stack you want to build and start:${NC}"
echo "  1) CLI only   – interactive shell with all RAG utilities (service: cli)"
echo "  2) App only   – Streamlit UI (service: app)"
echo "  3) Both       – build & start both cli and app (default)"
read -p "Enter 1, 2 or 3 [3]: " mode_choice

# Determine services based on user choice
case "$mode_choice" in
  1)
    SERVICES_BUILD=(cli)
    SERVICES_UP=(weaviate ollama cli)
    ;;
  2)
    SERVICES_BUILD=(app)
    SERVICES_UP=(weaviate ollama app)
    ;;
  *)
    SERVICES_BUILD=(cli app)
    SERVICES_UP=(weaviate ollama cli app)
    ;;
esac

echo ""
echo -e "${BOLD}You chose to build: ${SERVICES_BUILD[*]}${NC}"
echo -e "${BOLD}Services that will be started: ${SERVICES_UP[*]}${NC}"


# --- Script Start ---
echo -e "${BOLD}Starting the automatic setup for the RAG project...${NC}"

# Ensure helper scripts are executable
chmod +x cli.sh ingest.sh docker-reset.sh || true

# Create a logs directory if it doesn't exist
mkdir -p logs

# --- Step 1: Build Docker Images ---
echo ""
echo -e "${BOLD}--- Step 1: Building custom Docker images... ---${NC}"
echo "This may take a few minutes. Detailed output is being saved to 'logs/build.log'."
docker compose --file docker/docker-compose.yml build --progress=plain "${SERVICES_BUILD[@]}" 2>&1 | tee logs/build.log
echo -e "${GREEN}✓ Build complete.${NC}"


# --- Step 2: Start Services ---
echo ""
echo -e "${BOLD}--- Step 2: Starting all Docker services... ---${NC}"
echo "This can take a long time on the first run as models are downloaded."
echo "The script will wait for all services to report a 'healthy' status."
echo "Detailed output is being saved to 'logs/startup.log'."
docker compose --file docker/docker-compose.yml up --detach --wait "${SERVICES_UP[@]}" 2>&1 | tee logs/startup.log
echo -e "${GREEN}✓ All services are up and healthy.${NC}"


# --- Step 3: Verify Final Status ---
echo ""
echo -e "${BOLD}--- Step 3: Verifying final service status... ---${NC}"
docker compose --file docker/docker-compose.yml ps


# --- Success ---
echo ""
echo -e "${GREEN}${BOLD}========================================${NC}"
echo -e "${GREEN}${BOLD}✅ Setup Complete!${NC}"
echo -e "${GREEN}${BOLD}========================================${NC}"
echo ""
echo "The selected services are now running in the background."

# Tailored post-setup hints
if [[ " ${SERVICES_UP[*]} " == *" app "* ]]; then
  echo -e "You can access the Streamlit app at: ${BOLD}http://localhost:8501${NC}"
fi

if [[ " ${SERVICES_UP[*]} " == *" cli "* ]]; then
  echo "To open an interactive RAG CLI shell, run: ./cli.sh"
fi
echo ""
echo "To stop all services, run: docker compose --file docker/docker-compose.yml down"
echo "To completely reset the environment, run: ./docker-reset.sh"
echo "" 