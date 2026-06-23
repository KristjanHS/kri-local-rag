---
paths:
  - "**/*.py"
last_verified: 2026-06-23
---
## LangChain Integration

- LangChain is used **only in `backend/ingest.py`** (the `Document` type + text splitting); deps: `langchain-core`/`-text-splitters`, NOT `langchain-community` (dropped — PDFs load via `pypdf`, text via stdlib) and NOT the `langchain` umbrella. `qa_loop.py` uses custom Weaviate/Ollama clients.
- Keep API keys and endpoints in environment variables (`.env`), never hardcoded.
- Wrap external calls (Ollama, Weaviate, LangChain) in explicit error handling.
- Log the app↔LangChain interaction so retrieval and generation steps are traceable.
