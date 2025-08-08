# Docker Management Guide

> **Note:** Other documentation files refer to this guide for all Docker usage, troubleshooting, and advanced commands.

> **For basic startup and quick reference commands, see the root [README.md](../README.md).**

## Services

| Service | Purpose | Port |
|---------|---------|------|
| **weaviate** | Vector database | 8080 |
| **ollama** | LLM server | 11434 |
| **app** | Streamlit UI + backend | 8501 |
| **ingester** (profile: ingest) | One-off ingestion utility | - |

## Service Details

### Weaviate (Vector Database)
- **Purpose**: Stores document embeddings
- **Data**: Persisted in named volume `weaviate_db`

### Ollama (LLM Server)
- **Purpose**: Local LLM inference
- **Models**: Stored in named volume `ollama_models`

### app (Application + UI)
- **Purpose**: Main RAG application (Streamlit UI + backend)
- **Port**: 8501
- **Depends on**: weaviate, ollama

### ingester (One-off ingestion)
- **Purpose**: Batch ingest documents
- **Profile**: `ingest`

## Service Operations

```bash
# Pick up code changes (live mounts)
docker compose restart app

# Logs
docker compose logs -f app | cat

# Rebuild images
docker compose build
```

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
docker compose exec ollama nvidia-smi

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
# Weaviate
curl http://localhost:8080/v1/meta
# Ollama (service up, list models)
curl http://localhost:11434/api/tags
# App (basic reachability)
curl -fsS http://localhost:8501 >/dev/null && echo ok
```

### Service Issues
```bash
# Check logs
docker compose logs weaviate
docker compose logs ollama
docker compose logs rag-backend

# Check status
docker ps -a
```

### Access Service Shells
```bash
docker compose exec weaviate sh
docker compose exec ollama sh
docker compose exec app bash
```

## Volumes & Data Management

Persistent data uses named volumes:
- **weaviate_db**: Weaviate database
- **ollama_models**: Ollama model cache

### Common Commands (Work in WSL2 & Linux)

```bash
# List all project-related volumes
docker volume ls | grep kri-local-rag

# Remove old/unused volumes from previous project names
# (Refer to README.md for canonical reset instructions)
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

- **Weaviate data**: named volume `weaviate_db` (prefixed to `kri-local-rag_weaviate_db`)
- **Ollama models**: named volume `ollama_models` (prefixed to `kri-local-rag_ollama_models`)
- **Source documents**: Local `data/` directory (bind-mounted)

## Cleaning Up Containers & Images (Keep All Data)

This process removes all containers and images associated with the project but preserves your persistent data volumes.

### Step 1: Stop Services and Preserve Data

First, stop the running services. It is critical to use the correct `down` command to ensure your data volumes are not deleted.

```bash
# This command stops containers but PRESERVES all persistent data volumes.
docker compose down
```

> **⚠️ Important:**
> -   `docker compose down` **preserves** data volumes.
> -   `docker compose down -v` **deletes** data volumes.
> -   Always consider creating a backup first (see backup commands in the section above).

### Step 2: (Optional) Prune Unused System Resources

If you want to free up more disk space, you can remove any remaining stopped containers and all associated Docker images.

```bash
# Force-remove any remaining stopped containers
docker rm -f $(docker ps -aq)

# Remove all Docker images (this requires re-downloading/rebuilding them later)
docker rmi -f $(docker images -q)
```

### Step 3: Verify Data Preservation

After running the cleanup, your persistent data remains safe. The following volumes are preserved:
-   **`ollama_models`**: A named volume stored outside the project, containing downloaded LLMs.
-   **`docker/.data`**: A bind mount inside the `docker` directory, containing the Weaviate database.

## Next Steps

- [Development Guide](DEVELOPMENT.md)
- [Document Processing Guide](document-processing.md)