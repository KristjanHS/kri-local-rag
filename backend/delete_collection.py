import weaviate
import os

from config import COLLECTION_NAME

url = os.getenv("WEAVIATE_URL")
client = weaviate.Client(url=url) if url else weaviate.connect_to_local()  # type: ignore[attr-defined]
client.collections.delete(COLLECTION_NAME)  # type: ignore[attr-defined]
client.close()  # type: ignore[attr-defined]
