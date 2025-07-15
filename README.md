# kri-local-rag

Local RAG system using Weaviate, Ollama, and Python.

---

## Prerequisites
- Docker & Docker Compose
- 8GB+ RAM
- NVIDIA GPU (optional)
- Linux/WSL2

---

## Installation & Startup

### First-Time Setup: run these parts one by one:

```bash
# Part 1: Clone the repo and cd in:
git clone https://github.com/KristjanHS/kri-local-rag
cd kri-local-rag

# Part 2: Set environment variables and build images:
export COMPOSE_FILE=docker/docker-compose.yml  # Tells Docker Compose exactly which file to use.
export COMPOSE_PROJECT_NAME=kri-local-rag  # Sets a custom name for your project.
export BUILDKIT_PROGRESS=plain  # Ensures the Docker build output is shown as a continuous, plain-text log instead of the default progress bars.
docker compose build --progress=plain 2>&1 | tee build.log
# Wait until you see in the foreground that all builds completed successfully
  # The "2>&1 | tee build.log" pipes all output (both standard output and errors) to the tee command,
  # which simultaneously displays it on your screen and saves it to a file named build.log.

# Part 3: Start core services in the foreground (watch logs for errors or readiness):
docker compose up weaviate t2v-transformers ollama
# Wait until you see in the foreground that Weaviate and Ollama are ready. Use Ctrl+C to stop when services started up successfully.

# Part 4: This script will start services in the background and wait for them to be healthy before launching the CLI/backend:
./run-rag-cli.sh 
```

### Subsequent Launches

After the initial build, you can use the helper script to start services and the backend. 
This script will start services in the background and wait for them to be healthy before launching the CLI/backend:
```bash
./run-rag-cli.sh
```

For all other Docker usage, troubleshooting, and advanced commands, see [Docker Management Guide](docs/docker-management.md).

---

### Ingest Documents
```bash
docker compose run --rm rag-backend python ingest_pdf.py
```

### Ask Questions
```
> What is this document about?
> How does the system work?
> Can you summarize the key points?
```

For detailed document processing, see [Document Processing Guide](docs/document-processing.md).

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

## Troubleshooting & Service Management

For all Docker/service management and troubleshooting, see [Docker Management Guide](docs/docker-management.md).

---

## Resetting the Database

To delete all persistent data (including the Weaviate database), run:

```bash
docker compose down -v
```

This will remove all Docker volumes, including the Weaviate database volume, and delete all data.

Other documentation files refer to this section for database reset instructions.

---

## Data Locations

- **Weaviate data**: `.weaviate_db` directory at the project root (visible in WSL/Linux as <project-root>/.weaviate_db)
- **Ollama models**: `.ollama_models` directory at the project root (visible in WSL/Linux as <project-root>/.ollama_models)
- **Source documents**: Local `data/` directory

---

## Documentation

This project contains additional documentation in the `docs/` directory:

- [Development Guide](docs/DEVELOPMENT.md) – Development workflow and best practices
- [Docker Management](docs/docker-management.md) – Docker container management
- [Document Processing](docs/document-processing.md) – Document ingestion and processing
- [Embedding Model Selection](docs/embedding-model-selection.md) – Guide for changing or understanding embedding models

## License

MIT License - see [LICENSE](LICENSE) file.

