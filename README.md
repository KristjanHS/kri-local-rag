# Test commit to trigger CI workflow

# Local RAG with Ollama and Weaviate

This project provides a complete, local-only Retrieval-Augmented Generation (RAG) solution using Ollama for language model hosting and Weaviate as the vector database.

It is designed for simplicity, performance, and privacy, allowing you to chat with your documents without any data leaving your machine.

---

## Table of Contents

- [Key Features](#key-features)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Quick Start](#quick-start)
- [Usage](#usage)
  - [CLI Mode](#cli-mode)
  - [Web App Mode](#web-app-mode)
- [Future Work](#future-work)
- [Known Issues](#known-issues)
- [License](#license)
- [Contact](#contact)

---

## Key Features

- **Local-First**: All components (LLM, vector DB, UI) run locally. No internet connection is required after initial setup.
- **Privacy-Focused**: Your documents and chat history never leave your machine.
- **Easy to Use**: Simple setup with Docker Compose and a user-friendly web interface.
- **Interactive CLI**: A command-line interface for power users to quickly ask questions and get answers.
- **Metadata Filtering**: Filter your documents by source or language to narrow down the context for your questions.
- **Cross-Encoder Reranking**: Improves the quality of retrieved context chunks for more accurate answers.

---

## System Architecture

The system is composed of three main Docker containers:

1.  **Ollama**: Hosts the local language model (e.g., Llama 3, Mistral). It exposes an API for text generation.
2.  **Weaviate**: A modern vector database that stores document chunks and their embeddings for efficient similarity search.
3.  **RAG App**: The main application container that includes:
    - **Backend**: Python scripts for document ingestion, retrieval, and answering.
    - **Frontend**: A Streamlit-based web application for a user-friendly experience.

The backend uses a RAG pipeline that works as follows:

1.  **Ingestion**: Documents (PDFs) are parsed, split into chunks, and converted into vector embeddings using a sentence-transformer model.
2.  **Retrieval**: When a user asks a question, the backend converts the query into an embedding and searches Weaviate for the most similar document chunks.
3.  **Reranking**: A cross-encoder model reranks the retrieved chunks for relevance.
4.  **Generation**: The top-ranked chunks are combined with the user's question into a prompt that is sent to the Ollama language model to generate a final answer.

---

## Technology Stack

- **Language Model**: [Ollama](https://ollama.ai/) (with `cas/mistral-7b-instruct-v0.3`)
- **Vector Database**: [Weaviate](https://weaviate.io/)
- **Embedding Model**: `sentence-transformers/all-MiniLM-L6-v2`
- **Reranking Model**: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- **Backend Framework**: Python, LangChain
- **Frontend Framework**: Streamlit
- **Containerization**: Docker Compose

---

## Quick Start

### Prerequisites

- **Docker**: Ensure Docker and Docker Compose are installed on your system.
- **Git**: For cloning the repository.
- **For GPU Support (Optional but Recommended)**:
  - NVIDIA drivers installed on your host machine.
  - The [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html) installed to allow Docker to access your GPU.

### Steps

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/your-username/your-repo-name.git
    cd your-repo-name
    ```

2.  **Start the Services**
    This command will build the Docker images and start the Ollama, Weaviate, and RAG app containers.
    ```bash
    docker compose -f docker/docker-compose.yml up -d --build
    ```
    The first time you run this, it will download the language model and other required assets, which may take some time.

3.  **Ingest Your Documents**
    Place your PDF documents in the `data/` directory. Then, run the ingestion script to process them:
    ```bash
    docker compose -f docker/docker-compose.yml run --rm ingester
    ```

<<<<<<< HEAD
4.  **Start Chatting**
    - **CLI**: `docker attach <your-app-container-name>`
    - **Web App**: Open your browser to `http://localhost:8501`.
=======
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

To restart the services after they have been stopped (e.g., with `docker compose down`):
```bash
docker compose -f docker/docker-compose.yml up -d --no-build
```

---

## Usage

### CLI Mode

Attach to the running `app` container to use the interactive command-line interface:

```bash
docker attach kri-local-rag-app-1
```

You can then ask questions directly in your terminal.

### Web App Mode

The web application provides a more user-friendly interface. Open `http://localhost:8501` in your browser to:

- Ask questions and get answers.
- See the context chunks that were used to generate the answer.
- Apply filters to your documents.

---

## Future Work

- [ ] Support for more document types (e.g., DOCX, TXT).
- [ ] Add a document management interface to the web app.
- [ ] Implement conversation history.
- [ ] Explore more advanced RAG techniques.

---

## Known Issues

- The initial model download can be slow.
- The web app is simple and could be improved with more features.

---

## Local CI with `act`

This project uses `act` to run GitHub Actions locally. This allows you to test your changes before pushing them to GitHub, which can save time and prevent broken builds.

To run the local CI, you'll need to have `act` installed. You can find installation instructions on the official `act` repository.

This project is configured to use a specific Docker image for `act` that includes all the necessary dependencies for our CI environment. This configuration is defined in the `.actrc` file in the root of the project. This file is automatically used by `act`, so you don't need to do any special configuration to use it.

To run the local CI, simply run the following command in your terminal:

```bash
act
```

This will run all the jobs in the workflow. If you want to run a specific job, you can use the `-j` flag:

```bash
act -j lint-and-test
```

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

---

## Contact

For questions or feedback, please open an issue on the GitHub repository.
