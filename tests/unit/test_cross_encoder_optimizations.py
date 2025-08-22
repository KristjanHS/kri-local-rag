import logging
import os
from unittest.mock import MagicMock, patch

# Create a logger for this test file
logger = logging.getLogger(__name__)


# Now, import the module under test
from backend import qa_loop


@patch.dict(os.environ, {"RERANKER_CROSS_ENCODER_OPTIMIZATIONS": "true"})
def test_cross_encoder_loads(mocker):
    """
    Test that the cross encoder is loaded correctly.
    """
    logger.debug("--- Running test_cross_encoder_loads ---")

    # Mock the CrossEncoder class and its instance
    mock_ce_instance = MagicMock()
    mocker.patch("sentence_transformers.CrossEncoder", return_value=mock_ce_instance)

    # Mock the centralized configuration to use our dummy model
    with patch("backend.qa_loop.RERANKER_MODEL", "dummy-model"):
        # --- First call: should load the model ---
        cross_encoder = qa_loop._get_cross_encoder()

    # Assertions for the first call
    assert cross_encoder is not None, "The encoder should be a mock instance, not None"
    assert cross_encoder is mock_ce_instance, "Should return the main encoder instance"
