# Docker Management Guide

Run every command from the repo root. The compose file lives at `docker/docker-compose.yml`, so plain `docker compose` calls pass `-f docker/docker-compose.yml`.

## Services

| Service | Purpose | Port |
|---------|---------|------|
| weaviate | Vector database | 8080 |
| ollama | LLM server | 11434 |
| app | Streamlit UI + backend | 8501 |
| ingester (profile: ingest) | One-off ingestion utility | none |

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

Compose does not read the repo-root `.env`. It looks for `docker/.env`, next to the compose file, and the Makefile passes no `--env-file`. The repo-root `.env` is read only by host-side Python through `backend/config.py`, which covers `make cli`, `make ask` and host pytest runs. The containers get only the variables listed under `environment:` in the compose file, and `.env` is excluded from the image build.

The one variable compose itself interpolates is `OLLAMA_IMAGE`. To set it, export it in the shell, or call compose with `--env-file .env`. The `make` targets don't pass that flag.

For the host-side CLI, copy `.env.example` to `.env` and adjust:

```
LOG_LEVEL=INFO
OLLAMA_MODEL=gemma4:e4b-it-qat      # default from backend/config.py
OLLAMA_CONTEXT_TOKENS=8192
RETRIEVER_EMBEDDING_TORCH_COMPILE=false
RERANKER_CROSS_ENCODER_OPTIMIZATIONS=false
```

## Service Operations

`make stack-up` builds and starts all services and waits on their healthchecks (`compose up --wait`). `make stack-down` stops them and keeps the volumes. `make stack-reset` deletes the project's containers, images and Weaviate volume, then prunes unused Docker data across the whole host.

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
# Docker can reach the GPU (the toolkit injects nvidia-smi into the container)
docker run --rm --gpus all ubuntu nvidia-smi

# The running Ollama container sees the GPU
docker compose -f docker/docker-compose.yml exec ollama nvidia-smi
```

If the first command fails, install the NVIDIA Container Toolkit with [NVIDIA's install guide](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html).

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
# List the project's volumes (compose project name: kri-local-rag)
docker volume ls --filter label=com.docker.compose.project=kri-local-rag
```

### Backup/Restore Weaviate (via Docker Container)

```bash
# Backup Weaviate data to ./weaviate_backup.tar.gz (compose prefixes the volume with the project name):
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
sudo tar czf "$PWD/weaviate_backup.tar.gz" -C /var/lib/docker/volumes/kri-local-rag_weaviate_db/_data .
```

## Data Locations

- Weaviate data: named volume `weaviate_db`, created as `kri-local-rag_weaviate_db` because the compose file sets `name: kri-local-rag`.
- Ollama models: bind mount `model_cache/` in the repo root.
- Source documents: `data/` (bind-mounted into the app and ingester).

## Cleaning Up Containers & Images (Keep All Data)

This removes the project's containers and images and keeps your data. Both commands touch only the `kri-local-rag` compose project.

### Step 1: Stop Services and Preserve Data

```bash
# Stop the stack and keep data volumes
make stack-down
```

`docker compose down` keeps volumes. Adding `-v` deletes them, so back up Weaviate before you use it.

### Step 2: (Optional) Remove the Project's Images

```bash
# Remove the containers and every image the services use (app, Weaviate, Ollama); volumes stay
docker compose -f docker/docker-compose.yml down --rmi all
```

The next `make stack-up` rebuilds the app image and pulls Weaviate and Ollama again.

### Step 3: Verify Data Preservation

Two data stores survive the cleanup:
- `kri-local-rag_weaviate_db`: the named volume holding the Weaviate database.
- `model_cache/`: the bind mount holding downloaded Ollama models.

## Destructive Reset (Delete Volumes)

To wipe all app data managed by Compose, use:

```bash
make stack-reset
```

It asks you to type "yes", then removes the project's containers, its `kri-local-rag-*` images and the `weaviate_db` volume. Its last step runs `docker system prune -a -f`, which acts on the whole host: it deletes every stopped container, every unused network, every image no container uses and the build cache, from all projects. Ollama models in `model_cache/` stay on disk, since that is a bind mount. Back up Weaviate first if needed.
