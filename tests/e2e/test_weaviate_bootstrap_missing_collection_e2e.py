#!/usr/bin/env python3
"""E2E test: when the target collection is missing in a real Weaviate,
running ensure_weaviate_ready_and_populated should create it by ingesting
example_data/test.pdf, then remove the example data, leaving an empty
collection schema present.

This uses testcontainers' Weaviate for a real server.
"""

import os
from contextlib import contextmanager

import pytest
from testcontainers.weaviate import WeaviateContainer

pytestmark = [pytest.mark.slow, pytest.mark.e2e]


@contextmanager
def _env_vars(temp_env: dict[str, str]):
    old_env = {k: os.environ.get(k) for k in temp_env.keys()}
    try:
        os.environ.update(temp_env)
        yield
    finally:
        for k, v in old_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _collection_has_any_objects(client, collection_name: str) -> bool:
    try:
        collection = client.collections.get(collection_name)
    except Exception:
        # If get fails, try use for broader client versions
        collection = client.collections.use(collection_name)
    try:
        next(collection.iterator())
        return True
    except StopIteration:
        return False


def test_bootstrap_creates_missing_collection_and_cleans_example_data(tmp_path):
    # Start a real Weaviate instance
    with WeaviateContainer() as weaviate_container:
        client = weaviate_container.get_client()

        # We'll target the explicit test collection name
        target_collection = "TestCollection"

        # Point the app to this testcontainers Weaviate via env var.
        # The python client returned by testcontainers is already configured for host/ports.
        # We pass the URL it uses (http://localhost:<mapped_port>) into the app via env.
        http_port = weaviate_container.get_exposed_port(8080)
        weaviate_url = f"http://localhost:{http_port}"

        with _env_vars({"WEAVIATE_URL": weaviate_url, "DOCKER_ENV": ""}):
            # Run the bootstrap function
            # Also patch the app's collection name during this import
            import importlib

            from backend.qa_loop import ensure_weaviate_ready_and_populated

            qa_loop = importlib.import_module("backend.qa_loop")
            qa_loop.COLLECTION_NAME = target_collection

            # Ensure the target collection is absent before bootstrap
            try:
                if client.collections.exists(target_collection):
                    client.collections.delete(target_collection)
            except Exception:
                pass

            ensure_weaviate_ready_and_populated()

            # After bootstrap:
            # - The collection should exist (robust check via get)
            try:
                client.collections.get(target_collection)
            except Exception as e:  # pragma: no cover - diagnostic in CI
                pytest.fail(f"Collection 'TestCollection' does not exist after bootstrap: {e}")

            # - Example data should have been ingested and then removed, so the
            #   collection should now be empty
            has_objects = _collection_has_any_objects(client, target_collection)
            assert has_objects is False
