# Archived Tasks

This file records tasks that have been completed and moved out of the active TODO backlog.

## Archived on 2025-01-28

#### P0 — Epic: Refactor Testing Strategy for Robustness and Simplicity ✅ COMPLETED

- **High-Level Goal**: Overhaul the testing strategy to align with modern best practices. This involved centralizing the model cache for reliable offline testing, hardening the application's model-loading logic, and replacing fragile, module-level mocks with clean, scoped pytest fixtures.

- **Benefits Achieved**:
  - **Simplicity & Readability**: Tests became much easier to read, understand, and maintain.
  - **Reliability**: `monkeypatch` and fixtures provided robust test isolation, preventing tests from interfering with each other.
  - **Robustness**: Application logic was hardened by removing silent fallbacks in favor of explicit, predictable errors.
  - **Maintainability**: Followed standard pytest patterns, making it easier for new developers to contribute.

- **Phase 1: Harden Application Code and Centralize Model Cache** ✅ **COMPLETED**
  - **Context**: Before refactoring the tests, the application itself was made robust and the testing environment was stabilized. This involved making the CrossEncoder a hard dependency and ensuring models were cached for offline use.
  - [x] **Task 1.1: Centralize and Configure the Model Cache.**
    - **Action**: Ensured the `model_cache` directory was at the project root, ignored by Git, included in the Docker build context, and copied into the container with the `SENTENCE_TRANSFORMERS_HOME` environment variable correctly set.
    - **Verify**: The command `./scripts/test.sh integration` passed without requiring network access to download models.
  - [x] **Task 1.2: Remove Cross-Encoder Fallback Logic.**
    - **Action**: Modified `_score_chunks()` in `backend/qa_loop.py` to remove the keyword-based and neutral-score fallbacks. If the CrossEncoder model failed to load, the function raised a clear `RuntimeError`.
    - **Verify**: The code in `_score_chunks()` was simplified, containing only the CrossEncoder scoring path. The test suite had failures that the next phase addressed.

- **Phase 2: Refactor Unit Tests with Pytest Fixtures** ✅ **COMPLETED**
  - **Context**: With a hardened application and stable environment, the unit tests were refactored to use modern, simple mocking patterns. This phase replaced all global, stateful mocking with scoped pytest fixtures.
  - **Target Approach**: Modern pytest fixtures (`managed_cross_encoder`, `mock_embedding_model`) became the preferred method for unit tests.
  - [x] **Task 2.1: Create Mocking Fixtures in `conftest.py`.**
    - **Action**: Created `managed_cross_encoder` fixture that patched `backend.qa_loop._get_cross_encoder` (TARGET APPROACH).
    - **Action**: Created `mock_embedding_model` fixture that patched `backend.retriever.SentenceTransformer` (TARGET APPROACH).
    - **Action**: Created `reset_cross_encoder_cache` autouse fixture for state management.
    - **Verify**: The fixtures were available and working in the test suite.
  - [x] **Task 2.2: Refactor QA Loop Unit Tests.**
    - **Action**: Updated `tests/unit/test_qa_loop_logic.py` to use `managed_cross_encoder` fixture (TARGET APPROACH).
    - **Action**: Removed old setup/teardown logic and manual state manipulation.
    - **Action**: Tests now used modern pytest-native mocking patterns.
    - **Verify**: QA loop unit tests were stable and used the new fixture-based approach.
  - [x] **Task 2.3: Refactor Search Logic Unit Tests.**
    - **Action**: Updated `tests/unit/test_search_logic.py` to use `mock_embedding_model` fixture (TARGET APPROACH).
    - **Action**: Removed manual state manipulation.
    - **Verify**: Search logic unit tests passed using the new fixture-based mocking.

- **Phase 3: Full Suite Validation and Cleanup** ✅ **COMPLETED**
  - **Context**: After refactoring, the entire suite was validated to ensure it was stable, clean, and that no regressions were introduced.
  - [x] **Task 3.1: Run Full Test Suite.**
    - **Action**: Ran the entire test suite, including unit, integration, and E2E tests.
    - **Verify**: All tests passed (`.venv/bin/python -m pytest`).
  - [x] **Task 3.2: Remove Dead Code.**
    - **Action**: Removed any unused imports, variables, or helper functions related to the old mocking strategy from the test files.
    - **Verify**: The test codebase was clean, simpler, and followed a consistent, modern pattern.

**Status**: All phases completed. The testing strategy has been successfully refactored to use modern pytest fixtures, providing robust test isolation, improved maintainability, and hardened application logic.


## Archived on 2025-08-16

#### P1 — Final Verification of All Meta Linters

- **Overall P1 Goal**: Confirm that all meta-linters pass after all preceding fixes and optimizations.

#### P1.1 - [REVISED] Debug and Fix `yamlfmt` Failures
- **Goal**: Ensure `yamlfmt --lint` runs without errors by leveraging the existing `.gitignore` to exclude irrelevant files and directories.
- **Best Practice**: Use a single source of truth for ignored files (`.gitignore`) to avoid configuration drift and simplify maintenance. The `-gitignore_excludes` flag in `yamlfmt` is the ideal tool for this.

- [x] **Task 1: Validate `.gitignore`**
  - Action: Review the `.gitignore` file to confirm that it properly excludes virtual environment directories (`.venv/`, `tools/uv_sandbox/`) and other paths that might contain problematic YAML files.
  - Verify: The `.gitignore` file should already contain the necessary exclusion patterns.

- [x] **Task 2: Test `yamlfmt` with the correct glob pattern**
  - Action: Run the command `yamlfmt --lint "**/*.yaml" "**/*.yml"` to test the linter with the correct glob pattern.
  - Verify: The command should complete successfully.

- [x] **Task 3: Update the `product_todo.md`**
  - Action: Modify the original `P1` task to use the correct glob pattern for the `yamlfmt` command.
  - Verify: The `P1` task in `product_odo.md` should be updated to `yamlfmt --lint "**/*.yaml" "**/*.yml"`.

- [x] **Task 4: Final Verification**
  - Action: Run the updated `P1` task's commands.
  - Verify: All linter commands, including the revised `yamlfmt` command, should exit with code 0.

#### P1.2 — Fix `yamlfmt` Formatting Automatically

- **Goal**: Apply `yamlfmt` formatting rules directly to fix the `docker-compose.yml` file.
- **Best Practice**: Let the formatting tool manage the file's contents to ensure it conforms to all configured rules, including line length, quoting, and indentation.

- [x] **Action**: Run `yamlfmt` on the specific file that is causing issues, letting it automatically apply the correct formatting based on the rules in `.yamlfmt`.
  - Command: `yamlfmt docker/docker-compose.yml`
- [x] **Verify**: Run the linter check again to confirm that the file now passes.
  - Command: `yamlfmt --lint docker/docker-compose.yml`
- [x] **Verify**: Run the full linter suite again to ensure all meta-linters pass.
  - `actionlint -color`
  - `yamlfmt --lint "**/*.yaml" "**/*.yml"`
  - `hadolint docker/app.Dockerfile`


- [x] Action: Run all three meta linters:
  - `actionlint -color`
  - `yamlfmt --lint "**/*.yaml" "**/*.yml"`
  - `hadolint docker/app.Dockerfile`

- [x] Verify: All commands exit with code 0 and report no errors.

## Archived on 2025-01-27

### P0 — Docker Build Optimizations ✅ COMPLETED

- **Goal**: Improve Docker build performance by reducing the build context and leveraging BuildKit caching.

- [x] **Step 1: Add `.dockerignore`** ✅ **COMPLETED**
  - Action: Create a root `.dockerignore` file to exclude unnecessary files like `.git`, `.venv`, and `__pycache__` from the build context.
  - Verify: Observe a smaller "Sending build context to Docker daemon" size during the next build.

- [x] **Step 2: Use BuildKit Cache for `apt`** ✅ **COMPLETED**
  - Action: Modify the `apt-get` layer in `docker/app.Dockerfile` to use a `--mount=type=cache`, which will speed up subsequent builds.
  - Verify: Confirm that a second `docker build` run is significantly faster due to cache hits on `apt` downloads.

- [x] **Step 3: Verify Optimization Effectiveness** ✅ **COMPLETED**
  - Action: Run a second Docker build to measure cache effectiveness and document the performance improvement.
  - Verify: Second build should be significantly faster, especially in the `apt` layer, and build context should remain small at 1.54kB. Cache mounts working effectively.

- [x] **Step 4: Security Validation** ✅ **COMPLETED**
  - Action: Run security scans (Semgrep, Hadolint) to validate that optimizations don't introduce security vulnerabilities.
  - Verify: All security scans pass with no findings.
  - **Result**: Semgrep (1062 rules) and Hadolint found zero security issues. All changes follow security best practices.

**Status**: All steps completed. Docker build optimizations have been successfully implemented with significant performance improvements (32.663s vs 100s+ first build), proper security validation, and effective BuildKit cache utilization.

### P5 — Log File Cleanup and Standardization (Task 2) ✅ COMPLETED

- **Goal**: Move all log files from project root to `logs/` directory and establish proper logging practices.

- [x] **Task 2: Update logging rule enforcement** ✅ **COMPLETED**
  - Action: Ensure the new logging rule (`.cursor/rules/logging.mdc`) is properly configured and applied.
  - Action: Update any CI scripts or build processes to create logs in `logs/` directory.
  - Verify: All new log files are created in the correct location.

**Status**: Task 2 completed. Logging rule enforcement has been properly configured and applied, ensuring all new log files are created in the correct `logs/` directory location.

### P1 — Renovate Local Development Setup and Validation ✅ COMPLETED

- **Goal**: Establish proper local development workflow for Renovate configuration validation and testing to prevent future configuration errors.

- [x] **Step 1: Install Renovate CLI and Validation Tools** ✅ **COMPLETED**
  - Action: Install Renovate CLI globally or ensure it's available via npx for local validation.
  - Action: Test the `renovate-config-validator` tool: `npx --package renovate renovate-config-validator renovate.json`
  - Verify: Validator runs without errors and confirms configuration is valid.

- [x] **Step 2: Set Up Local Authentication for Testing** ✅ **COMPLETED**
  - Action: Create a GitHub Personal Access Token (PAT) with minimal permissions (repo scope) for local testing.
  - Action: Set up environment variable: `export GITHUB_TOKEN=your_test_token`
  - Action: Create a dedicated test repository or fork for Renovate testing.
  - Verify: Can run Renovate CLI with authentication: `npx renovate --help` (should not show auth errors).

- [x] **Step 3: Implement Local Dry-Run Testing** ✅ **COMPLETED**
  - Action: Create a test script `scripts/test-renovate-config.sh` that runs:
    ```bash
    LOG_LEVEL=debug npx renovate --platform=local --dry-run=full --require-config=ignored --token=$GITHUB_TOKEN .
    ```
  - Action: Add the script to the project's development workflow.
  - Verify: Dry-run completes successfully and shows expected behavior without creating actual PRs.

- [x] **Step 4: Add Configuration Validation to CI/CD** ✅ **COMPLETED**
  - Action: Add a GitHub Action step to validate `renovate.json` before deployment.
  - Action: Use `renovate-config-validator` in the CI pipeline.
  - Verify: CI fails if Renovate configuration is invalid, preventing deployment of broken configs.

- [x] **Step 5: Create Configuration Testing Documentation** ✅ **COMPLETED**
  - Action: Document the local Renovate testing workflow in `docs/DEVELOPMENT.md`.
  - Action: Include troubleshooting guide for common Renovate configuration issues.
  - Action: Add examples of valid configuration patterns and common pitfalls.
  - Verify: Documentation provides clear guidance for future Renovate configuration changes.

- [x] **Step 6: Implement Configuration Migration Checks** ✅ **COMPLETED**
  - Action: Add `--strict` flag to validation to catch deprecated options and suggest migrations.
  - Action: Set up periodic checks for configuration updates and deprecation warnings.
  - Verify: System proactively identifies configuration issues before they cause failures.

**Status**: All steps completed. Renovate local development setup and validation workflow has been established with secure npx-based validation, local authentication, dry-run testing, CI/CD integration, comprehensive documentation, and migration checks.

### P2 — Fix Renovate Security and Best Practice Issues ✅ COMPLETED

- **Goal**: Revert problematic changes that violate security and best practices, while maintaining the working validation functionality.

- [x] **Step 1: Remove Renovate from System Tools Installation** ✅ **COMPLETED**
  - Action: Remove the Renovate installation section from `scripts/install-system-tools.sh`
  - Action: Remove Renovate version check from the installed versions list
  - Verify: System tools script no longer installs Renovate globally

- [x] **Step 2: Revert CI Workflow to Use npx** ✅ **COMPLETED**
  - Action: Change CI workflow back to use `npx --package renovate renovate-config-validator`
  - Action: Ensure both basic and strict validation use npx approach
  - Verify: CI uses npx instead of assuming global installation

- [x] **Step 3: Update Documentation to Reflect npx Approach** ✅ **COMPLETED**
  - Action: Update `docs/DEVELOPMENT.md` to use npx commands
  - Action: Remove reference to system tools installation
  - Action: Add note about why npx is preferred over global installation
  - Verify: Documentation consistently recommends npx approach

- [x] **Step 4: Test the Corrected Approach** ✅ **COMPLETED**
  - Action: Test local validation using npx approach
  - Action: Verify CI workflow changes work correctly
  - Action: Confirm no security vulnerabilities are introduced
  - Verify: All validation functionality works without global installation

**Status**: All steps completed. Renovate security and best practice issues have been resolved by reverting to npx-based validation, removing global installation, updating documentation, and maintaining all validation functionality without security vulnerabilities.

### P3 — Cursor Rules Enhancement: Challenge User Requests ✅ COMPLETED

- **Goal**: Create a new Cursor rule that enables AI agents to challenge user requests that go against best practices, ensuring better code quality and adherence to project standards.

- [x] **Step 1: Create Challenge User Requests Rule** ✅ **COMPLETED**
  - Action: Create `.cursor/rules/challenge-user-requests.mdc` with comprehensive guidance for challenging user requests
  - Action: Include examples of requests to challenge (security vulnerabilities, breaking patterns, over-engineering)
  - Action: Define clear challenge format with acknowledgment, concern identification, alternatives, and clarification
  - Verify: Rule file exists with proper YAML frontmatter and comprehensive content

- [x] **Step 2: Refine Rule Format and Content** ✅ **COMPLETED**
  - Action: Fix YAML frontmatter to match other `.mdc` files format
  - Action: Remove unnecessary noise and make challenge format more concise
  - Action: Add prioritization guidance for security vulnerabilities
  - Action: Include documentation linking and learning from user feedback
  - Verify: Rule is concise, actionable, and follows best practices for constructive feedback

- [x] **Step 3: Review Against Best Practices** ✅ **COMPLETED**
  - Action: Review the rule against established best practices for AI agent behavior
  - Action: Ensure the rule promotes respectful and constructive dialogue
  - Action: Verify the rule helps maintain code quality without being overly prescriptive
  - Verify: Rule is comprehensive, well-structured, and follows best practices for constructive feedback

**Status**: All steps completed. The challenge-user-requests rule has been created, refined, and reviewed. It provides clear guidance for AI agents to challenge user requests that go against best practices while maintaining respectful and constructive dialogue.

### P4 — Fix Pyright Warnings ✅ COMPLETED

- **Goal**: Resolve code quality issues identified by the Pyright type checker.

- [x] **Fix unused imports in test file** ✅ **COMPLETED**
  - Action: Fix pyright warnings for unused imports in `tests/unit/test_logging_config.py`
  - Verify: Pyright runs without warnings for the test file

## Archived on 2025-01-27

### P1 — Fix Meta Linter Errors (YAML, Docker, GitHub Actions) ✅ COMPLETED

- **Goal**: Fix all meta linter errors found by actionlint, yamlfmt, and hadolint to ensure CI passes and code quality standards are met.

- [x] **Phase 1: Fix YAML Document Start Issues** ✅ **COMPLETED**
  - Action: Add `---` document start markers to all YAML files that are missing them:
    - `.github/workflows/semgrep.yml`
    - `.github/workflows/codeql.yml`
    - `.github/workflows/trivy_pip-audit.yml`
    - `.github/workflows/codeql_local.yml`
    - `.github/workflows/meta-linters.yml`
    - `.github/workflows/semgrep_local.yml`
    - `.github/workflows/python-lint-test.yml`
    - `docker/docker-compose.yml`
    - `docker/docker-compose.ci.yml`
    - `.pre-commit-config.yaml`
    - `.yamlfmt`
    - `Continue_AI_coder/config.yaml`
    - `.gemini/config.yaml`
  - Verify: `yamlfmt --lint .github/ docker/ .pre-commit-config.yaml .yamlfmt Continue_AI_coder/ .gemini/` shows no formatting issues.

- [x] **Phase 2: Fix YAML Truthy Values** ✅ **COMPLETED**
  - Action: Configure yamlfmt to handle truthy values appropriately in GitHub Actions workflow files
  - Action: Fixed `workflow_dispatch:` to `workflow_dispatch: {}` in workflow files where needed
  - Verify: No formatting issues in yamlfmt output.

- [x] **Phase 3.5: Adopt Dedicated YAML Formatter (2025 Best Practices) - CORRECTED APPROACH** ✅ **COMPLETED**
  - **Goal**: Replace manual YAML formatting with automated tools to prevent future formatting issues and ensure consistency.
  - **Problem**: Previous approach created over-engineered custom solution. Need to use established tools with minimal effort.
  - **Analysis**: yamllint was problematic because it only lints but doesn't format, creating maintenance burden. Modern best practice is to use a formatter that can both format and check formatting.
  - **Decision**: Replaced yamllint with yamlfmt (Google's tool, widely adopted, fast, opinionated)
  - **Corrected Plan**:
    - [x] **Step 1: Clean up session artifacts** ✅ **COMPLETED**
      - Action: Remove `test_yaml_formatting.py` from project root (should be in tests/ if needed)
      - Action: Remove `scripts/format_yaml.py` (over-engineered custom solution)
      - Action: Remove ruamel.yaml from .venv (not needed for final solution)
      - Action: Remove temporary `scripts/install-yamlfmt.sh` script.
      - Verify: No custom YAML formatting or installation files remain in the project.
    - [x] **Step 2: Install and configure yamlfmt** ✅ **COMPLETED**
      - Action: Modify `scripts/install-system-tools.sh` to correctly download the `yamlfmt` tarball, extract the binary, and move it to `/usr/local/bin` using the existing `SUDO_CMD` logic.
      - Action: Create `.yamlfmt` configuration file with project-specific settings.
      - Action: Create simple wrapper script `scripts/format_yaml.sh` that runs yamlfmt.
      - Verify: Running `scripts/install-system-tools.sh` successfully installs `yamlfmt`.
    - [x] **Step 3: Replace yamllint in CI** ✅ **COMPLETED**
      - Action: Updated `.github/workflows/meta-linters.yml` to use yamlfmt instead of yamllint
      - Action: Configured yamlfmt to run in lint mode (`--lint`) for CI checks
      - Action: Removed yamllint from system tools installation scripts
      - Verify: CI pipeline uses yamlfmt for YAML validation
    - [x] **Step 4: Add to pre-commit hooks** ✅ **COMPLETED**
      - Action: Add yamlfmt hook to `.pre-commit-config.yaml`
      - Action: Configure to run only on changed YAML files
      - Verify: `pre-commit run yamlfmt --all-files` works correctly
    - [x] **Step 5: Update documentation and remove yamllint config** ✅ **COMPLETED**
      - Action: Removed `.yamllint.yml` file (no longer needed)
      - Action: Updated `docs/DEVELOPMENT.md` with yamlfmt usage guidelines
      - Action: Updated system tools installation to include yamlfmt instead of yamllint
      - Verify: Documentation provides clear yamlfmt guidelines, yamllint config removed
    - [x] **Step 6: Format all existing YAML files** ✅ **COMPLETED**
      - Action: Run yamlfmt on all project YAML files to standardize formatting
      - Action: Commit formatting changes
      - Verify: All YAML files are consistently formatted, CI passes

- [x] **Phase 3.6: Review and Correct Course** ✅ **COMPLETED**
  - **Goal**: Validate session changes against best practices and correct any missteps.
  - **Action**:
    - Reviewed the migration from `yamllint` to `yamlfmt`, confirming it follows best practices for tooling integration (installer, config, CI, pre-commit).
    - Acknowledged and corrected an improper automated fix to `Continue_AI_coder/config.yaml`, learning from the manual correction.
  - **Outcome**: Confirmed the overall direction is sound. No outstanding corrections are needed from this review. Resuming original plan.

- [x] **Phase 4: Fix Local CI (`act`) Failures** ✅ **COMPLETED**
  - **Goal**: Address and resolve all script and workflow errors identified during the local `act` run of the meta-linters workflow.
  - **Context**: The `act` run revealed failures in the `actionlint` and `yamlfmt` jobs. `actionlint` failed due to `shellcheck` warnings (SC2086), and the `yamlfmt` job failed because of an environment variable issue in the installation script.
  - [x] **Step 1: Fix `shellcheck` SC2086 warnings in workflows** ✅ **COMPLETED**
    - Action: Add double quotes to variables in `run` steps in `.github/workflows/codeql_local.yml` and `.github/workflows/python-lint-test.yml` to prevent globbing and word splitting issues.
    - Verify: `actionlint -color` runs without any output.
  - [x] **Step 2: Fix environment variable handling in installer** ✅ **COMPLETED**
    - Action: Modify the `apt-get` command in `scripts/install-system-tools.sh` to use `env` for passing the `DEBIAN_FRONTEND` variable, ensuring it works correctly in all shell environments.
    - Verify: The `yamlfmt` job's "Install yamlfmt" step passes in a subsequent `act` run.
  - [x] **Step 3: Re-run local CI to confirm all fixes** ✅ **COMPLETED**
    - Action: Execute `act --workflows .github/workflows/meta-linters.yml` again.
    - Verify: The `actionlint` and `yamlfmt` jobs complete successfully. The `hadolint` job may show a SARIF upload error, which is expected and can be ignored locally.
    - **Note**: Verification was blocked by a local Docker/`act` authentication issue, but the code changes were deemed complete.

- [x] **Phase 4.1: Course Correction for `actionlint`** ✅ **COMPLETED**
  - **Goal**: Refactor the `actionlint` workflow to use the official, dedicated GitHub Action instead of a third-party action or a direct Docker invocation.
  - **Context**: During debugging, the `actionlint` job was changed to use `reviewdog/action-actionlint`, which was an unnecessary over-correction. The best practice is to use the simplest, most direct tool for the job. The action was already correct, so this task was just to verify.
  - [x] **Step 1: Revert to a simpler `actionlint` action** ✅ **COMPLETED**
    - Action: Modify `.github/workflows/meta-linters.yml` to use `rhysd/actionlint-github-actions@v1` instead of `reviewdog/action-actionlint@v1`. This is the official action from the `actionlint` author.
    - Verify: The `actionlint` job in the `meta-linters` workflow runs successfully (or fails gracefully if there are actual linting errors).

- [x] **Phase 5: Fix Dockerfile Issues** ✅ **COMPLETED**
  - Action: Address hadolint warnings in `docker/app.Dockerfile`:
    - Pin apt package versions (DL3008 warning on line 42)
    - Fix shell script logic issue (SC2015 warning on line 60)
  - Verify: `hadolint docker/app.Dockerfile` shows no warnings or errors.

**Status**: All phases completed. Meta linter errors have been resolved through systematic fixes to YAML formatting, CI workflow issues, and Dockerfile linting warnings. The project now uses modern tooling (yamlfmt) and follows best practices for CI/CD pipeline quality.

### P1.1 — Correct Dockerfile Package Pinning (Session Review) ✅ COMPLETED

- **Goal**: Fix the incorrect package pinning approach implemented in this session and ensure the linter correctly ignores the intentional use of unpinned packages.

- **Problem Analysis**:
  - The session incorrectly pinned `apt` package versions, which conflicted with the project's security strategy of using `apt-get upgrade` on a pinned base image. This was correctly reverted.
  - However, the `hadolint` inline ignore pragma (`# hadolint ignore=DL3008`) was misplaced during edits, causing the linter to fail unnecessarily. `hadolint` requires the ignore comment to be on the line immediately preceding the `RUN` command.

- [x] **Step 1: Fix `hadolint` Pragma Placement in Dockerfile** ✅ **COMPLETED**
  - Action: In `docker/app.Dockerfile`, move the `# hadolint ignore=DL3008` directive to the line immediately before the `RUN apt-get update ...` command so it is correctly detected.
  - Verify: Running `hadolint docker/app.Dockerfile` exits successfully with no errors.

- [x] **Step 2: Document Security Strategy in `docs/docker-management.md`** ✅ **COMPLETED**
  - Action: Add a brief section to `docs/docker-management.md` explaining the project's security strategy for OS packages in Docker (i.e., using `apt-get upgrade` on a pinned base image).
  - Verify: The documentation is updated to clarify this for future development.

**Status**: All steps completed. Dockerfile package pinning approach has been corrected and documented, ensuring the linter properly recognizes the intentional use of unpinned packages as part of the project's security strategy.

## Archived on 2025-01-27

### P1 — Remove sudo from install-system-tools.sh for devcontainer compatibility ✅ COMPLETED

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

**Status**: All steps completed. The install-system-tools.sh script now works correctly in both host and devcontainer environments by conditionally using sudo based on the execution environment.

### P6 — Cursor Rules Audit: Resolve Conflicts and Standardize ✅ COMPLETED

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

**Status**: All steps completed. Cursor rules have been audited, conflicts resolved, and standardized for consistent agent behavior. Rules are now concise, non-conflicting, and provide clear guidance.

### P0 — Completed ✅

- [x] Fix pytest mark warnings by removing `@pytest.mark.unit` and its registration
  - Rationale: Migrating to folder-based test bundles where test type is derived from path. Explicit `unit` markers are being removed.
  - Action: Find all Python test files using the `@pytest.mark.unit` decorator.
  - Action: Remove the `@pytest.mark.unit` line from each identified test.
  - Action: Remove the `"unit: marks tests as unit tests"` line from the `markers` array in `pyproject.toml`.
  - Verify: Run pre-push checks (`scripts/git-hooks/pre-push.sh`) and confirm "PytestUnknownMarkWarning: Unknown pytest.mark.unit" warnings are no longer present.
  - Verify: All existing tests still pass.

- [x] Document pip root user warnings (expected in CI)
  - Action: Add `--root-user-action=ignore` to pip commands in CI if warnings become too noisy
  - Verify: CI documentation clearly explains these warnings are not actionable and expected behavior

### P1 — CLI/QA Loop UX and Logging Cleanup (reduce clutter, keep essentials) ✅

- Context and goal
  - Current situation: The CLI prints duplicate and overly verbose INFO logs (e.g., both plain and rich formats), shows non-actionable boot warnings, and surfaces low-level retrieval details (candidate counts, chunk heads) at INFO. This clutters the UX and hides the actual answer stream.
  - Goal: Provide a clean, minimal default console that shows only essential status and the streamed answer, while keeping rich diagnostic detail in rotating file logs and behind an explicit `--debug` mode. Ensure there is a single logger initialization path and predictable verbosity controls.

- [x] **CRITICAL: Fix CLI Implementation Issues (prevents meeting P1 goals)**
  - **Problem**: Nested `console.status` calls cause `LiveError`, CLI doesn't actually work, and original UX goals are not verified.
  - **Root cause**: Focused on logging configuration without testing the actual CLI behavior and UX improvements.
  - **Best practice**: Test the actual user experience, not just the underlying configuration.
  
  - [x] **Fix 1: Resolve nested console.status calls**
    - Action: Remove nested `console.status` calls in `qa_loop()` and `ensure_weaviate_ready_and_populated()`
    - Action: Use single status spinner or simple console messages instead
    - Action: Ensure only one live display is active at any time
    - Verify: CLI runs without `LiveError` and shows appropriate status messages
  
  - [x] **Fix 2: Verify UX improvements actually work**
    - Action: Test that verbose logs are suppressed in default mode
    - Action: Test that detailed logs appear in file but not console
    - Action: Test that `--debug` mode shows detailed console output
    - Action: Test that answer streaming works with clean formatting
    - Verify: CLI actually provides clean, minimal console output as intended
  
  - [x] **Fix 3: Test verbosity controls work correctly**
    - Action: Test `-q/--quiet` shows only warnings/errors
    - Action: Test `-v/--verbose` shows more detailed output
    - Action: Test `--log-level DEBUG` shows debug messages
    - Action: Verify precedence: `--log-level` > `-q/-v` > `LOG_LEVEL` env > default
    - Verify: All verbosity controls work as specified in original goals

- [x] Step 1 — Centralize logging (root-only, minimal console)
  - Action: Make `backend.config.get_logger` the only logger factory. Remove or delegate `backend.console.get_logger` to avoid handler duplication.
  - Action: Initialize once in `backend.config`:
    - RichHandler to stderr for console (message-only), level from `LOG_LEVEL` (default INFO).
    - RotatingFileHandler at DEBUG to `logs/rag_system.log` with full format.
    - Set noisy third-party loggers (`httpx`, `urllib3`, `requests`, `transformers`, `torch`, `sentence_transformers`, `pypdf`) to WARNING/ERROR.
    - Enable `logging.captureWarnings(True)`.
  - Verify: `.venv/bin/python -m backend.qa_loop --question "ping"` prints each message once; DEBUG appears only in the file log.

- [x] Step 2 — Simplify console UX (show essentials only)
  - Action: Replace multi-line readiness/info banners with `Console().status(...)` spinners; show at most two lines before the input prompt.
  - Action: Stream the answer prefixed with a single "Answer: "; use `rich.rule.Rule` for separators as needed.
  - Action: Downgrade retrieval details and step-by-step readiness logs from INFO → DEBUG; keep user-facing guidance at INFO.
  - Verify: Default run shows a clean prompt, concise status, and the streamed answer; detailed steps are only in `logs/rag_system.log`.

- [x] Step 3 — Predictable verbosity controls (CLI > env > default)
  - Action: Support `-q/--quiet` and `-v/--verbose` (repeatable) plus `--log-level LEVEL` in `backend.qa_loop`. Apply level early.
  - Action: Precedence: `--log-level` > `-q/-v` > `LOG_LEVEL` env > default INFO. Keep file handler at DEBUG regardless.
  - Action: Simplify `scripts/cli.sh` to pass flags through; avoid exporting `LOG_LEVEL` when `--debug/-v` is provided to prevent conflicts.
  - Verify: `-q` shows only warnings/errors; default shows minimal INFO; `-vv` shows DEBUG.

- [x] Step 4 — Targeted warning handling (no blanket ignores)
  - Action: Add selective `warnings.filterwarnings` for known noisy imports (e.g., specific SWIG deprecations). Do not globally ignore `DeprecationWarning`.
  - Action: Keep filtered warnings recorded in file logs via `captureWarnings`; suppress them from console by default.
  - Verify: Boot-time SWIG warnings disappear from console; remain visible in `logs/rag_system.log`.

- [x] **FIX: Logging Configuration Issues (introduced in this session)**
  - **Problem**: Missing imports (`logging`, `RichHandler`) in `qa_loop.py` cause CLI to fail. Logging setup function is in wrong place.
  - **Root cause**: Violated single responsibility principle by putting logging configuration in CLI module instead of centralized config.
  - **Best practice**: Logging configuration should be centralized in `backend/config.py` and CLI should only set levels, not configure handlers.
  
  - [x] **Fix 1: Move logging setup to config.py**
    - Action: Move `_setup_cli_logging` function from `qa_loop.py` to `backend/config.py` as `set_log_level`
    - Action: Add missing imports (`logging`, `RichHandler`) to `qa_loop.py`
    - Action: Update `qa_loop.py` to call `config.set_log_level` instead of local function
    - Verify: CLI runs without import errors
  
  - [x] **Fix 2: Simplify test approach**
    - Action: Remove complex CLI output tests that require full backend setup
    - Action: Keep simple unit test for logging configuration
    - Action: Focus on testing the logging setup function directly, not CLI output
    - Verify: Tests pass without requiring backend services
  
  - [x] **Fix 3: Clean up imports and architecture**
    - Action: Ensure all imports are at top of files
    - Action: Remove any duplicate or circular imports
    - Action: Verify logging configuration follows single responsibility principle
    - Verify: Code follows Python best practices for imports and module organization

- [x] Step 5 — Guardrails and docs
  - Action: Add a unit test asserting a single Rich console handler and no duplicate stream handlers after importing `backend.retriever`, `backend.qa_loop`, etc.
  - Action: Add a CLI output test asserting default/quiet/verbose behaviors using `capsys`.
  - Action: Update `README.md` and `docs/DEVELOPMENT.md` to document flags, precedence, and log file location.
  - Verify: `.venv/bin/python -m pytest -q tests/unit/test_logging_config.py tests/integration/test_cli_output.py` passes.

- [x] **IMPROVE: Logging Configuration Robustness (follow-up improvements)**
  - **Problem**: Tests directly manipulate global state, error handling is incomplete, and documentation is lacking.
  - **Root cause**: Rushed implementation focused on functionality over maintainability and robustness.
  - **Best practice**: Tests should be isolated, error handling should be comprehensive, and public APIs should be well-documented.
  
  - [x] **Improvement 1: Robust test isolation**
    - Action: Create a proper test fixture that resets logging state without direct global manipulation
    - Action: Use `pytest.fixture` with `autouse=True` to ensure clean state for all logging tests
    - Action: Add test for concurrent logging setup to ensure thread safety
    - Verify: Tests are more reliable and don't interfere with each other
  
  - [x] **Improvement 2: Better error handling and validation**
    - Action: Add input validation to `set_log_level` (check for None, empty strings, etc.)
    - Action: Use the configured logger instead of `logging.warning` in error cases
    - Action: Add logging configuration validation function to verify handlers are properly set up
    - Verify: Error cases are handled gracefully and logged appropriately
  
  - [x] **Improvement 3: Documentation and examples**
    - Action: Add comprehensive docstring to `set_log_level` with usage examples
    - Action: Document the logging configuration in `docs/DEVELOPMENT.md`
    - Action: Add type hints and improve function signatures where needed
    - Verify: New developers can understand and use the logging system correctly

- [x] **FINAL: Code Cleanup and Quality Assurance**
  - **Problem**: Unused imports remain in `qa_loop.py` after refactoring, and some minor formatting inconsistencies exist.
  - **Root cause**: Focus on functionality over code quality during rapid development.
  - **Best practice**: Code should be clean, lint-free, and follow consistent formatting standards.
  
  - [x] **Cleanup 1: Remove unused imports**
    - Action: Remove unused `logging` and `RichHandler` imports from `qa_loop.py`
    - Action: Run linter to verify no unused imports remain
    - Action: Ensure all imports are actually used in the code
    - Verify: `ruff check` passes with no unused import errors
  
  - [x] **Cleanup 2: Formatting consistency**
    - Action: Run `ruff format` on all modified files
    - Action: Ensure consistent spacing and line breaks
    - Action: Verify no trailing whitespace or formatting issues
    - Verify: All files follow consistent formatting standards
  
  - [x] **Cleanup 3: Final validation**
    - Action: Run all tests to ensure cleanup didn't break anything
    - Action: Test CLI functionality to ensure it still works
    - Action: Verify logging configuration works as expected
    - Verify: All functionality works correctly after cleanup

## Archived on 2025-08-15

### P0.1b — Local dev checks (pre-push) ✅ COMPLETED

- [x] Re-enable local security scans in pre-push
  - Action: Run push with `SKIP_LOCAL_SEC_SCANS=0` to include Semgrep/CodeQL locally: `SKIP_LOCAL_SEC_SCANS=0 git push -n` (dry run) or actual push.
  - Verify: Pre-push log shows Semgrep/CodeQL steps executed without schema errors and exits 0.

- [x] Install pyright in `.venv` so type checks run in pre-push
  - Action: `.venv/bin/pip install pyright` (optionally pin to CI version) and commit if adding to `requirements-dev.txt`.
  - Verify: `.venv/bin/pyright --version` succeeds and pre-push no longer warns about missing pyright.

**Status**: All steps completed. Local security scans are re-enabled in pre-push, and pyright is installed in the local venv for type checking.

### P0.2 — Test suite bundling into four bundles (unit, integration, e2e, ui) — simplified ✅ COMPLETED

- Context and goal
  - Current situation: tests are split across `tests/unit`, `tests/integration`, `tests/e2e`, `tests/e2e_streamlit`, plus `tests/environment` and `tests/docker`. There are custom pytest flags/hooks and some global marker-based exclusions (e.g., `-m "not ui"`). Unit socket blocking exists but enforcement paths are a bit complex.
  - Goal: simplify to directory-as-bundle as the single source of truth; remove custom flags and most hooks; rename `e2e_streamlit` → `ui`; migrate `environment` and `docker` tests into `integration` or `e2e`; run UI explicitly without coverage; select suites by path in dev and CI; keep only cross-cutting markers (`slow`, `docker` if needed, `external`).

- [x] Step 1 — Use directory-as-bundle; keep tagging minimal
  - Action: Treat each folder under `tests/` as the bundle source of truth; select suites by directory paths only:
    - `tests/unit/` (sockets blocked; fully mocked)
    - `tests/integration/` (one real component; network allowed)
    - `tests/e2e/` (full stack via Docker Compose)
    - `tests/ui/` (UI; Playwright/Streamlit; coverage disabled; run only when targeted)
    - Keep only cross-cutting markers like `slow`, `docker`, or `external` when needed.
  - Verify: `.venv/bin/python -m pytest --co -q tests/unit tests/integration tests/e2e tests/ui` lists items by directory; no reliance on `-m`.

- [x] Step 1.0 — Remove custom suite flags and collection hooks; keep one simple unit guard
  - Action: Delete custom options `--test-fast`, `--test-core`, `--test-ui` and related `pytest_collection_modifyitems` logic from `tests/conftest.py`.
  - Action: Keep a minimal autouse fixture in `tests/unit/conftest.py` that calls `pytest_socket.disable_socket(allow_unix_socket=True)`; remove redundant double-guards and diagnostics unless actively needed.
  - Verify: Unit runs block sockets; selecting by directory runs the expected tests without any custom flags or mark expressions.

- [x] Step 1.1 — Unit bundle (fast, fully mocked, sockets blocked)
  - Action: Standardize command alias: `.venv/bin/python -m pytest tests/unit -n auto -q`. Keep `UNIT_ONLY_TESTS=1` behavior and socket guards from `tests/unit/conftest.py`.
  - Verify: Command runs only `tests/unit/*`, exits green, and any real socket attempt fails fast with `SocketBlockedError`.

- [x] Step 1.2 — Audit and migrate tests to correct bundles
  - Action: Move any heavy or external-service-touching tests out of `tests/unit/` into `tests/integration/` (or `e2e` if they require the full stack). Remove redundant `unit/integration/e2e/ui` markers where the directory already defines the type; keep only cross-cutting tags like `slow`, `docker`, `external`.
  - Verify: `.venv/bin/python -m pytest tests/unit -q` remains green and fast; directory-scoped runs cover the moved tests.

- [x] Step 1.2.1 — Pre-push and docs
  - Action: Update pre-push hook to run only unit bundle by default: `.venv/bin/python -m pytest tests/unit --maxfail=1 -q` (respect `SKIP_TESTS=1`).
  - Action: Update `docs/DEVELOPMENT.md` with bundle definitions, directory-based commands, and expectations (mocking policy, network rules, and when to promote a test to a heavier bundle).
  - Verify: Fresh clone dev can follow docs to run each bundle successfully; pre-push remains quick.

- [x] Step 1.3 — Deprecate `tests/environment/` by migrating tests
  - Action: Audit each test in `tests/environment/` and move to:
    - `tests/integration/` if it validates local/python/ML setup without full compose or cross-service orchestration.
    - `tests/e2e/` if it depends on the full Docker stack or multiple real services.
  - Action: Remove redundant `environment` markers once migrated; keep only cross-cutting tags if needed.
  - Action: Delete `tests/environment/` after migration.
  - Verify: Directory-scoped runs for integration and e2e remain green; CI no longer references `environment`.

- [x] Step 1.4 — Deprecate `tests/docker/` by migrating tests
  - Action: Audit each test in `tests/docker/` and move to:
    - `tests/integration/` if it validates packaging/imports, app image build, or a single service without orchestrating the full stack during the test run.
    - `tests/e2e/` if it requires bringing up the full Compose stack or exercises cross-service interactions as part of the test.
  - Action: Remove redundant `docker` markers once migrated; keep only cross-cutting tags like `slow` when applicable.
  - Action: Delete `tests/docker/` after migration.
  - Verify: Directory-scoped integration and e2e runs are green; CI no longer references the `tests/docker/` directory (optional `-m docker` marker usage remains only if still needed).

- [x] Step 1.5 — Rename UI directory and update configs
  - Action: Rename `tests/e2e_streamlit/` → `tests/ui/`.
  - Action: Update references in configs and docs:
    - `pyproject.toml` → `[tool.pytest.ini_options].testpaths` updated to include `tests/ui`.
    - `pyproject.toml` → `[tool.coverage.run].omit` updated to `tests/ui/*`.
    - `tests/ui/conftest.py` contains a guard: raise a `pytest.UsageError` if coverage is enabled (UI requires `--no-cov`).
    - `tests/conftest.py` path filters updated to `tests/ui/`.
    - CI workflow jobs and any scripts to point to `tests/ui`.
    - Docs (`DEVELOPMENT.md`, README, any references) to use `tests/ui` nomenclature.
  - Verify: `.venv/bin/python -m pytest tests/ui --no-cov -q` collects and runs the UI tests; coverage omit still skips UI as expected.

- [x] Step 1.6 — Normalize project config to new folder layout
  - Action: In `pyproject.toml` `[tool.pytest.ini_options].testpaths`, remove `tests/ui` so default runs exclude UI entirely; developers and CI must target `tests/ui` explicitly.
  - Action: Replace any `tests/e2e_streamlit` references with `tests/ui`; remove `tests/environment` and `tests/docker` after migration.
  - Action: In `pyproject.toml` `[tool.pytest.ini_options].markers`, trim to cross-cutting only: keep `slow`, `docker` (if still used post-migration), and `external`; remove `unit`, `integration`, `e2e`, `ui`, and `environment` to avoid marker drift.
  - Action: Update docs (`DEVELOPMENT.md`) to state that directories determine bundles; markers are for cross-cutting semantics only.
  - Verify: `pytest --markers | cat` shows only the minimal cross-cutting markers; `pytest --co -q` lists items from the expected directories.

- [x] Step 1.7 — Remove unused pytest-docker config and prefer explicit Compose in scripts
  - Action: If not using `pytest-docker` plugin features directly, delete `[tool.pytest.docker]*` sections from `pyproject.toml` to reduce confusion.
  - Action: Prefer e2e orchestration via `scripts/test.sh e2e` that wraps `docker compose up -d --build && pytest tests/e2e -q && docker compose down -v`.
  - Verify: No plugin warnings on run; e2e orchestration flows through the script.

- [x] Step 3 — Integration bundle (one real component; network allowed)
  - Action: Standardize command: `.venv/bin/python -m pytest tests/integration -q`.
  - Action: Document policy: prefer Testcontainers or a single real dependency; for multi-service needs, move test to `e2e`.
  - Verify: Typical tests (e.g., `tests/integration/test_weaviate_integration.py`) pass without requiring the full compose stack; logs show no socket-block enforcement.

  - [x] Fix: Reset cached globals to avoid cross-test state (best practices)
    - Action: Add autouse fixture in `tests/integration/conftest.py` that clears `RAG_FAKE_ANSWER` and resets caches only if respective modules are already imported: `backend.qa_loop._cross_encoder`, `backend.qa_loop._ollama_context`, and `backend.retriever._embedding_model` via `sys.modules`.
    - Rationale: Aligns with `docs_AI_coder/AI_instructions.md` guidance to prevent flaky tests caused by cached globals and to not import modules inside fixtures (keeps patch decorators effective).
    - Verify: `.venv/bin/python -m pytest tests/integration -q` shows deterministic results; streaming test passes in isolation and alongside others.
    - Validation: All integration tests pass (28/28); flaky-tests guidance updated and condensed in `docs_AI_coder/AI_instructions.md`.

- [x] Step 4 — E2E bundle (all real components; network allowed)
  - Action: Provide a single dispatcher script `scripts/test.sh` with usage: `test.sh [unit|integration|e2e|ui]` that runs the standardized directory-based commands; for e2e it does `docker compose up -d --wait && pytest tests/e2e -q && docker compose down` with `set -euo pipefail`.
  - Verify: `bash scripts/test.sh unit|integration|e2e|ui` runs the intended bundle with minimal flags.
  
  ##### Hotfix Log — 2025-08-14
- [x] Ensure real QA e2e test uses ingestion fixture
  - **Action**: Explicitly import `docker_services_ready` from `tests/e2e/fixtures_ingestion.py` in `tests/e2e/test_qa_real_end_to_end.py` so Weaviate is bootstrapped and populated before calling `answer()`.
  - **Rationale**: Tests should prepare their environment; `answer()` should not implicitly bootstrap databases. This aligns with best practices of explicit test setup and isolation.
  - **Verify**: `bash scripts/test.sh e2e` runs green.

- [x] Preserve volumes during e2e teardown and clean up only test data
  - **Action**: Change `scripts/test.sh` e2e teardown to `docker compose down` (without `-v`) to avoid removing persistent volumes.
  - **Action**: Add session autouse fixture in `tests/e2e/conftest.py` to delete only the `TestCollection` at the end of the e2e session.
  - **Rationale**: Prevent accidental production data loss while ensuring ephemeral test data does not persist.
  - **Verify**: After e2e, volumes remain; `TestCollection` is removed.

- [x] Make bootstrap e2e use compose Weaviate (no app rebuild), not Testcontainers
  - **Action**: Add `weaviate_compose_up` fixture in `tests/e2e/conftest.py` to start only the `weaviate` service via docker compose (`up -d --wait weaviate`).
  - **Action**: Update `tests/e2e/test_weaviate_bootstrap_missing_collection_e2e.py` to use this fixture and connect to `http://localhost:8080` with gRPC 50051.
  - **Rationale**: Mirrors production networking (HTTP + gRPC) and avoids gRPC port mismatch issues seen with Testcontainers defaults.
  - **Verify**: Running the single test passes; e2e suite remains green.

- [x] Ensure e2e tests that need real Ollama start that container too
  - **Action**: Add `ollama_compose_up` fixture in `tests/e2e/conftest.py` to start only the `ollama` service via docker compose (`up -d --wait ollama`).
  - **Action**: Update `tests/e2e/test_qa_real_end_to_end.py` to depend on both `weaviate_compose_up` and `ollama_compose_up` (and register `tests/e2e/fixtures_ingestion` via `pytest_plugins`).
  - **Rationale**: Makes tests explicitly start real services they need and aligns with the production stack; avoids hidden dependencies.
  - **Verify**: Test runs with real Weaviate + Ollama and returns a non-empty answer without "I found no relevant context".
  
- [x] Step 5 — UI bundle (frontend/UI only; network allowed; coverage disabled)
  - Action: Require `-e .[ui]` and browsers; standardize command: `.venv/bin/python -m pytest tests/ui --no-cov -q`.
  - Verify: Without `--no-cov`, the run errors with clear usage as enforced by `tests/ui/conftest.py`. With `--no-cov`, only `tests/ui/*` are collected and run.

- [x] Step 6 — CI wiring: dedicated jobs per bundle
  - Action: In `.github/workflows/python-lint-test.yml`, keep `fast_tests` for Unit; add (or adjust existing) manual/scheduled jobs:
    - Integration: run `pytest tests/integration -q` with caching; avoid Playwright and full compose.
    - E2E: manual or scheduled; bring up compose, run `pytest tests/e2e -q`, then tear down.
    - UI: keep existing `ui_tests_act` flow; ensure it installs `-e .[ui]` and `playwright install`, then run `pytest tests/ui --no-cov -q`.
  - Verify: `act pull_request -j fast_tests` remains green. Manual `act workflow_dispatch -j ui_tests_act` runs UI. Integration/E2E jobs run only when triggered and pass locally under `act`.

- [x] Step 6.1 — Simplify default pytest options to avoid marker drift
  - Action: In `pyproject.toml` `[tool.pytest.ini_options].addopts`, remove `-m "not ui"` (directory selection and UI testpaths exclusion handle UI). Keep coverage args.
  - Action: Keep marker declarations only for cross-cutting categories (`slow`, `docker`, `external`) to document intent; do not require `unit/integration/e2e/ui` markers.
  - Verify: `pytest -q` on a fresh env collects all non-UI tests due to UI's own conftest coverage gating and directory-based commands in CI/scripts.

- [x] Step 7 — Developer UX: top-level scripts/Make targets
  - Action: Add convenience wrappers: `scripts/test_unit.sh`, `scripts/test_integration.sh`, `scripts/test_e2e.sh`, `scripts/test_ui.sh` with the standardized directory-based commands and minimal flags.
  - Verify: `bash scripts/test_unit.sh` runs the unit bundle; similar for other scripts.

**Status**: All steps completed. Test suite has been successfully reorganized into four clear bundles (unit, integration, e2e, ui) with directory-based organization, simplified configuration, and proper CI integration.

### P5 — Pre-push performance optimizations (local DX) ✅ MOSTLY COMPLETED

- [x] Switch lint/typecheck to native venv (faster than act)
  - [x] Replace `act ... -j lint` in the pre-push hook with native calls: `.venv/bin/ruff check .` and `.venv/bin/ruff format --check .`
  - [x] Replace `act ... -j pyright` with `.venv/bin/pyright`
- [x] Keep tests via `act` for parity; native fast path runs the unit bundle: `.venv/bin/python -m pytest tests/unit --maxfail=1 -q`

- [x] Add pre-push skip toggles (env-driven)
  - [x] Support `SKIP_LINT=1`, `SKIP_PYRIGHT=1`, `SKIP_TESTS=1` to selectively skip steps locally
  - [x] Default heavy scans to opt-in (CodeQL already defaults to skip via `SKIP_LOCAL_SEC_SCANS=1`)

- [x] Fail-fast for local tests
  - [x] Update pre-push fast tests invocation to include `--maxfail=1 -q` for quicker feedback on first failure

- [x] Pre-push alignment
   - [x] Replace any `--test-fast` references with `tests/unit` for pre-push context and update `scripts/pre_push.sh` accordingly

**Status**: Core performance optimizations completed. Pre-push now uses native venv tools for faster execution, includes skip toggles for flexibility, and implements fail-fast behavior. Remaining tasks are documentation updates and pre-commit integration.

## Archived on 2025-08-15

### P0.1a — Git Hooks Management (Best Practices) ✅ COMPLETED

- [x] Step 1 — Centralize Git Hooks in a Versioned Directory
  - Action: Create a new directory `scripts/git-hooks/`.
  - Action: Move the existing `.git/hooks/pre-commit` and `.git/hooks/pre-push` scripts to `scripts/git-hooks/`.
  - Action: Ensure the new `scripts/git-hooks/` directory is tracked by git.
  - Verify: `ls scripts/git-hooks` shows `pre-commit` and `pre-push`. The files are added in `git status`.

- [x] Step 2 — Configure Git to Use the Centralized Hooks Directory
  - Action: In `docs/DEVELOPMENT.md`, instruct developers to run `git config core.hooksPath scripts/git-hooks` once after cloning.
  - Action: Add a small script or a make target (e.g., `make setup-hooks`) to automate this configuration.
  - Verify: Running `git config --get core.hooksPath` returns `scripts/git-hooks`. Committing triggers the centralized hook.

- [x] Step 3 — Clean Up and Document
  - Action: Document the purpose of the shared hooks and the setup command in `docs/DEVELOPMENT.md`.
  - Action: Remind developers they can still have local, untracked hooks in `.git/hooks/` if they need to override something for their own workflow, but the shared hooks should be the default.
  - Verify: The documentation is clear and easy for a new developer to follow.

**Status**: All steps completed. Git hooks are centralized in `scripts/git-hooks/`, git is configured to use the centralized path, and documentation is complete in `docs/DEVELOPMENT.md`.

## Archived on 2025-08-10

### Test Refactoring Status

- Unit tests properly isolated (17 tests, ~9s runtime)
- Integration tests properly categorized (13 tests, ~33s runtime)
- All tests run by default (59 tests, ~21s runtime)
- 58.68% test coverage achieved
- Python testing best practices implemented

### P0.1 — Weaviate API Migration

- Weaviate API Migration: Server Upgrade — Upgraded Weaviate server to v1.32.0 in local and CI compose.
- Weaviate API Migration: Client Version Pinning — `weaviate-client==4.16.6` pinned in `requirements.txt`.
- Weaviate API Migration: Remove Deprecated Fallbacks — Removed `vectorizer_config` fallbacks; code uses modern `vector_config` API.
- Weaviate API Migration: Update Integration Test — Integration tests use modern API without fallbacks.
- Weaviate API Migration: Verify Full System — Full system validated via integration tests (ingestion, retrieval, search).

### P1.1 — Other tasks

- Add CI environment validation — Implemented (e.g., `pip check`).
- Add unit test for CLI error handling — Added; asserts stderr and exit code on error.
- Add unit test verifying startup calls `ensure_model_available` — Added; startup path validated.

### P0.2 — E2E Tasks (CLI and Streamlit)

- CLI E2E: Interactive mode times out — Fixed. Interactive path robust to piped stdin, immediate flush, graceful EOF.
- CLI E2E: Single-question mode times out — Fixed. Single-question path prints promptly and exits 0.
- Streamlit E2E: Fake answer not visible after click — Fixed. App renders `[data-testid='answer']` and immediate fake-answer when `RAG_FAKE_ANSWER` is set; `RAG_SKIP_STARTUP_CHECKS=1` honored.
- Streamlit E2E: Strengthen assertion to wait for content — Implemented `to_contain_text("TEST_ANSWER", timeout=20000)`.
- Streamlit E2E: Add tiny diagnostic wait behind env flag — Implemented `RAG_E2E_DIAG_WAIT` optional wait.
- Streamlit E2E: Add explicit fake-mode marker and env echo — Added `[data-testid='fake-mode']`; app logs `RAG_SKIP_STARTUP_CHECKS` and `RAG_FAKE_ANSWER` at startup.
- Streamlit E2E: Ensure fake-answer path fully bypasses backend and runs first — Submit handler renders fake answer immediately.
- Streamlit E2E: Confirm server flags and isolate coverage — Launch with `--server.headless true` and `--server.fileWatcherType none`; E2E runs with `--no-cov`.

### P0.3 — Stabilization and Finalization

- Deflake: modest timeout bump after fixes — Timeouts bumped where needed; tests stable.

### P1.1 — Other tasks

- Add CI environment validation — Implemented (e.g., `pip check`).
- Add unit test for CLI error handling — Added; asserts stderr and exit code on error.
- Add unit test verifying startup calls `ensure_model_available` — Added; startup path validated.



## Archived on 2025-08-12

### P0.0a — Validating the Dependency Compatibility and Versions (completed subgroups)

#### Skepticism checks
- Verify `torch==2.7.x` support with `sentence-transformers==5.x` on Python 3.12 — monitored; unresolved in docs but sandbox OK.
- Confirm plain pip installs under WSL2 + act — stable.
- Re-check Semgrep opentelemetry requirement — not required by default; keep Semgrep containerized.
- Validate one pinned set of `requirements*.txt` across contexts — workable; remain flexible if divergence appears.

#### Modified plan steps
1) UV diagnostic sandbox for compatibility resolution
   - `tools/uv_sandbox/pyproject.toml` created with target versions; `run.sh` added and later corrected to use `uv lock --check` and `uv sync --frozen`, unset `VIRTUAL_ENV`, and use CPU wheels via `PIP_EXTRA_INDEX_URL`/`UV_EXTRA_INDEX_URL`.
   - Stable `uv.lock` committed. Notes: `protobuf==5.29.5`, `grpcio==1.63.0`, `torch==2.7.1` (CPU), `sentence-transformers==5.0.0`, `weaviate-client==4.16.6`, `langchain==0.3.27`. OTel excluded.

2) Pin propagation to pip requirements
   - Analyzed `uv.lock`/`uv tree`; propagated direct pins to `requirements*.txt`.
   - Verified with `pip check`; core tests pass.

3) CI integration (GitHub Actions + act)
   - Standardized installs from `requirements*.txt`, ensured CPU torch wheel index available, added caching, isolated Semgrep, excluded OTel until compatible.

4) Docker integration
   - Multi-stage build using `requirements.txt`; copied only runtime artifacts; validated image size and cold-start.

5) Validation and rollout
   - Dry-run results: pip check OK; core tests: 79 passed, 1 skipped, 9 deselected, 1 xpassed; versions: protobuf 5.29.5, grpcio 1.63.0, torch 2.7.1+cpu, sentence-transformers 5.0.0.
   - Docker smoke: torch 2.7.1+cpu cuda False; protobuf 5.29.5; grpcio 1.63.0.

6) Automation and upgrades
   - Renovate configured for `requirements*.txt` and actions; added concise UV/upgrade guidance to `docs/DEVELOPMENT.md` and `.cursor/rules/uv-sandbox.mdc`.

### P0.0d — ignoring call-arg ?

- Replace `# type: ignore[call-arg]` in `backend/ingest.py` with a typed helper
  - Change: Introduced `backend/vector_utils.py` with `to_float_list()` and updated `backend/ingest.py` to use it.
  - Verify: Lints clean; embedding conversion uses explicit typing without ignores.
- Audit remaining vector conversions and remove ignores where possible
  - Targets:
    - `backend/retriever.py`: Refactored to use `to_float_list` and removed ignore.
    - Tests under `tests/integration/test_vectorizer_enabled_integration.py` use `# type: ignore[attr-defined]` for `.tolist()`; consider using `to_float_list` or dedicated test helpers for clarity.

### P0 — Corrections from best-practice review (this session)

- Docker wheel index scoping
  - Action: Keep `TORCH_WHEEL_INDEX` only as a build-arg and avoid persisting `PIP_EXTRA_INDEX_URL` in the final image. Ensures build-only knobs do not leak to runtime.
  - Status: Done (builder keeps `ARG TORCH_WHEEL_INDEX`; final stage no longer sets `PIP_EXTRA_INDEX_URL`).

- Make wheels guidance concise
  - Action: Replace verbose wheel instructions with short, variable-based snippets for Docker and local venv.
  - Status: Done in `docs/DEVELOPMENT.md`.
 
- Vector conversion helper clarity and robustness
  - Action: Refine `backend/vector_utils.py::to_float_list` to:
    - Prefer straightforward `torch is not None and isinstance(x, torch.Tensor)`/`isinstance(x, np.ndarray)` checks over `locals()` tricks
    - Exclude `str`/`bytes`/`bytearray` from generic `Sequence` handling
    - Handle numeric scalars via `numbers.Real`
  - Verify: Lints clean; `.venv/bin/python -m pytest --test-core` passes.

## Archived on 2025-08-13

### P2.9 — Enforce no-network in unit tests (completed)

- Add `pytest-socket` to `pyproject.toml` test extras and document usage — done
- Add an `autouse=True` session fixture to call `disable_socket(allow_unix_socket=True)` — done
- Replace connection-based self-check in session fixture with a lightweight assert — done
- Drop per-test re-disable once the offender was disproven — done
- Provide `allow_network` opt-in fixture (function scope) for rare cases; ensure any such tests are moved to `tests/integration/` — done
- Keep root guards against real Weaviate/Ollama calls; reconciled with pytest-socket to avoid duplicate/confusing messages — done

- Verify: a unit test attempting `httpx.get("http://example.com")` fails with a clear error — `tests/unit/test_network_block_httpx_unit.py` covers this; passes in isolation and in suite.

- Unit networking flake (investigated and resolved)
  - Added per-test logging in `tests/unit/conftest.py` to record socket-blocking status and test `nodeid` — done
  - Added early/late canaries `tests/unit/test__network_canary_first.py` and `tests/unit/test__network_canary_last.py` — added then removed after stability
  - Implemented a fail-fast diagnostic to immediately surface the first victim when sockets were detected enabled — gated via `UNITNETGUARD_FAIL_FAST` and kept as a toggle
  - Bisection and inspection found no offender locally; validated stability with randomized orders; canaries removed and a sentinel test kept

- Fail-fast and localization steps (summary)
  1) Fail-fast diagnostic enabled via env flag; active check asserts `SocketBlockedError`
  2) Bisection with `-k` and randomized order; no offender reproduced locally
  3) Fixture/library inspection; no state leaks identified; continued monitoring strategy adopted
  4) Full suite re-run green; fail-fast left as optional toggle
  5) Cleanup: removed canaries; kept session guard and `allow_network` fixture
  6) Hardening: added sentinel test and `weaviate.connect_to_custom` guard; docs updated

- Follow-up corrections (best-practice alignment)
      - [x] Update unit tests to assert `pytest_socket.SocketBlockedError` explicitly instead of generic `Exception`
      - [x] Reduce `UnitNetGuard` diagnostic log level from WARNING to INFO to avoid noisy test output
- Skeptic checks considered: ensured detection isn't masked by OS errors; reviewed shared fixtures; verified serial vs. parallel behavior

#### P1 — Stabilization and Finalization
 
- [x] Finalize: Full suite green
  - Action: Run the full suite locally; then update CI if needed.
  - Verify: `.venv/bin/python -m pytest -q -m "not environment" --disable-warnings` passes with 0 failures.

#### P2 — CI pipeline separation and test architecture tasks

- [x] P2.1 — Split test suites and defaults (unit/integration with coverage vs. UI/E2E without coverage)
  - Action: Adjusted `addopts` in `pyproject.toml` to exclude UI/E2E tests by default. Added `pytest` options (`--test-core`, `--test-ui`) in `tests/conftest.py` to run specific suites.
  - Verify: `pytest --test-core` runs the core suite with coverage. `pytest --test-ui --no-cov` runs the UI suite without coverage.

- [x] P2.2 — Prefer marker selection over runtime skip hooks
  - Action: Added a `pytest_collection_modifyitems` hook in `tests/e2e_streamlit/conftest.py` that raises a `pytest.UsageError` if UI tests are run with coverage enabled. Marked Playwright tests with `@pytest.mark.ui`.
  - Verify: Running UI tests with coverage fails early with a clear error message.

- [x] P2.3 — Simplify logging; drop per-test file handlers
  - Action: Removed `pytest_runtest_setup/teardown/logreport` hooks from `tests/conftest.py`.
  - Verify: Logging now relies entirely on the centralized `log_cli`/`log_file` configuration in `pyproject.toml`.

- [x] P2.4 — Standardize Docker management via pytest-docker
  - Action: Removed the custom `docker_services` and `test_log_file` fixtures from `tests/conftest.py`, relying on the `pytest-docker` plugin.
  - Verify: Integration tests still pass, with service management handled by the plugin.

- [x] P2.5 — Normalize markers and directories
  - Action: Added a `ui` marker and ensured test selection commands work correctly.
  - Verify: `pytest --test-ui` selects only Playwright tests; `pytest --test-core` excludes them.

- [x] P2.6 — Coverage configuration hardening
  - Action: Configured `.coveragerc` and `pyproject.toml` to store coverage data in `reports/coverage/`. The UI test suite guard ensures it is run with `--no-cov`.
  - Verify: `.coverage` files no longer appear in the project root.

 - [x] P2.7 — CI pipeline separation
  - Action: Split CI into two jobs: `tests-core` (coverage) and `tests-ui` (no coverage). Publish coverage from core job only.
  - Verify: CI runs green; core job uploads coverage HTML; Playwright browsers cached for UI job.

- [x] P2.8 — Developer docs and DX commands
  - Action: Updated `docs/DEVELOPMENT.md` and `docs_AI_coder/AI_instructions.md` with new `pytest` options.
  - Verify: Documentation reflects the new testing commands.

 - [x] P2.9 — Optional hardening for unit/fast test suites
    - Post-cleanup follow-ups (keep unit suite fast and deterministic)
      - [x] Make per-test diagnostic fixture a no-op by default
        - Action: Update `tests/unit/conftest.py::_log_socket_block_status` to return immediately unless `UNITNETGUARD_FAIL_FAST=1` is set; avoid doing any socket probe/logging on the default path.
        - Verify: `.venv/bin/python -m pytest -q tests/unit` remains green; wall time improves vs current.
      - [x] Keep fail-fast as an opt-in toggle only
        - Action: Document in `docs_AI_coder/AI_instructions.md` that setting `UNITNETGUARD_FAIL_FAST=1` enables the per-test probe and immediate failure on first detection.
        - Verify: With `UNITNETGUARD_FAIL_FAST=1`, the first victim is reported; without it, suite runs with no per-test probe.
      - Rationale: Best practice with `pytest-socket` is to rely on a session-level block plus targeted opt-in allowances. A default per-test network probe adds overhead and can mask offenders; keeping it behind an env flag provides rapid diagnosis without slowing normal runs.
    - Speed up feedback
      - [x] Add `pytest-xdist` and run fast tests with `-n auto` in CI for quicker PR feedback
        - [x] Add dependency to test extras and local env; verify `pytest -q -n auto tests/unit` passes
        - [x] Update CI workflow to use `-n auto` for the fast/core job
  - Guard against accidental real clients in unit tests
    - [x] Add a unit-scope fixture that monkeypatches `weaviate.connect_to_custom` to raise if called (unless explicitly patched in a test)
    - [x] Verify: a unit test calling real `connect_to_custom` fails; patched tests still pass

### P0 — Must do now (stability, forward-compat, fast feedback)

- **Fix 5 failing tests (network blocking and heavyweight model downloads)**
  - Plan (small, incremental steps)
    - [x] Enable sockets per-test for all non-unit suites (integration, environment, e2e, docker)
      - [x] Action: Add/update autouse fixtures in each suite's `conftest.py` to enable sockets at test start and restore blocking at test end. Update root guard in `tests/conftest.py` to also allow `e2e` (currently allows only integration/slow/docker).
      - [x] Verify: Run a representative test from each suite; confirm no `SocketBlockedError` and real connections are attempted.
    - [x] Use real models in non-unit tests where applicable
      - [x] Action: Ensure integration/environment tests instantiate real `SentenceTransformer`/`CrossEncoder` as written; do not use dummy embedders.
      - [x] Verify: `tests/integration/test_ingest_pipeline.py::{test_ingest_pipeline_loads_and_embeds_data,test_ingest_pipeline_is_idempotent}` now use the real model.
    - [x] Do not skip non-unit tests on missing external components
      - [x] Action: Remove graceful skips everywhere (fixtures and tests). Specifically:
        - [x] Drop skip logic from `tests/integration/test_ingest_pipeline.py::weaviate_client`.
        - [x] Remove Docker pre-check skip from `tests/integration/test_weaviate_integration.py`.
      - [x] Verify: When external components are unavailable, these tests fail, surfacing the issue.
    - [x] Use real external components in non-unit tests
      - [x] Action: Ensure integration/env/e2e/docker tests target real services and models; no dummy stand-ins. Keep only mocks where a test explicitly verifies mocked behavior.
      - [x] Verify: `tests/integration/test_vectorizer_enabled_integration.py` uses live Weaviate; ingestion tests use real `SentenceTransformer`; environment tests download required models. The container lifecycle test should pass when Docker is available; if not available, it should fail clearly.
    - [x] Re-run the 5 previously failing tests
      - [x] Action: `pytest -q` targeted to those tests only.
      - [x] Verify: All five pass; failures should point to missing externals rather than being skipped.

  - **Container lifecycle and network policy corrections (from recent changes)**
    - [x] Align non-unit test behavior with "no graceful skip" policy
      - [x] Action: Update `tests/conftest.py::docker_services` to FAIL if Docker/daemon is unavailable instead of calling `pytest.skip` (only for non-unit suites). Keep the in-container CI guard (`/.dockerenv`) as-is.
      - [x] Verify: Run an integration test with Docker stopped; expect a clear failure explaining Docker is required (not a skip).
    - [x] Enforce teardown in CI; keep-up only for local iterations
      - [x] Action: In CI workflows, set `TEARDOWN_DOCKER=1` (or pass `--teardown-docker`) so the session fixture tears down services. Keep local default as keep-up for fast iterations.
      - [x] Verify: CI logs show `docker compose down -v` after tests; no leftover CI containers/volumes.
    - [x] Document fast-iteration defaults and the wrapper script
      - [x] Action: Add a short section to `docs/DEVELOPMENT.md` describing: default keep-up policy, `--teardown-docker` and env toggles (`KEEP_DOCKER_UP`, `TEARDOWN_DOCKER`), and usage of `scripts/pytest_with_cleanup.sh`.
      - [x] Verify: Follow the doc steps locally to run `scripts/pytest_with_cleanup.sh tests/integration` (keeps up by default) and with `--teardown-docker` (cleans up compose and Testcontainers).
    - [x] Ensure sockets are enabled per-suite for all non-unit tests
      - [x] Action: Confirm we have autouse fixtures that temporarily `enable_socket()` in `tests/integration/`, `tests/environment/`, and `tests/e2e/` (added). No suite should rely on global allow-all.
      - [x] Verify: Representative tests in each suite can reach real services without `SocketBlockedError` while unit tests remain blocked by default.

### P8.1 — Socket handling simplification (follow-up)

- [x] Simplify unit-only socket blocking configuration
  - [x] Action: In `tests/unit/conftest.py`, remove the `markexpr` heuristic from `_disable_network_for_unit_tests` (unit scope already limits it to unit tests).
  - [x] Action: Remove stack-based exceptions in `_guard_against_enable_socket_misuse`; keep a simple guard that allows `allow_network` only.
        - [x] Verify: `pytest -q -k network_block_unit` shows unit blocking still enforced; `pytest -q tests/integration` remains green.

- [x] Remove unnecessary socket toggles in non-unit fixtures
  - [x] Action: In `tests/conftest.py::docker_services`, drop temporary `enable_socket()/disable_socket()` — sockets are allowed by default now.
  - [x] Action: Remove no-op network fixtures/comments in `tests/integration/`, `tests/environment/`, and `tests/e2e/` where not needed.
        - [x] Verify: `pytest -q tests/integration`, `pytest -q tests/environment`, and E2E single tests still pass locally.

### P3 — Semgrep blocking findings visibility and triage (local)

- Objective: Make blocking findings clearly visible locally and fix at least the top one.
- Plan (small, incremental steps)
   1) Ensure findings are shown even when the scan fails locally
      - [x] Update Semgrep workflow to run the summary step unconditionally (always) while keeping PRs failing on findings in CI
  2) Surface findings in terminal during pre-push
     - [x] Run the pre-push hook and verify the Semgrep findings summary shows rule, file:line, and message
  3) Triage and fix the top finding
     - [x] Identify the most critical/simple-to-fix finding from the summary
     - [x] Implement a minimal, safe fix in code
      - [x] Add/adjust a unit test if applicable — Added timeout assertions for Ollama HTTP calls in `tests/unit/test_ollama_client_unit.py`
  4) Verify locally
     - [x] Re-run pre-push; confirm Semgrep has no blocking findings
       - [BLOCKED: pre-push stops at lint due to protobuf constraint mismatch; Semgrep job run directly reports 0 blocking findings]

### P4 — CI/SAST enforcement

- CodeQL workflow
  - [x] Disable Default CodeQL setup in GitHub repo settings (to avoid advanced-config conflict)
  - [x] Broaden PR trigger (run on all PRs): remove `branches: ["main"]` under `on.pull_request`
  - [x] Validate `analyze@v3` inputs against official docs; if `output` is unsupported, remove it and adjust the local summary step accordingly
  - [x] Keep uploads enabled only on GitHub (skip on forks and under Act), and enforce via branch protection rather than hard-fail
- Semgrep workflow
  - [x] Ensure robust baseline: add a step to unshallow history before scan (`git fetch --prune --unshallow || true`), or fetch base commit for PRs
  - [x] Switch to official Semgrep Docker action; do not run under local act
  - [x] Keep SARIF upload skipped for forked PRs; consider two-job upload pattern if uploads are needed for forks
- Pre-push (local)
  - [x] Make pre-push resilient if `act` is missing: detect and skip with a clear message
  - [x] Add `SKIP_LOCAL_SEC_SCANS=1` guard to optionally skip Semgrep/CodeQL locally when needed
  - [x] Document the guard and prerequisites in `docs/DEVELOPMENT.md`
- Repo protection
  - [x] Configure branch protection to require "Code scanning results / CodeQL" and Semgrep check on PRs

### P1 — Fix Environment Configuration Issues ✅ COMPLETED

- **Context**: Recent refactoring removed the `cli` service but introduced configuration issues that need immediate fixing.

- [x] **Task 1: Create missing .env.docker file**
  - Action: Create `docker/.env.docker` file with container-internal URLs:
    ```
    OLLAMA_URL=http://ollama:11434
    WEAVIATE_URL=http://weaviate:8080
    ```
  - Verify: `docker compose -f docker/docker-compose.yml config` shows no errors.

- [x] **Task 2: Remove obsolete container_internal_urls fixture**
  - Action: Remove the `container_internal_urls` fixture from `tests/e2e/conftest.py` since `DOCKER_ENV` logic was removed.
  - Action: Update `test_qa_real_end_to_end.py` to remove dependency on this fixture.
  - Verify: E2E tests can run without the obsolete fixture.

- [x] **Task 3: Verify containerized tests work**
  - Action: Run containerized E2E tests to ensure they work with the simplified configuration.
  - Verify: `tests/e2e/test_qa_real_end_to_end_container_e2e.py` passes.

**Status**: All tasks completed. Environment configuration issues have been resolved, including the creation of the missing .env.docker file, removal of obsolete fixtures, and verification that containerized tests work correctly.

#### P5 — Fix yamlfmt CI Job and Local Pre-push Hook ✅ COMPLETED

- **Context**: The `yamlfmt` CI job was failing due to formatting issues in `docker/docker-compose.yml`. The goal is to ensure that `yamlfmt` runs correctly in the CI pipeline and that there is a local pre-push hook to catch formatting issues before they are pushed.

- [x] **Task 1: Correct Formatting in `docker/docker-compose.yml`**
  - Action: Manually run `yamlfmt docker/docker-compose.yml` to fix the formatting issues.
  - Verify: Run `yamlfmt --lint docker/docker-compose.yml` and confirm that it passes.

- [x] **Task 2: Verify `meta-linters.yml` Workflow**
  - Action: Ensure the `yamlfmt` job in `.github/workflows/meta-linters.yml` is configured to run `yamlfmt --lint "**/*.yml" "**/*.yaml"`.
  - Verify: The CI job should fail if there are any YAML formatting issues.

- [x] **Task 3: Add `yamlfmt` to Pre-commit Hook**
  - Action: Add a `yamlfmt` hook to `.pre-commit-config.yaml` to automatically format YAML files.
  - Action: Run `pre-commit autoupdate` to refresh the hooks.
  - Action: Run `pre-commit run --all-files` to apply the formatting to all existing files.
  - Verify: Committing a poorly formatted YAML file should trigger the hook and fix it automatically.

**Status**: All tasks completed. The yamlfmt CI job and local pre-push hook are now properly configured and working. YAML formatting is automatically applied and validated both locally and in CI.