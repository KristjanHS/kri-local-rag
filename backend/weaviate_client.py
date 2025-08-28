from urllib.parse import urlparse

import weaviate
from weaviate.exceptions import WeaviateConnectionError

from backend.config import WEAVIATE_URL, get_logger

logger = get_logger(__name__)

# Module-level client cache
_client = None


def get_weaviate_client() -> weaviate.WeaviateClient:
    """
    Get a Weaviate client instance with centralized connection management.

    Returns:
        weaviate.WeaviateClient: A connected Weaviate client instance

    Raises:
        WeaviateConnectionError: If connection fails
    """
    global _client

    # Return cached client if available
    if _client is not None:
        return _client

    # Resolve URL from centralized config (preserves Docker service names vs localhost)
    parsed_url = urlparse(WEAVIATE_URL)
    hostname = parsed_url.hostname

    # Ensure we have a valid hostname (handles Docker service names and localhost)
    if not hostname:
        hostname = "localhost"

    http_host = hostname
    grpc_host = hostname

    try:
        logger.info(f"Connecting to Weaviate at {WEAVIATE_URL}")
        _client = weaviate.connect_to_custom(
            http_host=http_host,
            http_port=parsed_url.port or 80,
            grpc_host=grpc_host,
            grpc_port=50051,
            http_secure=parsed_url.scheme == "https",
            grpc_secure=parsed_url.scheme == "https",
        )
        logger.info("Weaviate connection established")
        return _client
    except Exception as e:
        logger.error(f"Failed to connect to Weaviate: {e}")
        raise WeaviateConnectionError(f"Weaviate connection failed: {e}") from e


def close_weaviate_client():
    """Close the Weaviate client connection if it exists."""
    global _client
    if _client is not None:
        try:
            _client.close()
            logger.info("Weaviate connection closed")
        except Exception as e:
            logger.warning(f"Error closing Weaviate connection: {e}")
        finally:
            _client = None
