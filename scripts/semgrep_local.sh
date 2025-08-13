#!/usr/bin/env bash

set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "[info] Running Semgrep via pipx (isolated from app .venv)"

# Find a pipx binary without relying on the active .venv
PIPX_BIN="$(command -v pipx || true)"
if [[ -z "${PIPX_BIN}" && -x "$HOME/.local/bin/pipx" ]]; then
  PIPX_BIN="$HOME/.local/bin/pipx"
fi

if [[ -z "${PIPX_BIN}" ]]; then
  echo "[info] Installing pipx for current user via system python…"
  if command -v /usr/bin/python3 >/dev/null 2>&1; then
    /usr/bin/python3 -m pip install --user pipx >/dev/null 2>&1 || true
  else
    python3 -m pip install --user pipx >/dev/null 2>&1 || true
  fi
  if [[ -x "$HOME/.local/bin/pipx" ]]; then
    PIPX_BIN="$HOME/.local/bin/pipx"
  else
    PIPX_BIN="$(command -v pipx || true)"
  fi
fi

if [[ -z "${PIPX_BIN}" ]]; then
  echo "[error] pipx not found and could not be installed. Please add ~/.local/bin to your PATH or install pipx manually." >&2
  exit 2
fi

# Show Semgrep version (best-effort)
"$PIPX_BIN" run semgrep --version || true

OUT="semgrep_local.sarif"
echo "[info] Scanning repository (output: $OUT)…"
"$PIPX_BIN" run semgrep ci \
  --config auto \
  --metrics off \
  --sarif \
  --output "$OUT" || true

echo "[info] Summary:"
python - << 'PY'
import json, os, sys
path = "semgrep_local.sarif"
if not os.path.exists(path):
    print("Semgrep findings: 0 (no semgrep_local.sarif found)")
    sys.exit(0)
try:
    with open(path, "r", encoding="utf-8") as f:
        sarif = json.load(f)
    runs = sarif.get("runs") or []
    results = (runs[0].get("results") if runs else []) or []
    print(f"\nSemgrep findings: {len(results)}")
    for i, r in enumerate(results, start=1):
        rule_id = r.get("ruleId") or (r.get("rule") or {}).get("id") or "unknown-rule"
        level = r.get("level") or (r.get("properties") or {}).get("severity") or "note"
        message = (r.get("message") or {}).get("text") or "(no message)"
        loc = ((r.get("locations") or [None])[0] or {}).get("physicalLocation") or {}
        file = (loc.get("artifactLocation") or {}).get("uri") or "unknown-file"
        line = (loc.get("region") or {}).get("startLine") or 1
        print(f"{i}. [{level}] {rule_id} at {file}:{line} - {message}")
except Exception as e:
    print(f"Could not parse semgrep_local.sarif: {e}")
PY

echo "[info] Done. Report: $OUT"


