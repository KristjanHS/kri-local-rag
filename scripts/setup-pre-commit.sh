#!/usr/bin/env bash
# scripts/setup-pre-commit.sh - Setup pre-commit framework with all advanced options
set -Eeuo pipefail

# Source the shared config file
# shellcheck source=scripts/config.sh
source "$(git rev-parse --show-toplevel)/scripts/config.sh"

# --- Start Logging ---
script_name="setup-pre-commit"
LOG_FILE=$(init_script_logging "$script_name")
enable_error_trap "$LOG_FILE" "$script_name"
# --- End Logging ---

# Ensure we are in the project root
cd "$(git rev-parse --show-toplevel)"

log INFO "🚀 Setting up pre-commit framework with advanced options..."

# Check if we're in a virtual environment
if [[ -z "${VIRTUAL_ENV:-}" ]]; then
    log WARN "⚠️  Not in a virtual environment. Consider activating .venv first."
    log INFO "💡 Run: source .venv/bin/activate"
fi

# Install pre-commit framework
log INFO "📦 Installing pre-commit framework..."
if [[ -x ".venv/bin/pip" ]]; then
    .venv/bin/pip install pre-commit
else
    pip install pre-commit
fi

# Install detect-secrets with all plugins
log INFO "🔐 Installing detect-secrets with advanced plugins..."
if [[ -x ".venv/bin/pip" ]]; then
    .venv/bin/pip install "detect-secrets[gibberish,entropy,wordlist]"
else
    pip install "detect-secrets[gibberish,entropy,wordlist]"
fi

# Install bandit for Python security scanning
log INFO "🔒 Installing bandit for Python security scanning..."
if [[ -x ".venv/bin/pip" ]]; then
    .venv/bin/pip install "bandit[toml]==1.8.6"
else
    pip install "bandit[toml]==1.8.6"
fi

# Install yamlfmt (requires Go)
log INFO "📋 Checking yamlfmt installation..."
if ! command -v yamlfmt >/dev/null 2>&1; then
    log WARN "⚠️  yamlfmt not found. Installing via Go..."
    if command -v go >/dev/null 2>&1; then
        go install github.com/google/yamlfmt/cmd/yamlfmt@latest
        log INFO "✅ yamlfmt installed successfully"
    else
        log ERROR "❌ Go not found. Please install Go to use yamlfmt."
        log INFO "💡 Install Go from: https://golang.org/dl/"
        log INFO "💡 Or skip yamlfmt by removing it from .pre-commit-config.yaml"
    fi
else
    log INFO "✅ yamlfmt already installed"
fi

# Install pre-commit hooks
log INFO "🔧 Installing pre-commit hooks..."

# Check if custom hooks path is configured
if git config --get core.hooksPath >/dev/null 2>&1; then
    log WARN "⚠️  Custom hooks path detected: $(git config --get core.hooksPath)"
    log INFO "💡 This project uses custom git hooks. Pre-commit will be available via:"
    log INFO "   • git commit (runs automatically)"
    log INFO "   • pre-commit run --all-files (manual run)"
    log INFO "   • pre-commit run <hook-id> (individual hooks)"
else
    pre-commit install
    log INFO "✅ Pre-commit hooks installed in .git/hooks/"
fi

# Initialize detect-secrets baseline if it doesn't exist
if [[ ! -f ".secrets.baseline" ]]; then
    log INFO "🔍 Initializing detect-secrets baseline..."
    if [[ -x ".venv/bin/detect-secrets" ]]; then
        .venv/bin/detect-secrets scan --baseline .secrets.baseline
    elif command -v detect-secrets >/dev/null 2>&1; then
        detect-secrets scan --baseline .secrets.baseline
    else
        log WARN "⚠️  detect-secrets not available for baseline initialization"
    fi
fi

# Run pre-commit on all files to ensure everything works
log INFO "🧪 Testing pre-commit setup..."
pre-commit run --all-files

log INFO "✅ Pre-commit framework setup complete!"
log INFO "🎉 Advanced features enabled:"
log INFO "   • Ruff code formatting and linting"
log INFO "   • YAML file formatting"
log INFO "   • GitHub Actions validation (actionlint)"
log INFO "   • Dockerfile validation (hadolint)"
log INFO "   • Python security scanning (bandit)"
log INFO "   • Static type checking (pyright)"
log INFO "   • Secrets detection with gibberish plugin"
log INFO ""
log INFO "💡 Usage:"
log INFO "   • Pre-commit runs automatically on git commit"
log INFO "   • Manual run: pre-commit run --all-files"
log INFO "   • Individual hook: pre-commit run <hook-id>"
