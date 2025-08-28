#!/usr/bin/env bash
# scripts/ci/promote_dev_to_main.sh – Safely promote changes from dev → main
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
#   ./scripts/ci/promote_dev_to_main.sh                 # normal run (dev → main)
#   ./scripts/ci/promote_dev_to_main.sh --dry-run       # run all checks; skip push
#   ./scripts/ci/promote_dev_to_main.sh --create-pr     # if push to protected 'main' is blocked, auto-create PR dev → main
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Source shared config (moves CWD to project root and prepares logs dir)
source "${SCRIPT_DIR}/common.sh"

SCRIPT_NAME="$(get_script_name "$0")"
LOG_FILE="$(get_log_file "$SCRIPT_NAME")"

# Simple colors
_red()   { printf "\e[31m%s\e[0m\n" "$*"; }
_green() { printf "\e[32m%s\e[0m\n" "$*"; }
_yellow(){ printf "\e[33m%s\e[0m\n" "$*"; }

DRY_RUN=0
PREFER_DEV_ALL=0
CREATE_PR=0

# Branch configuration (fixed defaults; intentionally not configurable to keep usage simple)
FROM_BRANCH="dev"
TO_BRANCH="main"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=1; shift ;;
    --prefer-dev-all) PREFER_DEV_ALL=1; shift ;;
    --create-pr) CREATE_PR=1; shift ;;
    *) _red "Unknown argument: $1"; exit 2 ;;
  esac
done

setup_logging "$SCRIPT_NAME"

PY=".venv/bin/python"
RUFF_BIN=".venv/bin/ruff"
if [[ ! -x "$RUFF_BIN" ]]; then
  RUFF_BIN="ruff"
fi
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
need "$RUFF_BIN"

ensure_min_versions() {
  # Require Git >= 2.20.0
  local git_ver
  git_ver=$(git --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n1)
  if [[ -n "$git_ver" ]]; then
    if [[ "$(printf '%s\n%s\n' "$git_ver" "2.20.0" | sort -V | head -n1)" != "2.20.0" ]]; then
      _red "ERROR: Git version $git_ver is too old; require >= 2.20.0" | tee -a "$LOG_FILE"
      exit 1
    fi
  fi
  # Require Ruff >= 0.5.0
  local ruff_ver
  ruff_ver=$($RUFF_BIN --version 2>/dev/null | awk '{print $2}')
  if [[ -n "$ruff_ver" ]]; then
    if [[ "$(printf '%s\n%s\n' "$ruff_ver" "0.5.0" | sort -V | head -n1)" != "0.5.0" ]]; then
      _red "ERROR: Ruff version $ruff_ver is too old; require >= 0.5.0" | tee -a "$LOG_FILE"
      exit 1
    fi
  fi
}

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
  if [[ -f .git/MERGE_HEAD ]]; then
    _yellow "A merge is in progress. Resolve conflicts or run: git merge --abort" | tee -a "$LOG_FILE"
  fi
  rollback_branch
  exit "$exit_code"
}
trap on_error ERR

log_step() {
  log_message "INFO" "$*" | tee -a "$LOG_FILE"
}

switch_to_branch() {
  local target_branch="$1"
  if git show-ref --verify --quiet "refs/heads/${target_branch}"; then
    git checkout "$target_branch" >/dev/null 2>&1 || {
      _yellow "Could not switch back to ${target_branch} automatically; staying on $(git rev-parse --abbrev-ref HEAD)." | tee -a "$LOG_FILE"
      return
    }
    log_step "Switched back to ${target_branch} for next changes."
  else
    _yellow "Local branch '${target_branch}' not found; staying on $(git rev-parse --abbrev-ref HEAD)." | tee -a "$LOG_FILE"
  fi
}

ensure_clean_worktree() {
  if ! git diff-index --quiet HEAD --; then
    _red "ERROR: Working tree has uncommitted changes. Commit or stash first." | tee -a "$LOG_FILE"
    exit 1
  fi
}

ensure_no_pending_git_ops() {
  # Prevent running during ongoing merge/rebase/cherry-pick/bisect
  if [[ -f .git/MERGE_HEAD ]] || [[ -f .git/REBASE_HEAD ]] || [[ -d .git/rebase-apply ]] || [[ -d .git/rebase-merge ]] || [[ -f .git/CHERRY_PICK_HEAD ]] || [[ -f .git/BISECT_LOG ]]; then
    _red "ERROR: A Git operation is in progress (merge/rebase/cherry-pick/bisect). Please complete or abort it before running this script." | tee -a "$LOG_FILE"
    exit 1
  fi
}

ensure_git_identity() {
  local name email
  name=$(git config --get user.name || true)
  email=$(git config --get user.email || true)
  if [[ -z "$name" || -z "$email" ]]; then
    _red "ERROR: Git user identity not configured (user.name/user.email)." | tee -a "$LOG_FILE"
    _yellow "Hint: git config --global user.name 'Your Name'; git config --global user.email 'you@example.com'" | tee -a "$LOG_FILE"
    exit 1
  fi
}

ensure_origin_and_branches() {
  if ! git remote get-url origin >/dev/null 2>&1; then
    _red "ERROR: Remote 'origin' is not configured." | tee -a "$LOG_FILE"
    exit 1
  fi
  # Check that main/dev exist remotely to give early feedback
  if ! git ls-remote --exit-code --heads origin "$TO_BRANCH" >/dev/null 2>&1; then
    _red "ERROR: Remote branch '${TO_BRANCH}' not found on origin." | tee -a "$LOG_FILE"
    exit 1
  fi
  if ! git ls-remote --exit-code --heads origin "$FROM_BRANCH" >/dev/null 2>&1; then
    _red "ERROR: Remote branch '${FROM_BRANCH}' not found on origin." | tee -a "$LOG_FILE"
    exit 1
  fi
}

sync_submodules_if_any() {
  if [[ -f .gitmodules ]]; then
    log_step "Syncing and updating git submodules (recursive)…"
    git submodule sync --recursive 2>&1 | tee -a "$LOG_FILE"
    git submodule update --init --recursive 2>&1 | tee -a "$LOG_FILE"
  fi
}

fast_checks() {
  log_step "Running Ruff (lint)…"
  "$RUFF_BIN" check . 2>&1 | tee -a "$LOG_FILE"
  log_step "Running Ruff format --check…"
  "$RUFF_BIN" format --check . 2>&1 | tee -a "$LOG_FILE"
  log_step "Running pytest (fast suite)…"
  "$PY" -m pytest -q tests/ 2>&1 | tee -a "$LOG_FILE"
}

auto_resolve_conflicts() {
  # Returns 0 if all conflicts were resolved, 1 to abort
  local prefer_all="$1"  # 1 or 0
  local conflicts
  mapfile -t conflicts < <(git diff --name-only --diff-filter=U)

  if [[ ${#conflicts[@]} -eq 0 ]]; then
    return 0
  fi

  if [[ "$prefer_all" -eq 1 ]]; then
    _yellow "Auto-resolving ALL conflicts by preferring ${FROM_BRANCH} (theirs)…" | tee -a "$LOG_FILE"
    for f in "${conflicts[@]}"; do
      git checkout --theirs -- "$f"
      git add -- "$f"
    done
    git commit -m "chore: resolve merge conflicts by preferring ${FROM_BRANCH}" 2>&1 | tee -a "$LOG_FILE"
    return 0
  fi

  # Allow-list of files we auto-resolve by preferring the source branch
  local allow=()
  local rules_file
  rules_file=".promotion-rules.conf"
  if [[ -f "$rules_file" ]]; then
    while IFS= read -r line; do
      # skip comments and empty lines
      [[ -z "$line" || "$line" =~ ^# ]] && continue
      allow+=("$line")
    done < "$rules_file"
    log_step "Loaded ${#allow[@]} auto-resolve patterns from ${rules_file}."
  else
    allow+=("README.md" "docs/" "docs_AI_coder/")
  fi

  local unresolved=()
  for f in "${conflicts[@]}"; do
    local ok=0
    for a in "${allow[@]}"; do
      if [[ "$f" == "$a" || "$f" == $a* ]]; then ok=1; break; fi
    done
    if [[ $ok -eq 1 ]]; then
      git checkout --theirs -- "$f"
      git add -- "$f"
      log_step "Auto-resolved $f by preferring ${FROM_BRANCH}"
    else
      unresolved+=("$f")
    fi
  done

  if [[ ${#unresolved[@]} -eq 0 ]]; then
    git commit -m "chore: resolve selected conflicts by preferring ${FROM_BRANCH}" 2>&1 | tee -a "$LOG_FILE"
    return 0
  fi

  _red "Unresolved conflicts detected:" | tee -a "$LOG_FILE"
  printf '  %s\n' "${unresolved[@]}" | tee -a "$LOG_FILE"
  _yellow "Aborting merge. Please resolve manually or re-run with --prefer-dev-all." | tee -a "$LOG_FILE"
  git merge --abort
  return 1
}

ensure_clean_worktree
ensure_no_pending_git_ops
ensure_git_identity
ensure_origin_and_branches
ensure_min_versions

log_step "Fetching remotes…"
git fetch --all --prune 2>&1 | tee -a "$LOG_FILE"

sync_submodules_if_any

log_step "Checking out ${FROM_BRANCH} and pulling (ff-only)…"
git checkout "$FROM_BRANCH" 2>&1 | tee -a "$LOG_FILE"
git pull --ff-only 2>&1 | tee -a "$LOG_FILE"

# Informational: show divergence from origin for source branch
set +e
div_source=$(git rev-list --left-right --count "origin/${FROM_BRANCH}...${FROM_BRANCH}" 2>/dev/null)
set -e
if [[ -n "${div_source:-}" ]]; then
  behind_src=$(awk '{print $1}' <<<"$div_source")
  ahead_src=$(awk '{print $2}' <<<"$div_source")
  log_step "Source ${FROM_BRANCH}: behind origin by ${behind_src}, ahead by ${ahead_src}."
fi

log_step "Installing dev dependencies (if needed)…"
"$PY" -m pip install -r requirements-dev.txt --disable-pip-version-check --no-input 2>&1 | tee -a "$LOG_FILE"

fast_checks

log_step "Checking out ${TO_BRANCH} and pulling (ff-only)…"
git checkout "$TO_BRANCH" 2>&1 | tee -a "$LOG_FILE"
git pull --ff-only 2>&1 | tee -a "$LOG_FILE"

# Informational: show divergence from origin for target branch
set +e
div_target=$(git rev-list --left-right --count "origin/${TO_BRANCH}...${TO_BRANCH}" 2>/dev/null)
set -e
if [[ -n "${div_target:-}" ]]; then
  behind_tgt=$(awk '{print $1}' <<<"$div_target")
  ahead_tgt=$(awk '{print $2}' <<<"$div_target")
  log_step "Target ${TO_BRANCH}: behind origin by ${behind_tgt}, ahead by ${ahead_tgt}."
fi

# Try a fast-forward first. Use an if-guard to avoid triggering ERR trap on non-zero.
if git merge --ff-only "$FROM_BRANCH" >/dev/null 2>&1; then
  _green "Fast-forward succeeded." | tee -a "$LOG_FILE"
else
  _yellow "Fast-forward not possible; performing a merge…" | tee -a "$LOG_FILE"
  # Perform merge (may create conflicts). Pipeline guarded by if to avoid ERR trap.
  if git merge "$FROM_BRANCH" -m "chore: merge ${FROM_BRANCH} into ${TO_BRANCH}" 2>&1 | tee -a "$LOG_FILE"; then
    :
  else
    _yellow "Merge reported conflicts; attempting auto-resolution…" | tee -a "$LOG_FILE"
    auto_resolve_conflicts "$PREFER_DEV_ALL" || exit 1
  fi
fi

  # Safety: verify that source is ancestor of target after merge
  if ! git merge-base --is-ancestor "$FROM_BRANCH" "$TO_BRANCH"; then
    _red "ERROR: Post-merge validation failed: '${FROM_BRANCH}' is not an ancestor of '${TO_BRANCH}'." | tee -a "$LOG_FILE"
    exit 1
  fi

  # Safety: scan for unresolved conflict markers in the latest tree
  if git grep -nE '^(<<<<<<<|=======|>>>>>>>)' HEAD -- . >/dev/null 2>&1; then
    _red "ERROR: Conflict markers detected in committed files after merge. Aborting push." | tee -a "$LOG_FILE"
    _yellow "Hint: run: git grep -nE '^(<<<<<<<|=======|>>>>>>>)' HEAD" | tee -a "$LOG_FILE"
    exit 1
  fi

# Final checks on main
fast_checks

if [[ "$DRY_RUN" -eq 1 ]]; then
  _yellow "Dry run: skipping push to origin/main." | tee -a "$LOG_FILE"
  switch_to_branch "$FROM_BRANCH"
  _green "Done (dry run)."
  exit 0
fi

log_step "Pushing ${TO_BRANCH} to origin (pre-push hooks may run)…"

# Push with one retry on transient local CI/act failures. If remote rejects due to
# branch protection (PRs required), guide the user to open a PR instead of forcing.
push_main_once() {
  local output
  set +e
  output=$(git push origin "$TO_BRANCH" 2>&1)
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
    _red "Push to protected '${TO_BRANCH}' blocked by server policy." | tee -a "$LOG_FILE"
    if [[ "$CREATE_PR" -eq 1 ]]; then
      if command -v gh >/dev/null 2>&1; then
        _yellow "Attempting to create PR ${FROM_BRANCH} → ${TO_BRANCH} via GitHub CLI…" | tee -a "$LOG_FILE"
        # Ensure dev is pushed
        git checkout "$FROM_BRANCH" >/dev/null 2>&1 || true
        git merge --ff-only "$TO_BRANCH" >/dev/null 2>&1 || true
        git push origin "$FROM_BRANCH" 2>&1 | tee -a "$LOG_FILE"
        # Create PR if one does not exist; otherwise, show existing
        set +e
        gh pr view --head "$FROM_BRANCH" --base "$TO_BRANCH" >/dev/null 2>&1
        has_pr=$?
        set -e
        if [[ $has_pr -ne 0 ]]; then
          gh pr create --base "$TO_BRANCH" --head "$FROM_BRANCH" --title "Promote ${FROM_BRANCH} to ${TO_BRANCH}" --body "Automated PR created by promote script." 2>&1 | tee -a "$LOG_FILE"
        else
          _yellow "A PR from ${FROM_BRANCH} to ${TO_BRANCH} already exists. Opening details…" | tee -a "$LOG_FILE"
          gh pr view --head "$FROM_BRANCH" --base "$TO_BRANCH" 2>&1 | tee -a "$LOG_FILE"
        fi
        switch_to_branch "$FROM_BRANCH"
        exit 2
      else
        _yellow "GitHub CLI (gh) not found. Install gh or run without --create-pr." | tee -a "$LOG_FILE"
      fi
    fi
    _yellow "Create a PR from '${FROM_BRANCH}' to '${TO_BRANCH}' instead." | tee -a "$LOG_FILE"
    _yellow "Hint: git checkout ${FROM_BRANCH} && git merge --ff-only ${TO_BRANCH} && git push origin ${FROM_BRANCH}; then open PR ${FROM_BRANCH} → ${TO_BRANCH}." | tee -a "$LOG_FILE"
    switch_to_branch "$FROM_BRANCH"
    exit 1
  fi

  # Detect common local act/docker flake signatures and retry once
  if grep -qiE "(Job 'Lint and Fast Tests' failed|exitcode '137'|unexpectedly nil|RWLayer)" "$LOG_FILE"; then
    _yellow "Pre-push CI appears flaky (act/Docker). Retrying push once…" | tee -a "$LOG_FILE"
    sleep 2
    if push_main_once; then
      :
    else
      _red "Push failed again. Consider running: ./scripts/docker/cleanup_docker_and_ci_cache.sh and retrying." | tee -a "$LOG_FILE"
      _yellow "You can also bypass locally with --no-verify if tests already passed: git push --no-verify origin ${TO_BRANCH}" | tee -a "$LOG_FILE"
      switch_to_branch "$FROM_BRANCH"
      exit 1
    fi
  else
    _red "Push failed. See $LOG_FILE for details." | tee -a "$LOG_FILE"
    switch_to_branch "$FROM_BRANCH"
    exit 1
  fi
fi

switch_to_branch "$FROM_BRANCH"
_green "✅ Promotion complete. ${TO_BRANCH} is up to date with ${FROM_BRANCH}."

