from urllib.parse import urlparse

import weaviate
from weaviate.classes.config import Configure, DataType, Property

from backend.config import COLLECTION_NAME, WEAVIATE_URL

parsed_url = urlparse(WEAVIATE_URL)
client = weaviate.connect_to_custom(
    http_host=parsed_url.hostname or "localhost",
    http_port=parsed_url.port or 80,
    grpc_host=parsed_url.hostname or "localhost",
    grpc_port=50051,
    http_secure=parsed_url.scheme == "https",
    grpc_secure=parsed_url.scheme == "https",
)


def ensure_collection(client: weaviate.WeaviateClient):
    if not client.collections.exists(COLLECTION_NAME):
        # For this utility, default to manual vectors like main app; keep fallback
        try:
            client.collections.create(
                name=COLLECTION_NAME,
                properties=[
                    Property(name="content", data_type=DataType.TEXT),
                    Property(name="source_file", data_type=DataType.TEXT),
                    Property(name="page", data_type=DataType.INT),
                    Property(name="source", data_type=DataType.TEXT),
                    Property(name="section", data_type=DataType.TEXT),
                    Property(name="created_at", data_type=DataType.DATE),
                    Property(name="language", data_type=DataType.TEXT),
                ],
                vector_config=[Configure.Vectors.self_provided()],
            )
        except (AttributeError, TypeError):
            client.collections.create(
                name=COLLECTION_NAME,
                properties=[
                    Property(name="content", data_type=DataType.TEXT),
                    Property(name="source_file", data_type=DataType.TEXT),
                    Property(name="page", data_type=DataType.INT),
                    Property(name="source", data_type=DataType.TEXT),
                    Property(name="section", data_type=DataType.TEXT),
                    Property(name="created_at", data_type=DataType.DATE),
                    Property(name="language", data_type=DataType.TEXT),
                ],
                vectorizer_config=Configure.Vectorizer.none(),
            )
    return client.collections.get(COLLECTION_NAME)


try:
    client.collections.delete(COLLECTION_NAME)
finally:
    client.close()
