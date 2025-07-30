# kri-local-rag

Local RAG system using Weaviate, Ollama, and Python.

---

## Prerequisites
- Docker & Docker Compose
- 8GB+ RAM
- NVIDIA GPU (optional)
- Linux/WSL2

---

## Project Structure

This project follows Python best practices with organized directories:

```
kri-local-rag/
├── backend/           # Core RAG backend code
├── frontend/          # Streamlit web interface
├── scripts/           # Utility scripts
│   ├── shell/        # Shell scripts (setup, CLI, etc.)
│   └── debug/        # Debug and test scripts
├── tools/            # Development tools and utilities
├── docs/             # Documentation
│   ├── guides/       # User guides and tutorials
│   └── api/          # API documentation
├── tests/            # Test suite
├── logs/             # Log files
├── data/             # User data directory
├── example_data/     # Sample data for testing
└── docker/           # Docker configuration
```

## Automated Scripts

This project includes organized scripts to manage the entire Docker environment:

-   `scripts/docker-setup.sh`: Builds all images and starts all services for the first time.
-   `scripts/cli.sh`: Provides CLI access to the APP container. Starts interactive RAG CLI by default.
-   `scripts/ingest.sh`: Convenience wrapper to ingest PDFs from a host path using the APP container.
-   `scripts/docker-reset.sh`: Stops and completely removes all containers, volumes, and images for this project.
-   `cli.py`: Python-based CLI entry point (recommended for development).

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

3.  Run the automated setup script. This will build the Docker images and start all services.
    ```bash
    ./scripts/docker-setup.sh
    ```
    **Note:** The first run can be very slow (10-20 minutes or more) as it downloads several gigabytes of models. Subsequent launches are much faster.

Once the setup is complete, the Streamlit RAG app will be available at **[http://localhost:8501](http://localhost:8501)**.

### Subsequent Launches

If you have stopped the containers (e.g., with `docker compose down`), you can restart them with:
```bash
# Re-start only previously-built containers, skip building anything new
docker compose -f docker/docker-compose.yml up --detach --no-build
```

---

## Usage

### Ingest Documents

You can add PDFs to the vector-database in several convenient ways – pick whichever fits your workflow:

| Method | Command / UI | When to use |
|--------|--------------|-------------|
| **1. Streamlit UI** | Open the app in your browser, expand *Ingest PDFs* in the sidebar, upload one or more PDF files and click **Ingest** | Quick, small uploads, no terminal needed |
| **2. Helper script** | `./ingest.sh <path>` | Fast one-liner from a terminal **(spins up a temporary APP container automatically)** |
| **3. One-off Docker Compose profile** | `docker compose --profile ingest up ingester` | Fire-and-forget batch ingestion without launching the full UI |
| **4. CLI utility wrapper** | `./cli.sh` or `./cli.sh <command>` | Start interactive RAG CLI by default, or run any backend command inside the persistent APP container (e.g. `./cli.sh python backend/ingest_pdf.py ./docs/my.pdf`) |

Details:

**Helper script (`ingest.sh`)**
Runs `ingest_pdf.py` in a temporary *app* container (it will start one automatically if needed):

```bash
./scripts/ingest.sh data/
```
The script spins up `docker compose run --rm app ...` and passes the folder to `ingest_pdf.py --data-dir <folder>`, so no prior `app` container must be running.

**One-off Compose profile**
Builds a minimal “ingester” container (same image as the app) and executes ingestion once from data/ folder, then exits:

```bash
docker compose --profile ingest up ingester
```

The default command ingests any PDFs found in `data/`. Edit `docker/docker-compose.yml` if you need a different folder or command.

**APP container**
For advanced or scripted workflows you can run arbitrary Python inside the APP container:

```bash
./scripts/cli.sh python backend/ingest_pdf.py docs/my.pdf
```

To open an interactive RAG CLI shell at any time run:

```bash
./scripts/cli.sh   # starts interactive qa_loop.py by default
```

Or run specific commands:
```bash
./scripts/cli.sh python backend/ingest_pdf.py docs/my.pdf  # Ingest specific files
./scripts/cli.sh bash                                       # Start bash shell
```

**Python CLI (Recommended)**
For development, use the Python-based CLI:

```bash
python cli.py                    # Interactive mode
python cli.py --question "What is AI?"  # Single question
python cli.py --debug            # Enable debug logging
```

### Ask Questions

Once documents are ingested, you can ask questions via the Streamlit app at **[http://localhost:8501](http://localhost:8501)**.

---

## Environment Reset

To completely reset the project, which will stop and delete all Docker containers, volumes (including the Weaviate database and Ollama models), and custom images, run the reset script:

```bash
./scripts/docker-reset.sh
```
The script will ask for confirmation before deleting anything.

---

## Data Locations

- **Weaviate data**: `.weaviate_db` directory at the project root (visible in WSL/Linux as <project-root>/.weaviate_db)
- **Ollama models**: `.ollama_models` directory at the project root (visible in WSL/Linux as <project-root>/.ollama_models)
- **Source documents**: Local `data/` directory

## GPU Monitoring

This project includes a GPU monitoring script optimized for WSL + Docker setups:

### Quick Monitoring
```bash
./scripts/monitor_gpu.sh
```
Shows:
- Overall GPU memory usage and utilization
- Container resource usage (CPU, RAM, network)
- Clean, WSL-friendly output

### Continuous Monitoring
```bash
# Updates every 2 seconds
gpustat -i 2

# Or use watch for the monitoring script
watch -n 5 ./scripts/monitor_gpu.sh

### Why This Monitoring Script?

The included `scripts/monitor_gpu.sh` script is specifically designed for WSL + Docker environments where:
- Standard `nvidia-smi` process-level reporting is unreliable
- Container GPU usage isn't properly isolated
- You need to correlate GPU usage with container activity

The script provides reliable GPU monitoring without the noise of unreliable process-level details.

---

## Documentation

This project contains additional documentation in the `docs/` directory:

- [Development Guide](docs/DEVELOPMENT.md) – Development workflow and best practices
- [Docker Management](docs/docker-management.md) – Docker container management
- [Document Processing](docs/document-processing.md) – Document ingestion and processing
- [Embedding Model Selection](docs/embedding-model-selection.md) – Guide for changing or understanding embedding models

## License

MIT License - see [LICENSE](LICENSE) file.

