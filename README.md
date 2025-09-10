# kri-local-rag

Local RAG system using Weaviate, Ollama, and a CPU-optimized Python backend.

---

## What you can do

- Ingest your local PDFs/Markdown into a vector DB
- Ask questions about your documents via a CLI or a simple web UI
- Run everything locally with Docker (recommended)

---

## Quick Start (Docker)

1) Start services (recommended)
```bash
make stack-up
```
- Builds the app image, starts Weaviate, Ollama, and the app, and waits until services are healthy.
- The first run can take a while due to downloading base images and models.

2) Open the web UI at `http://localhost:8501`

3) Ingest documents
- Put your files into the `data/` folder, then run:
```bash
make ingest                   # uses ./data by default
make ingest INGEST_SRC=./data # explicit path
make ingest INGEST_SRC=/abs/path
```

4) Ask questions
- Web UI: use the Streamlit app at `http://localhost:8501`
- CLI inside container:
```bash
make cli                         # interactive
make cli ARGS='--debug'          # interactive with verbose streaming logs
make ask Q="What is in my docs?" # one-off question
```

5) Stop services (data persists)
```bash
make stack-down
```

Full reset (deletes containers, images, and volumes):
```bash
make stack-reset
```

---

## Local (no Docker)

If you prefer to run Python locally and point to Docker services (or your own):

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-dev.txt
pip install -e .

# Start Docker services (for Weaviate + Ollama) in another shell if needed
make stack-up

# Ingest local docs from ./data
make ingest

# Ask questions via CLI
make cli
make ask Q="Summarize project setup"
```

Notes:
- By default the app expects `WEAVIATE_URL=http://weaviate:8080` and `OLLAMA_URL=http://ollama:11434` in Docker. When running fully locally without Docker networking, set them to `http://localhost:8080` and `http://localhost:11434` respectively.
 - Compose uses service healthchecks; when starting manually, prefer `--wait` to block until ready.
 - To pin the Ollama image, copy `.env.example` to `.env` and adjust `OLLAMA_IMAGE=ollama/ollama:<version>`.
 - For tests, use the Makefile harness: `make test-up` (unique project name), `make test-run-integration`, then `make test-down` (tears down with `-v` for the test stack only).

---

## Common Docker commands

```bash
# Rebuild just the app image (advanced)
docker compose -f docker/docker-compose.yml build app

# Restart the app to pick up code changes (advanced)
docker compose -f docker/docker-compose.yml restart app

# Follow logs
make app-logs LINES=200          # add FOLLOW=1 to tail
```

---

## Prerequisites
- Docker & Docker Compose
- 8GB+ RAM
- **Optional NVIDIA GPU**: For hardware-accelerating the `ollama` LLM service. The main `app` container is CPU-only.
- Linux/WSL2

---

## Documentation

- [Development Guide](docs/dev_test_CI/DEVELOPMENT.md) – More setup, testing, helper scripts, and power-user tips.
- [AI-coder guide](docs/AI_coder/AI_instructions.md) – automation-friendly commands.
- [Docker Management](docs/operate/docker-management.md) – deeper service ops and troubleshooting.

## License

MIT License - see [LICENSE](LICENSE) file.
