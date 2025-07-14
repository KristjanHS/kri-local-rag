# kri-local-rag

Local RAG system using Weaviate, Ollama, and Python.

## Quick Start

```bash
git clone <your-repo-url>
cd kri-local-rag
./run-docker.sh
```

## Features

- **Vector Database** (Weaviate) - Store document embeddings
- **Local LLM** (Ollama) - Run models locally
- **Interactive Console** - Ask questions about documents
- **PDF Processing** - Ingest and embed PDFs
- **GPU Support** - Optional acceleration

## System Requirements

- Docker & Docker Compose
- 8GB+ RAM
- NVIDIA GPU (optional)
- Linux/WSL2

## Usage

### 1. Start System
```bash
./run-docker.sh
```

### 2. Ingest Documents
```bash
docker compose run --rm rag-backend python ingest_pdf.py
```

### 3. Ask Questions
```
> What is this document about?
```

## Development

### Code Changes
```bash
# Make changes to backend/ files
# Restart to pick up changes
docker compose restart rag-backend
```

### Debug Levels
```bash
docker compose run --rm rag-backend --debug-level 1
```

## Troubleshooting

### Common Issues
- **No results** - Check if documents were ingested
- **Model not found** - Wait for download or pull manually
- **GPU issues** - Check NVIDIA Container Toolkit
- **Port conflicts** - Check ports 8080, 8081, 11434

### Quick Commands
```bash
docker ps                    # Check status
docker compose logs rag-backend  # View logs
docker compose down -v && ./run-docker.sh  # Reset
```

## Documentation

- [Getting Started](docs/GETTING_STARTED.md)
- [Document Processing](docs/document-processing.md)
- [Docker Management](docs/docker-management.md)
- [Development Guide](docs/DEVELOPMENT.md)

## License

MIT License - see [LICENSE](LICENSE) file.
