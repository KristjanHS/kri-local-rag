# Getting Started

This guide covers everything you need to set up, run, use, and troubleshoot the kri-local-rag system.

---

## Prerequisites
- Docker & Docker Compose
- 8GB+ RAM
- NVIDIA GPU (optional)
- Linux/WSL2

---

## Installation & Startup

### Quick Install
```bash
git clone <your-repo-url>
cd kri-local-rag
./run-docker.sh
```

### Manual Startup
```bash
export COMPOSE_FILE=docker/docker-compose.yml
export COMPOSE_PROJECT_NAME=kri-local-rag
docker compose up --build -d weaviate t2v-transformers ollama
sleep 10
docker compose run --rm rag-backend
```

### GPU Setup (Optional)
```bash
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

---

## Using the System

### Start the Console
```bash
./run-docker.sh
```
You should see:
```
RAG console – type a question, Ctrl-D/Ctrl-C to quit
Ready for questions!
```

### Ingest Documents
```bash
# In a new terminal
docker compose run --rm rag-backend python ingest_pdf.py
```

### Ask Questions
```
> What is this document about?
> How does the system work?
> Can you summarize the key points?
```

---

## Document Processing

- **Supported formats:** PDF, TXT, MD
- Place files in the `data/` directory

### Verify Ingestion
```bash
docker compose run --rm rag-backend python -c "
import weaviate
client = weaviate.Client('http://weaviate:8080')
print('Collections:', [c['class'] for c in client.schema.get()['classes']])
"
```

### View Document Counts
```bash
docker compose run --rm rag-backend python -c "
import weaviate
client = weaviate.Client('http://weaviate:8080')
for collection in client.schema.get()['classes']:
    print(f'Collection: {collection[\"class\"]}')
    result = client.query.aggregate(collection['class']).with_meta_count().do()
    print(f'Documents: {result[\"data\"][\"Aggregate\"][collection[\"class\"]][0][\"meta\"][\"count\"]}')
"
```

### Delete All Data
```bash
docker compose run --rm rag-backend python delete_collection.py
```

---

## Docker & Service Management

### Start/Stop/Logs
```bash
docker compose up -d      # Start services
docker compose down       # Stop services
docker compose logs -f    # View logs
```

### Restart/Build
```bash
docker compose restart rag-backend
# Rebuild backend
docker compose build rag-backend
```

### Debug/Access
```bash
docker compose exec rag-backend bash
```

---

## Usage Options

### Debug Levels
```bash
docker compose run --rm rag-backend --debug-level 1   # Basic debug
docker compose run --rm rag-backend --debug-level 2   # Detailed debug
```

### Filtering
```bash
docker compose run --rm rag-backend --source pdf      # Filter by source
docker compose run --rm rag-backend --language en     # Filter by language
docker compose run --rm rag-backend --k 5             # Adjust results
```

---

## Troubleshooting

### Common Issues & Fixes

**Docker Permission Denied**
```bash
sudo usermod -aG docker $USER
newgrp docker
```

**GPU Not Available**
```bash
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi
```

**Port Conflicts**
```bash
sudo netstat -tulpn | grep :8080
sudo netstat -tulpn | grep :11434
```

**Container Won't Start**
```bash
docker compose logs rag-backend
docker compose logs ollama
docker compose logs weaviate
```

**No Results Found**
```bash
docker compose run --rm rag-backend python delete_collection.py
docker compose run --rm rag-backend python ingest_pdf.py
```

**Model Not Found**
```bash
docker compose exec ollama ollama pull cas/mistral-7b-instruct-v0.3
```

**Slow Responses**
```bash
nvidia-smi
# Reduce debug level
docker compose run --rm rag-backend --debug-level 0
```

**Weaviate/Embedding/Memory Issues**
```bash
docker ps | grep weaviate
docker compose logs weaviate
docker ps | grep t2v-transformers
docker compose logs t2v-transformers
# Increase Docker memory limits in docker-compose.yml
```

---

## Performance & Data

- Use GPU for faster embedding generation
- Monitor memory usage during ingestion
- Use SSD storage for better I/O

### Docker Volumes
```bash
docker volume ls | grep kri-local-rag
# Backup data
docker run --rm -v kri-local-rag_weaviate_data:/data -v $(pwd):/backup alpine tar czf /backup/weaviate_backup.tar.gz -C /data .
```

---

## Services

| Service            | Purpose              | Port  |
|--------------------|---------------------|-------|
| weaviate           | Vector database      | 8080  |
| ollama             | LLM server           | 11434 |
| t2v-transformers   | Embedding generation | 8081  |
| rag-backend        | RAG application      | -     |

---

**You’re ready to use kri-local-rag!** 