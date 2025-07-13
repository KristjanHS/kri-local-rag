# Development Guide

This guide covers setting up your development environment, automating project startup, and (optionally) migrating the repository.

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

## Appendix: Repository Migration

If you need to migrate a part of this project to new repo, follow these steps:

### 1. Prepare the New Repo
- Create a new empty repo on GitHub (no README, .gitignore, or license)
- Clone it locally

### 2. Copy Files
- Copy the desired files and folders from the old repo to the new one
- Use `cp` or your file manager

### 3. Initialize and Push
```bash
git init -b main
git remote add origin <your-new-repo-url>
git add --all
git commit -m "Initial import"
git push -u origin main
```

### Troubleshooting
- If you see `fatal: refusing to merge unrelated histories`, recreate the repo without initial files
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

**`ingest_pdf.py`**
- PDF text extraction using `unstructured`
- Text chunking and embedding generation
- Weaviate collection management

**`retriever.py`**
- Vector similarity search
- Context chunk retrieval
- Metadata filtering

## Configuration

### Model Settings
Default: `cas/mistral-7b-instruct-v0.3`

Edit `ollama_client.py`:
```python
OLLAMA_MODEL = "your-model-name"
```

### Debug Levels
- **0**: Minimal output (default)
- **1**: Basic debug info
- **2**: Detailed debug info
- **3**: Verbose debug info

## Local Development

### Setup
```bash
pip install -r requirements.txt
python qa_loop.py
```

### Testing
```bash
# Test Ollama connection
python -c "from ollama_client import test_ollama_connection; test_ollama_connection()"

# Test Weaviate connection
python -c "import weaviate; client = weaviate.Client('http://localhost:8080'); print('Connected')"
```

## Performance

### Optimization Tips
- Use GPU for faster LLM inference
- Adjust chunk size based on documents
- Monitor memory usage during ingestion
- Use appropriate debug levels

### Resource Requirements
- **CPU**: 4+ cores recommended
- **RAM**: 8GB+ for smooth operation
- **GPU**: Optional but recommended
- **Storage**: 10GB+ for models and data