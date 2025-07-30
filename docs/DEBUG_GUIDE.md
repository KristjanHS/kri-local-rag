# Debug Guide

## Common Issues and Solutions

### PyTorch FutureWarning: `encoder_attention_mask` is deprecated

**Symptoms:**
```
FutureWarning: `encoder_attention_mask` is deprecated and will be removed in version 4.55.0 for `BertSdpaSelfAttention.forward`.
```

**Cause:**
This warning appears when loading the sentence transformer model (`all-MiniLM-L6-v2`) due to deprecated PyTorch parameters in the BERT attention mechanism.

**Solutions:**

1. **Suppressed by Default (Recommended):**
   The warning is automatically suppressed in `backend/ingest_pdf.py`. This is the safest approach.

2. **Show Warnings (Debug):**
   ```bash
   # To see the warnings for debugging
   SUPPRESS_TORCH_WARNINGS=false python backend/ingest_pdf.py
   ```

3. **Use Alternative Model:**
   ```python
   # In backend/ingest_pdf.py, change the model to:
   model = SentenceTransformer("sentence-transformers/all-mpnet-base-v2")  # 768d, better quality
   # or
   model = SentenceTransformer("sentence-transformers/multi-qa-MiniLM-L6-cos-v1")  # 384d, similar
   ```

**Note:** This warning doesn't affect functionality - it's just a deprecation notice from PyTorch that will be resolved in future versions of the sentence-transformers library.

---

## Debug Logging Guide for Weaviate Chunks

### Problem
You increased the debug level to 3 in the app but still can't see what chunks Weaviate is giving as response to your prompts.

### Solution

#### 1. Set the Correct Environment Variable

The key is to set `LOG_LEVEL=DEBUG` in your environment. The debug level in the UI only controls the debug parameter passed to functions, but the actual logging level is controlled by the `LOG_LEVEL` environment variable.

**Option A: Set environment variable before running**
```bash
export LOG_LEVEL=DEBUG
docker compose -f docker/docker-compose.yml up
```

**Option B: Create a .env file**
Create a `.env` file in the project root with:
```
LOG_LEVEL=DEBUG
DEBUG_LEVEL=3
```

**Option C: Set in Docker Compose**
Add to your `docker/docker-compose.yml` in the app service:
```yaml
environment:
  - LOG_LEVEL=DEBUG
```

#### 2. What You'll See

With debug logging enabled, you'll see detailed information about each chunk returned by Weaviate:

```
2025-07-30 09:21:42,905 - retriever - DEBUG - Found 3 candidates.
2025-07-30 09:21:42,906 - retriever - DEBUG - Chunk 1:
2025-07-30 09:21:42,906 - retriever - DEBUG -   Distance: 0.1234
2025-07-30 09:21:42,906 - retriever - DEBUG -   Score: 0.8765
2025-07-30 09:21:42,906 - retriever - DEBUG -   Content: This is the actual chunk content from Weaviate...
2025-07-30 09:21:42,906 - retriever - DEBUG -   Content length: 147 characters
```

#### 3. Test the Debug Logging

Run the test script to verify debug logging works:
```bash
docker exec kri-local-rag-app-1 python test_weaviate_debug.py
```

#### 4. Check Your Logs

The debug output will appear in:
- Console output (if running in terminal)
- `logs/rag_system.log` file
- Streamlit app debug area (if using the web interface)

#### 5. Troubleshooting

**If you still don't see debug output:**
1. Make sure `LOG_LEVEL=DEBUG` is set
2. Restart the containers after setting the environment variable
3. Check that you have data in your Weaviate collection
4. Verify the debug parameter is `True` in your function calls

**To check if you have data:**
```bash
curl -s "http://localhost:8080/v1/objects?class=Document&limit=1" | jq .
```

**To ingest test data:**
Use the Streamlit interface or run:
```bash
./scripts/ingest.sh data/
```

### Summary

The issue was that you need to set `LOG_LEVEL=DEBUG` in addition to setting the debug level to 3 in the UI. The UI debug level only controls the `debug=True` parameter, but the actual logging output is controlled by the `LOG_LEVEL` environment variable. 