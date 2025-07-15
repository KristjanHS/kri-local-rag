# 🧠 Embedding Model Selection Guide (Sentence-Transformers, Local GPU)

This guide will help you choose and use the best sentence-transformers embedding models for semantic search, RAG, and related tasks on a local GPU (e.g., RTX 3070 with 8GB VRAM).

---
## ⚡️ Tips for Local GPU Use

- All models above fit comfortably on an 8GB VRAM GPU.
- For larger models (e.g., mpnet-base), reduce batch size if you hit memory limits.
- For maximum throughput, use the MiniLM models.
- For best retrieval quality, try mpnet-base or L12-v2 models.

---


## 🚀 Top Models for 8GB VRAM GPUs

| Model Name                                   | Embedding Size | Speed      | Quality      | Link                                                                 |
|-----------------------------------------------|----------------|------------|--------------|----------------------------------------------------------------------|
| all-MiniLM-L6-v2                             | 384            | ⚡️ Fast    | ⭐⭐⭐⭐         | [HuggingFace](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2)      |
| all-MiniLM-L12-v2                            | 384            | ⚡️ Fast    | ⭐⭐⭐⭐⭐        | [HuggingFace](https://huggingface.co/sentence-transformers/all-MiniLM-L12-v2)     |
| multi-qa-MiniLM-L6-cos-v1                    | 384            | ⚡️ Fast    | ⭐⭐⭐⭐         | [HuggingFace](https://huggingface.co/sentence-transformers/multi-qa-MiniLM-L6-cos-v1) |
| multi-qa-mpnet-base-dot-v1                   | 768            | 🚀 Medium  | ⭐⭐⭐⭐⭐        | [HuggingFace](https://huggingface.co/sentence-transformers/multi-qa-mpnet-base-dot-v1) |
| paraphrase-mpnet-base-v2                     | 768            | 🚀 Medium  | ⭐⭐⭐⭐⭐        | [HuggingFace](https://huggingface.co/sentence-transformers/paraphrase-mpnet-base-v2)   |
| distilbert-base-nli-stsb-mean-tokens         | 768            | 🚀 Medium  | ⭐⭐⭐⭐         | [HuggingFace](https://huggingface.co/sentence-transformers/distilbert-base-nli-stsb-mean-tokens) |

---

## 🏆 Recommendations

- **Best Quality vs. Speed/Memory:**  
  Use `all-MiniLM-L12-v2` or `paraphrase-mpnet-base-v2`
- **Maximum Speed & Large Batches:**  
  Use `all-MiniLM-L6-v2` or `multi-qa-MiniLM-L6-cos-v1`
- **Highest Quality (smaller batches):**  
  Use `multi-qa-mpnet-base-dot-v1` or `paraphrase-mpnet-base-v2`

---

## 🔄 How to Change the Embedding Model in This App (via Dockerfile)

In this app, the embedding model used by Weaviate is determined by the Dockerfile for the `t2v-transformers` service.

### Step-by-Step Instructions

1. **Open** `docker/t2v-transformers.Dockerfile` in your project.
2. **Change the model** by editing the `FROM` line to use your desired model. For example:
   
   - To use `all-MiniLM-L6-v2` (default):
     ```dockerfile
     FROM semitechnologies/transformers-inference:sentence-transformers-all-MiniLM-L6-v2
     ```
   - To use `paraphrase-mpnet-base-v2`:
     ```dockerfile
     FROM semitechnologies/transformers-inference:sentence-transformers-paraphrase-mpnet-base-v2
     ```
   - For other models, check available tags at: https://cr.weaviate.io/v2/semitechnologies/transformers-inference/tags/list

3. **Rebuild the Docker image** so the new model is downloaded and used:
   ```bash
   docker compose build t2v-transformers
   docker compose up -d t2v-transformers
   ```
   Or, if using the provided script:
   ```bash
   ./run-docker.sh
   ```

4. **Verify**: Your Weaviate instance will now use the new embedding model for all future ingestions and queries.

> **Tip:** If you want to use a custom HuggingFace model not available as a pre-built image, you can use the `custom` image and set the `MODEL_NAME` environment variable. See the comments in the Dockerfile for details.

---

## 🤔 When Should You Use Weaviate's Vectorizer vs. Python Embedding?

Choosing where to generate your embeddings depends on your needs for simplicity, control, and performance. Here’s a breakdown:

| Feature                       | Weaviate Vectorizer (Your Current Setup) | Direct Python Embedding                                  |
| ----------------------------- | ---------------------------------------- | -------------------------------------------------------- |
| **Simplicity**                | ⭐⭐⭐⭐⭐ (Easier)                          | ⭐⭐⭐ (More complex)                                      |
| **Flexibility & Control**     | ⭐⭐ (Limited)                            | ⭐⭐⭐⭐⭐ (Total control)                                   |
| **Performance**               | ⭐⭐⭐⭐ (Good)                             | ⭐⭐⭐⭐⭐ (Potentially higher for custom batching)           |
| **Architecture**              | Decoupled (Microservice)                 | Tightly Coupled (Monolithic)                            |
| **Best For**                  | Simplicity, standard use cases, scalability | Advanced techniques, custom models, max performance   |

### When to Use Weaviate's Vectorizer
- **You want simplicity and speed of development.**
- **You prefer a decoupled, microservice architecture.**
- **A standard, pre-trained model is good enough.**

This is ideal for most ingestion pipelines, where you want to keep your codebase clean and let Weaviate handle embedding as a service.

### When to Generate Embeddings Directly in Python
- **You need full control over the model** (custom or fine-tuned models).
- **You need to pre-process text before embedding** (e.g., prepend instructions, custom chunking).
- **You want to optimize batching for maximum GPU performance.**
- **You are using advanced techniques like re-ranking** (e.g., cross-encoders that require both query and document at runtime).

This is necessary for advanced RAG pipelines, custom research, or when you want to maximize performance and flexibility.

### Hybrid Approach Example
Your project uses both:
- **Ingestion (`ingest_pdf.py`):** Uses Weaviate's vectorizer for simplicity and throughput.
- **Q&A (`qa_loop.py`):** Loads a cross-encoder in Python for advanced re-ranking, which Weaviate cannot do at ingestion time.

**Rule of thumb:**
- Use Weaviate's vectorizer for simple, robust, high-throughput ingestion.
- Use Python for embedding when you need advanced features, custom logic, or fine-tuned performance.

---

## 🛠️ How to Use a Model in Python (Only for the Manual Embedding Workflow)

> **Note:** You only need to follow these steps if you choose to generate embeddings directly in Python (the "manual embedding" workflow). If you use Weaviate's built-in vectorizer, you do **not** need to do this—Weaviate will handle embedding automatically.

1. **Install the library:**
   ```bash
   pip install -U sentence-transformers
   ```

2. **Load and use a model:**
   ```python
   from sentence_transformers import SentenceTransformer

   # Choose your model here
   model = SentenceTransformer('sentence-transformers/all-MiniLM-L12-v2')

   sentences = ["This is an example sentence", "Each sentence is converted"]
   embeddings = model.encode(sentences)
   print(embeddings)
   ```

3. **Switching Models:**
   - Just change the model name in the `SentenceTransformer(...)` call to any from the table above.

---

## 📚 References

- [Sentence-Transformers Documentation](https://www.sbert.net/)
- [All Models on HuggingFace](https://huggingface.co/sentence-transformers)

---

**Happy embedding!** 🚀 