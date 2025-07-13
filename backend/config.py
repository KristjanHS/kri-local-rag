COLLECTION_NAME = "Document"

# Text splitting parameters
CHUNK_SIZE = 800
CHUNK_OVERLAP = 100

# Hybrid search parameters
DEFAULT_HYBRID_ALPHA = 0.5  # 0 → pure BM25, 1 → pure vector

# Ollama LLM settings (used by qa_loop.py)
# OLLAMA_MODEL = "huihui_ai/deepseek-r1-abliterated:7b"
OLLAMA_MODEL = "cas/mistral-7b-instruct-v0.3"
OLLAMA_URL = "http://localhost:11434"
