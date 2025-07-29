#!/bin/bash
set -e    # It tells the shell: "Exit immediately if any command in the script returns a non-zero (error) status."

export COMPOSE_FILE=docker/docker-compose.yml
export COMPOSE_PROJECT_NAME=kri-local-rag

echo "Starting Docker services (weaviate, ollama) in background..."
docker compose up -d weaviate ollama

# Wait for Ollama
until [ "$(docker inspect -f '{{.State.Health.Status}}' $(docker compose ps -q ollama))" = "healthy" ]; do
  echo "Waiting for ollama to be healthy..."
  sleep 5
done

# Wait for Weaviate
until [ "$(docker inspect -f '{{.State.Health.Status}}' $(docker compose ps -q weaviate))" = "healthy" ]; do
  echo "Waiting for weaviate to be healthy..."
  sleep 5
done

# If arguments were passed, run them inside the CLI container; otherwise open the interactive QA shell.
if [ "$#" -gt 0 ]; then
  echo "Running command inside CLI container: $@"
  docker compose run --rm -it cli "$@"
else
  echo "Starting interactive RAG CLI shell..."
  docker compose run --rm -it cli python backend/qa_loop.py
fi

# The --rm flag tells Docker to Automatically remove the container after it exits.

# docker compose up --build -d
# -d: run the containers in the background
# --force-recreate: force the recreation of the containers
# --remove-orphans: remove orphaned containers
# --no-deps: do not start dependent containers
# --no-build: do not build the images
# --no-start: do not start the containers
# --no-recreate: do not recreate the containers
# --no-restart: do not restart the containers
