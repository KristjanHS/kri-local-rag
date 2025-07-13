import weaviate

from config import COLLECTION_NAME

client = weaviate.connect_to_local()
client.collections.delete(COLLECTION_NAME)
client.close()  # type: ignore[attr-defined]
