# kri-local-rag

Local RAG system using Weaviate, Ollama, and a CPU-optimized Python backend.

---

## Quick Start

See `docs/DEVELOPMENT.md` for setup, Docker, testing, and helper scripts.

---

## Prerequisites
- Docker & Docker Compose
- 8GB+ RAM
- **Optional NVIDIA GPU**: For hardware-accelerating the `ollama` LLM service. The main `app` container is CPU-only.
- Linux/WSL2

---

## Documentation

- [Development Guide](docs/DEVELOPMENT.md) – Setup, Docker, helper scripts, usage details.
- AI-coder guide: `docs_AI_coder/AI_instructions.md` – automation-friendly commands.

## License

MIT License - see [LICENSE](LICENSE) file.
