from __future__ import annotations

import pytest


def _is_coverage_enabled(config: pytest.Config) -> bool:
    """Best-effort detection of active pytest-cov coverage collection.

    We only want to skip when coverage collection is actually enabled, not merely
    when the plugin is installed. This allows separate E2E runs with --no-cov.
    """
    if not config.pluginmanager.hasplugin("cov"):
        return False
    # Prefer checking parsed options on config.option for robustness
    option = getattr(config, "option", None)
    if option is not None:
        # Explicit opt-out
        if getattr(option, "no_cov", False):
            return False
        # Any of these imply coverage is active
        if (
            getattr(option, "cov", None)  # list of --cov targets
            or getattr(option, "cov_source", None)
            or getattr(option, "cov_report", None)
            or getattr(option, "cov_branch", False)
            or getattr(option, "cov_fail_under", None)
            or getattr(option, "cov_append", False)
            or getattr(option, "cov_config", None)
        ):
            return True
    # Fallback to getoption lookups
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
    """Skip Playwright tests when coverage is enabled to avoid launch errors."""
    if _is_coverage_enabled(config):
        skip_marker = pytest.mark.skip(reason="Skipped because pytest-cov interferes with Playwright browser launch.")
        for item in items:
            item.add_marker(skip_marker)
