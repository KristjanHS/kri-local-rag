import weaviate
from weaviate.classes.config import Configure, DataType, Property

from backend.config import COLLECTION_NAME
from backend.weaviate_client import close_weaviate_client, get_weaviate_client

client = get_weaviate_client()


def ensure_collection(client: weaviate.WeaviateClient):
    if not client.collections.exists(COLLECTION_NAME):
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
            vector_config=Configure.Vectors.self_provided(),
        )
    return client.collections.get(COLLECTION_NAME)


try:
    client.collections.delete(COLLECTION_NAME)
finally:
    close_weaviate_client()
