# AI Agent Instructions

Action-first cheatsheet for automations.

### Golden Commands

- **Start services**: `./scripts/docker-setup.sh`
- **Stop services**: `docker compose -f docker/docker-compose.yml down`
- **Run E2E tests**: `.venv/bin/python -m pytest -q tests/e2e --disable-warnings --maxfail=1`
- **Quick dev setup**: `bash scripts/setup-dev-env.sh`
- **Run QA loop**: `.venv/bin/python -m backend.qa_loop`

Ports: app `http://localhost:8501`, Weaviate `http://localhost:8080`, Ollama `http://localhost:11434`.

### Core Policies

- **No PYTHONPATH**: Use editable install and `-m` execution
- **Absolute imports**: `from backend.config import get_logger`
- **Module execution**: `.venv/bin/python -m backend.qa_loop`
- **Renovate validation**: `npx --package renovate renovate-config-validator renovate.json`
- **YAML formatting**: `yamlfmt "**/*.yaml" "**/*.yml"`

### Project Structure

- **Backend**: `qa_loop.py` (RAG loop), `weaviate_client.py` (DB), `ollama_client.py` (LLM)
- **Key Directories**: `backend/`, `frontend/`, `tests/`, `docker/`, `scripts/`
- **Data Ingestion**: Streamlit upload, `scripts/ingest.sh`, or compose `ingest` profile

### ML Strategy

Client-side vectorization and reranking with centralized model loading:
- Models configured in `backend/config.py` with environment overrides
- Uses `backend.models.load_embedder()` and `backend.models.load_reranker()`
- Offline-first with fallback to pinned downloads

## Testing Strategy

### Test Organization
- `tests/unit/` - Fast, isolated unit tests with mocking
- `tests/integration/` - Real models + mocked external services
- `tests/e2e/` - Full system validation

### Key Commands
```bash
# Fast tests (unit + integration)
.venv/bin/python -m pytest -q tests/unit tests/integration

# All tests with coverage
.venv/bin/python -m pytest -v -m "not environment" --cov-fail-under=60

# E2E tests
.venv/bin/python -m pytest -v tests/e2e

# Service-specific tests
pytest -m "requires_weaviate"                    # Weaviate only
pytest -m "requires_ollama"                      # Ollama only
pytest -m "requires_weaviate and requires_ollama" # Both services
```

### Environment Configuration
**Environment Variable**: `TEST_DOCKER`
- `true` → Docker services (`weaviate:8080`, `ollama:11434`)
- `false`/`not set` → Local services (`localhost:8080`, `localhost:11434`)

**Configuration**: Centralized in `pyproject.toml` under `[tool.integration]`

**Health Checks**:
- Weaviate: `http://weaviate:8080/v1/.well-known/ready`
- Ollama: `http://ollama:11434/api/version`

### Integration Test Patterns

**Weaviate Integration:**
- Use `@pytest.mark.requires_weaviate` marker
- Get service URL via `integration["get_service_url"]("weaviate")`
- Connect using `weaviate.connect_to_custom()` with proper host/port configuration
- Test vector operations with real embedding models
- Always close client connections in try/finally blocks

**Ollama Integration:**
- Use `@pytest.mark.requires_ollama` marker
- Get service URL via `integration["get_service_url"]("ollama")`
- Make HTTP requests to `/api/generate` endpoint
- Validate response status and content structure
- Test with various prompts and parameters

**Multi-Service Integration:**
- Use both `@pytest.mark.requires_weaviate` and `@pytest.mark.requires_ollama` markers
- Get URLs for both services via integration fixture
- Combine vector search results with LLM generation
- Test complete RAG pipeline end-to-end

### Key Mocking Fixtures

**`mock_weaviate_connect`**:
- Mocks Weaviate database connections
- Use with real embedding models for retrieval testing
- Configure mock responses for controlled testing
- Verify service interaction without actual database calls

**`mock_httpx_get`**:
- Mocks HTTP requests and API calls
- Combine with real models for API integration testing
- Set up mock responses for different scenarios
- Validate request parameters and verify call patterns

### Real Model Testing Patterns

**Basic Model Integration:**
- Use `real_embedding_model` and `real_reranker_model` fixtures
- Test actual model behavior and outputs
- Validate embedding dimensions and model responses
- Check model ranking and scoring accuracy

  **Model Configuration Testing:**
- Use `monkeypatch.setenv()` to override environment variables
- Test custom model repositories and commit hashes
- Reload configuration modules to pick up changes
- Validate configuration loading and parsing

### Model Cache Management

**Session-scoped caching**: Models loaded once per session and reused across tests
**Environment-based paths**: `HF_HOME` and `SENTENCE_TRANSFORMERS_HOME` control storage
**Automatic cleanup**: Cache directories cleared after test sessions

**Cache Management Best Practices:**
- Use `real_embedding_model` and `reset_global_cache` fixtures together
- Verify model instances are properly cached and reused
- Ensure clean state between tests with cache reset
- Test operations with actual cached models

### Flaky Test Fixes
- Use `real_embedding_model` and `real_reranker_model` fixtures for real ML models
- Use `mock_weaviate_connect`, `monkeypatch` for external services
- Use `reset_global_cache` fixture to prevent state leakage
- Set `RAG_FAKE_ANSWER` per-test via `monkeypatch.setenv`

### Integration Test Best Practices
1. **Use pytest markers** instead of manual service checking
2. **Leverage the `integration` fixture** for service management
3. **Keep tests simple** - focus on one service requirement at a time
4. **Use descriptive test names** that indicate service requirements
5. **Handle service unavailability gracefully** - tests should skip with clear messages
6. **Use `monkeypatch`** for focused mocking instead of complex fixture chains
7. **Set `TEST_DOCKER`** explicitly rather than relying on auto-detection

## Development Environment

**Dependencies**:
- `requirements.txt`: production deps
- `requirements-dev.txt`: dev/testing deps (includes production)
- Install: `.venv/bin/python -m pip install -r requirements-dev.txt && .venv/bin/python -m pip install -e .`

**Quick Commands**:
- Setup dev env: `bash scripts/setup-dev-env.sh`
- Activate venv: `source .venv/bin/activate`
- Run QA loop: `.venv/bin/python -m backend.qa_loop`

## Docker Workflow

**Quick Commands**:
- Build app: `./scripts/build_app.sh --no-cache`
- Restart app: `docker compose -f docker/docker-compose.yml up -d --force-recreate app`
- Clean rebuild: `./scripts/build_app.sh --no-cache && docker compose -f docker/docker-compose.yml up -d --force-recreate app`

**Troubleshooting**:
- Validate config: `docker compose -f docker/docker-compose.yml config`

## Quick Reference

**Key Files**:
- `backend/qa_loop.py` - Main RAG loop
- `backend/weaviate_client.py` - Vector DB client
- `backend/ollama_client.py` - LLM client
- `backend/config.py` - Model configuration
- `backend/models.py` - Model loading utilities

**Environment Variables**:
- `TEST_DOCKER` - Control service URLs in tests (true/false)
- `RAG_FAKE_ANSWER` - Mock LLM responses in tests
- `HF_HOME` - Model cache location
