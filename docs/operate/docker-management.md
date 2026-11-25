# Docker Management Guide

Run every command from the repo root. The compose file lives at `docker/docker-compose.yml`, so plain `docker compose` calls pass `-f docker/docker-compose.yml`.

## Services

| Service | Purpose | Port |
|---------|---------|------|
| **weaviate** | Vector database | 8080 |
| **ollama** | LLM server | 11434 |
| **app** | Streamlit UI + backend | 8501 |
| **ingester** (profile: ingest) | One-off ingestion utility | - |

## Service Details

### Weaviate (Vector Database)
- Purpose: stores document embeddings.
- Data: named volume `weaviate_db`.

### Ollama (LLM Server)
- Purpose: local LLM inference.
- Models: bind mount `model_cache/` in the repo root.

### app (Application + UI)
- Purpose: main RAG application (Streamlit UI + backend).
- Port: 8501.
- Depends on: weaviate, ollama.

### ingester (One-off ingestion)
- Purpose: batch ingest documents from `data/`.
- Profile: `ingest`.

## Ports and environment

Weaviate (8080, plus gRPC on 50051) and Ollama (11434) bind to `127.0.0.1` only. The app publishes 8501 on all host interfaces, so other machines on your network can reach the UI.

Compose reads `.env` from the repo root. Copy `.env.example` and adjust:

```
LOG_LEVEL=INFO
OLLAMA_MODEL=gemma4:e4b-it-qat      # default from backend/config.py
OLLAMA_CONTEXT_TOKENS=8192
RETRIEVER_EMBEDDING_TORCH_COMPILE=false
RERANKER_CROSS_ENCODER_OPTIMIZATIONS=false
OLLAMA_IMAGE=ollama/ollama:<version>   # optional; pins the Ollama image
```

## Service Operations

`make stack-up` builds and starts all services and waits on their healthchecks (`compose up --wait`). `make stack-down` stops them and keeps the volumes. `make stack-reset` is the destructive teardown at the end of this page.

```bash
# Rebuild just the app image
docker compose -f docker/docker-compose.yml build app

# Restart the app to pick up code changes
docker compose -f docker/docker-compose.yml restart app

# Follow logs
make app-logs LINES=200          # add FOLLOW=1 to tail

# Rebuild all images with no cache (slower, clean rebuild)
DOCKER_BUILDKIT=1 docker compose -f docker/docker-compose.yml build --no-cache

# Restart only Weaviate and follow its logs
docker compose -f docker/docker-compose.yml restart weaviate && docker compose -f docker/docker-compose.yml logs -f weaviate

# Open a shell in the app container with debug logging
docker compose -f docker/docker-compose.yml exec -e LOG_LEVEL=DEBUG app bash
```

## Docker Image Security

### OS Package Security Strategy

`docker/app.Dockerfile` builds on `python:3.14-slim-bookworm` and points apt at a dated Debian snapshot (`ARG SNAPSHOT`). The snapshot pins the whole OS package set, security archive included, so the `apt-get install` line names packages without versions. Bumping `SNAPSHOT` picks up security fixes in one reviewed change.

Hadolint flags unversioned installs (DL3008); the Dockerfile ignores that rule inline (`# hadolint ignore=DL3008`) because the snapshot already pins them.

## Troubleshooting

### Port Conflicts
```bash
sudo netstat -tulpn | grep :8080
sudo netstat -tulpn | grep :11434
```

### GPU Issues
```bash
# Check GPU availability
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi

# Test GPU in containers
docker compose -f docker/docker-compose.yml exec ollama nvidia-smi

# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

## Debug & Monitoring

### Service Health
```bash
# Weaviate readiness and cluster status
curl -fsS http://localhost:8080/v1/.well-known/ready && echo ready
curl -fsS http://localhost:8080/v1/meta | jq .

# Ollama: list models, pull the configured model
curl -fsS http://localhost:11434/api/tags | jq .
docker compose -f docker/docker-compose.yml exec -T ollama ollama pull gemma4:e4b-it-qat

# App reachability with headers
curl -I http://localhost:8501
```

### Service Issues
```bash
# App/Weaviate/Ollama logs (200 lines; add FOLLOW=1 to tail)
make app-logs LINES=200

# Check status
docker ps -a
```

### Access Service Shells
```bash
docker compose -f docker/docker-compose.yml exec weaviate sh
docker compose -f docker/docker-compose.yml exec ollama sh
docker compose -f docker/docker-compose.yml exec app bash
```

## Volumes & Data Management

### Common Commands (Work in WSL2 & Linux)

```bash
# List all project-related volumes
docker volume ls | grep kri-local-rag
```

### Backup/Restore Weaviate (via Docker Container)

```bash
# Backup Weaviate data (volume name usually prefixed):
docker run --rm -v kri-local-rag_weaviate_db:/data -v $(pwd):/backup alpine tar czf /backup/weaviate_backup.tar.gz -C /data .
# Restore Weaviate data:
docker run --rm -v kri-local-rag_weaviate_db:/data -v $(pwd):/backup alpine tar xzf /backup/weaviate_backup.tar.gz -C /data .
```

### Environment-Specific Differences

On native Linux you can directly access named volume paths. On WSL2 (Docker Desktop), data lives inside Docker’s VM and direct access is not recommended.

```bash
# Example (Linux Only): Direct filesystem access
sudo ls -la /var/lib/docker/volumes/kri-local-rag_weaviate_db/_data

# Example (Linux Only): Direct filesystem backup
sudo tar czf /backup/weaviate_backup.tar.gz -C /var/lib/docker/volumes/kri-local-rag_weaviate_db/_data .
```

## Data Locations

- Weaviate data: named volume `weaviate_db` (prefixed to `kri-local-rag_weaviate_db`).
- Ollama models: bind mount `model_cache/` in the repo root.
- Source documents: `data/` (bind-mounted into the app and ingester).

## Cleaning Up Containers & Images (Keep All Data)

This removes the project's containers and images and keeps your data.

### Step 1: Stop Services and Preserve Data

```bash
# Stop the stack and keep data volumes
make stack-down
```

`docker compose down` keeps volumes; `docker compose down -v` deletes them. Back up Weaviate first (see Backup/Restore Weaviate).

### Step 2: (Optional) Prune Unused System Resources

To free more disk space, remove stopped containers and images. Both commands act on every container and image on the host, not only this project's.

```bash
# Force-remove any remaining stopped containers
docker rm -f $(docker ps -aq)

# Remove all Docker images (this requires re-downloading/rebuilding them later)
docker rmi -f $(docker images -q)
```

### Step 3: Verify Data Preservation

Two data stores survive the cleanup:
- `kri-local-rag_weaviate_db`: the named volume holding the Weaviate database.
- `model_cache/`: the bind mount holding downloaded Ollama models.

## Destructive Reset (Delete Volumes)

To wipe all app data managed by Compose, use:

```bash
make stack-reset
```

This removes the project's containers, images and the `weaviate_db` volume. Ollama models in `model_cache/` stay on disk. Back up Weaviate first if needed.
