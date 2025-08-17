"""Configuration for the integration test suite."""

import pytest


# This fixture automatically applies the 'docker_services' fixture from the root
# conftest.py to every test in the integration suite. This ensures that the
# Docker environment is up and running before any integration tests are executed.
@pytest.fixture(autouse=True)
def use_docker_services(docker_services):
    """Ensure Docker services are running for all integration tests."""
    pass
