# Getting Started

This guide covers everything you need to set up, run, use, and troubleshoot the kri-local-rag system.

---

## Prerequisites
- Docker & Docker Compose
- 8GB+ RAM
- NVIDIA GPU (optional)
- Linux/WSL2

---

## Installation & Startup

### Quick Install
```bash
git clone <your-repo-url>
cd kri-local-rag
./run-docker.sh
```

### Manual Startup
```bash
export COMPOSE_FILE=docker/docker-compose.yml
export COMPOSE_PROJECT_NAME=kri-local-rag
docker compose up --build -d weaviate t2v-transformers ollama
sleep 10
docker compose run --rm rag-backend
```

For detailed Docker management, see [Docker Management Guide](docker-management.md).

---

## Using the System

### Basic Usage
```bash
# Start the console
./run-docker.sh

# Ingest documents (in a new terminal)
docker compose run --rm rag-backend python ingest_pdf.py
```

**Example questions:**
```
> What is this document about?
> How does the system work?
> Can you summarize the key points?
```

For detailed document processing, see [Document Processing Guide](document-processing.md).

---

## Docker & Service Management

For all Docker/service management and troubleshooting, see [Docker Management Guide](docker-management.md).

**Quick commands:**
```bash
docker compose up -d      # Start services
docker compose down       # Stop services
docker compose logs -f    # View logs
```

---

## Usage Options

```bash
# Debug levels
docker compose run --rm rag-backend --debug-level 1   # Basic debug
docker compose run --rm rag-backend --debug-level 2   # Detailed debug

# Filtering options
docker compose run --rm rag-backend --source pdf      # Filter by source
docker compose run --rm rag-backend --language en     # Filter by language
docker compose run --rm rag-backend --k 5             # Set number of chunks to use after re-ranking
```

---

**For troubleshooting, performance tips, and advanced usage, see:**
- [Docker Management Guide](docker-management.md)
- [Document Processing Guide](document-processing.md)

**You’re ready to use kri-local-rag!** 