# Document Processing Guide

## Supported Formats

- **PDF files** (`.pdf`) - Primary format

## Quick Ingestion

```bash
# 1. Prepare documents
cp your-document.pdf data/

# 2. Run ingestion
docker compose run --rm rag-backend python ingest_pdf.py

# 3. Verify
docker compose run --rm rag-backend python -c "
import weaviate
client = weaviate.Client('http://weaviate:8080')
print('Collections:', [c['class'] for c in client.schema.get()['classes']])
"
```

## Ingestion Process

1. **Document Processing** - PDFs parsed, text extracted, chunks created
2. **Embedding Generation** - Chunks converted to embeddings using text2vec-transformers
3. **Storage** - Embeddings stored in Weaviate with metadata

## Managing Data

```bash
# View documents (list collections and counts)
docker compose run --rm rag-backend python -c "
import weaviate
client = weaviate.Client('http://weaviate:8080')
for collection in client.schema.get()['classes']:
    print(f'Collection: {collection[\"class\"]}')
    result = client.query.aggregate(collection['class']).with_meta_count().do()
    print(f'Documents: {result[\"data\"][\"Aggregate\"][collection[\"class\"]][0][\"meta\"][\"count\"]}')
"

# Delete all data
# docker compose run --rm rag-backend python delete_collection.py
```

For all Docker-related activities (starting, stopping, resetting, troubleshooting), see [Docker Management Guide](docker-management.md).