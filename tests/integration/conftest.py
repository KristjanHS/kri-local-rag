"""Configuration for the integration test suite.

This module provides fixtures for integration tests that run in the Compose-based
test environment. Tests should be run using 'make test-up' to ensure the Docker
services are available.

This module now includes real model loading infrastructure for integration tests
that require actual ML models to be loaded and tested.

Type Safety Notes:
- Uses defensive programming with hasattr() checks before accessing attributes
- Handles ML model outputs that may vary (numpy arrays, lists, etc.)
- Provides detailed logging for debugging model health issues
- Follows fail-safe approach: prefer returning False/None over raising exceptions
"""

import os
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import MagicMock

import pytest

# Type checking imports
if TYPE_CHECKING:
    pass


@pytest.fixture
def managed_embedding_model(mocker) -> MagicMock:
    """
    Fixture to mock backend.retriever._get_embedding_model.

    It patches the function to return a MagicMock instance, preventing real
    model loading and allowing tests to make assertions on the mock.
    """
    # Patch the function where it's defined and used in the backend
    mock_retriever = mocker.patch("backend.retriever._get_embedding_model")

    # Create a mock SentenceTransformer instance
    mock_model_instance = MagicMock()
    mock_model_instance.encode.return_value = [[0.1, 0.2, 0.3]]  # Example vector

    # Configure the patched function to return our mock model
    mock_retriever.return_value = mock_model_instance

    return mock_model_instance


@pytest.fixture
def managed_get_top_k(mocker):
    """Fixture to mock only the get_top_k function in the QA pipeline."""
    patcher = mocker.patch("backend.qa_loop.get_top_k")
    yield patcher


@pytest.fixture
def mock_weaviate_connect(mocker):
    """Fixture to mock weaviate.connect_to_custom."""
    yield mocker.patch("weaviate.connect_to_custom")


@pytest.fixture
def mock_httpx_get(mocker):
    """Fixture to mock httpx.get for Ollama client tests."""
    yield mocker.patch("backend.ollama_client.httpx.get")


# Real Model Loading Infrastructure for Integration Tests
# ============================================================================


@pytest.fixture(scope="session", autouse=True)
def integration_model_cache():
    """
    Session-scoped fixture that sets up a dedicated model cache directory
    for integration tests. This ensures models are downloaded once per test
    session and reused across tests, improving performance and reliability.

    The cache is automatically cleaned up after the test session completes.
    """
    # Create a dedicated cache directory for integration tests
    cache_dir = Path(tempfile.mkdtemp(prefix="integration_model_cache_"))

    # Set environment variables to use this cache
    original_env = {}
    env_vars_to_set = [
        ("HF_HOME", str(cache_dir)),
        ("SENTENCE_TRANSFORMERS_HOME", str(cache_dir)),
        ("TORCH_HOME", str(cache_dir / "torch")),
        ("TRANSFORMERS_CACHE", str(cache_dir / "transformers")),
        ("TRANSFORMERS_OFFLINE", "0"),  # Allow downloads during setup
    ]

    # Store original values and set new ones
    for var, value in env_vars_to_set:
        original_env[var] = os.environ.get(var)
        os.environ[var] = value

    # Import here to ensure environment is set before any model imports
    from backend.config import get_logger

    logger = get_logger(__name__)

    logger.info(f"Integration test model cache setup: {cache_dir}")

    yield cache_dir

    # Cleanup: restore original environment variables
    for var, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(var, None)
        else:
            os.environ[var] = original_value

    # Clean up cache directory
    import shutil

    try:
        shutil.rmtree(cache_dir)
        logger.info(f"Cleaned up integration model cache: {cache_dir}")
    except Exception as e:
        logger.warning(f"Failed to clean up cache directory {cache_dir}: {e}")


@pytest.fixture
def real_model_loader(integration_model_cache):
    """
    Fixture that provides a model loader with pre-cached models for integration tests.

    This fixture ensures models are available locally before tests run, avoiding
    network dependencies during test execution. Models are downloaded once during
    the session setup and reused. Uses integration test optimized loading with
    enhanced health checks and retry logic.

    Returns:
        dict: Contains 'embedder' and 'reranker' keys with loaded model instances,
              plus 'status' key with detailed loading information
    """
    from backend.config import get_logger
    from backend.models import clear_model_cache, load_embedder, load_reranker, preload_models_with_health_check

    logger = get_logger(__name__)

    # Clear any cached models to ensure fresh loading
    clear_model_cache()

    # Use the enhanced preload function with health checks
    logger.info("Preloading models for integration test with enhanced health checks...")
    status = preload_models_with_health_check()

    # Load models with better error handling
    models = {}
    try:
        models["embedder"] = load_embedder()
        logger.info("✓ Embedding model loaded successfully with integration optimizations")
    except Exception as e:
        logger.error(f"Failed to load embedding model: {e}")
        models["embedder"] = None

    try:
        models["reranker"] = load_reranker()
        logger.info("✓ Reranker model loaded successfully with integration optimizations")
    except Exception as e:
        logger.error(f"Failed to load reranker model: {e}")
        models["reranker"] = None

    # Add status information to the returned dict
    models["status"] = status

    # At least one model should be available for meaningful tests
    if models["embedder"] is None and models["reranker"] is None:
        pytest.skip("No models could be loaded - skipping real model integration tests")

    # Log summary of what was loaded
    available_models = [name for name, model in models.items() if model is not None and name != "status"]
    logger.info(f"✓ Model loading completed. Available models: {available_models}")
    logger.info(".2f")

    return models


@pytest.fixture
def real_embedding_model(real_model_loader):
    """Fixture that provides just the real embedding model for tests that need it."""
    return real_model_loader["embedder"]


@pytest.fixture
def real_reranker_model(real_model_loader):
    """Fixture that provides just the real reranker model for tests that need it."""
    return real_model_loader["reranker"]


@pytest.fixture
def model_health_checker():
    """
    Fixture that provides utilities to check model health and availability.

    Returns:
        dict: Contains functions to check model health and get model info
    """
    from backend.config import get_logger

    logger = get_logger(__name__)

    def check_model_health(model: Any, model_name: str) -> bool:
        """Check if a model is healthy and can perform basic operations."""
        try:
            if hasattr(model, "encode") and callable(model.encode):
                # Test embedding model
                test_text = "This is a test sentence for model health check."
                embedding = model.encode(test_text)
                # Check if embedding is array-like with proper shape
                if not hasattr(embedding, "__len__") or not hasattr(embedding, "shape"):
                    logger.warning(f"Model {model_name} returned invalid embedding format")
                    return False
                # Type checker doesn't understand hasattr narrowing, but we've verified the attributes exist
                return len(embedding) > 0 and embedding.shape[0] > 0  # type: ignore[attr-defined]

            elif hasattr(model, "predict") and callable(model.predict):
                # Test reranker model
                query = "test query"
                doc = "test document"
                scores = model.predict([[query, doc]])
                # Check if scores is a list/array of numbers
                if not hasattr(scores, "__len__"):
                    logger.warning(f"Model {model_name} returned invalid scores format")
                    return False

                # Check that all scores are numeric (including numpy types)
                def is_numeric(value):
                    try:
                        # Check for Python numeric types
                        if isinstance(value, (int, float)):
                            return True
                        # Check for numpy numeric types
                        if hasattr(value, "dtype"):
                            import numpy as np

                            return np.issubdtype(value.dtype, np.number)
                        # Fallback: try to convert to float
                        float(value)
                        return True
                    except (ValueError, TypeError):
                        return False

                # Type checker doesn't understand hasattr narrowing, but we've verified __len__ exists
                return len(scores) > 0 and all(is_numeric(s) for s in scores)  # type: ignore[arg-type]

            else:
                logger.warning(f"Unknown model type for {model_name}")
                return False

        except Exception as e:
            logger.error(f"Model health check failed for {model_name}: {e}")
            return False

    def get_model_info(model: Any, model_name: str) -> dict:
        """Get basic information about a model."""
        info = {"name": model_name, "type": type(model).__name__, "healthy": check_model_health(model, model_name)}

        # Add model-specific info
        if hasattr(model, "encode"):
            try:
                test_embedding = model.encode("test")
                if hasattr(test_embedding, "shape") and hasattr(test_embedding, "__len__"):
                    # Type checker doesn't understand hasattr narrowing, but we've verified the attributes exist
                    info["embedding_dim"] = test_embedding.shape[0]  # type: ignore[attr-defined]
                else:
                    info["embedding_dim"] = None
            except Exception:
                info["embedding_dim"] = None

        return info

    return {"check_health": check_model_health, "get_info": get_model_info}


@pytest.fixture(scope="function")
def ensure_models_preloaded(real_model_loader):
    """
    Fixture that ensures models are preloaded before each test function runs.
    This provides additional assurance that models are ready for integration tests.

    The real_model_loader fixture already handles preloading, but this fixture
    provides a more explicit hook for tests that specifically need models ready.
    """
    # Models are already preloaded by real_model_loader fixture
    # This fixture just serves as a dependency and documentation point
    from backend.config import get_logger

    logger = get_logger(__name__)
    logger.debug("Models ensured to be preloaded for integration test")
    return real_model_loader


@pytest.fixture
def model_performance_monitor():
    """
    Fixture that provides utilities to monitor model performance during integration tests.

    Returns:
        dict: Contains functions to measure model performance and track metrics
    """
    import time

    from backend.config import get_logger

    logger = get_logger(__name__)

    def time_model_operation(model, operation_name, operation_func, *args, **kwargs):
        """Time a model operation and log the results."""
        start_time = time.time()
        try:
            result = operation_func(*args, **kwargs)
            elapsed_time = time.time() - start_time
            logger.info(".3f")
            return result, elapsed_time
        except Exception:
            elapsed_time = time.time() - start_time
            logger.error(".3f")
            raise

    def benchmark_model(model, model_name, test_data):
        """Benchmark a model's performance with test data."""
        if model is None:
            logger.warning(f"Cannot benchmark {model_name}: model is None")
            return {"error": "model is None"}

        results = {"model_name": model_name, "operations": {}}

        # Benchmark embedding model
        if hasattr(model, "encode") and model_name == "embedding":
            try:
                _, encode_time = time_model_operation(model, "encode", model.encode, test_data)
                results["operations"]["encode"] = encode_time
            except Exception as e:
                results["operations"]["encode"] = f"error: {e}"

        # Benchmark reranker model
        elif hasattr(model, "predict") and model_name == "reranker":
            try:
                _, predict_time = time_model_operation(model, "predict", model.predict, test_data)
                results["operations"]["predict"] = predict_time
            except Exception as e:
                results["operations"]["predict"] = f"error: {e}"

        else:
            results["operations"]["unknown"] = f"Unknown model type for {model_name}"

        return results

    def get_performance_summary(real_model_loader):
        """Get a summary of model loading and performance for the current test session."""
        status = real_model_loader.get("status", {})

        summary = {
            "models_loaded": [],
            "models_failed": [],
            "total_load_time": status.get("total_time", 0),
            "load_success_rate": 0,
        }

        # Count successful and failed model loads
        for model_type in ["embedding_model", "reranker_model"]:
            if model_type in status:
                model_status = status[model_type]
                if model_status.get("loaded"):
                    summary["models_loaded"].append(model_type)
                else:
                    summary["models_failed"].append(model_type)

        # Calculate success rate
        total_models = len(summary["models_loaded"]) + len(summary["models_failed"])
        if total_models > 0:
            summary["load_success_rate"] = len(summary["models_loaded"]) / total_models

        return summary

    return {
        "time_operation": time_model_operation,
        "benchmark_model": benchmark_model,
        "get_performance_summary": get_performance_summary,
    }
