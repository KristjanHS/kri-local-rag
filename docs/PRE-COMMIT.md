# Pre-commit Framework Setup

This project uses a comprehensive pre-commit framework that combines multiple tools for code quality, formatting, and security scanning.

## 🚀 Quick Setup

Run the setup script to install and configure all pre-commit hooks:

```bash
./scripts/setup-pre-commit.sh
```

## 📋 What's Included

### 1. **Ruff Code Quality** (`ruff-pre-commit`)
- **Linting**: Automatically fixes common Python issues (unused imports, etc.)
- **Formatting**: Formats code according to `pyproject.toml` rules
- **Advanced**: Uses Ruff v0.12.9 with `--fix` option

### 2. **YAML Formatting** (`yamlfmt`)
- **Formatting**: Standardizes YAML file formatting
- **Files**: All `.yaml` and `.yml` files
- **Advanced**: Uses Google's yamlfmt with consistent styling

### 3. **GitHub Actions Validation** (`actionlint`)
- **Validation**: Lints GitHub Actions workflow files for syntax and best practices
- **Files**: All `.yaml` and `.yml` files (excluding common directories)
- **Advanced**: Uses actionlint v1.7.1 with color output

### 4. **Dockerfile Validation** (`hadolint`)
- **Validation**: Lints Dockerfiles for best practices and common mistakes
- **Files**: `Dockerfile`, `*.dockerfile`, `docker/*.Dockerfile`
- **Advanced**: Uses hadolint v2.12.0 with SARIF output format

### 5. **Python Security Scanning** (`bandit`)
- **Security**: Scans Python code for common security vulnerabilities
- **Configuration**: Uses `pyproject.toml` for configuration
- **Advanced**: Includes TOML configuration support

### 6. **Static Type Checking** (`pyright`)
- **Type Checking**: Performs static type analysis on Python code
- **Configuration**: Uses project's pyright configuration
- **Advanced**: Integrates with project's type checking setup

### 7. **Secrets Detection** (`detect-secrets`)
- **Security**: Scans for secrets and credentials in codebase
- **Plugins**: Includes gibberish detection
- **Baseline**: Uses `.secrets.baseline` for tracking known secrets
- **Exclusions**: Ignores common directories (`.venv/`, `node_modules/`, etc.)

## 🔧 Configuration Files

### `.pre-commit-config.yaml`
Main configuration file containing all hooks and their settings.

### `scripts/git-hooks/pre-commit`
Git hook script that runs the pre-commit framework with logging and error handling.

### `.secrets.baseline`
Baseline file for detect-secrets to track known secrets and reduce false positives.

## 🎯 Usage

### Automatic (Recommended)
Pre-commit hooks run automatically on every `git commit`:

```bash
git add .
git commit -m "Your commit message"
# Pre-commit hooks run automatically
```

### Manual Execution
Run all hooks on all files:
```bash
pre-commit run --all-files
```

Run specific hook:
```bash
pre-commit run ruff
pre-commit run yamlfmt
pre-commit run detect-secrets
```

Run on specific files:
```bash
pre-commit run --files path/to/file.py
```

## 🛠️ Advanced Options

### Environment Variables
- `VIRTUAL_ENV`: Automatically detected for proper dependency management

### Detect-Secrets Plugins
- **gibberish**: Detects random-looking strings that might be secrets

### Excluded Directories
The secrets scanner automatically excludes:
- `.venv/`, `.git/`, `node_modules/`
- `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`
- `dist/`, `build/`, `.mypy_cache/`
- `.coverage`, `.secrets.baseline`

## 🔍 Troubleshooting

### Pre-commit Not Found
```bash
# Install in virtual environment
.venv/bin/python -m pip install pre-commit

# Or install globally
pip install pre-commit
```

### YAMLfmt Not Found
```bash
# Install Go first, then yamlfmt
go install github.com/google/yamlfmt/cmd/yamlfmt@latest
```

### Detect-Secrets Issues
```bash
# Install with all plugins
pip install "detect-secrets[gibberish,entropy,wordlist]"

# Initialize baseline
detect-secrets scan --baseline .secrets.baseline
```

### Hook Failures
1. **Ruff errors**: Fix linting issues automatically with `ruff check . --fix`
2. **YAML formatting**: Run `yamlfmt` on specific files
3. **Secrets detected**: Review `.secrets.baseline` and update if needed

## 📝 Migration from Old System

The old system used separate scripts:
- `scripts/lint.sh` → Now handled by `ruff-pre-commit`
- `scripts/pre-commit.sh` → Now handled by `detect-secrets` hooks
- Custom git hooks → Now uses pre-commit framework

### Benefits of New System
- **Standardized**: Uses industry-standard pre-commit framework
- **Faster**: Parallel execution and caching
- **Maintainable**: Centralized configuration
- **Extensible**: Easy to add new hooks
- **Consistent**: Same behavior across all environments

## 🔄 Updating Hooks

Update all hooks to latest versions:
```bash
pre-commit autoupdate
```

Update specific repository:
```bash
pre-commit autoupdate --freeze
```

## 📊 Performance

The pre-commit framework includes:
- **Caching**: Hooks cache results for faster subsequent runs
- **Parallel execution**: Multiple hooks can run simultaneously
- **Incremental**: Only processes changed files by default
- **Optimized**: Uses efficient algorithms for each tool

## 🛡️ Security Features

- **Secrets detection**: Multiple detection methods
- **Baseline tracking**: Reduces false positives
- **Environment awareness**: Respects security settings
- **Graceful degradation**: Continues if tools are unavailable
