# Lean guide: Handling `SENTENCE_TRANSFORMERS` and `CROSS_ENCODER` models in Docker

**Defaults:** Prod runs **offline** with models **baked into the image** (pinned commits). Dev/CI
uses a **cache volume** and may download on first use. Keep the loader the same in both cases.

---

## 0) Goals (why this setup)
- Reproducible builds and cold starts (no surprises from the network).
- Simple mental model: prod = baked + offline, dev/CI = cached downloads.
- One small loader that works for both.

---

## 1) Pick models and pin **commit hashes**
Record the exact commit for each model (don’t use mutable tags). A plain `.env` is enough:

```env
EMBED_REPO=sentence-transformers/all-MiniLM-L6-v2
EMBED_COMMIT=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
RERANK_REPO=BAAI/bge-reranker-base
RERANK_COMMIT=bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb
```

---

## 2) Dockerfile (two stages; minimal)

```dockerfile
# Dockerfile

# ---- Stage 1: fetch pinned model snapshots ----
FROM python:3.12-slim AS models
RUN pip install --no-cache-dir huggingface_hub sentence-transformers transformers
ARG EMBED_REPO EMBED_COMMIT RERANK_REPO RERANK_COMMIT
RUN python - <<'PY'from huggingface_hub import snapshot_downloadimport ossnapshot_download(os.environ["EMBED_REPO"], revision=os.environ["EMBED_COMMIT"],                  local_dir="/models/emb", local_dir_use_symlinks=False)snapshot_download(os.environ["RERANK_REPO"], revision=os.environ["RERANK_COMMIT"],                  local_dir="/models/rerank", local_dir_use_symlinks=False)PY

# ---- Stage 2: runtime ----
FROM python:3.12-slim AS runtime
RUN pip install --no-cache-dir sentence-transformers transformers
COPY --from=models /models /models
ENV TRANSFORMERS_OFFLINE=1     SENTENCE_TRANSFORMERS_HOME=/models
WORKDIR /app
COPY . /app
# CMD ["python", "-m", "your_app"]
```

**Why this is enough:** models are fetched once at build using pinned commits. Runtime is offline
and predictable. No extra tooling, no special accelerators.

---

## 3) Loader code (one small function per model)

```python
# models.py
from sentence_transformers import SentenceTransformer
from sentence_transformers.cross_encoder import CrossEncoder
from pathlib import Path
import os

EMBED_PATH = os.getenv("EMBED_MODEL_PATH", "/models/emb")
RERANK_PATH = os.getenv("RERANK_MODEL_PATH", "/models/rerank")
HF_CACHE = os.getenv("HF_HOME", "/data/hf")
EMBED_REPO = os.getenv("EMBED_REPO")
RERANK_REPO = os.getenv("RERANK_REPO")
EMBED_REV = os.getenv("EMBED_COMMIT")
RERANK_REV = os.getenv("RERANK_COMMIT")
OFFLINE = bool(os.getenv("TRANSFORMERS_OFFLINE"))

def load_embedder() -> SentenceTransformer:
    if Path(EMBED_PATH).exists():
        return SentenceTransformer(EMBED_PATH)
    return SentenceTransformer(EMBED_REPO, cache_folder=HF_CACHE, revision=EMBED_REV,
                               local_files_only=OFFLINE)

def load_reranker() -> CrossEncoder:
    if Path(RERANK_PATH).exists():
        return CrossEncoder(RERANK_PATH)
    return CrossEncoder(RERANK_REPO, cache_folder=HF_CACHE, revision=RERANK_REV,
                        local_files_only=OFFLINE)
```

**Rule:** In prod the paths exist and `TRANSFORMERS_OFFLINE=1`. In dev/CI the paths may not exist,
so the first run downloads to `HF_HOME` and later runs hit the cache.

---

## 4) Compose (prod): offline, read-only, no volumes for models

```yaml
# compose.prod.yml
services:
  app:
    image: your/app:1.0.0
    read_only: true
    environment:
      TRANSFORMERS_OFFLINE: "1"
      EMBED_MODEL_PATH: "/models/emb"
      RERANK_MODEL_PATH: "/models/rerank"
```

That’s it. Models are inside the image; no writable mounts required unless your app needs them.

---

## 5) Compose (dev/CI): named cache volume for faster rebuilds

```yaml
# compose.dev.yml
services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        EMBED_REPO: ${EMBED_REPO}
        EMBED_COMMIT: ${EMBED_COMMIT}
        RERANK_REPO: ${RERANK_REPO}
        RERANK_COMMIT: ${RERANK_COMMIT}
    environment:
      HF_HOME: "/data/hf"
      SENTENCE_TRANSFORMERS_HOME: "/data/hf/sbert"
      # leave TRANSFORMERS_OFFLINE unset for first-run downloads in dev
    volumes:
      - hf_cache:/data/hf
      - .:/app:rw

volumes:
  hf_cache: {}
```

**Optional warm-up (CI):**
```bash
python - <<'PY'
from huggingface_hub import snapshot_download
import os
snapshot_download(os.environ["EMBED_REPO"], revision=os.environ["EMBED_COMMIT"],
                  local_dir=os.path.join(os.environ.get("HF_HOME", "/data/hf"), "emb"),
                  local_dir_use_symlinks=False)
snapshot_download(os.environ["RERANK_REPO"], revision=os.environ["RERANK_COMMIT"],
                  local_dir=os.path.join(os.environ.get("HF_HOME", "/data/hf"), "rerank"),
                  local_dir_use_symlinks=False)
PY
```

---

## 6) Minimal testing (keep flakes out)

- **Offline integration test (prod-like):** run stack with `TRANSFORMERS_OFFLINE=1`. Assert the
  app can load both models from `/models/*` and answer one trivial request.
- **Cache test (dev):** start with empty `hf_cache`; first run downloads and works; second run is
  faster (cache hit).

That’s enough to cover the two modes without complex fixtures.

---

## 7) Checklist (copy into your PR)

- [ ] Choose models and record commit hashes in `.env`.
- [ ] Two-stage Dockerfile: fetch snapshots, copy into runtime, set `TRANSFORMERS_OFFLINE=1`.
- [ ] Loader uses local paths if present; otherwise downloads with `revision` into `HF_HOME`.
- [ ] `compose.prod.yml`: `read_only: true`, env points to baked paths.
- [ ] `compose.dev.yml`: named volume for `HF_HOME`, optional warm-up in CI.
- [ ] Two tests: offline load works; cache behavior works.

---

### Optional (only if many services need the same models)
Run a small **model service** and call it over HTTP. Do this later if/when duplication or scaling
becomes painful. It is not required for a single app.
