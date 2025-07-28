# kri-local-rag

Local RAG system using Weaviate, Ollama, and Python.

---

## Prerequisites
- Docker & Docker Compose
- 8GB+ RAM
- NVIDIA GPU (optional)
- Linux/WSL2

---

## Automated Scripts

This project includes simple shell scripts to manage the entire Docker environment:

-   `docker-setup.sh`: Builds all images and starts all services for the first time.
-   `cli.sh`: Executes commands inside the running CLI container (e.g., for ingestion).
-   `docker-reset.sh`: Stops and completely removes all containers, volumes, and images for this project.

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
    chmod +x docker-setup.sh cli.sh docker-reset.sh ingest.sh
    ```

3.  Run the automated setup script. This will build the Docker images and start all services.
    ```bash
    ./docker-setup.sh
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
| **2. Helper script** | `./ingest.sh <path>` | Fast one-liner from a terminal when the App container is already running |
| **3. One-off Docker Compose profile** | `docker compose --profile ingest up ingester` | Fire-and-forget batch ingestion without launching the full UI |
| **4. Full CLI shell** | `./cli.sh python backend/ingest_pdf.py <path>` | Maximum flexibility: run any backend script inside a temporary CLI container |

Details:

**Helper script (`ingest.sh`)**
Runs `ingest_pdf.py` inside the *cli* container that is already running:

```bash
./ingest.sh data/
```

**One-off Compose profile**
Builds a minimal “ingester” container (same image as the app) and executes ingestion once, then exits:

```bash
docker compose --profile ingest up ingester
```

The default command ingests any PDFs found in `data/`. Edit `docker/docker-compose.yml` if you need a different folder or command.

**CLI container**
For advanced or scripted workflows you can run arbitrary Python inside the CLI image:

```bash
./cli.sh python backend/ingest_pdf.py docs/my.pdf
```

To open an interactive RAG CLI shell at any time run:

```bash
./cli.sh   # launches interactive qa_loop.py inside the CLI container
```

### Ask Questions

Once documents are ingested, you can ask questions via the Streamlit app at **[http://localhost:8501](http://localhost:8501)**.

---

## Environment Reset

To completely reset the project, which will stop and delete all Docker containers, volumes (including the Weaviate database and Ollama models), and custom images, run the reset script:

```bash
./docker-reset.sh
```
The script will ask for confirmation before deleting anything.

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

