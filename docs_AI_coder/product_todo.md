# Product TODO List

This file tracks outstanding tasks and planned improvements for the project.

## Context

- **App**: Local RAG using Weaviate (8080), Ollama (11434), Streamlit UI (8501)
- **Security**: Only Streamlit should be user-visible. Other services should be local-only (loopback or compose-internal)
- **Python execution**: Avoid `PYTHONPATH`; run modules with `python -m` from project root to ensure imports work
- **Environment**: Prefer the project venv (`.venv/bin/python`) or an equivalent Python environment
- **Vectorization**: Uses a local `SentenceTransformer` model for client-side embeddings. Weaviate is configured for manually provided vectors.
- **Reranking**: A separate, local `CrossEncoder` model is used to re-score initial search results for relevance.

## Conventions

- **Commands are examples**: Any equivalent approach that achieves the same outcome is acceptable
- **Paths, ports, and model names**: Adapt to your environment as needed
- Each step has Action and Verify. Aim for one change per step to allow quick fix-and-retry.
- On any Verify failure: stop and create a focused debugging plan before proceeding (assume even these TODO instructions may be stale or mistaken). The plan should:
   - Summarize expected vs. actual behavior
   - Re-check key assumptions
   - Consider that the step description might be wrong; cross-check code for the source of truth.
   - Propose 1–3 small, reversible next actions with a clear Verify for each. Apply the smallest change first.
   - After a change, re-run the same Verify command from the failed step. Only then continue.
   - If blocked, mark the step as `[BLOCKED: <short reason/date>]` in this todo file and proceed to the smallest independent next step if any; otherwise stop and request help.

## Quick References

- **AI agent cheatsheet and E2E commands**: [`docs_AI_coder/AI_instructions.md`](AI_instructions.md)
- **Human dev quickstart**: [`docs/DEVELOPMENT.md`](../docs/DEVELOPMENT.md)
- **Archived tasks**: [`docs_AI_coder/archived-tasks.md`](archived-tasks.md)

## Prioritized Backlog

#### P1 — Remove sudo from install-system-tools.sh for devcontainer compatibility

- **Context**: The script uses sudo throughout but devcontainer runs as root, making sudo unnecessary and potentially problematic
- **Goal**: Make the script work in both host and devcontainer environments without sudo dependency

- [x] Step 1 — Detect environment and conditionally use sudo
  - Action: Add environment detection at the top of `scripts/install-system-tools.sh`:
    ```bash
    # Detect if we're running as root (devcontainer) or need sudo (host)
    if [ "$(id -u)" -eq 0 ]; then
        SUDO_CMD=""
    else
        SUDO_CMD="sudo"
    fi
    ```
  - Verify: Script runs without errors in both host and devcontainer environments ✅

- [x] Step 2 — Replace all sudo calls with conditional sudo
  - Action: Replace all `sudo` commands with `$SUDO_CMD`:
    - `sudo apt-get update` → `$SUDO_CMD apt-get update` ✅
    - `sudo rm -f /usr/local/bin/hadolint` → `$SUDO_CMD rm -f /usr/local/bin/hadolint` ✅
    - `sudo curl -fLso /usr/local/bin/hadolint` → `$SUDO_CMD curl -fLso /usr/local/bin/hadolint` ✅
    - `sudo chmod +x /usr/local/bin/hadolint` → `$SUDO_CMD chmod +x /usr/local/bin/hadolint` ✅
    - `sudo bash "$TMP_SCRIPT"` → `$SUDO_CMD bash "$TMP_SCRIPT"` ✅
  - Verify: All commands execute correctly in both environments ✅

- [x] Step 3 — Test in both environments
  - Action: Test the script in host environment (should use sudo) and devcontainer (should not use sudo)
  - Verify: Both environments work correctly and no temporary files are left behind ✅

#### P2 — Containerized CLI E2E copies (keep host-run E2E; add container-run twins)

- Why: Host-run E2E miss packaging/runtime issues (entrypoint, PATH, env, OS libs). Twins validate the real image without replacing fast host tests.

- [ ] Step 1 — Identify candidates
  - Action: List E2E tests invoking CLI in-process (e.g., `backend.qa_loop`) such as `tests/e2e/test_qa_real_end_to_end.py`.
  - Verify: Confirm they don't already run via container.

- [ ] Step 2 — Compose runner for CLI (no bind mounts)
  - Action: Add `cli` service (profile `cli`) in `docker/docker-compose.yml` using `kri-local-rag-app`, no `volumes`, `working_dir: /app`, and env:
    - `WEAVIATE_URL=http://weaviate:8080`, `OLLAMA_URL=http://ollama:11434`.
  - Verify: `docker compose --profile cli run --rm cli python -m backend.qa_loop --help | cat` exits 0.

- [ ] Step 3 — Test helper
  - Action: In `tests/e2e/conftest.py`, add `run_cli_in_container(args, env=None)` that runs `docker compose --profile cli run --rm cli ...`, returns `returncode/stdout/stderr`.
  - Verify: `--help` smoke passes.

- [ ] Step 4 — Readiness and URLs
  - Action: Use existing `weaviate_compose_up`/`ollama_compose_up`; ensure ingestion uses compose-internal URLs.
  - Verify: Readiness checks pass before CLI twin runs.

- [ ] Step 5 — Create test twins
  - Action: Add `_container_e2e.py` twins that call `run_cli_in_container([...])` with equivalent CLI subcommands; optionally mark with `@pytest.mark.docker`.
  - Verify: Single twin passes via `.venv/bin/python -m pytest -q tests/e2e/test_qa_real_end_to_end_container_e2e.py` after compose `--wait`.

- [ ] Step 6 — Build outside tests
  - Action: Ensure scripts/CI build `kri-local-rag-app` once; helper should raise `pytest.UsageError` if image missing.
  - Verify: Second run is faster due to image reuse.

- [ ] Step 7 — Diagnostics and isolation
  - Action: On failure, print exit code, last 200 lines of app logs, and tails of `weaviate`/`ollama` logs; use ephemeral dirs/volumes.
  - Verify: Failures are actionable; runs are deterministic and isolated.

- [ ] Step 8 — Wire into scripts/docs/CI
  - Action: Document commands in `docs/DEVELOPMENT.md` and `AI_instructions.md`; mention in `scripts/test.sh e2e` help; add a CI job for the containerized CLI subset.
  - Verify: Fresh env runs `tests/e2e/*_container_e2e.py` green; CI job passes locally under `act` and on hosted runners.

#### P3 — E2E retrieval failure: QA test returns no context (Weaviate)

 - Context and goal
   - Failing test returns no context from Weaviate. Likely mismatch between collection name used by retrieval and the one populated by ingestion, or ingestion not executed.

 - [ ] Task 1 — Reproduce quickly
   - Run only the failing test to confirm the symptom.

 - [ ] Task 2 — Check config and schema
   - Confirm effective `COLLECTION_NAME` and that the corresponding collection exists in Weaviate.

 - [ ] Task 3 — Confirm data population
   - Ensure the ingestion fixture ran and that the target collection contains objects.

 - [ ] Task 4 — Probe retrieval directly
   - Call the retriever to verify it returns non-empty results when data is present.

 - [ ] Task 5 — Standardize collection naming
   - Decide one collection name for E2E and apply consistently (tests, fixtures, and config).

 - [ ] Task 6 — Implement and verify
   - Apply the change, re-run E2E, and confirm the QA test passes.

 - [ ] Task 7 — Add minimal guardrails
   - Log the active collection name in the e2e fixture and add a small test ensuring graceful behavior when empty.

#### P4 — Minimalist Scripts Directory Cleanup

- **Goal**: Reorganize the `scripts/` directory for better clarity with minimal effort. Group related scripts into subdirectories. Avoid complex refactoring or new patterns like dispatchers.

- [ ] **Phase 1: Create Grouping Directories and a `common.sh`**
  - Action: Create the new directory structure: `scripts/test/`, `scripts/lint/`, `scripts/docker/`, `scripts/ci/`, `scripts/dev/`.
  - Action: Create a single `scripts/common.sh` file. Initially, it will only contain `set -euo pipefail` and basic color variables for logging.
  - Verify: The new directories and the `common.sh` file exist.

- [ ] **Phase 2: Move All Scripts into Logical Groups**
  - Action: Move existing scripts into their new homes.
    - **test/**: `test_unit.sh`, `test_integration.sh`, `test_e2e.sh`, `test_ui.sh`, `test.sh` (old), `pytest_with_cleanup.sh`
    - **lint/**: `lint.sh` (old), `semgrep_local.sh`
    - **docker/**: `build_app.sh`, `docker-setup.sh`, `docker-reset.sh`, `cleanup_docker_and_ci_cache.sh`
    - **ci/**: `pre_push.sh`, `pre-commit.sh`, `ci_local_fast.sh`, `ci_act.sh`
    - **dev/**: `setup-dev-env.sh`, `install-system-tools.sh`, `promote_dev_to_main.sh`, `clean_artifacts.sh`, `monitor_gpu.sh`
  - Action: Keep top-level, user-facing scripts as they are: `ingest.sh`, `cli.sh`, `config.sh`.
  - Verify: `ls scripts/` is clean. `ls scripts/test/` (and others) contain the moved scripts.

- [ ] **Phase 3: Update Script Paths in a Few Key Places**
  - Action: Add `source "$(dirname "$0")/../common.sh"` to the top of the moved scripts.
  - Action: Update the paths in `scripts/git-hooks/` to point to the new locations (e.g., `scripts/ci/pre-push.sh`).
  - Action: Update the paths in `.github/workflows/` to point to the new script locations.
  - Verify: Git hooks and CI workflows continue to work correctly.

- [ ] **Phase 4: Document the New (Simpler) Structure**
  - Action: Add a `scripts/README.md` that briefly explains the purpose of each subdirectory.
  - Verify: The documentation provides a clear map of the new structure.

#### P5 — Pre-push performance optimizations (local DX) — remaining tasks

- [ ] Pre-commit integration for changed-files speedups
  - [ ] Add `.pre-commit-config.yaml` with `ruff` (lint + format) and optional `pyright` hooks
  - [ ] Install hooks (`pre-commit install`) and document usage
  - [ ] Configure to run only on changed files to keep local runs snappy

- [ ] Documentation updates
  - [ ] Document all local toggles in `docs/DEVELOPMENT.md` (e.g., `SKIP_LINT`, `SKIP_PYRIGHT`, `SKIP_TESTS`, and `SKIP_LOCAL_SEC_SCANS`)
  - [ ] Provide a "fast push" recipe, e.g.: ``SKIP_PYRIGHT=1 SKIP_LOCAL_SEC_SCANS=1 git push``
  - [ ] Note how to opt-in to CodeQL locally: ``SKIP_LOCAL_SEC_SCANS=0 git push``

- [ ] Version alignment and consistency
  - [ ] Pin the local `pyright` version (e.g., in `requirements-dev.txt`) to match CI
  - [ ] Ensure `ruff` version in pre-commit matches the CI action version (`0.5.3` today)

#### P5.1 — Docker build cache and context optimizations

- [ ] Add a root `.dockerignore` to shrink build context and improve cache hits
  - Action: Create `.dockerignore` at repo root including at minimum: `.git`, `.venv`, `__pycache__/`, `*.pyc`, `logs/`, `data/`, `node_modules/`, `dist/`, `build/`, `*.ipynb_checkpoints`.
  - Verify: Run a build and confirm the "Sending build context" size drops and cache hit rate increases on subsequent builds.

- [ ] Use BuildKit apt cache for OS package installs
  - Action: In `docker/app.Dockerfile`, change the apt layer to use a cache mount:
    - Replace the apt RUN with `RUN --mount=type=cache,target=/var/cache/apt apt-get update && apt-get install -y --no-install-recommends ... && apt-get clean && rm -rf /var/lib/apt/lists/*`.
  - Verify: Second build is faster with cache hits on apt downloads.

#### P6 — Cursor Rules Audit: Resolve Conflicts and Standardize

- **Context**: Audit of `.cursor/rules/` identified critical conflicts between rules that could cause inconsistent agent behavior
- **Goal**: Resolve conflicts and standardize guidance for consistent agent behavior

#### **Best Practices Alignment: Simplify Overly Detailed Rules**

- [x] **Simplify 1: Overly lengthy uv-sandbox rule**
  - Action: Condense the 30-line uv-sandbox rule to focus on core principles only
  - Action: Remove detailed step-by-step instructions that belong in documentation
  - Action: Keep only essential guidance for when and how to use uv sandbox
  - Verify: Rule is concise and actionable without being overly prescriptive ✅

- [x] **Simplify 2: Overly detailed testing rule**
  - Action: Reduce the 23-line testing rule to core testing principles
  - Action: Remove specific implementation details that belong in docs
  - Action: Focus on high-level testing guidance and markers
  - Verify: Rule provides clear direction without excessive detail ✅

- [x] **Simplify 3: Overly constraining problem-solving rule**
  - Action: Condense the verbose problem-solving rule to essential steps
  - Action: Remove redundant explanations and repetitive language
  - Action: Keep the core 3-attempt sequence but make it more concise
  - Verify: Rule is clear and actionable without being overly prescriptive ✅

- [x] **Simplify 4: Overly detailed linting rule**
  - Action: Consolidate the linting rule to focus on core principles
  - Action: Remove implementation details that belong in documentation
  - Action: Keep essential guidance for Ruff and Pyright usage
  - Verify: Rule is concise and focuses on key principles ✅

#### **Correction Plan: Fix Remaining Issues in Modified Rules**

- [x] **Fix 1: Inconsistent globs usage between related rules**
  - Action: Update `terminal_and_python.mdc` to include `globs: ["**/*.py"]` to match `linting.mdc` and `testing.mdc`
  - Action: Ensure all Python-related rules have consistent glob patterns
  - Verify: All Python-related rules use consistent glob patterns ✅

- [x] **Fix 2: Missing cross-reference in error-handling rule**
  - Action: Add reference to problem-solving rule in error-handling.mdc for clarity
  - Action: Ensure rules properly reference each other for sequence understanding
  - Verify: Rules clearly reference their related counterparts ✅

- [x] **Fix 3: Inconsistent Python path in linting rule**
  - Action: Update `linting.mdc` to use `.venv/bin/python` instead of just `python` for consistency
  - Action: Ensure all rules use the same Python path format
  - Verify: All rules use consistent `.venv/bin/python` path ✅

- [x] **Fix 4: Verify problem-solving rule precedence is clear**
  - Action: Ensure problem-solving rule clearly states when it overrides error-handling
  - Action: Add explicit sequence guidance for agents
  - Verify: Clear sequence: error-handling first, then problem-solving after 3 attempts ✅

- [x] **Critical Fix 1: Resolve problem-solving vs error-handling conflict**
  - Action: Update `error-handling.mdc` to clarify it applies to initial validation failures only, not after problem-solving attempts
  - Action: Update `problem-solving.mdc` to specify it applies after error-handling has been attempted 3 times
  - Verify: Rules provide clear, non-conflicting guidance on failure handling sequence ✅

- [x] **Critical Fix 2: Standardize Python path usage**
  - Action: Update `terminal_and_python.mdc` to use `.venv/bin/python` consistently instead of `python` alias
  - Action: Ensure alignment with user rules preference for explicit venv path
  - Verify: All terminal command examples use consistent Python path ✅

- [x] **Critical Fix 3: Clarify revert vs stop behavior**
  - Action: Merge guidance from `post-edit-build-test.mdc` and `error-handling.mdc`
  - Action: Specify when to revert changes vs when to just stop execution
  - Verify: Clear, non-conflicting guidance on failure response ✅

- [x] **Minor Fix 4: Consolidate testing guidance**
  - Action: Review overlap between `testing.mdc` and `linting.mdc` for pytest execution
  - Action: Consolidate redundant guidance into single source of truth
  - Verify: No duplicate or conflicting testing instructions ✅

- [x] **Minor Fix 5: Clarify agent stopping conditions**
  - Action: Review `plan-agent-dont-execute.mdc` and `stop-custom-agent.mdc` for overlap
  - Action: Clarify when each rule applies and their relationship
  - Verify: Clear distinction between plan mode and execution mode stopping ✅




 