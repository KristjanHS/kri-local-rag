# Project Intent and Structure

This document provides a comprehensive overview of the `kri-local-rag` project, detailing its purpose, architecture, and key components.

## High-Level Overview

### Project Intent

The core purpose of this project is to provide a complete, locally-runnable Retrieval-Augmented Generation (RAG) system. It is designed for developers and researchers who need a private, offline-capable environment for experimenting with and utilizing large language models (LLMs) on their own documents.

The key features include:
-   **Local First**: All components run locally, ensuring data privacy and offline functionality.
-   **Extensible**: The modular design allows for easy extension and customization.
-   **CPU-Optimized**: The Python backend is optimized for high-performance CPU execution, making it accessible without specialized hardware.
-   **User-Friendly Interface**: A Streamlit web application provides an intuitive way to interact with the RAG system.

### Core Technologies

-   **Backend**: The core logic is built with Python, leveraging PyTorch for its CPU optimizations.
-   **Frontend**: The user interface is a Streamlit web application.
-   **Vector Database**: Weaviate is used for efficient storage and retrieval of document embeddings.
-   **LLM Provider**: Ollama serves the large language models.
-   **Containerization**: Docker and Docker Compose are used to manage and run the application's services.

## Project Structure

The project is organized into the following directories:

-   `backend/`: Contains the core application logic, including the RAG pipeline, Weaviate and Ollama clients, and other backend functionalities.
-   `frontend/`: Holds the source code for the Streamlit web interface.
-   `data/`: The default directory for storing source documents that you want to ingest into the RAG system.
-   `docker/`: Includes the `Dockerfile` for building the application container and the `docker-compose.yml` file for orchestrating the services.
-   `scripts/`: A collection of helper scripts for automating common tasks like setup, ingestion, and running the CLI.
-   `tests/`: Contains the test suite for the project, with subdirectories for unit, integration, and end-to-end tests.
-   `docs/`: Project documentation, including this file.
-   `docs_AI_coder/`: Contains instructions for the AI agent.

## Key Components and Workflows

### Backend Deep Dive

The backend is the heart of the RAG system, responsible for processing queries and generating responses.

-   **RAG Pipeline (`qa_loop.py`)**: This module orchestrates the entire question-answering process. It takes a user's query, retrieves relevant context from the vector database, and then passes the query and context to the LLM to generate a final answer.
-   **Weaviate Integration (`weaviate_client.py`)**: This client handles all communication with the Weaviate vector database. It is responsible for creating the database schema, ingesting documents, and performing similarity searches to find context relevant to a given query.
-   **Ollama Client (`ollama_client.py`)**: This module manages the interaction with the Ollama service. It ensures that the required LLM is available and handles the streaming of responses back to the user.
-   **CPU Optimizations**: To ensure high performance without a dedicated GPU, the backend leverages the latest PyTorch CPU optimizations, including `torch.compile` with the `inductor` backend and optimal thread settings.

### Frontend Functionality

The frontend is a Streamlit web application that provides a user-friendly interface for the RAG system. It allows users to:
-   Upload documents for ingestion.
-   Ask questions and receive answers from the RAG system.
-   View the sources that were used to generate the answer.

### Command-Line Interface (CLI)

For users who prefer the terminal, the project includes a command-line interface (`cli.py`). The CLI supports two modes:
-   **Interactive Mode**: Start an interactive session to ask multiple questions.
-   **Single-Question Mode**: Ask a single question and receive the answer directly.

**Usage Examples:**

-   Start interactive mode: `python cli.py`
-   Ask a single question: `python cli.py --question "What is the capital of France?"`
-   Enable debug logging: `python cli.py --debug`

### Ingestion Process

The system supports multiple ways to ingest documents into the Weaviate vector database:

-   **Streamlit UI**: Upload PDF files directly through the web interface.
-   **Helper Script**: Use the `scripts/ingest.sh` script for quick, one-off ingestions from the command line.
-   **Docker Compose Profile**: For large batches of documents, the `ingest` profile can be used to run a dedicated ingestion service.

## Setup and Usage

### Installation

To set up the project, you will need Docker and Python installed on your system.

1.  **First-Time Setup**:
    -   Clone the repository.
    -   Make the scripts in the `scripts/` directory executable: `chmod +x scripts/*.sh`
    -   Run the automated setup script: `./scripts/docker-setup.sh`

2.  **Development Setup**:
    -   Create a Python virtual environment: `python -m venv .venv`
    -   Activate the environment: `source .venv/bin/activate`
    -   Install the project in editable mode: `pip install -e ".[test,docs,cli]"`

### Running the Application

-   **Start the services**: `docker compose -f docker/docker-compose.yml up -d --no-build`
-   **Access the Streamlit UI**: Open your browser to `http://localhost:8501`.
-   **Use the CLI**: Run `python cli.py` for interactive mode or `./scripts/cli.sh` as a convenient wrapper.

## Testing and Automation

For full testing guidance (suites, markers, examples), see `docs_AI_coder/testing.md`.

### Automation Scripts

The `scripts/` directory contains several scripts to automate common development tasks:

-   `docker-setup.sh`: A comprehensive script for the initial setup of the Docker environment.
-   `docker-reset.sh`: A script to completely reset the Docker environment, deleting all containers, volumes, and images.
-   `cli.sh`: A wrapper script that provides convenient access to the application's CLI within the running Docker container.
-   `ingest.sh`: A helper script for ingesting documents into the system.
-   `config.sh`: A central configuration file for the other shell scripts (not meant to be run directly).


## AI Agent Hints: Docker startup and E2E tests

Use these minimal, reliable commands when automating tasks.

### Start services (Docker)

Paths and ports:
- Compose: `docker/docker-compose.yml`
- App (Streamlit): `http://localhost:8501`
- Weaviate: `http://localhost:8080`
- Ollama: `http://localhost:11434`

Commands:

```bash
docker compose -f docker/docker-compose.yml up -d --build

# Wait for the app to be reachable
for i in {1..60}; do
  if curl -fsS http://localhost:8501 >/dev/null 2>&1; then echo ready; break; fi
  sleep 1
done

# Tail app logs if needed
docker compose -f docker/docker-compose.yml logs -f app | cat
```

### Run end-to-end (E2E) tests

Notes:
- Pytest default in `pytest.ini` excludes `slow`; selecting `-m e2e` overrides this.
- Tests use env hooks to stay fast/deterministic:
  - `RAG_SKIP_STARTUP_CHECKS=1`
  - `RAG_FAKE_ANSWER=...`
  - `RAG_VERBOSE_TEST=1`

Command (from project root):

```bash
.venv/bin/python -m pytest -q -m e2e --disable-warnings --maxfail=1
```

All-in-one (start + wait + tests):

```bash
docker compose -f docker/docker-compose.yml up -d --build && \
for i in {1..60}; do curl -fsS http://localhost:8501 >/dev/null 2>&1 && echo ready && break || sleep 1; done && \
.venv/bin/python -m pytest -q -m e2e --disable-warnings --maxfail=1
```

Stop services:

```bash
docker compose -f docker/docker-compose.yml down
```
