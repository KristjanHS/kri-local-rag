#!/usr/bin/env bash
# scripts/dev/pushpr.sh
# Simple, best-practice flow: push → local integration tests → create/show PR via GitHub CLI.
# Usage examples:
#   scripts/dev/pushpr.sh                 # uses default remote 'origin' and HEAD
#   scripts/dev/pushpr.sh origin HEAD     # pass any git push args
#   BASE=develop scripts/dev/pushpr.sh    # change PR base
#
# Env vars:
#   BASE=main     - target base branch for PR
#   HEAD=<branch> - head branch for PR (defaults to current)
#   PYTEST_ARGS=  - extra pytest args for integration run

set -Eeuo pipefail

ROOT_DIR="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT_DIR"

BASE=${BASE:-main}
HEAD=${HEAD:-$(git rev-parse --abbrev-ref HEAD)}

echo "[pushpr] Repo: $ROOT_DIR"

# 1) Push
if [ "$#" -gt 0 ]; then
  echo "[pushpr] git push $*"
  git push "$@"
else
  echo "[pushpr] git push origin HEAD"
  git push origin HEAD
fi

# 2) Local integration tests (only after successful push)
if [[ ! -x ".venv/bin/python" ]]; then
  echo "[pushpr] ERROR: .venv/bin/python not found. Create venv and install dev deps."
  echo "         e.g., uv venv --seed && make uv-sync-test"
  exit 1
fi

mkdir -p reports
echo "[pushpr] Running local integration tests…"
echo "[pushpr] .venv/bin/python -m pytest tests/integration -q ${PYTEST_ARGS:-}"
if ! .venv/bin/python -m pytest tests/integration -q ${PYTEST_ARGS:-}; then
  echo "[pushpr] Integration tests failed — aborting PR creation."
  exit 1
fi

# 3) Create or show PR via GitHub CLI (standard command)
if ! command -v gh >/dev/null 2>&1; then
  echo "[pushpr] WARN: GitHub CLI 'gh' not found; skipping PR creation. Install: https://cli.github.com/"
  exit 0
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "[pushpr] WARN: gh not authenticated. Run: gh auth login"
  exit 0
fi

echo "[pushpr] Creating PR: head=$HEAD → base=$BASE (using --fill)"
if gh pr create --base "$BASE" --head "$HEAD" --fill --label auto-generated >/dev/null 2>&1; then
  :
else
  echo "[pushpr] PR may already exist; resolving URL…"
fi

PR_URL=$(gh pr view --head "$HEAD" --json url -q .url 2>/dev/null || true)
if [[ -z "$PR_URL" ]]; then
  PR_URL=$(gh pr list --state open --search "head:$HEAD base:$BASE" --json url -q '.[0].url' 2>/dev/null || true)
fi

if [[ -n "$PR_URL" ]]; then
  echo "[pushpr] PR: $PR_URL"
else
  echo "[pushpr] WARN: Unable to resolve PR URL. Try: gh pr create --base $BASE --head $HEAD --fill"
fi

echo "[pushpr] Done."
