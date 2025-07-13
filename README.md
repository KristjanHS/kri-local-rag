# Phase 2 — Local RAG Experimentation

This phase focuses on building and experimenting with a local Retrieval-Augmented Generation (RAG) pipeline. The goal is to use the `nomic-embed-text` model for creating text embeddings and FAISS for efficient similarity search.

## Directory Layout

```text
phase2/
├── data/                     # Sample data for the RAG pipeline
├── notebooks/                # Jupyter notebooks for experimentation
├── python_code/              # Python scripts for the RAG pipeline
└── tests/                    # Tests for the RAG pipeline
```

## Key Components

- **Embedding Model**: `nomic-embed-text` for creating high-quality text embeddings.
- **Vector Store**: FAISS for efficient storage and retrieval of text embeddings.
- **RAG Pipeline**: A Python script that demonstrates how to load data, create embeddings, and perform similarity search.
