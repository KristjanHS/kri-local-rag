---
paths:
  - "**/docker-compose*.yml"
  - "**/Dockerfile*"
  - "**/*.sh"
last_verified: 2026-06-23
---
## Docker Volume Safety

- **Never remove production Docker volumes.** Do not pass `-v` to `docker compose down` on non-test stacks — it destroys persisted Weaviate/Ollama state.
- Forbidden pattern: `docker compose -f docker/docker-compose.yml down -v`.
- `-v` is acceptable only against test-only compose files (the `make test-*` targets).
- When unsure which environment you are in, assume production and omit volume-removal flags.
- Prefer local installed tools over Docker/CI wrappers for local dev (check `which <tool>` first); CI uses Docker for consistency.
