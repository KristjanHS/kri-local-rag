# Backend Service

Core RAG functionality with document ingestion, vector search, and LLM integration.

## Components

- **`qa_loop.py`** - Interactive RAG console
- **`ollama_client.py`** - Ollama LLM integration
- **`ingest_pdf.py`** - PDF document processing
- **`retriever.py`** - Vector search logic
- **`delete_collection.py`** - Weaviate collection management
- **`config.py`** - Configuration settings

## Quick Start

```bash
# Start console
docker compose run --rm rag-backend

# Ingest documents
docker compose run --rm rag-backend python ingest_pdf.py

# Delete data
docker compose run --rm rag-backend python delete_collection.py
```

## Architecture

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

### Environment Variables
```bash
OLLAMA_URL=http://ollama:11434
WEAVIATE_URL=http://weaviate:8080
```

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

## Development

### Local Development
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

## Troubleshooting

### Common Issues

**Ollama Connection Failed**
```bash
docker ps | grep ollama
curl http://localhost:11434/api/tags
```

**Weaviate Connection Failed**
```bash
docker ps | grep weaviate
curl http://localhost:8080/v1/meta
```

**Model Not Found**
```bash
docker compose exec ollama ollama pull cas/mistral-7b-instruct-v0.3
```

**PDF Processing Errors**
```bash
pip install "unstructured[pdf]"
file data/*.pdf
```

### Debug Mode
```bash
docker compose run --rm rag-backend --debug-level 3
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

## API Reference

### Command Line Options
```bash
qa_loop.py [--source SOURCE] [--language LANGUAGE] [--k K] [--debug-level DEBUG_LEVEL]
```

### Key Functions
```python
# Ollama client
test_ollama_connection()
download_model_if_needed(model_name)
generate_response(prompt, model, context)

# Weaviate operations
get_top_k(question, k=3, debug=False, metadata_filter=None)
ingest_documents(data_dir="data/")
delete_collection()
```

## Next Steps

- [Main README](../README.md)
- [Docker Management](../docs/setup/docker-management.md)
- [Basic Usage](../docs/usage/basic-usage.md) 