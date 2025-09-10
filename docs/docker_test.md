# Docker Change Validation Plan

Use this checklist to validate recent Dockerfile/Compose changes in small chunks. Run commands from the repo root.

## Prep
- [x] Export BuildKit: `export DOCKER_BUILDKIT=1`
- [x] Ensure working dir: `cd ~/projects/kri-local-rag`

## Static checks (fast)
- [x] Run pre-commit: `make pre-commit`
- [x] Run unit tests: `make unit`
- [x] Dry build image (runtime target) to observe context size: `docker build -f docker/app.Dockerfile -t test-app --target runtime . --progress=plain`

## Bring up full stack
- [x] Start services: `make stack-up`
- [x] Verify status: `docker compose -f docker/docker-compose.yml ps` (expect app/weaviate/ollama healthy)

## Healthcheck and flags verification
- [x] Host health probe: `wget -q --spider http://localhost:8501/_stcore/health && echo OK`
- [x] In-container health probe: `docker compose -f docker/docker-compose.yml exec app sh -lc 'wget -qO- http://localhost:8501/_stcore/health && echo'`
- [ ] Inspect logs for headless/no-telemetry: `make app-logs LINES=100`

## Quick app smoke
- [x] CLI smoke: `docker compose -f docker/docker-compose.yml exec -T app /opt/venv/bin/python -m backend.qa_loop --question "hello"`
- [x] UI smoke (manual): open http://localhost:8501

## Ingestion (small sample)
- [x] Ingest example data: `./scripts/ingest.sh ./example_data`

## Test profile (compose)
- [ ] Start test env: `make test-up` (app-test builds with INSTALL_DEV=1, idles)
- [ ] Run integration tests: `make test-run-integration`
- [ ] Tear down test env: `make test-down`

## Cleanup
- [ ] Stop services: `make stack-down`
- [ ] Optional: prune builder cache: `docker builder prune -af`
