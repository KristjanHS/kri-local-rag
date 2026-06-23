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

## Docker Compose Targeting

- Target compose **services by name** (`app`, `app-test`, `weaviate`, `ollama`) in `build`/`up`/`run` — never pass a profile name as a target.
- Compose resolves paths relative to the **compose-file location**, not your CWD — reference env files as `.env.docker`, not `./docker/.env.docker`. Verify with `docker compose -f docker/docker-compose.yml config`.
