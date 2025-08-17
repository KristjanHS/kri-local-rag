import logging
import os
from unittest.mock import MagicMock, patch

import pytest

# Create a logger for this test file
logger = logging.getLogger(__name__)


# Now, import the module under test
from backend import qa_loop


@pytest.mark.unit
@patch.dict(os.environ, {"RERANKER_CROSS_ENCODER_OPTIMIZATIONS": "true"})
def test_cross_encoder_compiles_once_and_caches(mocker):
    """
    Test that torch.compile is called on the first run and the result is cached,
    avoiding re-compilation on subsequent calls.
    """
    logger.debug("--- Running test_cross_encoder_compiles_once_and_caches ---")

    # Reset the cache to ensure the logic is re-run for this test
    qa_loop._cross_encoder = None

    # Mock the CrossEncoder class and its instance
    mock_ce_instance = MagicMock()

    # The CrossEncoder instance has a 'model' attribute. We need to mock it
    # to simulate that it's not compiled yet. The check is `hasattr(model, "_orig_mod")`.
    # A simple object won't have it, which is what we want for the first call.
    class MockModel:
        pass

    mock_model_instance = MockModel()
    mock_ce_instance.model = mock_model_instance

    mocker.patch("sentence_transformers.CrossEncoder", return_value=mock_ce_instance)

    # Mock torch.compile to return a new "compiled" model mock
    mock_compiled_model = MagicMock()
    mock_compile = mocker.patch("torch.compile", return_value=mock_compiled_model)
    mocker.patch("torch.set_num_threads")

    # --- First call: should load and compile the model ---
    encoder1 = qa_loop._get_cross_encoder(model_name="dummy-model")

    # Assertions for the first call
    assert encoder1 is not None, "The encoder should be a mock instance, not None"
    mock_compile.assert_called_once_with(mock_model_instance, backend="inductor", mode="max-autotune")
    assert encoder1 is mock_ce_instance, "Should return the main encoder instance"
    assert encoder1.model is mock_compiled_model, "Model should be the compiled version"

    # --- Second call: should return the cached instance without re-compiling ---
    encoder2 = qa_loop._get_cross_encoder(model_name="dummy-model")

    # Assertions for the second call
    mock_compile.assert_called_once()  # Should NOT be called again
    assert encoder2 is encoder1, "Should return the exact same cached instance"
