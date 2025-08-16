import logging
from pathlib import Path

from sentence_transformers import CrossEncoder

# Define the model name and the local cache directory
MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
# Assumes the script is run from the project root
CACHE_DIR = Path("tests/model_cache")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_model():
    """Downloads the CrossEncoder model to a local cache directory."""
    logger.info(f"Downloading model: {MODEL_NAME} to {CACHE_DIR.resolve()}")

    # Create the cache directory if it doesn't exist
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # Download and cache the model.
    # The CrossEncoder class will handle the caching mechanism.
    # We just need to ensure the cache_folder parameter is set.
    CrossEncoder(MODEL_NAME, cache_folder=str(CACHE_DIR))

    logger.info("Model downloaded and cached successfully.")


if __name__ == "__main__":
    download_model()
