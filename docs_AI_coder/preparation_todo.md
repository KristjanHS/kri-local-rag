## Preparation TODO (for AI agent / developers)

Context
- App: Local RAG using Weaviate (8080), Ollama (11434), Streamlit UI (8501).
- Only Streamlit should be user-visible. Other services should be local-only (loopback or compose-internal).
- Mandatory env vars used by code: `OLLAMA_URL`, `WEAVIATE_URL`, plus flags: `RETRIEVER_EMBEDDING_TORCH_COMPILE`, `RERANKER_CROSS_ENCODER_OPTIMIZATIONS`.

Repository preparation tasks
0) Preflight
- [ ] Docker + Compose v2 installed locally
- [ ] Adequate disk space for models/DB (several GB)

1) Environment
- [ ] Add `.env.example` with minimal keys:
  - `LOG_LEVEL=INFO`
  - `OLLAMA_MODEL=cas/mistral-7b-instruct-v0.3`
  - `OLLAMA_CONTEXT_TOKENS=8192`
  - `RETRIEVER_EMBEDDING_TORCH_COMPILE=false`
  - `RERANKER_CROSS_ENCODER_OPTIMIZATIONS=false`
  - `OLLAMA_URL=http://ollama:11434`
  - `WEAVIATE_URL=http://weaviate:8080`

2) Network exposure (security)
- [ ] Edit `docker/docker-compose.yml` to bind Weaviate and Ollama to loopback and publish only Streamlit:
  ```yaml
  weaviate:
    ports: ["127.0.0.1:8080:8080", "127.0.0.1:50051:50051"]
  ollama:
    ports: ["127.0.0.1:11434:11434"]
  app:
    ports: ["8501:8501"]
  ```
- [ ] Verify exposure from host:
  ```bash
  ss -tulpen | grep -E ":(8501|8080|11434)"
  ```

3) Minimal, incremental bring-up (assume CLI and app may be broken)
3.0) Trusted tests to drive bring-up (match local CI/act)
- [ ] Use the same selection CI runs (ruff + pytest with default markers from `pyproject.toml`):
  ```bash
  ./scripts/ci_local.sh
  ```
  This runs:
  - Ruff checks
  - `pytest -q tests/` with default addopts: excludes `environment`, `e2e`, and `slow`, so it runs unit + integration tests
- [ ] If a single failing test blocks iteration, narrow temporarily:
  ```bash
  .venv/bin/python -m pytest -q -k "test_name_or_class"  # then restore full run
  ```
3.1) Lint & fast tests first
- [ ] Run linter: `.venv/bin/python -m ruff check .`
- [ ] Run unit tests only: `.venv/bin/python -m pytest -q -m unit`
- [ ] Fix import errors or missing deps reported by tests/linter

3.2) Validate external services standalone
- [ ] Start only `weaviate` and `ollama`:
  ```bash
  docker compose -f docker/docker-compose.yml up -d weaviate ollama
  docker compose -f docker/docker-compose.yml exec weaviate wget -qO - http://localhost:8080/v1/.well-known/ready
  docker compose -f docker/docker-compose.yml exec ollama curl -s http://localhost:11434/api/tags
  ```

3.3) Backend primitives in isolation (no UI)
- [ ] Quick Weaviate connect from host Python:
  ```bash
  .venv/bin/python - <<'PY'
import os, weaviate
from urllib.parse import urlparse
weaviate_url=os.getenv('WEAVIATE_URL','http://weaviate:8080')
pu=urlparse(weaviate_url)
client=weaviate.connect_to_custom(http_host=pu.hostname or 'localhost', http_port=pu.port or 80, grpc_host=pu.hostname or 'localhost', grpc_port=50051, http_secure=pu.scheme=='https', grpc_secure=pu.scheme=='https')
print('is_ready=', client.is_ready())
client.close()
PY
  ```
- [ ] Quick Ollama generate (tiny prompt) via `backend/ollama_client.test_ollama_connection()` using a small helper snippet or with `curl`:
  ```bash
  docker compose -f docker/docker-compose.yml exec ollama curl -s http://localhost:11434/api/tags
  ```

3.4) Backend modules
- [ ] Import `backend.retriever` and call `get_top_k("test", k=1)` with empty DB → expect [] (no crash):
  ```bash
  .venv/bin/python - <<'PY'
from backend.retriever import get_top_k
print(get_top_k('test', k=1))
PY
  ```
- [ ] Import `backend.qa_loop` and run `ensure_weaviate_ready_and_populated()` → expect collection created with example warmup then cleaned, no crash:
  ```bash
  .venv/bin/python - <<'PY'
from backend.qa_loop import ensure_weaviate_ready_and_populated
ensure_weaviate_ready_and_populated()
print('weaviate ok')
PY
  ```

3.5) Ingestion minimal path
- [ ] Place a tiny PDF in `data/` (or use `example_data/test.pdf` if present)
- [ ] Run ingestion: `./scripts/ingest.sh data`
- [ ] Re-run `get_top_k('test', k=1)` → expect non-empty or still stable behavior without exceptions

3.6) CLI minimal
- [ ] Run CLI single question path in verbose mode to surface errors early:
  ```bash
  ./scripts/cli.sh --debug --question "hello"
  ```
- [ ] If it fails, capture the first error, fix, and retry; repeat until CLI single-shot works

3.7) Streamlit minimal
- [ ] Start only `app`: `docker compose -f docker/docker-compose.yml up -d app`
- [ ] Open `http://localhost:8501` and submit a single short question
- [ ] If it fails, read container logs: `docker compose -f docker/docker-compose.yml logs --tail=200 app`
- [ ] Fix one error at a time and retry the same action

4) Broader tests
- [ ] Run integration tests (optionally with dockerized services): `.venv/bin/python -m pytest -q -m integration`
- [ ] Run e2e tests when stable: `.venv/bin/python -m pytest -q -m e2e`

5) Build validation
- [ ] `docker compose -f docker/docker-compose.yml build app`
- [ ] Ensure build completes without errors

6) Persistence
- [ ] Restart Weaviate and app: `docker compose -f docker/docker-compose.yml restart weaviate app`
- [ ] Re-ask a prior question; confirm data persists and answers remain grounded

7) Handover bundle
- [ ] Ensure `docs_AI_coder/mvp_deployment.md` is up to date for admin
- [ ] Provide `.env.example` and any model/tag pin notes

8) Done criteria (all must pass)
- [ ] Services healthy; UI loads
- [ ] CLI single-shot works for a trivial question
- [ ] First answer latency acceptable (< ~2 min on fresh model)
- [ ] Ingestion succeeds; answers are grounded and coherent
- [ ] Data persists after restart
- [ ] Logs present; no critical errors in `logs/rag_system.log`

Post-MVP (defer)
- [ ] Add app healthcheck/readiness for Streamlit
- [ ] Produce lean production image (remove dev deps, avoid editable install)
- [ ] Enable Weaviate auth; front with reverse proxy/SSO; HTTPS termination
- [ ] Resource limits, GPU scheduling policy
- [ ] Model/version pinning and offline model cache warm-up
- [ ] Metrics, tracing, alerts


