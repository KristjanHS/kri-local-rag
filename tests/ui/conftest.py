from __future__ import annotations

import pytest


def _is_coverage_enabled(config: pytest.Config) -> bool:
    """Detect active pytest-cov coverage collection.

    We only want to guard when coverage collection is actually enabled, not merely
    when the plugin is installed. This allows separate E2E runs with --no-cov.
    """
    if not config.pluginmanager.hasplugin("cov"):
        return False
    option = getattr(config, "option", None)
    if option is not None:
        if getattr(option, "no_cov", False):
            return False
        if (
            getattr(option, "cov", None)
            or getattr(option, "cov_source", None)
            or getattr(option, "cov_report", None)
            or getattr(option, "cov_branch", False)
            or getattr(option, "cov_fail_under", None)
            or getattr(option, "cov_append", False)
            or getattr(option, "cov_config", None)
        ):
            return True
    try:
        if config.getoption("--no-cov"):
            return False
    except Exception:
        pass
    try:
        cov_targets = config.getoption("--cov")
        if cov_targets:
            return True
    except Exception:
        pass
    for opt in ("--cov-config", "--cov-branch", "--cov-fail-under", "--cov-report", "--cov-append", "--cov-context"):
        try:
            if config.getoption(opt):
                return True
        except Exception:
            continue
    return False


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Skip UI tests when coverage is enabled; otherwise enforce --no-cov for explicit UI runs.

    This makes the default, coverage-enabled full suite run green by skipping
    Playwright tests. UI tests must be run separately with `--no-cov`.
    """
    if not items:
        return

    # If coverage collection is active, deselect all tests in this directory to avoid
    # initializing Playwright fixtures during setup.
    if _is_coverage_enabled(config):
        config.hook.pytest_deselected(items=items[:])
        items[:] = []
        return

    # Explicit UI suite must also be run with --no-cov
    is_ui_suite = bool(getattr(config.option, "test_ui", False))
    is_coverage_disabled = bool(getattr(config.option, "no_cov", False))
    if is_ui_suite and not is_coverage_disabled:
        raise pytest.UsageError("The --test-ui suite cannot be run with coverage. Please run with --no-cov.")
