# Docker Services

Docker configuration for the kri-local-rag system.

## Services

| Service | Purpose | Port |
|---------|---------|------|
| **weaviate** | Vector database | 8080 |
| **ollama** | LLM server | 11434 |
| **t2v-transformers** | Embedding generation | 8081 |
| **rag-backend** | RAG application | - |

## Quick Start

```bash
# Start all services
./run-docker.sh

# Manual start
export COMPOSE_FILE=docker/docker-compose.yml
export COMPOSE_PROJECT_NAME=kri-local-rag
docker compose up --build -d weaviate t2v-transformers ollama
sleep 10
docker compose run --rm rag-backend
```

## Service Details

### Weaviate (Vector Database)
- **Image**: `cr.weaviate.io/semitechnologies/weaviate:1.25.1`
- **Purpose**: Stores document embeddings
- **Port**: 8080 (external), 50051 (gRPC)
- **Data**: Persisted in `./.data` volume

### Ollama (LLM Server)
- **Image**: `ollama/ollama:latest`
- **Purpose**: Local LLM inference
- **Port**: 11434
- **Models**: Stored in `ollama_models` volume

### t2v-transformers (Embedding Service)
- **Image**: Custom build from `t2v-transformers.Dockerfile`
- **Purpose**: Generates text embeddings
- **Port**: 8081 (external)
- **GPU**: CUDA support

### rag-backend (Application)
- **Image**: Custom build from `backend.Dockerfile`
- **Purpose**: Main RAG application
- **Dependencies**: weaviate, ollama
- **Volume**: Live-mounted project directory

## Code Changes

Live volume mounting means changes are immediate:
```bash
# Make changes to backend/ files
# Restart to pick up changes
docker compose restart rag-backend
```

## Service Management

```bash
# Start services
docker compose up -d

# Stop services
docker compose down

# View logs
docker compose logs -f

# Restart specific service
docker compose restart rag-backend
```

## Rebuilding

```bash
# Rebuild specific service
docker compose build rag-backend

# Rebuild all services
docker compose build

# Force rebuild
docker compose build --no-cache
```

## GPU Support

### Requirements
- NVIDIA GPU with CUDA support
- NVIDIA Container Toolkit installed

### Verification
```bash
# Check GPU availability
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi

# Test GPU in containers
docker compose exec ollama nvidia-smi
```

## Troubleshooting

### Common Issues

**Port Conflicts**
```bash
sudo netstat -tulpn | grep :8080
sudo netstat -tulpn | grep :11434
```

**GPU Not Available**
```bash
# Check NVIDIA runtime
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi

# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

**Service Issues**
```bash
# Check logs
docker compose logs weaviate
docker compose logs ollama
docker compose logs rag-backend

# Check status
docker ps -a
```

## Debug Commands

```bash
# Access service shells
docker compose exec weaviate sh
docker compose exec ollama sh
docker compose exec rag-backend bash

# Check service health
curl http://localhost:8080/v1/meta  # Weaviate
curl http://localhost:11434/api/tags  # Ollama
curl http://localhost:8081/health  # Transformers
```

## Volumes

```bash
# List volumes
docker volume ls | grep kri-local-rag

# Backup data
docker run --rm -v kri-local-rag_weaviate_data:/data -v $(pwd):/backup alpine tar czf /backup/weaviate_backup.tar.gz -C /data .
```

## Next Steps

- [Backend Service](../backend/README.md)
- [Getting Started Guide](../docs/setup/getting-started.md)
- [Basic Usage](../docs/usage/basic-usage.md) 