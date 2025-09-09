import logging
import os
from unittest.mock import MagicMock

# Create a logger for this test file
logger = logging.getLogger(__name__)


# Now, import the module under test
from backend import qa_loop


def test_cross_encoder_loads(mocker):
    """
    Test that the cross encoder is loaded correctly.
    """
    logger.debug("--- Running test_cross_encoder_loads ---")

    # Set environment variable using mocker (modern approach)
    mocker.patch.dict(os.environ, {"RERANKER_CROSS_ENCODER_OPTIMIZATIONS": "true"})

    # Provide a dummy encoder instance via our app's loader boundary
    mock_encoder_instance = MagicMock()
    mocker.patch("backend.qa_loop.load_reranker", return_value=mock_encoder_instance)

    # --- First call: should load the model ---
    cross_encoder = qa_loop._get_cross_encoder()

    # Assertions for the first call
    assert cross_encoder is not None, "The encoder should be a mock instance, not None"
    assert cross_encoder is mock_encoder_instance, "Should return the mocked encoder instance"
