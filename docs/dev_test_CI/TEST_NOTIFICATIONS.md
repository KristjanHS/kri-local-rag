# Test Notifications Setup

This document explains how to set up and use test notifications in your IDE for the kri-local-rag project.

## Overview

The project includes a simple, reliable notification system for test results:

1. **Terminal notifications** with colored output
2. **Terminal bell sounds** for failures
3. **Comprehensive logging** to files
4. **VS Code integration** via tasks

## Quick Start

### 1. Automatic Notifications (Post-Push)

After every `git push`, integration tests run automatically with notifications:

```bash
git push origin your-branch
```

You'll see:
- Colored success/failure output in terminal
- Terminal bell sound for failures
- Log file location for debugging

### 2. Manual Test Notifications

Run tests with notifications manually:

```bash
# Integration tests
./scripts/dev/test-notification.sh integration

# Unit tests
./scripts/dev/test-notification.sh unit

# All tests
./scripts/dev/test-notification.sh all
```

### 3. VS Code Integration

Use VS Code tasks for test notifications:

1. **Ctrl+Shift+P** → "Tasks: Run Task"
2. Select "Run Tests with Notifications"

Or use the test explorer:
- Install recommended extensions (see `.vscode/extensions.json`)
- Use the Testing panel in VS Code

## Configuration

### Environment Variables

Control test behavior:

```bash
# Skip post-push tests entirely
export SKIP_POST_PUSH_TESTS=1

# Add extra pytest arguments
export POST_PUSH_PYTEST_ARGS="-x --tb=short"
```

### VS Code Settings

Key settings in `.vscode/settings.json`:

```json
{
    "python.testing.pytestEnabled": true,
    "python.testing.autoTestDiscoverOnSaveEnabled": false,
    "terminal.integrated.enableBell": true,
    "notifications.showInProblemsPanel": true
}
```

## Troubleshooting

### Test Failures

If tests fail consistently:

1. **Check virtual environment:**
   ```bash
   ls -la .venv/bin/python
   ```

2. **Reinstall dependencies:**
   ```bash
   .venv/bin/pip install -r requirements-dev.txt
   ```

3. **Check logs:**
   ```bash
   tail -f logs/test-notification.log
   tail -f logs/post-push.log
   ```

### Missing Terminal Bells

If you don't hear terminal bells:

1. **Check terminal bell:**
   ```bash
   echo -e "\a"
   ```

2. **Enable in VS Code:**
   - Settings → "Terminal › Integrated: Enable Bell"

## Advanced Usage

### Custom Test Commands

Add custom pytest arguments:

```bash
# With extra args
POST_PUSH_PYTEST_ARGS="-x --tb=short" ./scripts/dev/test-notification.sh integration

# Debug mode
POST_PUSH_PYTEST_ARGS="-s -v" ./scripts/dev/test-notification.sh integration
```

### Integration with CI/CD

The notification system works with:

- **Git hooks** (automatic on push)
- **VS Code tasks** (manual execution)
- **GitHub Actions** (CI/CD pipeline)
- **Local development** (manual testing)

### Performance Monitoring

The notification script includes timing:

```bash
./scripts/dev/test-notification.sh integration
# Output: ✓ Integration Tests passed in 2m 15s
```

## File Locations

- **Notification script:** `scripts/dev/test-notification.sh`
- **Post-push hook:** `scripts/git-hooks/post-push`
- **VS Code config:** `.vscode/tasks.json`, `.vscode/settings.json`
- **Logs:** `logs/test-notification.log`, `logs/post-push.log`

## Best Practices

1. **Keep terminal bells enabled** for immediate feedback
2. **Check logs** when tests fail for detailed error information
3. **Use VS Code debugging** for complex test failures
4. **Run tests locally** before pushing to catch issues early
5. **Monitor test duration** to identify performance regressions
