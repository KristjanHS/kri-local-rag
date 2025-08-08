#!/usr/bin/env bash
# scripts/promote_dev_to_main.sh – Safely promote changes from dev → main
#
# Features
# - Verifies clean working tree and up-to-date branches
# - Runs lint + tests on dev before merge
# - Fast-forward main to dev when possible; otherwise merges
# - Optional auto-resolution of conflicts by preferring dev
# - Re-runs checks on main after merge
# - Pushes main and shows live progress; logs to logs/promote_dev_to_main.log
#
# Usage
#   ./scripts/promote_dev_to_main.sh                   # normal run
#   ./scripts/promote_dev_to_main.sh --dry-run         # skip push
#   ./scripts/promote_dev_to_main.sh --prefer-dev-all  # auto-resolve ALL conflicts preferring dev
#   ./scripts/promote_dev_to_main.sh --create-pr       # if push to protected 'main' is blocked, auto-create PR dev → main
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source shared config (moves CWD to project root and prepares logs dir)
source "${SCRIPT_DIR}/config.sh"

SCRIPT_NAME="$(get_script_name "$0")"
LOG_FILE="$(get_log_file "$SCRIPT_NAME")"

# Simple colors
_red()   { printf "\e[31m%s\e[0m\n" "$*"; }
_green() { printf "\e[32m%s\e[0m\n" "$*"; }
_yellow(){ printf "\e[33m%s\e[0m\n" "$*"; }

DRY_RUN=0
PREFER_DEV_ALL=0
CREATE_PR=0

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    --prefer-dev-all) PREFER_DEV_ALL=1 ;;
    --create-pr) CREATE_PR=1 ;;
    *) _red "Unknown argument: $arg"; exit 2 ;;
  esac
done

setup_logging "$SCRIPT_NAME"

PY=".venv/bin/python"
if [[ ! -x "$PY" ]]; then
  _red "ERROR: $PY not found or not executable. Create the venv and install deps first." | tee -a "$LOG_FILE"
  exit 1
fi

need() {
  if ! command -v "$1" >/dev/null 2>&1; then
    _red "ERROR: required tool '$1' not found in PATH" | tee -a "$LOG_FILE"
    exit 1
  fi
}

need git
need ruff

# Track current branch to restore on exit
CURRENT_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")"

rollback_branch() {
  if [[ -n "${CURRENT_BRANCH:-}" && "$CURRENT_BRANCH" != "unknown" ]]; then
    git checkout "$CURRENT_BRANCH" >/dev/null 2>&1 || true
  fi
}

on_error() {
  local exit_code=$?
  _red "⛔ Failure (exit $exit_code). See $LOG_FILE for details." | tee -a "$LOG_FILE"
  # If a merge is in progress, give a hint
  if [[ -d .git/MERGE_HEAD ]]; then
    _yellow "A merge is in progress. Resolve conflicts or run: git merge --abort" | tee -a "$LOG_FILE"
  fi
  rollback_branch
  exit "$exit_code"
}
trap on_error ERR

log_step() {
  log_message "INFO" "$*" | tee -a "$LOG_FILE"
}

switch_to_dev() {
  if git show-ref --verify --quiet refs/heads/dev; then
    git checkout dev >/dev/null 2>&1 || {
      _yellow "Could not switch back to dev automatically; staying on $(git rev-parse --abbrev-ref HEAD)." | tee -a "$LOG_FILE"
      return
    }
    log_step "Switched back to dev for next changes."
  else
    _yellow "Local branch 'dev' not found; staying on $(git rev-parse --abbrev-ref HEAD)." | tee -a "$LOG_FILE"
  fi
}

ensure_clean_worktree() {
  if ! git diff-index --quiet HEAD --; then
    _red "ERROR: Working tree has uncommitted changes. Commit or stash first." | tee -a "$LOG_FILE"
    exit 1
  fi
}

fast_checks() {
  log_step "Running Ruff (lint)…"
  ruff check . | tee -a "$LOG_FILE"
  log_step "Running Ruff format --check…"
  ruff format --check . | tee -a "$LOG_FILE"
  log_step "Running pytest (fast suite)…"
  "$PY" -m pytest -q tests/ | tee -a "$LOG_FILE"
}

auto_resolve_conflicts() {
  # Returns 0 if all conflicts were resolved, 1 to abort
  local prefer_all="$1"  # 1 or 0
  local conflicts
  mapfile -t conflicts < <(git status --porcelain | awk '$1=="UU"{print $2}')

  if [[ ${#conflicts[@]} -eq 0 ]]; then
    return 0
  fi

  if [[ "$prefer_all" -eq 1 ]]; then
    _yellow "Auto-resolving ALL conflicts by preferring dev (theirs)…" | tee -a "$LOG_FILE"
    for f in "${conflicts[@]}"; do
      git checkout --theirs -- "$f"
      git add -- "$f"
    done
    git commit -m "chore: resolve merge conflicts by preferring dev" | tee -a "$LOG_FILE"
    return 0
  fi

  # Allow-list of files we auto-resolve by preferring dev
  local allow=(
    "README.md"
    "docs/"
    "docs_AI_coder/"
  )

  local unresolved=()
  for f in "${conflicts[@]}"; do
    local ok=0
    for a in "${allow[@]}"; do
      if [[ "$f" == "$a" || "$f" == $a* ]]; then ok=1; break; fi
    done
    if [[ $ok -eq 1 ]]; then
      git checkout --theirs -- "$f"
      git add -- "$f"
      log_step "Auto-resolved $f by preferring dev"
    else
      unresolved+=("$f")
    fi
  done

  if [[ ${#unresolved[@]} -eq 0 ]]; then
    git commit -m "chore: resolve selected conflicts by preferring dev" | tee -a "$LOG_FILE"
    return 0
  fi

  _red "Unresolved conflicts detected:" | tee -a "$LOG_FILE"
  printf '  %s\n' "${unresolved[@]}" | tee -a "$LOG_FILE"
  _yellow "Aborting merge. Please resolve manually or re-run with --prefer-dev-all." | tee -a "$LOG_FILE"
  git merge --abort
  return 1
}

ensure_clean_worktree

log_step "Fetching remotes…"
git fetch --all --prune | tee -a "$LOG_FILE"

log_step "Checking out dev and pulling (ff-only)…"
git checkout dev | tee -a "$LOG_FILE"
git pull --ff-only | tee -a "$LOG_FILE"

log_step "Installing dev dependencies (if needed)…"
"$PY" -m pip install -r requirements-dev.txt --disable-pip-version-check --no-input | tee -a "$LOG_FILE"

fast_checks

log_step "Checking out main and pulling (ff-only)…"
git checkout main | tee -a "$LOG_FILE"
git pull --ff-only | tee -a "$LOG_FILE"

# Try a fast-forward first. Use an if-guard to avoid triggering ERR trap on non-zero.
if git merge --ff-only dev >/dev/null 2>&1; then
  _green "Fast-forward succeeded." | tee -a "$LOG_FILE"
else
  _yellow "Fast-forward not possible; performing a merge…" | tee -a "$LOG_FILE"
  # Perform merge (may create conflicts). Pipeline guarded by if to avoid ERR trap.
  if git merge dev -m "chore: merge dev into main" | tee -a "$LOG_FILE"; then
    :
  else
    _yellow "Merge reported conflicts; attempting auto-resolution…" | tee -a "$LOG_FILE"
    auto_resolve_conflicts "$PREFER_DEV_ALL"
  fi
fi

# Final checks on main
fast_checks

if [[ "$DRY_RUN" -eq 1 ]]; then
  _yellow "Dry run: skipping push to origin/main." | tee -a "$LOG_FILE"
  switch_to_dev
  _green "Done (dry run)."
  exit 0
fi

log_step "Pushing main to origin (pre-push hooks may run)…"

# Push with one retry on transient local CI/act failures. If remote rejects due to
# branch protection (PRs required), guide the user to open a PR instead of forcing.
push_main_once() {
  local output
  set +e
  output=$(git push origin main 2>&1)
  local rc=$?
  set -e
  printf "%s\n" "$output" | tee -a "$LOG_FILE"
  return $rc
}

attempt=1
if push_main_once; then
  :
else
  # Detect protected-branch/PR-required server-side policy
  if grep -qiE "(must be made through a pull request|protected branch|hooks.*rejected|pre-receive hook declined)" "$LOG_FILE"; then
    _red "Push to protected 'main' blocked by server policy." | tee -a "$LOG_FILE"
    if [[ "$CREATE_PR" -eq 1 ]]; then
      if command -v gh >/dev/null 2>&1; then
        _yellow "Attempting to create PR dev → main via GitHub CLI…" | tee -a "$LOG_FILE"
        # Ensure dev is pushed
        git checkout dev >/dev/null 2>&1 || true
        git merge --ff-only main >/dev/null 2>&1 || true
        git push origin dev | tee -a "$LOG_FILE"
        # Create PR if one does not exist; otherwise, show existing
        set +e
        gh pr view --head dev --base main >/dev/null 2>&1
        has_pr=$?
        set -e
        if [[ $has_pr -ne 0 ]]; then
          gh pr create --base main --head dev --title "Promote dev to main" --body "Automated PR created by promote script." | tee -a "$LOG_FILE"
        else
          _yellow "A PR from dev to main already exists. Opening details…" | tee -a "$LOG_FILE"
          gh pr view --head dev --base main | tee -a "$LOG_FILE"
        fi
        switch_to_dev
        exit 2
      else
        _yellow "GitHub CLI (gh) not found. Install gh or run without --create-pr." | tee -a "$LOG_FILE"
      fi
    fi
    _yellow "Create a PR from 'dev' to 'main' instead." | tee -a "$LOG_FILE"
    _yellow "Hint: git checkout dev && git merge --ff-only main && git push origin dev; then open PR dev → main." | tee -a "$LOG_FILE"
    switch_to_dev
    exit 1
  fi

  # Detect common local act/docker flake signatures and retry once
  if grep -qiE "(Job 'Lint and Fast Tests' failed|exitcode '137'|unexpectedly nil|RWLayer)" "$LOG_FILE"; then
    _yellow "Pre-push CI appears flaky (act/Docker). Retrying push once…" | tee -a "$LOG_FILE"
    sleep 2
    if push_main_once; then
      :
    else
      _red "Push failed again. Consider running: ./scripts/cleanup_docker_and_ci_cache.sh and retrying." | tee -a "$LOG_FILE"
      _yellow "You can also bypass locally with --no-verify if tests already passed: git push --no-verify origin main" | tee -a "$LOG_FILE"
      switch_to_dev
      exit 1
    fi
  else
    _red "Push failed. See $LOG_FILE for details." | tee -a "$LOG_FILE"
    switch_to_dev
    exit 1
  fi
fi

switch_to_dev
_green "✅ Promotion complete. main is up to date with dev."

