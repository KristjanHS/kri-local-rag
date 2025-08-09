# CI/CD & Release Management

## Overview

This project uses GitHub Actions for CI/CD and security scanning, with automated release processes for promoting changes from `dev` to `main`.

## Available Workflows

### 1. CodeQL Analysis (`codeql.yml`)
- **Purpose**: Static code analysis for security vulnerabilities
- **Triggers**: Push to main, PR to main, weekly schedule, manual
- **Duration**: Up to 6 hours

### 2. Semgrep Security Analysis (`semgrep.yml`)
- **Purpose**: Pattern-based security scanning
- **Triggers**: Push to main, PR to main, manual
- **Duration**: Up to 30 minutes

### 3. CI Pipeline (`python-lint-test.yml`)
- **Purpose**: Linting, testing, and type checking
- **Triggers**: PR to main/dev, manual, weekly schedule
- **Jobs**: `lint_and_fast_tests`, `pyright`, `docker_smoke_tests`
- **Duration**: 5-15 minutes for fast tests

## Local Development with Act CLI

### Installation
```bash
# Linux/macOS
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

```

### Project Configuration
The `.actrc` file uses optimized Docker images.

### Usage
```bash
# List workflows
act -l

# Run CI locally
./scripts/ci_act.sh

# Run specific workflows
act workflow_dispatch -W .github/workflows/codeql.yml
act workflow_dispatch -W .github/workflows/semgrep.yml

# Run specific jobs
act workflow_dispatch -j lint_and_fast_tests
act workflow_dispatch -j pyright
```

### Troubleshooting
```bash
# Clean up CI cache
./scripts/cleanup_docker_and_ci_cache.sh

# Aggressive cleanup
./scripts/cleanup_docker_and_ci_cache.sh --restart-docker --builder-prune
```

## Release Process

### Promote `dev` to `main`
```bash
# Normal release
./scripts/promote_dev_to_main.sh

# Dry run (no push)
./scripts/promote_dev_to_main.sh --dry-run

# Auto-resolve all conflicts
./scripts/promote_dev_to_main.sh --prefer-dev-all
```

### What the Release Script Does
1. Ensures clean working tree
2. Updates `dev` branch
3. Runs checks on `dev`:
   - Ruff lint + format check
   - Pytest (fast suite)
4. Updates `main` (fast-forward or merge)
5. Re-runs checks on `main`
6. Pushes to `origin/main`
7. Switches back to `dev`

### Requirements
- Local virtual environment with dependencies
- Clean working tree (no uncommitted changes)
- Push permissions to `origin/main`

### Troubleshooting Release Issues
- **Merge conflicts**: Resolve manually or use `--prefer-dev-all`
- **Pre-push CI failures**: Check `logs/pre-push.log`, run cleanup script
- **Branch protection**: If "PRs only" is enforced, create PR manually
- **Fast test failures**: Run `ruff check .` and `pytest -q tests/` locally

## Testing Workflows

### Manual Testing
1. GitHub UI: Actions tab → Select workflow → "Run workflow"
2. Act CLI: `act workflow_dispatch -W .github/workflows/[workflow].yml`
3. Push to main: `git push origin main`
4. Create test PR: `git checkout -b test-workflows && git push origin test-workflows`

### Automated Testing
- **Pre-push hooks**: Automatically run CI on push
- **Release process**: CI checks before and after merge
- **PR triggers**: Automatic CI on all pull requests

## Project Scripts

### CI Scripts
- `scripts/ci_act.sh`: Run full CI locally
- `scripts/cleanup_docker_and_ci_cache.sh`: Cleanup Docker and act cache
- `scripts/ci_local_fast.sh`: Fast local CI testing

### Release Scripts
- `scripts/promote_dev_to_main.sh`: Safe dev → main promotion

## Security & Best Practices

### Secrets Management
- Use GitHub Secrets for sensitive data
- Never commit secrets to repository
- Rotate secrets regularly

### Workflow Security
- Use pinned action versions
- Review third-party actions
- Validate inputs and outputs

### Code Scanning
- Review security findings promptly
- Set up automated alerts
- Maintain security baseline

## Getting Help

- **GitHub Actions**: https://docs.github.com/en/actions
- **Act CLI**: https://github.com/nektos/act
- **CodeQL**: https://docs.github.com/en/code-security
- **Semgrep**: https://semgrep.dev/docs/
