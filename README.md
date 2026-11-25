# kri-local-rag

Ask questions about your local PDFs offline, with Ollama and Weaviate.

[![CI](https://github.com/KristjanHS/kri-local-rag/actions/workflows/python-lint-test.yml/badge.svg?branch=main)](https://github.com/KristjanHS/kri-local-rag/actions/workflows/python-lint-test.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/KristjanHS/kri-local-rag/blob/main/LICENSE)

## Quick start

Prerequisites: Docker with Docker Compose and GNU Make, on Linux or WSL2.

```bash
git clone https://github.com/KristjanHS/kri-local-rag.git && cd kri-local-rag
make stack-up                                  # type "yes" at the prompt
make ingest INGEST_SRC=./example_data
```

Open `http://localhost:8501` and ask what year the Juniper Point lighthouse was built. The first `make stack-up` builds the app image and pulls the Weaviate image, the Ollama image and the default LLM.

## What it does

- Ingests PDF and Markdown files from any folder into a local Weaviate index.
- Answers questions in a Streamlit web UI, or in a CLI (`make cli`, `make ask`) that runs from the local Python setup in the dev docs.
- Streams the answer token by token from a local Ollama model.

## How it works

1. Ingest splits each document into 800-character chunks with 100 characters of overlap.
2. The app embeds each chunk with `sentence-transformers/all-MiniLM-L6-v2` and stores text and vector in Weaviate.
3. A question is embedded the same way. Weaviate runs a hybrid search (BM25 keywords and vector similarity, weighted 50/50) and returns 60 candidates.
4. A cross-encoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`) re-scores the 60 and keeps the top 3.
5. Those 3 chunks go into the prompt for the Ollama LLM (`gemma4:e4b-it-qat` by default).

Weaviate runs with its vectorizer module off. The app computes every vector itself, which keeps ingest and query on the same embedding model and leaves Weaviate with no model to load.

Service operations and troubleshooting: [docs/operate/docker-management.md](docs/operate/docker-management.md).

## How it was built

Coding agents wrote the code; I reviewed it and steered. The agents changed over time: Cursor (`.cursor/rules/`), Codex (`.codex/`), Gemini CLI and Gemini Code Assist (`gemini.md`, `.gemini/`), Continue with open-weight models (`Continue_AI_coder/`) and Claude Code (`CLAUDE.md`, `.claude/rules/`), with `AGENTS.md` as the shared brief. Their config files stay tracked as they were used. Bigger changes began as a written plan, and 17 of those are in [docs/plans/](docs/plans/) (12 finished and archived). The method that grew out of this project is published, cleaned up, as [claudeconf](https://github.com/KristjanHS/claudeconf).

## Tests

```bash
make unit
```

Tests per suite (static count of `def test_` under `tests/`): unit 52, integration 11, E2E 2, UI 1. CI runs Ruff lint, Pyright, the unit tests and Deptry on every push to `main` and every pull request. Pull requests also run CodeQL and Semgrep. `uv audit` and Trivy run weekly and on pull requests that touch dependencies or Docker files. Setup, suites and the CI flow: [docs/dev_test_CI/README.md](docs/dev_test_CI/README.md).

## Limits

- One question peaked at 8.4 GiB of RAM across the three containers, 7.7 GiB of it Ollama with the model on an NVIDIA GPU (`docker stats`). The app container itself runs on CPU only.
- The first `make stack-up` downloads 10.8 GB of images and a 6.1 GB model (`docker image ls`, `ollama list`).
- The embedding and re-ranking models download from Hugging Face on first use in each new app container, and `make ingest` starts a new one every run, so ingest needs network access.
- The LLM context window defaults to 8,192 tokens (`OLLAMA_CONTEXT_TOKENS` in `backend/config.py`).
- Integration and E2E tests (13 of 66) need the full Docker stack and run only locally, never on GitHub CI.

## License

MIT, see `LICENSE`.
