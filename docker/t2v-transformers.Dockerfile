FROM semitechnologies/transformers-inference:sentence-transformers-all-MiniLM-L6-v2

# Install curl so the healthcheck command can run
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# The Weaviate registry doesn’t have a pre-built image whose tag matches nomic-ai-nomic-embed-text-v1.5
# You can verify by listing the tags available:
# https://cr.weaviate.io/v2/semitechnologies/transformers-inference/tags/list
# FROM cr.weaviate.io/semitechnologies/transformers-inference:sentence-transformers-all-MiniLM-L6-v2

# Solution: reuse the custom weaviate image and tell it which HF model to download at start-up
#FROM cr.weaviate.io/semitechnologies/transformers-inference:custom
# tell the entrypoint to fetch the Nomic model
# ENV MODEL_NAME="nomic-ai/nomic-embed-text-v1.5"

# Install specific torch version optimized for CUDA 12.8 (RTX 30–series)
# Explanation: "--no-cache-dir" inside Docker layers prevents the wheel cache from bloating the image
#RUN pip install --no-cache-dir --progress=plain --upgrade \
#    torch==2.7.1+cu128 \
#    --extra-index-url https://download.pytorch.org/whl/cu128


# I NEVER GOT THIS TO WORK - every time i tried to run docker compose up, 
# it would fail with t2v-transformers-1 exited with code 0
# Add wrapper that converts Docker secret into environment variable
# COPY docker-entrypoint.sh /docker-entrypoint.sh
#RUN chmod +x /docker-entrypoint.sh

# Use wrapper as entrypoint, forwarding any arguments to the original CMD
#ENTRYPOINT ["/docker-entrypoint.sh"]