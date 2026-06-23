---
paths:
  - "**/*.py"
last_verified: 2026-06-23
---
## LangChain Integration

- This is a RAG app on `langchain` + `langchain-community` (retrieval/QA in `backend/qa_loop.py`).
- Keep API keys and endpoints in environment variables (`.env`), never hardcoded.
- Wrap external calls (Ollama, Weaviate, LangChain) in explicit error handling.
- Log the app↔LangChain interaction so retrieval and generation steps are traceable.
