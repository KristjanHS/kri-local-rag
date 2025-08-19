#!/usr/bin/env python3
"""Integration tests for Weaviate using Docker Compose."""

import logging
import os
import subprocess
import time

import pytest
import weaviate

logger = logging.getLogger(__name__)


@pytest.fixture(scope="module")
def weaviate_service():
    """Starts and stops the Weaviate service for the test module."""
    # Use the Makefile to bring up the test environment
    subprocess.run(["make", "test-up"], check=True)
    yield
    # Use the Makefile to tear down the test environment
    subprocess.run(["make", "test-down"], check=True)


@pytest.mark.slow
def test_weaviate_service_is_ready(weaviate_service):
    """Verify that the Weaviate service is ready to accept connections."""
    # Get the RUN_ID from the .run_id file
    run_id_file = ".run_id"
    if not os.path.exists(run_id_file):
        pytest.fail("No active test environment found. Run 'make test-up' first.")

    with open(run_id_file, "r") as f:
        run_id = f.read().strip()

    # Run the test inside the app container where it can access the Docker network
    test_command = [
        "docker",
        "compose",
        "-f",
        "docker/docker-compose.yml",
        "-f",
        "docker/compose.test.yml",
        "-p",
        run_id,
        "exec",
        "-T",
        "app",
        "python",
        "-m",
        "pytest",
        "tests/integration/test_weaviate_integration.py::test_weaviate_service_is_ready",
        "-v",
    ]

    result = subprocess.run(test_command, capture_output=True, text=True)

    if result.returncode != 0:
        logger.error("Test output:")
        logger.error(result.stdout)
        logger.error("Test errors:")
        logger.error(result.stderr)
        pytest.fail(f"Test failed with return code {result.returncode}")

    logger.info("Test output:")
    logger.info(result.stdout)


def test_weaviate_service_is_ready_internal():
    """Internal test that runs inside the container to verify Weaviate connectivity."""
    # This test runs inside the app container where it can access the Docker network

    client = weaviate.connect_to_local(
        host="weaviate",
        port=8080,
        grpc_port=50051,
    )

    # Wait for Weaviate to be ready
    max_retries = 30
    for i in range(max_retries):
        try:
            if client.is_ready():
                break
        except Exception:
            if i == max_retries - 1:
                raise
            time.sleep(2)

    try:
        assert client.is_ready()
    finally:
        client.close()
