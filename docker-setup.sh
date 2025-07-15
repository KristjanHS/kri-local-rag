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
echo "  1. Building the necessary Docker images (backend, frontend)."
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


# --- Script Start ---
echo -e "${BOLD}Starting the automatic setup for the RAG project...${NC}"

# Create a logs directory if it doesn't exist
mkdir -p logs

# --- Step 1: Build Docker Images ---
echo ""
echo -e "${BOLD}--- Step 1: Building custom Docker images... ---${NC}"
echo "This may take a few minutes. Detailed output is being saved to 'logs/build.log'."
docker compose --file docker/docker-compose.yml build --progress=plain 2>&1 | tee logs/build.log
echo -e "${GREEN}✓ Build complete.${NC}"


# --- Step 2: Start Services ---
echo ""
echo -e "${BOLD}--- Step 2: Starting all Docker services... ---${NC}"
echo "This can take a long time on the first run as models are downloaded."
echo "The script will wait for all services to report a 'healthy' status."
echo "Detailed output is being saved to 'logs/startup.log'."
docker compose --file docker/docker-compose.yml up --detach --wait 2>&1 | tee logs/startup.log
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
echo "The RAG application stack is now running in the background."
echo -e "You can access the Streamlit frontend at: ${BOLD}http://localhost:8501${NC}"
echo ""
echo "To stop all services, run: docker compose --file docker/docker-compose.yml down"
echo "To completely reset the environment, run: ./docker-reset.sh"
echo "" 