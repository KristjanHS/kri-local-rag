#!/usr/bin/env python3
"""E2E test: when the target collection is missing in a real Weaviate,
running ensure_weaviate_ready_and_populated should create it by ingesting
example_data/test.md (and test.pdf), then remove the example data, leaving
an empty collection schema present.

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

        # Pick the same collection used by the app during bootstrap
        from backend.config import COLLECTION_NAME as APP_COLLECTION

        # Ensure the collection is absent
        try:
            if client.collections.exists(APP_COLLECTION):
                client.collections.delete(APP_COLLECTION)
        except Exception:
            pass

        # Point the app to this testcontainers Weaviate via env var
        weaviate_url = weaviate_container.get_url()

        with _env_vars({"WEAVIATE_URL": weaviate_url}):
            # Run the bootstrap function
            from backend.qa_loop import ensure_weaviate_ready_and_populated

            ensure_weaviate_ready_and_populated()

            # After bootstrap:
            # - The collection should exist
            assert client.collections.exists(APP_COLLECTION)

            # - Example data should have been ingested and then removed, so the
            #   collection should be empty of objects
            has_objects = _collection_has_any_objects(client, APP_COLLECTION)
            assert has_objects is False
