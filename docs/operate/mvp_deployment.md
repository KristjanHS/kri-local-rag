## MVP Deployment

This guide shows how to run the Local RAG MVP with Docker Compose and verify it quickly.

### Prerequisites
- Docker and Compose v2
- Disk space for models and Weaviate volume
- `.env` configured (see `.env.example`)

Key ports and exposure:
- Weaviate: 8080 (loopback-only)
- Ollama: 11434 (loopback-only)
- Streamlit app: 8501 (user-facing)

### Environment
Set variables in `.env` (example values shown):
```
LOG_LEVEL=INFO
OLLAMA_MODEL=cas/mistral-7b-instruct-v0.3  # Default defined in backend/config.py
OLLAMA_CONTEXT_TOKENS=8192
RETRIEVER_EMBEDDING_TORCH_COMPILE=false
RERANKER_CROSS_ENCODER_OPTIMIZATIONS=false
OLLAMA_URL=http://localhost:11434
WEAVIATE_URL=http://localhost:8080
```

### Start core services (recommended)
```
./scripts/docker/docker-setup.sh
```
Manual alternative (advanced users):
```
docker compose -f docker/docker-compose.yml up -d weaviate ollama
```
Verify readiness:
```
docker compose -f docker/docker-compose.yml exec -T weaviate wget -qO - http://localhost:8080/v1/.well-known/ready
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:11434/api/tags
```
If needed, pull the Ollama model specified by `OLLAMA_MODEL`:
```
docker compose -f docker/docker-compose.yml exec -T ollama ollama pull "$OLLAMA_MODEL"
```

### Start the app (Streamlit)
If you used `docker-setup.sh`, the app is already running at http://localhost:8501

Manual alternative:
```
docker compose -f docker/docker-compose.yml up -d app
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8501
```

### Ingest sample data (host preferred)
```
.venv/bin/python -m backend.ingest --data-dir data
```

### Quick CLI smoke
```
.venv/bin/python -m cli --question "hello"
```

### Common checks
- Weaviate reachable from host: `http://localhost:8080`
- Ollama reachable from host: `http://localhost:11434`
- App reachable: `http://localhost:8501`
- Logs: `logs/rag_system.log` should be free of errors during normal operation

### Restart and persistence check
```
docker compose -f docker/docker-compose.yml restart weaviate app
.venv/bin/python -m cli --question "hello after restart"
```

### Notes
- Run Python modules from the project root with `-m` to avoid `PYTHONPATH` issues.
- Prefer host ingestion if container Python deps drift.

