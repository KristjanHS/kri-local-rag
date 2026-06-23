# AGENTS.md — Instructions for Coding Agents

Local RAG system: document ingestion → vector index → retrieval → answer.
Python 3.13, Streamlit UI, Weaviate (vector DB), Ollama (local embeddings + LLM), Docker Compose.

**This file is a pointer.** To avoid drift, all project instructions live in one place:

- **`CLAUDE.md`** — project overview, Reference Index, Critical Rules, Tooling Quickref.
  Read this first: it covers where to run from (repo root), the `.venv/bin/python`
  interpreter, secrets policy, test/quality gates, and Conventional Commits.
- **`.claude/rules/*.md`** — topic-specific rules (linting, logging, langchain, testing,
  imports/deps, docker-safety, plan-hygiene, rule-authoring). Mirrored as `.cursor/rules/*.mdc`
  for Cursor.
- **`README.md`**, **`docs/dev_test_CI/README.md`**, **`docs/operate/`** — deeper reference docs.

Follow those as if written for you. When in doubt about security or data handling, stop and
ask a human.
