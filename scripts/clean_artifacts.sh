#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "🧹 Cleaning test reports and old logs…"

# Ensure directories exist
mkdir -p "$ROOT/reports/logs" "$ROOT/logs"

# 1) Clear test artifacts (safe to regenerate on next pytest run)
find "$ROOT/reports" -mindepth 1 -maxdepth 1 -type f -print -delete || true
find "$ROOT/reports/logs" -type f -print -delete || true

# 2) Prune old script/runtime logs (keep last 7 days)
find "$ROOT/logs" -type f -name '*.log' -mtime +7 -print -delete || true

echo "✅ Done."


