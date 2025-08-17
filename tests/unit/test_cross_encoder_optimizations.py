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
def test_cross_encoder_enables_heavy_optimizations_when_allowed(mocker):
    """Test that torch.compile is called when optimizations are enabled."""
    logger.debug("--- Running test_cross_encoder_enables_heavy_optimizations_when_allowed ---")

    # Reset the cache to ensure the logic is re-run
    qa_loop._cross_encoder = None

    # Mock the CrossEncoder class and its instance
    mock_ce_instance = MagicMock()
    mocker.patch("sentence_transformers.CrossEncoder", return_value=mock_ce_instance)

    # Mock only the necessary torch functions
    mock_compile = mocker.patch("torch.compile", return_value=mock_ce_instance)
    mocker.patch("torch.set_num_threads")

    # Call the function that should trigger the optimization
    encoder = qa_loop._get_cross_encoder(model_name="dummy-model")

    # Verify that torch.compile was called
    mock_compile.assert_called_once()

    # Verify that the returned encoder is the one processed by torch.compile
    assert encoder is mock_ce_instance
