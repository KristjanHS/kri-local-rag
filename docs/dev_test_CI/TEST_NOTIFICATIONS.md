# Test Notifications Setup

This document explains how to set up and use test notifications in your IDE for the kri-local-rag project.

## Overview

The project includes multiple notification methods for test failures:

1. **Desktop notifications** (Linux: `notify-send`)
2. **Terminal bells and colored output**
3. **VS Code integrated notifications**
4. **Sound alerts** (if available)

## Quick Start

### 1. Automatic Notifications (Post-Push)

After every `git push`, integration tests run automatically with notifications:

```bash
git push origin your-branch
```

You'll see:
- Desktop notification popup
- Terminal bell sound
- Colored success/failure output
- Log file location

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
2. Select "Run Integration Tests with Notifications"

Or use the test explorer:
- Install recommended extensions (see `.vscode/extensions.json`)
- Use the Testing panel in VS Code

## Configuration

### Environment Variables

Control notification behavior:

```bash
# Disable success notifications
export NOTIFY_ON_SUCCESS=false

# Disable failure notifications  
export NOTIFY_ON_FAILURE=false

# Disable sound alerts
export PLAY_SOUND=false

# Skip post-push tests entirely
export SKIP_POST_PUSH_TESTS=1
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

### Missing Desktop Notifications

If you don't see desktop notifications:

1. **Check if `notify-send` is available:**
   ```bash
   which notify-send
   ```

2. **Install if missing (Ubuntu/Debian):**
   ```bash
   sudo apt-get install libnotify-bin
   ```

3. **Check notification daemon:**
   ```bash
   systemctl --user status notification-daemon
   ```

### Missing Sound Alerts

If you don't hear terminal bells:

1. **Check terminal bell:**
   ```bash
   echo -e "\a"
   ```

2. **Enable in VS Code:**
   - Settings → "Terminal › Integrated: Enable Bell"

3. **System sound:**
   - Check system volume
   - Test with: `paplay /usr/share/sounds/freedesktop/stereo/dialog-error.oga`

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
   ```

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
- **Logs:** `logs/test-notification.log`

## Best Practices

1. **Keep notifications enabled** for immediate feedback
2. **Check logs** when tests fail for detailed error information
3. **Use VS Code debugging** for complex test failures
4. **Run tests locally** before pushing to catch issues early
5. **Monitor test duration** to identify performance regressions
