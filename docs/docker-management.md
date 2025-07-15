# Docker Management Guide

> **Note:** Other documentation files refer to this guide for all Docker usage, troubleshooting, and advanced commands.

> **For basic startup and quick reference commands, see the root [README.md](../README.md).**

## Services

| Service | Purpose | Port |
|---------|---------|------|
| **weaviate** | Vector database | 8080 |
| **ollama** | LLM server | 11434 |
| **t2v-transformers** | Embedding generation | 8081 |
| **rag-backend** | RAG application | - |

## Service Details

### Weaviate (Vector Database)
- **Purpose**: Stores document embeddings
- **Data**: Persisted in `./.data` volume

### Ollama (LLM Server)
- **Purpose**: Local LLM inference
- **Models**: Stored in `ollama_models` volume

### t2v-transformers (Embedding Service)
- **Purpose**: Generates text embeddings
- **GPU**: CUDA support

### rag-backend (Application)
- **Purpose**: Main RAG application
- **Dependencies**: weaviate, ollama
- **Volume**: Live-mounted project directory

## Service Operations

```bash
# Code changes (live volume mounting)
docker compose restart rag-backend

# Service management
docker compose logs -f

# Rebuilding
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
# Check service health
curl http://localhost:8080/v1/meta  # Weaviate
curl http://localhost:11434/api/tags  # Ollama - is service up, what models are available
curl http://localhost:8081/health  # Transformers
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
docker compose exec rag-backend bash
```

## Volumes & Data Management

This project uses two types of volumes:
- **Named volumes** (`ollama_models`): Managed by Docker, stored outside the project.
- **Bind mounts** (`docker/.data`): Stored inside the project directory.

### Common Commands (Work in WSL2 & Linux)

```bash
# List all project-related volumes
docker volume ls | grep kri-local-rag

# Remove old/unused volumes from previous project names
# (Refer to README.md for canonical reset instructions)
```

### Universal Backup/Restore Method (via Docker Container)

```bash
# Backup Weaviate data:
docker run --rm -v kri-local-rag_weaviate_data:/data -v $(pwd):/backup alpine tar czf /backup/weaviate_backup.tar.gz -C /data .
# Restore Weaviate data:
docker run --rm -v kri-local-rag_weaviate_data:/data -v $(pwd):/backup alpine tar xzf /backup/weaviate_backup.tar.gz -C /data .
```

### Environment-Specific Differences

On native Linux, you can directly access the filesystem path of a named volume. This is NOT the standard or recommended way on WSL2, where Docker Desktop manages data within its own virtual disk, making direct filesystem access complex.

```bash
# Example (Linux Only): Direct filesystem access
sudo ls -la /var/lib/docker/volumes/kri-local-rag_weaviate_data/_data

# Example (Linux Only): Direct filesystem backup
sudo tar czf /backup/weaviate_backup.tar.gz -C /var/lib/docker/volumes/kri-local-rag_weaviate_data/_data .
```

## Data Locations

- **Weaviate data**: `.weaviate_db` directory at the project root (visible in WSL/Linux as <project-root>/.weaviate_db)
- **Ollama models**: `.ollama_models` directory at the project root (visible in WSL/Linux as <project-root>/.ollama_models)
- **Source documents**: Local `data/` directory

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

- [Getting Started Guide](GETTING_STARTED.md)
- [Document Processing Guide](document-processing.md) 