## Minimal Deployment Guide (for Admin)

Purpose
- Run the local RAG stack (Weaviate + Ollama + Streamlit app) on a single server, internal-only.

Prerequisites
- Docker with Compose v2 installed
- Network: expose only port 8501 to users; keep 8080 and 11434 local-only
- Disk space: several GB for models and DB

1) Prepare environment
- Place the project directory on the server
- In the project root, copy the sample env and adjust values:
  ```bash
  cp .env.example .env
  ```

2) Start the stack
- Make scripts executable:
  ```bash
  chmod +x scripts/*.sh
  ```
- Build and start services (waits for health):
  ```bash
  ./scripts/docker-setup.sh
  ```

3) Validate services
- Inside containers:
  ```bash
  docker compose -f docker/docker-compose.yml exec weaviate \
    wget -qO - http://localhost:8080/v1/.well-known/ready
  docker compose -f docker/docker-compose.yml exec ollama \
    curl -s http://localhost:11434/api/tags
  ```
- Open the app in a browser: `http://<server>:8501`

4) Ingest documents
- Copy PDFs into the `data/` folder on the server
- Run ingestion in container:
  ```bash
  ./scripts/ingest.sh data
  ```

5) Smoke test
- In the UI, ask a simple question based on the ingested PDFs
- Expected: grounded answer with minimal latency (first run may load models)

6) Persistence check
- Restart key services:
  ```bash
  docker compose -f docker/docker-compose.yml restart weaviate app
  ```
- Re-open the UI and ask again; answers should still be grounded in the PDFs

7) Normal operations
- Stop services:
  ```bash
  docker compose -f docker/docker-compose.yml down
  ```
- Full reset (destructive, removes volumes and models):
  ```bash
  ./scripts/docker-reset.sh
  ```

Security note
- Keep `weaviate` (8080) and `ollama` (11434) bound to 127.0.0.1
- Only `8501` (Streamlit) should be reachable by users


