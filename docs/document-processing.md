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
docker compose run --rm rag-backend python delete_collection.py
```

## Advanced Options

### Custom Configuration
```python
# Edit ingest_pdf.py
CHUNK_SIZE = 1000  # Characters per chunk
CHUNK_OVERLAP = 200  # Overlap between chunks
```

### Batch Processing
```bash
# Process all PDFs in data/ directory
docker compose run --rm rag-backend python ingest_pdf.py
```

## Troubleshooting

### Common Issues

**No PDFs found**
```bash
ls -la data/
```

**Weaviate connection failed**
```bash
docker ps | grep weaviate
docker compose logs weaviate
```

**Embedding generation failed**
```bash
docker ps | grep t2v-transformers
docker compose logs t2v-transformers
```

**Memory error**
```bash
# Increase Docker memory limits in docker-compose.yml
```

## Performance Tips

- Use GPU for faster embedding generation
- Process documents in smaller batches
- Monitor memory usage during ingestion
- Use SSD storage for better I/O

## Data Persistence

### Docker Volumes & Backup
```bash
# List volumes
docker volume ls | grep kri-local-rag

# Backup data
docker run --rm -v kri-local-rag_weaviate_data:/data -v $(pwd):/backup alpine tar czf /backup/weaviate_backup.tar.gz -C /data .
```

### Data Locations
- **Weaviate data**: `kri-local-rag_weaviate_data` volume
- **Ollama models**: `ollama_models` volume  
- **Source documents**: Local `data/` directory

## Next Steps

- [Getting Started Guide](GETTING_STARTED.md)
- [Docker Management Guide](docker-management.md) 