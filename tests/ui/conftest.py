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
    """Enforce --no-cov for UI tests to prevent coverage-related issues.

    UI tests must be run with --no-cov to avoid Playwright coverage issues.
    """
    if not items:
        return

    # Check if --no-cov is explicitly provided
    is_coverage_disabled = bool(getattr(config.option, "no_cov", False))

    if not is_coverage_disabled:
        raise pytest.UsageError(
            "UI tests cannot be run with coverage enabled. Please run with --no-cov. "
            "Example: pytest tests/ui --no-cov"
        )
