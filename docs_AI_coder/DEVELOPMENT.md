# Development Guide

This guide covers setting up your development environment, managing dependencies, and running tests.

## ⚠️ Important: Avoid PYTHONPATH

**NEVER use PYTHONPATH in this project.** Setting PYTHONPATH can cause AppImage overrides that break virtual environment detection for Cursor IDE and agents. This project uses proper Python module structure with `pyproject.toml` configuration and editable installs.

- ✅ **Correct**: `python -m pytest tests/`
- ❌ **Incorrect**: `PYTHONPATH=. python -m pytest tests/`

---

## Quick Project Launcher (WSL/VS Code)

Add this function to your `~/.bashrc` or `~/.zshrc` to jump into the project, activate the venv, and open VS Code:

```bash
llm () {
    local project=~/projects/kri-local-rag
    local ws="$project/kri-local-rag.code-workspace"
    cd "$project" || return 1
    [ -f .venv/bin/activate ] && source .venv/bin/activate
    code "$ws" >/dev/null 2>&1 &
}
```

- **Reload your shell:**
  ```bash
  source ~/.bashrc   # or source ~/.zshrc
  ```
- **Usage:**
  ```bash
  llm  # Opens VS Code, activates venv, sets cwd
  ```
---

## Local Development

### Dependency Management

This project uses a standard `requirements.txt` based approach for managing dependencies.

-   `requirements.txt`: Contains the core application dependencies for production.
-   `requirements-dev.txt`: Has additional dependencies for development and testing, and includes `requirements.txt`.

### Setup

1.  **Create a virtual environment (recommended)**

    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```

2.  **Install Dependencies**

    You have two main sets of dependencies you can install.

    *   **For core application development (production-like environment):**
        ```bash
        pip install --upgrade pip
        pip install -r requirements.txt
        ```

    *   **For running tests and using linters (full development environment):**
        ```bash
        pip install --upgrade pip
        pip install -r requirements-dev.txt
        ```

3.  **Install the project in editable mode**

    This step makes your local `backend` code importable.

    ```bash
    pip install -e .
    ```

    Running `pip install -e .` tells Python to resolve all imports that start with `backend.` directly from your working copy. Any changes you make under the `backend/` directory are picked up immediately without an extra install step.

4.  **Launch the QA loop**

    ```bash
    python -m backend.qa_loop
    ```

### Updating Dependencies

When you need to add or update a package, edit the appropriate `requirements.txt` or `requirements-dev.txt` file directly.

---

## Running Tests

To run the test suite, ensure you have installed the full development and testing dependencies, then run `pytest` from the project root.

1.  **Set up the test environment:**
    ```bash
    # Make sure your virtualenv is active
    pip install -r requirements-dev.txt
    pip install -e .
    ```
2.  **Run the tests:**
    ```bash
    python -m pytest
    ```
    Using `python -m pytest` is the most robust method, as it ensures imports are resolved correctly from the project root.

---

## Troubleshooting

### ModuleNotFoundError

If you encounter a `ModuleNotFoundError` when running tests or scripts, it typically means that the `backend` package is not correctly installed in your virtual environment. This can happen if you forget to install the project in editable mode.

- **Error example**: `ModuleNotFoundError: No module named 'backend'`
- **Solution**: Make sure you have installed the project in editable mode. This command needs to be run from the root of the project, with your virtual environment activated:
  ```bash
  pip install -e .
  ```
This will link the `backend` directory into your environment, allowing Python to find and import your local modules.

---

## Docker Workflow

The Docker image for production should be built using `requirements.txt` to ensure a lean and reproducible container.

*   `pip install -r requirements.txt` installs the pinned *external* libraries for the application.
*   `pip install -e .` installs the *project itself* in editable mode so that Python can import `backend.*` from `/app/backend`.

This logic should be reflected in your `docker/app.Dockerfile`:

```dockerfile
# Copy only the production requirements file
COPY requirements.txt .

# Install production dependencies
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt

# Copy project source and install it
COPY backend/ ./backend
COPY pyproject.toml .
RUN pip install -e .
```

### Cleanly Rebuilding the `app` Container
When you make changes to `docker/app.Dockerfile` or want to ensure a fresh build after updating `requirements.txt`, use this two-step process:

1.  **Build the image without using the cache:**
    ```bash
    docker compose -f docker/docker-compose.yml build --no-cache app
    ```

2.  **Restart the container to use the new image:**
    ```bash
    docker compose -f docker/docker-compose.yml up -d --force-recreate app
    ```

---

## Python Module and Import Strategy

To ensure a scalable and maintainable codebase, this project adheres to the following Python import and module conventions:

1.  **Packages over Directories**: Directories containing Python source code (like `backend/`) are treated as official packages. This is enforced by including an `__init__.py` file in them and configuring `pyproject.toml`.

2.  **Absolute Imports**: All internal imports must be **absolute** from the project root. This practice, recommended by [PEP 8](https://www.python.org/dev/peps/pep-0008/#imports), makes dependencies explicit and avoids ambiguity.
    *   **Correct**: `from backend.config import get_logger`
    *   **Incorrect**: `from config import get_logger`

3.  **Module Execution**: Scripts within a package should be executed as modules using the `-m` flag. This ensures that Python's import system correctly resolves package-level imports.
    *   **Correct**: `python -m backend.qa_loop`
    *   **Incorrect**: `python backend/qa_loop.py`

---

## Backend Architecture

### Data Flow
1. **Document Ingestion** - PDFs → Text chunks → Embeddings → Weaviate
2. **Query Processing** - Question → Vector search → Context chunks → LLM → Answer
3. **LLM Integration** - Model management → Inference → Streaming responses

### Key Components

**`qa_loop.py`**
- Interactive question-answering console
- RAG pipeline implementation
- Debug levels and filtering support

**`ollama_client.py`**
- Ollama model downloads and management
- Streaming inference
- Connection testing

**`ingest.py`**
- PDF text extraction using `unstructured`
- Text chunking and embedding generation
- Weaviate collection management

**`retriever.py`**
- Vector similarity search
- Context chunk retrieval
- Metadata filtering
