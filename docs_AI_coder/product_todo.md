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

#### P1 — CLI/QA Loop UX and Logging Cleanup (reduce clutter, keep essentials)

- Context and goal
  - Current situation: The CLI prints duplicate and overly verbose INFO logs (e.g., both plain and rich formats), shows non-actionable boot warnings, and surfaces low-level retrieval details (candidate counts, chunk heads) at INFO. This clutters the UX and hides the actual answer stream.
  - Goal: Provide a clean, minimal default console that shows only essential status and the streamed answer, while keeping rich diagnostic detail in rotating file logs and behind an explicit `--debug` mode. Ensure there is a single logger initialization path and predictable verbosity controls.

- [ ] Step 1 — Centralize logging (root-only, minimal console)
  - Action: Make `backend.config.get_logger` the only logger factory. Remove or delegate `backend.console.get_logger` to avoid handler duplication.
  - Action: Initialize once in `backend.config`:
    - RichHandler to stderr for console (message-only), level from `LOG_LEVEL` (default INFO).
    - RotatingFileHandler at DEBUG to `logs/rag_system.log` with full format.
    - Set noisy third-party loggers (`httpx`, `urllib3`, `requests`, `transformers`, `torch`, `sentence_transformers`, `pypdf`) to WARNING/ERROR.
    - Enable `logging.captureWarnings(True)`.
  - Verify: `.venv/bin/python -m backend.qa_loop --question "ping"` prints each message once; DEBUG appears only in the file log.

- [ ] Step 2 — Simplify console UX (show essentials only)
  - Action: Replace multi-line readiness/info banners with `Console().status(...)` spinners; show at most two lines before the input prompt.
  - Action: Stream the answer prefixed with a single "Answer: "; use `rich.rule.Rule` for separators as needed.
  - Action: Downgrade retrieval details and step-by-step readiness logs from INFO → DEBUG; keep user-facing guidance at INFO.
  - Verify: Default run shows a clean prompt, concise status, and the streamed answer; detailed steps are only in `logs/rag_system.log`.

- [ ] Step 3 — Predictable verbosity controls (CLI > env > default)
  - Action: Support `-q/--quiet` and `-v/--verbose` (repeatable) plus `--log-level LEVEL` in `backend.qa_loop`. Apply level early.
  - Action: Precedence: `--log-level` > `-q/-v` > `LOG_LEVEL` env > default INFO. Keep file handler at DEBUG regardless.
  - Action: Simplify `scripts/cli.sh` to pass flags through; avoid exporting `LOG_LEVEL` when `--debug/-v` is provided to prevent conflicts.
  - Verify: `-q` shows only warnings/errors; default shows minimal INFO; `-vv` shows DEBUG.

- [ ] Step 4 — Targeted warning handling (no blanket ignores)
  - Action: Add selective `warnings.filterwarnings` for known noisy imports (e.g., specific SWIG deprecations). Do not globally ignore `DeprecationWarning`.
  - Action: Keep filtered warnings recorded in file logs via `captureWarnings`; suppress them from console by default.
  - Verify: Boot-time SWIG warnings disappear from console; remain visible in `logs/rag_system.log`.

- [ ] Step 5 — Guardrails and docs
  - Action: Add a unit test asserting a single Rich console handler and no duplicate stream handlers after importing `backend.retriever`, `backend.qa_loop`, etc.
  - Action: Add a CLI output test asserting default/quiet/verbose behaviors using `capsys`.
  - Action: Update `README.md` and `docs/DEVELOPMENT.md` to document flags, precedence, and log file location.
  - Verify: `.venv/bin/python -m pytest -q tests/unit/test_logging_config.py tests/integration/test_cli_output.py` passes.

#### P2 — Containerized CLI E2E copies (keep host-run E2E; add container-run twins)

- Why: Host-run E2E miss packaging/runtime issues (entrypoint, PATH, env, OS libs). Twins validate the real image without replacing fast host tests.

- [ ] Step 1 — Identify candidates
  - Action: List E2E tests invoking CLI in-process (e.g., `backend.qa_loop`) such as `tests/e2e/test_qa_real_end_to_end.py`.
  - Verify: Confirm they don’t already run via container.

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

- [ ] Document BuildKit and cache guidance
  - Action: In `docs/DEVELOPMENT.md` (Docker section), note that BuildKit is on by default; prefer cached builds. Use `--no-cache` only when intentionally refreshing. Mention `scripts/build_app.sh` passes through extra flags (e.g., `--no-cache`).
  - Verify: Doc updated and referenced from README as appropriate.

- [ ] Pin remote image tags for reproducibility (where reasonable)
  - Action: Audit image tags in `docker/docker-compose.yml` and `docker/app.Dockerfile`.
    - Keep `weaviate` pinned (already pinned).
    - Consider pinning `OLLAMA_IMAGE` default from `latest` to a known-good version; document override via env var.
    - Python base images are already pinned; keep that practice.
  - Verify: `docker compose up` uses the pinned versions; builds remain reproducible.

- [ ] Optional: Add opt-in image refresh step while defaulting to cache usage
  - Action: In `scripts/docker-setup.sh`, honor an env flag `FORCE_PULL=1` to run `docker compose pull` before build/up; default to not pulling.
  - Verify: With `FORCE_PULL=1`, images are updated; without it, local cache is used.

- [ ] Optional: Avoid dependency-layer cache busting
  - Action: Keep `requirements.txt` stable and separate dev/runtime dependencies (`requirements-dev.txt` vs runtime). Ensure `docker/app.Dockerfile` installs only runtime deps to preserve cache.
  - Verify: Code-only changes do not invalidate the dependency install layer; rebuilds are fast.

#### P5.2 — NLTK data setup - to make .md ingestion work (deterministic and reproducible)

- [ ] Replace brittle inline NLTK downloads in Docker with official downloader CLI
  - Action: In `docker/app.Dockerfile`, replace the current `python -c "import nltk; ..."` with:
    ```Dockerfile
    RUN mkdir -p /opt/venv/nltk_data \
        && ${VENV_PATH}/bin/python -m nltk.downloader -d /opt/venv/nltk_data punkt punkt_tab
    ```
  - Action: Remove any `|| true` so the build fails fast if downloads fail.
  - Verify: A fresh build succeeds and the layer contains `tokenizers/punkt` and `tokenizers/punkt_tab` under `/opt/venv/nltk_data`.

- [ ] Establish a single data path via `NLTK_DATA`
  - Action: Keep `ENV NLTK_DATA=/opt/venv/nltk_data` in Docker. For local dev, document using `export NLTK_DATA="$(pwd)/.venv/nltk_data"`.
  - Verify: `python -c "import nltk.data; print(nltk.data.path)"` includes the expected path in both envs.

- [ ] Local dev parity: documented bootstrap
  - Action: In `docs/DEVELOPMENT.md`, add a snippet for devs:
    ```bash
    export NLTK_DATA="$(pwd)/.venv/nltk_data"
    mkdir -p "$NLTK_DATA"
    .venv/bin/python -m nltk.downloader -d "$NLTK_DATA" punkt punkt_tab
    ```
  - Verify: On a clean venv, the commands complete and `nltk.data.find('tokenizers/punkt')` succeeds.

- [ ] Startup verification with clear error
  - Action: Add a lightweight check at app startup (or first-use path) to assert NLTK resources exist, e.g. `nltk.data.find('tokenizers/punkt')`, and raise a helpful message if missing.
  - Verify: When the data is removed/absent, the app fails fast with a clear remediation hint referencing the dev/Docker steps above.

- [ ] Pin library version for stability
  - Action: Pin `nltk` to a known-working version in `requirements.txt` (runtime) and `requirements-dev.txt` if needed.
  - Verify: Rebuild/install resolves the pinned version; tokenization works as before.

- [ ] Optional: Offline/CI artifacts for corpora
  - Action: For fully offline or hermetic builds, package the required subset of `nltk_data` as a build artifact (e.g., tarball) and add a Docker build step to extract it to `/opt/venv/nltk_data` with checksum verification.
  - Verify: Docker build succeeds without network when the artifact is provided; app runs and passes the startup verification.

#### P6 — E2E testing Tasks (CLI and Streamlit)

  - [ ] Create dedicated UI dependency extra (isolate Playwright)
    - [ ] Action: In `pyproject.toml`, move `pytest-playwright==0.4.4` and `playwright>=1.45,<2` out of the `test` extra and define a new extra: `[project.optional-dependencies].ui = ["pytest-playwright==0.4.4", "playwright>=1.45,<2"]`.
    - [ ] Action: Ensure default local/dev installs do NOT include `ui` (e.g., keep `-e .[test,docs,cli]`).
    - [ ] Verify: A fresh `pip install -e .[test,docs,cli]` does not install Playwright; `python -m playwright` is not available until `-e .[ui]` is installed.

  - [ ] CI dependency isolation for UI suite
    - [ ] Action: In `.github/workflows/python-lint-test.yml`, ensure only the UI job installs the UI extra (e.g., `pip install -e .[ui]` or `-e .[test,docs,cli,ui]` if those are needed there).
    - [ ] Action: In the same UI job, run `python -m playwright install --with-deps` before executing tests; remove any Playwright installs from non-UI jobs.
    - [ ] Verify: `act pull_request -j ui_tests_act` shows the UI extra being installed and browsers installed; `-j fast_tests`/`-j core_suite` do not install Playwright nor browsers.

  - [ ] Document isolated UI workflow for developers
    - [ ] Action: Update `docs/DEVELOPMENT.md` to show two paths:
      - Regular dev: `pip install -e .[test,docs,cli]` (no Playwright)
      - UI run: `pip install -e .[ui] && python -m playwright install --with-deps && pytest --test-ui --no-cov`
    - [ ] Verify: Follow the doc steps on a clean venv; UI tests only run after installing the `ui` extra and browsers.

  - [ ] Playwright dependency explicit pin (stability)
    - [ ] Action: In `pyproject.toml` add `"playwright>=1.45,<2"` to `[project.optional-dependencies].test` next to `pytest-playwright==0.4.4`, then reinstall dev deps.
    - [ ] Verify: `.venv/bin/python -m playwright --version` succeeds; `.venv/bin/python -m pytest --test-ui --no-cov -q` collects and runs UI tests.

  - [ ] Trim CI Playwright browser installs to UI jobs only (simplify CI)
    - [ ] Action: In `.github/workflows/python-lint-test.yml`, remove Playwright browser install steps from non-UI jobs (e.g., `core_suite`). Keep them only where `--test-ui` (or other Playwright tests) actually run.
    - [ ] Verify: `act pull_request -j fast_tests` and `-j core_suite` show no Playwright install step; `-j ui_tests_act` still installs browsers and runs UI tests.

  - [ ] Simplify UI coverage gating (reduce custom logic)
    - [ ] Action: In `tests/e2e_streamlit/conftest.py`, simplify the collection hook to only enforce: if `--test-ui` is used while coverage is enabled, raise a clear `pytest.UsageError`. Rely on default `-m "not ui"` from `pyproject.toml` to exclude UI tests in normal runs; drop verbose coverage detection/deselect logic if not needed.
    - [ ] Verify: `.venv/bin/python -m pytest -q` runs green with UI tests deselected; `.venv/bin/python -m pytest --test-ui --no-cov -q` runs UI tests; `.venv/bin/python -m pytest --test-ui -q` errors with the expected usage message.

  - [ ] Streamlit E2E: Improve locator resilience (only if still flaky)
    - Action: Switch input selection to `get_by_label("Ask a question:")`, keep `[data-testid]` for answers, and if needed add `page.wait_for_function` to await `TEST_ANSWER` text.
    - Verify: Re-run the single test; expect pass without diagnostic waits.

  - [ ] **Task 1: Isolate and Reproduce the Failure Reliably.**
    - **Goal:** Create a minimal, fast command that reliably demonstrates the failure, so we don't have to run the full 1-minute test suite to verify our fix.
    - **Action:** Use the simplest Playwright test we have (`test_browser_launch_only.py`) and run it with `pytest-cov` enabled.
    - **Verify:** Confirm this single test fails with the known `AttributeError`. Then, run it with `--no-cov` and confirm it passes. This gives us a clear baseline.

  - [ ] **Task 2: Implement a Conditional Skip.**
    - **Goal:** Ensure the default, coverage-enabled full suite runs green by not executing Playwright tests.
    - **Action:** In `tests/e2e_streamlit/conftest.py`, add a `pytest_collection_modifyitems` hook that unconditionally skips all tests in this directory whenever `--no-cov` is not present (i.e., default coverage runs). Keep a guard that raises if `--test-ui` is used without `--no-cov`.
    - **Verify:** Re-run the failing command from Task 1. All UI tests should now report as `SKIPPED` instead of `ERROR`.

  - [ ] Correction plan: Make UI skip unconditional under coverage
    - [ ] Simplify detection to: if not `--no-cov`, fully deselect items in `tests/e2e_streamlit` to avoid fixture setup
    - [ ] Re-run full suite: `.venv/bin/python -m pytest -q -m "not environment" --disable-warnings` should pass with 0 errors
    - [ ] Run UI-only suite without coverage: `.venv/bin/python -m pytest --test-ui --no-cov -q` should pass or at least run without coverage-related errors

  - [ ] **Task 3: Achieve a "Green" Full Suite Run.**
    - **Goal:** Ensure the main test suite can now run to completion and generate a coverage report without any errors.
    - **Action:** Run the full test suite command (`pytest -m "not environment"`).
    - **Verify:** The command should complete with all tests either passing or being skipped (specifically the Playwright tests). There should be zero errors, and a coverage report should be generated for the rest of the codebase.

  - [ ] **Task 4: Create a Separate, Coverage-Free E2E Test Run.**
    - **Goal:** Make sure our important Playwright E2E tests are still executed somewhere.
    - **Action:** Define a new, separate command that runs *only* the Playwright tests and explicitly disables coverage (`--no-cov`). This command will be used in our CI pipeline and for local E2E checks.
    - **Verify:** Run this new command and confirm that all Playwright tests pass.

#### P7 — Dependencies management last tasks: Compatibility monitors and guardrails

- Goal: Stabilize on Protobuf 5.x lane, keep sentence-transformers 5.x, and address dependency compatibility to minimize future surprises.
- Proposed Approach: Use `uv` as a diagnostic tool to find compatible pinned versions for `pip`, simplifying requirements management and isolating tooling.

#### Skepticism checks (archived; see `docs_AI_coder/archived-tasks.md`)
#### Modified plan steps (archived; see `docs_AI_coder/archived-tasks.md`)

**Compatibility monitors and guardrails (integrate into workflow)**
    - [ ] Active monitoring: Actively track the status of `opentelemetry-proto` support for Protobuf ≥5. If opentelemetry becomes a requirement later, and compatibility is confirmed, update the sandbox and re-pin. Until then, strictly avoid including opentelemetry in the application's main environment.
    - [ ] Weaviate-client integration: Confirm the tested version range for gRPC compatibility with the current Weaviate server version used. Add specific integration tests that target gRPC paths within the application if not already present.
    - [ ] Rollback strategy: Define clear rollback procedures. If updates introduced regressions, revert the pins in `requirements*.txt` and iterate in the `uv` sandbox to find a stable, compatible set before re-attempting the upgrade.

#### P7.3 — Renovate configuration best practices alignment

- [ ] Validate current Renovate config against best practices
  - Action: Run config validator locally to confirm schema and detect deprecations:
    - `npx --yes --package renovate -- renovate-config-validator`
  - Verify: Command exits 0; no errors; note any warnings for follow-up.

- [ ] Consider adopting Renovate `config:best-practices` (or add equivalent presets explicitly)
  - Action: Evaluate replacing `extends` with `config:best-practices`. If unavailable in your Renovate runner version, add the nearest equivalents explicitly:
    - Keep `config:recommended`
    - Add `helpers:pinGitHubActionDigests` (pin Actions to commit SHAs)
    - Add `:configMigration` (auto-migrate deprecated options)
    - Keep `docker:pinDigests` (already present)
  - Verify: Re-run validator; open a Renovate onboarding PR reflecting the new extends; confirm Actions are pinned to SHAs in subsequent PRs.

- [ ] Enable and verify GitHub vulnerability alerts integration
  - Action: Add/verify `"vulnerabilityAlerts": true` so Renovate opens PRs for GH advisories when supported by the platform/repo permissions.
  - Verify: After next run, security alert PRs appear when applicable; Renovate log shows the vulnerability alerts step enabled.

- [ ] Keep PR noise low while maintaining safety
  - Action: Review/update limits and schedule:
    - Confirm `prConcurrentLimit: 10`, `prHourlyLimit: 2` fit team capacity
    - Keep off-hours schedule (currently `before 6am on monday`) or consider `schedule:nonOfficeHours`
  - Verify: Next cycle keeps PR volume manageable; no daytime bursts.

- [ ] CI guardrail: validate Renovate config on PRs that touch it
  - Action: Add a lightweight CI job that runs the validator when `renovate.json` changes:
    - `npx --yes --package renovate -- renovate-config-validator`
  - Verify: Open a dummy PR modifying `renovate.json`; job runs and passes/fails appropriately.

- [ ] Python updates: confirm pinning and grouping strategy
  - Action: Keep `rangeStrategy: "replace"` for `pip_requirements` to update pins in `requirements*.txt`.
  - Action: Audit `pip_requirements.fileMatch` patterns cover all requirement files (e.g., `requirements.txt`, `requirements-dev.txt`, any `requirements-*.txt`). Expand if needed.
  - Action: Keep/adjust grouping rules (pytest/ruff/mypy/sphinx) and patch-only automerge for Python for safe, low-risk merges.
  - Verify: Sample cycle shows grouped PRs as expected; patch PRs for Python auto-merge cleanly.

- [ ] GitHub Actions updates: safety and automation
  - Action: Keep minor/patch automerge for Actions; ensure digest pinning is enabled via `helpers:pinGitHubActionDigests` (or `config:best-practices`).
  - Verify: New Actions PRs use commit SHAs and auto-merge when minor/patch.

- [ ] Docker updates: digest safety and auto-merge
  - Action: Keep `docker:pinDigests` extend and the packageRule that auto-merges `digest` updates on branch.
  - Verify: Digest-only PRs auto-merge and images remain pinned by digest.

#### P8 Next up (maintainability, observability)
- [ ] Refactor Weaviate connection logic into a single reusable function.
- [ ] Replace fragile relative paths with robust absolute paths where appropriate.
- [ ] Configure centralized file logging (e.g., `logs/app.log`) across CLI and services.
- [ ] Enhance progress logging for long-running ingestion (progress bar or granular steps).
- [ ] Review integration suite Docker autostart
  - [ ] Action: Measure runtime impact of `tests/integration/conftest.py::_start_docker_services_session` autouse startup.
  - [ ] Action: If overhead is significant and not broadly needed, scope compose startup to tests that require it (explicit `docker_services` usage) or guard autostart behind an env flag (e.g., `INTEGRATION_AUTOSTART_COMPOSE=1`).
  - [ ] Verify: Integration tests that need compose still pass; testcontainers-only tests remain unaffected and faster.

#### P8.1 — Socket handling simplification (follow-up)

Archived on 2025-08-13

#### P8.2 — Test path trust and tagging simplification

- Goal: Make test type derive from path (source of truth) and simplify markers to align with best practices.
- Plan (small, incremental steps)
  1) Enforce path-derived default markers
     - [ ] Action: Add/adjust a `pytest_collection_modifyitems` hook in `tests/conftest.py` to auto-apply markers by path:
       - `tests/unit/` → `unit`
       - `tests/integration/` → `integration`
       - `tests/environment/` → `environment`
       - `tests/e2e/` → `e2e`
       - `tests/e2e_streamlit/` → `ui`
       - `tests/docker/` → `docker`
     - [ ] Verify: `pytest --co -q` shows sample items with expected markers.
  2) Tighten fast suite selection
     - [x] Action: Ensure `--test-fast` collects only from `tests/unit/` and sets `UNIT_ONLY_TESTS=1` to enforce early socket block.
     - [ ] Verify: `.venv/bin/python -m pytest --test-fast -q` is green; no external network attempts appear in logs.
  3) Audit and relocate miscategorized tests
     - [ ] Action: Scan for tests under `tests/unit/` importing heavy/external services or carrying non-unit markers; move them to the correct directory (usually `tests/integration/`).
     - [ ] Verify: Re-run `--test-fast`; confirm it remains green and faster. Run `-m integration` to ensure moved tests are collected there.
  4) Simplify explicit markers
     - [ ] Action: Remove redundant `@pytest.mark.<type>` where the path already determines the type; keep only additional markers like `slow`, `ui`, or `docker` when needed.
     - [ ] Verify: `pytest -q` collects the same tests as before; diffs show only marker removals.
  5) Guardrail: reject mismatched path/marker
     - [ ] Action: In `pytest_collection_modifyitems`, error if a test under `tests/unit/` has markers `integration`, `e2e`, `docker`, or `environment` (and vice versa when appropriate).
     - [ ] Verify: Introduce a deliberate mismatch in a temporary branch; confirm collection fails with a clear message; revert.
  6) Documentation
     - [ ] Action: Update `docs/DEVELOPMENT.md` to document that path determines test type; markers are optional for extra semantics only. Document `--test-fast`, `--test-core`, `--test-ui` behavior.
     - [ ] Verify: Follow the doc to run each suite locally; results match expectations.
  7) CI alignment
     - [ ] Action: Keep the CI "Fast Tests" job on `--test-fast`. Add a lightweight job or step to run `pytest --check-test-paths` (via env/flag) to enforce the guardrail in PRs.
     - [ ] Verify: Open a draft PR with an intentional mismatch; CI step fails with a helpful message; revert.

#### P9 — Soon (quality, CI structure, performance)
- [ ] Expand unit test coverage, focusing on core logic and error paths.
- [ ] Improve test assertions and edge case testing across existing tests.
- [ ] Implement test data management fixtures for consistent, reliable tests.
- [ ] Review all integration tests for isolation and resource cleanup.
- [ ] Improve overall test isolation to ensure tests do not interfere with each other.
- [ ] Separate test jobs by type in GitHub Actions and update workflow/service deps.
- [ ] Add test quality gates (coverage thresholds, basic performance checks).
- [ ] Add performance benchmarks for critical paths (embedding generation, retrieval).
- [ ] Add further test categories/organization (logic, utils, mocks, etc.).

#### P10 — Later (docs, standards, templates, metrics)
- [ ] Update `DEVELOPMENT.md` with dependency management guidelines.
- [ ] Document logging and monitoring strategy in `DEVELOPMENT.md`.
- [ ] Create testing standards document.
- [ ] Add test templates for consistency and performance benchmarking.
- [ ] Improve test documentation and add test quality metrics tracking over time.




 