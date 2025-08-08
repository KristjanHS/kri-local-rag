# Plan for Drafting `instructions.md`

This plan outlines the steps to create a comprehensive `instructions.md` file that details the project's intent, structure, and key components.

## Phase 1: High-Level Overview

1.  **Project Intent**: Define the project's core purpose.
    -   What problem does it solve? (Local RAG system)
    -   Who is the target audience? (Developers, researchers)
    -   What are the key features? (Weaviate, Ollama, CPU-optimized backend, Streamlit UI)

2.  **Core Technologies**: Briefly describe the main technologies and their roles.
    -   **Backend**: Python (CPU-optimized with PyTorch)
    -   **Frontend**: Streamlit
    -   **Vector Database**: Weaviate
    -   **LLM Provider**: Ollama
    -   **Containerization**: Docker

## Phase 2: Project Structure

1.  **Directory Layout**: Document the project's directory structure, explaining the purpose of each top-level folder.
    -   `backend/`: Core application logic.
    -   `frontend/`: Streamlit UI code.
    -   `data/`: Source documents for ingestion.
    -   `docker/`: Docker configurations.
    -   `scripts/`: Automation and helper scripts.
    -   `tests/`: Test suites.
    -   `docs/`: Project documentation.

## Phase 3: Key Components and Workflows

1.  **Backend Deep Dive**:
    -   Explain the RAG pipeline (`qa_loop.py`).
    -   Describe the Weaviate integration (`weaviate_client.py`).
    -   Detail the Ollama client (`ollama_client.py`).
    -   Document the CPU optimizations.

2.  **Frontend Functionality**:
    -   Describe the user interface components.
    -   Explain how to interact with the Streamlit app.

3.  **Command-Line Interface (CLI)**:
    -   Document the CLI's purpose (`cli.py`).
    -   Provide usage examples for both interactive and single-question modes.
    -   Explain the available arguments (`--question`, `--debug`, etc.).

4.  **Ingestion Process**:
    -   Outline the different methods for ingesting documents (Streamlit UI, `ingest.sh`, etc.).
    -   Explain the document processing pipeline.

## Phase 4: Setup and Usage

1.  **Installation**: Provide clear, step-by-step instructions for setting up the project.
    -   Prerequisites (Docker, Python).
    -   First-time setup using `docker-setup.sh`.
    -   Development setup (virtual environment, editable install).

2.  **Running the Application**:
    -   How to start the services (`docker compose up`).
    -   How to access the Streamlit UI.
    -   How to use the CLI.

## Phase 5: Testing and Automation

1.  **Testing Strategy**:
    -   Explain the different types of tests (unit, integration, e2e).
    -   How to run the tests (`pytest`).
    -   Describe the purpose of the different test markers.

2.  **Automation Scripts**:
    -   Document the key scripts in the `scripts/` directory (`docker-setup.sh`, `cli.sh`, etc.).
    -   Explain the role of `config.sh`.

## Phase 6: Final Review

1.  **Review and Refine**:
    -   Read through the entire `instructions.md` file for clarity, accuracy, and completeness.
    -   Ensure all code examples are correct and easy to follow.
    -   Add links to relevant documentation where appropriate.

