# kri-local-rag

Local RAG system using Weaviate, Ollama, and a CPU-optimized Python backend.

---

## Quick Start (Docker)

```bash
# Start services (build if needed)
docker compose -f docker/docker-compose.yml up -d --build

# Wait for Streamlit app readiness (http://localhost:8501)
for i in {1..60}; do \
  curl -fsS http://localhost:8501 >/dev/null 2>&1 && echo ready && break || sleep 1; \
done
```

Run end-to-end tests (optional):

```bash
.venv/bin/python -m pytest -q -m e2e --disable-warnings --maxfail=1
```

See `docs/docker-management.md` for service health checks and troubleshooting.

---

## Prerequisites
- Docker & Docker Compose
- 8GB+ RAM
- **Optional NVIDIA GPU**: For hardware-accelerating the `ollama` LLM service. The main `app` container is CPU-only.
- Linux/WSL2

---

## Project Structure

This project follows a standard structure for Python applications, separating concerns into distinct directories:

```
kri-local-rag/
├── .devcontainer/     # VS Code Dev Container configuration
├── .venv/             # Python virtual environment
├── .vscode/           # VS Code workspace settings
├── backend/           # Core RAG backend code (CPU-optimized)
├── data/              # Source documents for ingestion
├── docs/              # Project documentation
├── docker/            # Dockerfiles and docker-compose.yml
├── example_data/      # Sample data for testing
├── frontend/          # Streamlit web interface
├── logs/              # Log files from scripts and services
├── scripts/           # Automation and utility scripts
└── tests/             # Test suite
```

---

## Automated Scripts

This project includes a suite of scripts in the `scripts/` directory to automate common tasks. They are all powered by a central `config.sh` file, which manages paths, service names, and logging.

-   **`config.sh`**: Central configuration for all shell scripts. Not meant to be run directly, but sourced by other scripts.
-   **`docker-setup.sh`**: Performs a full, first-time setup, building all Docker images and starting the services.
-   **`docker-reset.sh`**: Completely resets the project by stopping and deleting all containers, volumes, and images.
-   **`cli.sh`**: Provides CLI access to the running `app` container. It clears the Python cache and restarts the container to ensure live code changes are applied before executing a command. Starts an interactive RAG console by default.
-   **`ingest.sh`**: A convenience wrapper to ingest PDFs from a host path into Weaviate using a temporary `app` container.
-   **`monitor_gpu.sh`**: Monitors NVIDIA GPU usage, useful for observing the `ollama` service if you have a GPU.
-   **`cleanup_docker_and_ci_cache.sh`**: Cleans unused Docker data and the local `act` cache. Use when local CI pre-push runs flake due to Docker issues.

---

## Installation & Startup

### First-Time Setup

1.  Clone the repository:
    ```bash
    git clone https://github.com/KristjanHS/kri-local-rag
    cd kri-local-rag
    ```

2.  Make the scripts executable:
    ```bash
    chmod +x scripts/*.sh
    ```

3.  Run the automated setup script:
    ```bash
    ./scripts/docker-setup.sh
    ```
    **Note:** The first run can be very slow as it downloads several gigabytes of models.

Once complete, the Streamlit app will be available at **[http://localhost:8501](http://localhost:8501)**.

### Development Installation

If you want to run the scripts locally for development, you'll need to install the project in editable mode.

1.  Create a virtual environment:
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```

2.  Install the project in editable mode with all optional dependencies:
    ```bash
    pip install -e ".[test,docs,cli]"
    ```
    This will install the project and its dependencies, including the CLI and its `rich` dependency.

### Subsequent Launches

- Rebuild the app image and capture build logs:
  ```bash
  ./scripts/build_app.sh
  ```

- Start (without rebuilding):
  ```bash
  docker compose -f docker/docker-compose.yml up -d --no-build
  ```

---

## Usage

### Ingest Documents

There are several ways to add PDFs to the vector database:

| Method | Command / UI | When to use |
|--------|--------------|-------------|
| **1. Streamlit UI** | Upload PDFs directly in the browser. | Quick, small uploads without using the terminal. |
| **2. Helper script** | `./scripts/ingest.sh <path>` | A fast one-liner that runs ingestion in a temporary container. |
| **3. Docker Compose Profile** | `docker compose -f docker/docker-compose.yml --profile ingest up` | Fire-and-forget batch ingestion using the dedicated `ingester` service. |
| **4. CLI Wrapper** | `./scripts/cli.sh <command>` | Run any command inside the persistent `app` container. |


### Ask Questions

Once documents are ingested, you can ask questions via the Streamlit app at **[http://localhost:8501](http://localhost:8501)** or use the interactive CLI:
```bash
./scripts/cli.sh
```

---

## Testing

- Fast default tests:
  ```bash
  .venv/bin/python -m pytest -v
  ```
- E2E tests only:
  ```bash
  .venv/bin/python -m pytest -v -m "e2e"
  ```
- All tests (including slow):
  ```bash
  .venv/bin/python -m pytest -v -m "not environment"
  ```

See `docs_AI_coder/testing.md` for markers and guidance.

---

## CPU Optimizations

The `app` container is configured for high-performance CPU execution using the latest PyTorch optimizations:

-   **Latest PyTorch CPU Wheels**: Includes oneDNN 3.x and Inductor improvements for AVX2 and scalable workloads.
-   **`torch.compile`**: Uses the `inductor` backend with `max-autotune` mode for 5-25% speed-ups on CPU-intensive models.
-   **Optimal Threading**: Environment variables like `OMP_NUM_THREADS` and `MKL_NUM_THREADS` are set in the `Dockerfile` for efficient CPU utilization.

---

## Data Locations

- **Weaviate data**: Stored in the `weaviate_db` Docker volume.
- **Ollama models**: Stored in the `ollama_models` Docker volume.
- **Source documents**: Place your PDFs in the `data/` directory.

---

## GPU Monitoring (for Ollama)

If you are using an NVIDIA GPU for the `ollama` service, you can monitor its usage with the included script. Note that the `app` container is CPU-only and will not register GPU usage.

```bash
./scripts/monitor_gpu.sh
```

---

## Documentation

This project contains additional documentation in the `docs/` directory:

- [Development Guide](docs/DEVELOPMENT.md) – Local setup, Docker workflows, and architecture.
- [Docker Management](docs/docker-management.md) – In-depth guide to managing the project's Docker containers.
- [Debugging Guide](docs/DEBUG_GUIDE.md) – A comprehensive guide to debugging `pytest` hangs and other issues.
- [Document Processing](docs/document-processing.md) – Overview of the document ingestion and processing pipeline.
- [Embedding Model Selection](docs/embedding-model-selection.md) – Guide for evaluating and choosing different embedding models.
- [Cursor Terminal Fix](docs/cursor_terminal_fix.md) – Notes on fixing and improving the integrated terminal experience.
- [Reorganization Summary](docs/REORGANIZATION_SUMMARY.md) – Summary of the project's code and file structure reorganization.

AI-coder docs (automation hints):
- `docs_AI_coder/instructions.md` – Docker startup, readiness checks, and E2E run commands.
- `docs_AI_coder/DEVELOPMENT.md` – Development workflows and import strategy.
- `docs_AI_coder/testing.md` – Test suite organization and marker usage.

## Local CI with `act`

This project uses `act` to run GitHub Actions locally.

- Pre-push hook: `.git/hooks/pre-push` runs
  ```bash
  act pull_request -j lint_and_fast_tests --pull=false --log-prefix-job-id
  ```
  so local pushes mimic the PR “Lint and Fast Tests” job.
- Manual run matching the hook:
  ```bash
  ./scripts/ci_act.sh
  # or directly
  act pull_request -j lint_and_fast_tests
  ```

Notes
- Act runner images pinned in `.actrc`.
- Full workflow file: `.github/workflows/python-lint-test.yml`.

Troubleshooting flaky local CI
- If the pre-push run fails with errors like exitcode 137 or "RWLayer ... is unexpectedly nil", it's a Docker/act hiccup, not a code failure.
  - Quick fix:
    ```bash
    ./scripts/cleanup_docker_and_ci_cache.sh
    # optionally, for aggressive cleanup/restart
    ./scripts/cleanup_docker_and_ci_cache.sh --restart-docker --builder-prune
    ```
  - If needed on WSL2, restart Docker Desktop and/or run `wsl --shutdown`.

## License

MIT License - see [LICENSE](LICENSE) file.

---

## Logs and Test Reports

- **logs/**: Runtime and script logs. Ignored by Git. Auto-created by the app and scripts. Safe to delete anytime; they are recreated on next run. A cleanup script prunes files older than 7 days.
- **reports/**: Pytest artifacts (HTML/JUnit reports, session log, per-test logs). Ignored by Git and auto-created by tests. Safe to delete; regenerated on next test run.

Utilities
- Clean artifacts quickly:
  ```bash
  ./scripts/clean_artifacts.sh
  ```
- CI uploads reports as artifacts from the `reports/` directory for both fast and slow test jobs.
