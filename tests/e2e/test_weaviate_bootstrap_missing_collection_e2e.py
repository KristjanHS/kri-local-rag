#!/usr/bin/env python3
"""E2E test: when the target collection is missing in a real Weaviate,
running ensure_weaviate_ready_and_populated should create it by ingesting
example_data/test.pdf, then remove the example data, leaving an empty
collection schema present.

This prepares Weaviate by starting the docker-compose service (no rebuild of the app).
"""

import os
from contextlib import contextmanager

import pytest

from backend.weaviate_client import close_weaviate_client, get_weaviate_client
from tests.conftest import TEST_COLLECTION_NAME

pytestmark = [pytest.mark.slow]


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


def test_bootstrap_creates_missing_collection_and_cleans_example_data(tmp_path, weaviate_compose_up):
    # Target the explicit test collection. Do NOT hardcode the Weaviate URL: the
    # client resolves it via get_service_url("weaviate"), which reads the
    # compose-injected WEAVIATE_URL — "http://weaviate:8080" inside the test
    # container, "http://localhost:8080" on the host. Overriding it here broke the
    # hermetic in-container run (`make test-e2e`) with connection refused.
    target_collection = TEST_COLLECTION_NAME

    with _env_vars({"COLLECTION_NAME": target_collection}):
        # Connect a client to the compose Weaviate via centralized wrapper
        client = get_weaviate_client()
        try:
            # Run the bootstrap function with the collection name provided via environment
            from backend.qa_loop import ensure_weaviate_ready_and_populated

            # Ensure the target collection is absent before bootstrap
            try:
                if client.collections.exists(target_collection):
                    client.collections.delete(target_collection)
            except Exception:
                pass

            ensure_weaviate_ready_and_populated()

            # After bootstrap, get a fresh client since bootstrap may have closed it
            fresh_client = get_weaviate_client()
            try:
                # After bootstrap:
                # - The collection should exist (robust check via get)
                try:
                    fresh_client.collections.get(target_collection)
                except Exception as e:  # pragma: no cover - diagnostic in CI
                    pytest.fail(f"Collection '{TEST_COLLECTION_NAME}' does not exist after bootstrap: {e}")

                # - Example data should have been ingested and then removed, so the
                #   collection should now be empty
                has_objects = _collection_has_any_objects(fresh_client, target_collection)
                assert has_objects is False
            finally:
                close_weaviate_client()
        finally:
            try:
                close_weaviate_client()
            except Exception:
                pass
