**Need the right Weaviate transformers Docker image for your local GPU?**

Follow this step-by-step guide to pick (and run) the tag that best matches your use-case, GPU memory budget, and language requirements.

---

## 0  Quick decision cheat-sheet

| Goal                                                | Recommended tag                                               | VRAM (fp16/ONNX)                              | Languages |
| --------------------------------------------------- | ------------------------------------------------------------- | --------------------------------------------- | --------- |
| Highest recall, hybrid dense-multi-sparse retrieval | `baai-bge-m3-onnx`                                            | ≈ 4 GB fp16 (≈ 2 GB ONNX) ([Hugging Face][1]) | 100 +     |
| Fast English-only search, lightest footprint        | `sentence-transformers-all-MiniLM-L6-v2-onnx`                 | < 1 GB ([Hugging Face][2])                    | en        |
| Question/answer corpora, tiny model                 | `sentence-transformers-multi-qa-MiniLM-L6-cos-v1`             | < 1 GB ([Hugging Face][3])                    | en        |
| Multilingual under 2 GB                             | `sentence-transformers-paraphrase-multilingual-MiniLM-L12-v2` | ≈ 1.6 GB ([Hugging Face][4])                  | 50 +      |

> **Why these four?** They are the officially pre-baked images shipped by Weaviate’s `semitechnologies/transformers-inference` repo, tested against CUDA 12 and the `text2vec-transformers` module. ([GitHub][5], [GitHub][5])

---

## 1  Prerequisites

1. **GPU driver ≥ 535** — supports CUDA 12.x used in the images. ([Weaviate Docs][6])
2. **Docker 24 + NVIDIA Container Toolkit** – grants containers access to the RTX 3070’s 8 GB VRAM. ([Weaviate Docs][6])
3. **Compose file** (or `docker run`) with `ENABLE_CUDA=1`; that env-var flips the inference server to GPU mode. ([Weaviate Docs][7])

---

## 2  Understand the tags

### 2.1  `baai-bge-m3-onnx`

* 560 M-parameter **BGE-M3** model; supports dense, sparse and multi-vector retrieval. ([GitHub][8])
* Packaged as an **ONNX** graph, executed by ONNX Runtime → -10-30 % latency vs PyTorch on NVIDIA GPUs. ([Dev Kit][9])
* Needs \~4 GB fp16 but only \~2 GB when ONNX weight-compressed, fitting alongside a small LLM on an 8 GB card. ([Hugging Face][1])

### 2.2  MiniLM family (`all-MiniLM-L6` & `multi-qa-MiniLM-L6`)

* 22 M parameters, 384-D vectors – tiny and fast. ([Hugging Face][2])
* `multi-qa` fine-tuned on 215 M Q-A pairs – higher passage-ranking accuracy than the generic MiniLM. ([Hugging Face][3])

### 2.3  `paraphrase-multilingual-MiniLM-L12-v2`

* 118 M parameters, covers 50 + languages with decent English performance. ([Hugging Face][4])

---

## 3  Choose with a four-question checklist

1. **Do you need hybrid retrieval (BM25 + dense + sparse)?**
   → pick **BGE-M3**. ([GitHub][8])
2. **Is sub-20 ms embedding latency critical and corpus is English?**
   → pick **all-MiniLM-L6-v2-onnx**. ([Hugging Face][2])
3. **Are you indexing Q-A style documents?**
   → choose **multi-qa-MiniLM-L6-cos-v1** for higher hit-rates. ([Hugging Face][3])
4. **Need multilingual search but must stay < 2 GB VRAM?**
   → go **paraphrase-multilingual-MiniLM-L12-v2**. ([Hugging Face][4])

---

## 4  Pull & run the image (example: BGE-M3)

```bash
docker run -d --gpus all \
  -e ENABLE_CUDA=1 \
  -p 8080:8080 \
  semitechnologies/transformers-inference:baai-bge-m3-onnx
```

*The container already contains the model; no `MODEL_NAME` override required.* ([GitHub][10])

---

## 5  Wire Weaviate to the inference container

```yaml
services:
  weaviate:
    image: semitechnologies/weaviate:1.25.7
    environment:
      ENABLE_MODULES: text2vec-transformers
      TRANSFORMERS_INFERENCE_API: "http://vectorizer:8080"
      WEAVIATE_DEFAULT_VECTORIZER_MODULE: text2vec-transformers
  vectorizer:
    image: semitechnologies/transformers-inference:baai-bge-m3-onnx
    deploy:
      resources:
        reservations:
          devices:
            - capabilities: [gpu]
    environment:
      ENABLE_CUDA: "1"
```

*This pattern is the same for every tag – just swap the `image:` line.* ([GitHub][11])

---

## 6  Validate GPU usage

```bash
docker exec -it <container-id> nvidia-smi
```

You should see the image name and \~2 – 4 GB memory usage, confirming CUDA kernels are active. An RTX 3070 has exactly 8 GB GDDR6, so remaining headroom indicates how many additional services you can run concurrently. ([TechPowerUp][12])

---

## 7  When to fall back to `:custom`

If you someday need a **different** model (e.g. `nomic-embed-text-v1.5`) or a bleeding-edge PyTorch build, derive from the `:custom` tag and set `MODEL_NAME=<your-model>` in the Dockerfile, as shown in Weaviate’s official README. ([GitHub][10])

---

## 8  Key take-aways

* **Use an off-the-shelf tag whenever possible** – zero build effort, maintained by Weaviate. ([GitHub][5])
* **Match VRAM to tag** – BGE-M3 for recall, MiniLMs for speed, multilingual MiniLM-L12 when language coverage trumps English quality.
* **Always set `ENABLE_CUDA=1`** and expose port 8080; Weaviate discovers the GPU automatically via the env-var. ([Weaviate Docs][7])

With these steps, you’ll have a GPU-powered Weaviate vectorizer tuned perfectly to your RTX 3070 in minutes—no custom builds required.

[1]: https://huggingface.co/BAAI/bge-m3/discussions/64?utm_source=chatgpt.com "BAAI/bge-m3 · [AUTOMATED] Model Memory Requirements"
[2]: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2?utm_source=chatgpt.com "sentence-transformers/all-MiniLM-L6-v2 · Hugging Face"
[3]: https://huggingface.co/sentence-transformers/multi-qa-MiniLM-L6-cos-v1?utm_source=chatgpt.com "sentence-transformers/multi-qa-MiniLM-L6-cos-v1 · Hugging Face"
[4]: https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2?utm_source=chatgpt.com "paraphrase-multilingual-MiniLM-L12-v2 - Hugging Face"
[5]: https://github.com/weaviate/t2v-transformers-models?utm_source=chatgpt.com "GitHub - weaviate/t2v-transformers-models: This is the repo for the ..."
[6]: https://docs.weaviate.io/deploy/installation-guides/docker-installation?utm_source=chatgpt.com "Docker | Weaviate Documentation"
[7]: https://docs.weaviate.io/deploy/configuration/env-vars?utm_source=chatgpt.com "Environment variables | Weaviate Documentation"
[8]: https://github.com/liuyanyi/transformers-bge-m3?utm_source=chatgpt.com "GitHub - liuyanyi/transformers-bge-m3"
[9]: https://dev-kit.io/blog/machine-learning/onnx-vs-pytorch-speed-comparison?utm_source=chatgpt.com "ONNX vs PyTorch Speed: In-Depth Performance Comparison - Dev-kit"
[10]: https://github.com/weaviate/t2v-transformers-models/blob/main/README.md?utm_source=chatgpt.com "t2v-transformers-models/README.md at main - GitHub"
[11]: https://github.com/weaviate/weaviate-io/blob/main/developers/weaviate/model-providers/transformers/embeddings.md?utm_source=chatgpt.com "weaviate-io/developers/weaviate/model-providers/transformers ... - GitHub"
[12]: https://www.techpowerup.com/gpu-specs/geforce-rtx-3070.c3674?utm_source=chatgpt.com "NVIDIA GeForce RTX 3070 Specs | TechPowerUp GPU Database"
