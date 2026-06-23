# Gemini Guidelines — Project Instructions for Gemini CLI

## Project Overview
Local RAG system: document ingestion → vector index → retrieval → answer. Python 3.13, Streamlit UI, Weaviate (vector DB), Ollama (local embeddings + LLM), packaged with Docker Compose.

- `backend/` — ingestion (`ingest.py`), retrieval/QA (`qa_loop.py`), Weaviate/Ollama clients, config.
- `frontend/` — Streamlit app (`rag_app.py`).
- `scripts/`, `docker/` — developer helpers and compose/Dockerfiles.
- `tests/` — `unit/`, `integration/`, `e2e/`, `ui/`.

## Reference Index
| Trigger | Read |
|---------|------|
| Quick start, run commands, Makefile targets | `README.md`, `Makefile` |
| Dev setup, test suites, CI/release flow, env vars | `docs/dev_test_CI/README.md` |
| Docker stack management, volumes, reset | `docs/operate/docker-management.md` |

## Critical Rules

1. **Run commands from repo root.** Use `.venv/bin/python` for Python. **Never set `PYTHONPATH`** — the editable install handles import paths.
2. **`ModuleNotFoundError` ⇒ re-run editable install** (`uv sync` or `uv pip install -e .`) before investigating — stale installs are the dominant cause.
3. **Run pytest as a module:** `.venv/bin/python -m pytest tests/` to avoid `ImportError`.
4. **No `print` in app or test code** — use `logging`. Log files only under `logs/`.
5. **Never `docker compose down -v` on non-test stacks** — it destroys persisted Weaviate/Ollama volumes. Plain `down` only.
6. **Run pre-commit + tests after edits.** On a failure that persists, stop and surface logs (max 3 attempts); state expected vs. actual before changing the test or the code.
7. **Conventional Commits.** Feature/fix work on `dev` (permanent integration branch — never delete/auto-merge it as if disposable); primary branch is `main`. The pre-commit wrapper re-stages only files already staged for the commit, so unrelated working-tree edits aren't swept in.
8. **Secrets stay out of git** — `.secrets.baseline` (detect-secrets) gates this; don't bypass.
9. **No trailing summary docs** (`TASK_SUMMARY.md`-style). End summaries go in chat or the commit message. Approved plans go in `docs/plans/`.
10. **Prefer local installed tools** over Docker/CI wrappers for local dev; CI uses Docker for consistency.

## Tooling Quickref

- Stack: `make stack-up` (build + start app/Weaviate/Ollama/Streamlit at `http://localhost:8501`), `make stack-down`.
- Ingest / ask: `make ingest`, `make cli` (`ARGS='--question "..."'`). Logs: `make app-logs`.
- Lint/format/types: `ruff check . --fix`, `ruff format .`, `make pyright`.
- Tests: `make unit`, `make integration`; dockerized: `make test-up` → `make test-integration` → `make test-down`.
- Pre-commit: `make pre-commit`. Deps: edit `pyproject.toml`, then `make export-reqs`. Audit: `make audit` (`uv audit`, OSV, reads `uv.lock`; needs uv ≥0.10.12).
- Torch: `make sync` installs the PyPI/GPU wheel by default; pass `--extra cpu` (CI/Docker use `SYNC_EXTRA="--extra cpu"`) for slim CPU-only wheels.

---

## Detailed Rules & Guidelines (Adopted from `.claude/rules/`)

### 1. Linting, Formatting & Types
- **Ruff** is the single tool for Python lint + format (config in `pyproject.toml`: line length 120, double quotes). Runs on save and on commit. Headless: `ruff check . --fix` then `ruff format .`.
- **No `print`** in app or test code — Ruff `T201` enforces this. Use `logging` (see Logging below).
- **Pyright** for type checking (`pyrightconfig.json`). Headless: `make pyright` or `pyright .`. Use `# type: ignore[...]` sparingly, always with a justifying comment.

### 2. Logging
- All log files go under the `logs/` directory at the project root — never elsewhere.
- Use structured logging with appropriate levels (DEBUG, INFO, WARNING, ERROR), not `print`.
- Use descriptive log file names (e.g. `rag_system.log`, `cli.log`).
- Test logging config in `pyproject.toml` (`[tool.pytest.ini_options]`): console INFO, file DEBUG, dated per-run by `tests/conftest.py` (`reports/test_session-<ts>.log` + `test_session.log` symlink). Never `logging.shutdown()` in tests — closes pytest's file handler.

### 3. LangChain Integration
- LangChain is used **only in `backend/ingest.py`** (loaders + splitting); deps: `langchain-community`/`-core`/`-text-splitters`, NOT the `langchain` umbrella. `qa_loop.py` uses custom Weaviate/Ollama clients.
- Keep API keys and endpoints in environment variables (`.env`), never hardcoded.
- Wrap external calls (Ollama, Weaviate, LangChain) in explicit error handling.
- Log the app↔LangChain interaction so retrieval and generation steps are traceable.

### 4. Testing
- Run pytest as a module from repo root: `.venv/bin/python -m pytest tests/unit/`.
- Folder-based suites (see `pyproject.toml` `testpaths`):
  - `tests/unit/` — fast, sockets blocked (`pytest-socket`), parallel via `-n auto` (`pytest-xdist`).
  - `tests/integration/` — one real component, network allowed.
  - `tests/e2e/` — full stack via Docker Compose.
  - `tests/ui/` — Playwright browser tests.
- Unit tests must do no real network I/O — put network behavior in integration/e2e.
- Import integration helpers (`get_service_url`, `is_service_healthy`) from `tests/integration/conftest.py` — never reimplement.
- On a failing test: state what it asserts, then the code's actual behavior, then decide which is wrong before editing. Stop and surface logs after 3 failed attempts.

### 5. Imports & Dependencies
- On `ModuleNotFoundError`, first re-run the editable install (`uv sync` or `uv pip install -e .`) — a stale install is the dominant cause. The `backend` package resolves through this install; never set `PYTHONPATH`. See `docs/dev_test_CI/README.md`.
- **`uv` is the source of truth**: declare runtime deps in `pyproject.toml` `[project.dependencies]`, dev/test deps in `[dependency-groups]` (`dev`, `test`). Bounds are major-capped (`>=X,<X+1`).
- `requirements.txt` is **autogenerated and not committed** (gitignored) — a derived scan artifact, regenerated via `make export-reqs` (also run in CI). Never hand-edit or commit it. `torch` is pinned to the CPU index and excluded from the export.

### 6. Docker Volume Safety & Compose Targeting
- **Never remove production Docker volumes.** Do not pass `-v` to `docker compose down` on non-test stacks — it destroys persisted Weaviate/Ollama state.
- Forbidden pattern: `docker compose -f docker/docker-compose.yml down -v`.
- `-v` is acceptable only against test-only compose files (the `make test-*` targets).
- When unsure which environment you are in, assume production and omit volume-removal flags.
- Prefer local installed tools over Docker/CI wrappers for local dev (check `which <tool>` first); CI uses Docker for consistency.
- Target compose **services by name** (`app`, `app-test`, `weaviate`, `ollama`) in `build`/`up`/`run` — never pass a profile name as a target.
- Compose resolves paths relative to the **compose-file location**, not your CWD — reference env files as `.env.docker`, not `./docker/.env.docker`. Verify with `docker compose -f docker/docker-compose.yml config`.

### 7. Plan / Doc Hygiene

#### When to write a plan doc
- No plan doc for features ≤ 2 files changed AND ≤ 1 session of work. Commit message + code diff is the record.
- Single plan doc (not multi-stage split) for features ≥ 2 sessions or ≥ 3 files.
- Multi-stage split (one file per stage) only after ≥ 2 stages have already shipped and a handoff is actually needed. Do not split speculatively at design time.

#### Plan archival
- Plans representing a single shipped session (≤ 1 day end-to-end, all commits reference the plan path or feature name): `git rm`, don't `git mv`. Git log is the audit trail; the archived md is a second copy. Archive only plans whose design rationale isn't fully captured in commit messages.

Shipped plans left in `docs/plans/` auto-load into future sessions and masquerade as active work. When a plan-survey step finds a plan fully shipped, `git mv` it into an `archive/` sibling the same session — don't just note shipped status and move on.

Before `git mv`: grep the plan path across the codebase, docs, and update references to the archived location. If a sibling plan references the archived one with conditional/status language (`"Doc A pending"`, `"if X ships first"`, `"either can ship first"`), the condition has resolved — resolve sibling status notes and post-archive diff-list section headers to state the realized order concretely, not as a hypothetical.

Before `git mv`ing a design doc to `archive/`, grep §Design content against the living reference docs. Any load-bearing fact not present is merge-debt — migrate first. Walk each §section — vocabulary grep hits upstream §s but misses downstream rendering rationale. Do NOT archive plans marked "approved but not implemented" — those are still active even if dormant.

If the plan has working-tree amendments (e.g. a §0 resolution note added in the archiving session), `git add <plan>` the amendment BEFORE `git mv` — `git mv` stages the rename against HEAD content, silently dropping uncommitted working-tree edits. The archive commit then ships without the amendment and the audit-trail content is lost.

When a multi-stage split IS warranted: one file per stage under `docs/plans/`, each sized to fit a 200k-token session context. Write `<date>-<feature>-stage-A.md`, `-stage-B.md`, … plus a short `<date>-<feature>-overview.md` index if useful; cross-reference between files. Single-stage plans stay in one file (Design + Plan + Corrections sections in place). Archive rule (`git mv` to `archive/` after ship) applies per-stage file. No `-v2-` / `-enhancements-` version siblings — amend in place with a changelog entry inside the same stage file.

#### Doc hygiene
Session-generated audits, analyses, and reports go in an `archived/` or `analysis/` subfolder (and should be `.claudeignore`'d / `.aiignore`'d) — not in the reference-doc root. The `docs/` root is for trigger-indexed reference docs listed in this index. Don't drop one-off session outputs into the reference tier.

Migration tasks (moving content out of a module/subsystem): before committing, grep the old identifier across `docs/` and `gemini.md`. Additive migrations leave stale prose in downstream docs the migrator never opened.

vN → vN+1 design migrations: grep both the identifier AND the *human-readable feature names* that the old design used. Identifier-level sweeps come up clean while stale wording survives in comments, docstrings, and architecture notes.

#### Re-work audit scope isn't gated by "phased plan"
Any design doc that lands a long ordered step list (≥10 steps, even a single-PR rollout) has the same cross-step re-write risk as a multi-phase plan. Walk each step's concrete edits and tag which file/function each touches. If the same file appears in two sequential steps where the first's change depends on state the second removes, merge them into one per-file pass. **Trigger is "same target, two steps," not "≥3 phases."**

Test deletes go where the prod-code removal lands, not where the topic finishes — late-stage test deletes leave earlier stages pytest-broken.

#### Feature-removal grep
Before finalizing a removal design, sweep `raise.*Error.*"`, `"""` docstrings, and `\.value\s*=\s*"` literals.

### 8. Rule Authoring
When adding a rule example that documents a *shipped* fix, grep the actual emitted form in the committed code and copy it verbatim — not the design-doc version. Design docs often carry the pre-fix form; shipping that as the rule example re-introduces the original bug as a template for the next implementer.
