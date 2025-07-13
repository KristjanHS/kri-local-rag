#!/bin/bash
export COMPOSE_FILE=docker/docker-compose.yml
export COMPOSE_PROJECT_NAME=kri-local-rag

echo "Starting Docker services (weaviate, t2v-transformers, ollama) in background..."
docker compose up --build -d weaviate t2v-transformers ollama

echo "Waiting for services to be ready..."
sleep 10

echo "Starting interactive RAG backend..."
docker compose run --rm rag-backend

# docker compose up --build -d
# -d: run the containers in the background
# --force-recreate: force the recreation of the containers
# --remove-orphans: remove orphaned containers
# --no-deps: do not start dependent containers
# --no-build: do not build the images
# --no-start: do not start the containers
# --no-recreate: do not recreate the containers
# --no-restart: do not restart the containers