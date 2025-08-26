# Lean guide: Centralized Model Handling with `backend/config.py`

**Current Architecture:** The project uses a **centralized configuration system** in `backend/config.py` with **offline-first model loading** through `backend/models.py`. All model settings are managed centrally with environment variable overrides, supporting both development (with downloads) and production (offline with pre-baked models).

---

## 0) Goals (why this setup)
- **Centralized Configuration**: Single source of truth in `backend/config.py` for all model settings
- **Reproducible Builds**: Pinned commits ensure consistent model versions across environments
- **Offline-First**: Production runs with pre-baked models, no network dependencies
- **Environment Flexibility**: Environment variables allow easy overrides for development/testing
- **Simple API**: Clean `load_embedder()` and `load_reranker()` functions for all code

---

## 1) Centralized Configuration in `backend/config.py`

All model configuration is centralized in `backend/config.py`. The system supports:

### Default Models
```python
# In backend/config.py
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
DEFAULT_OLLAMA_MODEL = "cas/mistral-7b-instruct-v0.3"
```

### Environment Variable Overrides
Set these in your `.env` file or environment:

```env
# Model repositories (override defaults)
EMBED_REPO=sentence-transformers/all-MiniLM-L6-v2
RERANK_REPO=cross-encoder/ms-marco-MiniLM-L-6-v2

# Pinned commits for reproducibility
EMBED_COMMIT=c9745ed1d9f207416be6d2e6f8de32d1f16199bf
RERANK_COMMIT=ce0834f22110de6d9222af7a7a03628121708969

# Ollama model
OLLAMA_MODEL=cas/mistral-7b-instruct-v0.3
```

---

## 2) Current Dockerfile Implementation

The project uses two-stage Docker builds for both app and test environments:

### App Dockerfile (`docker/app.Dockerfile`)
```dockerfile
# ---- Stage 1: Fetch models ----
FROM python:3.12-slim AS models
RUN pip install --no-cache-dir huggingface_hub
ARG EMBED_REPO EMBED_COMMIT RERANK_REPO RERANK_COMMIT
RUN python -c "from huggingface_hub import snapshot_download; import os; \
    snapshot_download(os.environ['EMBED_REPO'], revision=os.environ['EMBED_COMMIT'], local_dir='/models/emb', local_dir_use_symlinks=False); \
    snapshot_download(os.environ['RERANK_REPO'], revision=os.environ['RERANK_COMMIT'], local_dir='/models/rerank', local_dir_use_symlinks=False)"

# ---- Stage 2: Runtime ----
FROM python:3.12-slim AS runtime
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --from=models /models /models
ENV TRANSFORMERS_OFFLINE=1
ENV EMBED_MODEL_PATH=/models/emb
ENV RERANK_MODEL_PATH=/models/rerank
WORKDIR /app
COPY backend/ ./backend/
COPY pyproject.toml .
RUN pip install -e .
```

**Key Features:**
- Models are downloaded once at build time using pinned commits
- Production runs completely offline with `TRANSFORMERS_OFFLINE=1`
- Model paths are configured via environment variables
- Separate test Dockerfile with similar structure

---

## 3) Current Model Loading Implementation

The model loading is implemented in `backend/models.py` with centralized configuration from `backend/config.py`:

### Main Loader Functions
```python
# backend/models.py
from backend.config import (
    EMBED_MODEL_PATH, RERANK_MODEL_PATH, HF_CACHE_DIR,
    EMBED_REPO, RERANK_REPO, EMBED_COMMIT, RERANK_COMMIT,
    TRANSFORMERS_OFFLINE
)

def load_embedder() -> SentenceTransformer:
    """Load embedding model with offline-first logic."""
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model

    # Check if baked model exists (production/offline mode)
    if Path(EMBED_MODEL_PATH).exists():
        _embedding_model = SentenceTransformer(EMBED_MODEL_PATH)
        return _embedding_model

    # Fallback to downloading with pinned revision (development mode)
    _embedding_model = SentenceTransformer(
        EMBED_REPO,
        cache_folder=HF_CACHE_DIR,
        revision=EMBED_COMMIT,
        local_files_only=TRANSFORMERS_OFFLINE
    )
    return _embedding_model

def load_reranker() -> CrossEncoder:
    """Load reranker model with offline-first logic."""
    global _cross_encoder
    if _cross_encoder is not None:
        return _cross_encoder

    # Check if baked model exists (production/offline mode)
    if Path(RERANK_MODEL_PATH).exists():
        _cross_encoder = CrossEncoder(RERANK_MODEL_PATH)
        return _cross_encoder

    # Fallback to downloading with pinned revision (development mode)
    _cross_encoder = CrossEncoder(
        RERANK_REPO,
        cache_folder=HF_CACHE_DIR,
        revision=RERANK_COMMIT,
        local_files_only=TRANSFORMERS_OFFLINE
    )
    return _cross_encoder
```

**Key Features:**
- **Offline-first**: Checks for local models first, falls back to downloads
- **Centralized config**: All settings imported from `backend/config.py`
- **Caching**: Models are cached to avoid reloading
- **Error handling**: Proper exception handling for missing models

---

## 4) Current Docker Compose Configuration

The project uses environment-specific Docker Compose configurations:

### Production Mode (`docker/docker-compose.yml`)
```yaml
services:
  app:
    build:
      context: .
      dockerfile: docker/app.Dockerfile
      args:
        EMBED_REPO: ${EMBED_REPO}
        EMBED_COMMIT: ${EMBED_COMMIT}
        RERANK_REPO: ${RERANK_REPO}
        RERANK_COMMIT: ${RERANK_COMMIT}
    environment:
      TRANSFORMERS_OFFLINE: "1"
      EMBED_MODEL_PATH: "/models/emb"
      RERANK_MODEL_PATH: "/models/rerank"
    # Models are baked into the image - no volumes needed
```

**Production Benefits:**
- Models are pre-baked into the Docker image
- Completely offline operation with `TRANSFORMERS_OFFLINE=1`
- No external dependencies or downloads at runtime
- Reproducible builds with pinned commits

---

## 5) Development and Testing Workflows

### Local Development (venv)
For local development without Docker, the system automatically handles model downloading:

```bash
# Set environment variables for custom models (optional)
export EMBED_REPO="sentence-transformers/all-mpnet-base-v2"
export RERANK_REPO="cross-encoder/ms-marco-MiniLM-L-6-v2"

# Run the application - models download automatically on first use
.venv/bin/python -m backend.qa_loop
```

**Development Benefits:**
- Models download automatically on first use
- Cached in `HF_HOME` directory (default: `/tmp/hf_cache`)
- No Docker required for basic development
- Easy model switching via environment variables

### Testing with Fixtures
The project provides testing fixtures for clean model mocking:

```python
def test_with_mocked_models(mock_embedding_model):
    """Test using the project's mock_embedding_model fixture."""
    from backend.retriever import _get_embedding_model
    model = _get_embedding_model()
    assert model is not None  # Returns the mock instance
```

**Testing Benefits:**
- `mock_embedding_model` fixture prevents real model downloads
- `managed_cross_encoder` fixture for reranker testing
- Clean isolation between tests
- No network dependencies in unit tests

---

## 6) Updated Testing Strategy

The project uses a comprehensive testing strategy that covers all model loading scenarios:

### Unit Tests
- **Import/mocking tests**: Verify configuration imports work correctly
- **Model loading tests**: Use fixtures like `mock_embedding_model` to test without real downloads
- **Configuration tests**: Test environment variable overrides

### Integration Tests
- **Real model loading**: Test with actual models (with timeout protection)
- **Caching behavior**: Verify models are cached and reused properly
- **Error scenarios**: Test behavior with missing models or network issues

### E2E Tests
- **Docker environment**: Test complete stack with pre-baked models
- **Offline functionality**: Verify production mode works without network
- **Service integration**: Test interaction between Weaviate, Ollama, and model loading

### Testing Best Practices
- **Use project fixtures**: `mock_embedding_model` instead of manual patches
- **Environment isolation**: Each test manages its own configuration
- **Network blocking**: Unit tests prevent real network calls
- **Cache management**: Proper cleanup between tests

**Key Testing Principle**: The centralized configuration system makes testing easier by providing predictable behavior and clean separation between environments.

---

## 7) Updated Implementation Checklist

The new centralized model handling system provides these benefits:

### ✅ **Current Implementation Status**
- [x] **Centralized Configuration**: All model settings in `backend/config.py` with `DEFAULT_*` constants
- [x] **Environment Overrides**: Support for `EMBED_REPO`, `RERANK_REPO`, `EMBED_COMMIT`, `RERANK_COMMIT`
- [x] **Offline-First Loading**: `load_embedder()` and `load_reranker()` functions check local paths first
- [x] **Docker Integration**: Two-stage builds with model fetching at build time
- [x] **Testing Infrastructure**: Project fixtures like `mock_embedding_model` for clean testing
- [x] **Production Ready**: Offline operation with `TRANSFORMERS_OFFLINE=1`

### 🔄 **Key Improvements Over Previous Version**
- **No more scattered config**: Single source of truth in `backend/config.py`
- **Better error handling**: Proper exception handling in model loading functions
- **Cleaner testing**: Established fixtures prevent real model downloads in tests
- **Environment flexibility**: Easy switching between development and production modes
- **Simplified API**: Just `load_embedder()` and `load_reranker()` for all code

### 📚 **Documentation**
All documentation has been updated to reflect this new architecture:
- `docs/dev_test_CI/DEVELOPMENT.md` - Added model system section
- `docs/dev_test_CI/testing_approach.md` - Updated with new testing patterns
- `docs/AI_coder/cursor_hints.md` - Added architecture guidance
- `docs/AI_coder/AI_instructions.md` - Updated testing and configuration guidance

---

### Optional (only if many services need the same models)
Run a small **model service** and call it over HTTP. Do this later if/when duplication or scaling
becomes painful. It is not required for a single app.
