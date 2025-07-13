#!/usr/bin/env python3
"""Interactive console for Retrieval-Augmented Generation."""

# External libraries
from __future__ import annotations
import sys
import httpx  # For catching connection errors
import requests
import json
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any

# Local .py imports
from config import OLLAMA_MODEL, OLLAMA_URL
from retriever import get_top_k
from windows_ip_in_wsl import get_windows_host_ip


# ---------- cross-encoder helpers --------------------------------------------------
@dataclass
class ScoredChunk:
    """A context *chunk* paired with its relevance *score*."""

    text: str
    score: float


# Try to import a cross-encoder model for re-ranking retrieved chunks
try:
    from sentence_transformers import CrossEncoder  # type: ignore
except ImportError:  # pragma: no cover – optional dependency
    CrossEncoder = None  # type: ignore

# Cache the cross-encoder instance after first load to avoid re-loading on every question
_cross_encoder: "CrossEncoder | None" = None  # type: ignore

# Keep Ollama context tokens between calls so the model retains conversation state
_ollama_context: list[int] | None = None

# ✅ Re-ranking of retrieved chunks implemented below using a cross-encoder (sentence-transformers).


# ---------- Ollama helpers --------------------------------------------------
def _get_ollama_base_url() -> str:
    """Return the Ollama base URL accessible from WSL.

    Prefers the Windows host IP if available, otherwise falls back to the
    default URL from config.
    """
    ip = get_windows_host_ip()
    if ip:
        return f"http://{ip}:11434"
    return OLLAMA_URL


'''
def _detect_ollama_model() -> str | None:
    """Return the first available model reported by the Ollama server or None."""
    try:
        # /api/tags lists all pulled models
        base_url = _get_ollama_base_url()
        resp = httpx.get(f"{base_url.rstrip('/')}/api/tags", timeout=2)
        resp.raise_for_status()
        models = resp.json().get("models", [])
        if models:
            # The endpoint returns a list of objects; each has a `name` field.
            return models[0].get("name")
    except Exception:
        # Any issue (network, JSON, etc.) – silently ignore and let caller fall back.
        pass
    return None
'''


# ---------- Cross-encoder helpers --------------------------------------------------
def _get_cross_encoder(model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
    """Return a (cached) CrossEncoder instance or ``None`` if the library is unavailable.

    If ``sentence_transformers`` is not installed, the function returns ``None`` so that the
    calling code can gracefully fall back to vector-search ordering.
    """
    global _cross_encoder
    if CrossEncoder is None:
        return None
    if _cross_encoder is None:
        try:
            _cross_encoder = CrossEncoder(model_name)
        except Exception:
            # Any issue loading the model (e.g. no internet) – skip re-ranking.
            _cross_encoder = None
    return _cross_encoder


# ---------- Scoring of retrieved chunks --------------------------------------------------
def _score_chunks(question: str, chunks: List[str], debug: bool = False) -> List[ScoredChunk]:
    """Return *chunks* each paired with a relevance score for *question*."""

    encoder = _get_cross_encoder()

    if encoder is None and debug:
        print("[Debug] Cross-encoder unavailable – falling back to neutral scores.")

    if encoder is None:
        # No re-ranker available – every chunk gets a neutral score of 0.
        return [ScoredChunk(text=c, score=0.0) for c in chunks]

    try:
        pairs: List[Tuple[str, str]] = [(question, c) for c in chunks]
        scores = encoder.predict(pairs)  # logits, pos > relevant
    except Exception:
        # If inference fails we fall back to neutral scores as well.
        return [ScoredChunk(text=c, score=0.0) for c in chunks]

    return [ScoredChunk(text=c, score=float(s)) for c, s in zip(chunks, scores)]


# ---------- Reranking of retrieved chunks --------------------------------------------------
def _rerank(question: str, chunks: List[str], k_keep: int, debug: bool = False) -> List[ScoredChunk]:
    """Return the *k_keep* most relevant chunks for *question*, sorted by score."""

    scored = _score_chunks(question, chunks, debug)
    scored.sort(key=lambda sc: sc.score, reverse=True)
    return scored[:k_keep]


# ---------- Prompt building --------------------------------------------------
def build_prompt(question: str, context_chunks: list[str]) -> str:
    context = "\n\n".join(context_chunks)
    prompt = (
        "You are a helpful assistant who answers strictly from the provided context.\n\n"
        f'Context:\n"""\n{context}\n"""\n\n'
        f"Question: {question}\nAnswer:"
    )
    return prompt


# ---------- Answer generation --------------------------------------------------
def answer(
    question: str,
    k: int = 3,
    *,
    debug: bool = False,
    metadata_filter: Optional[Dict[str, Any]] = None,
) -> str:
    """Return an answer from the LLM using RAG with optional debug output."""

    global _ollama_context

    # ---------- 1) Retrieve -----------------------------------------------------
    initial_k = max(k * 20, 100)  # ask vector DB for more than we eventually keep
    candidates = get_top_k(question, k=initial_k, debug=debug, metadata_filter=metadata_filter)
    if not candidates:
        return "I found no relevant context to answer that question."

    # ---------- 2) Re-rank ------------------------------------------------------
    scored_chunks = _rerank(question, candidates, k_keep=k, debug=debug)

    if debug:
        print("\n[Debug] Reranked context chunks:")
        for idx, sc in enumerate(scored_chunks, 1):
            preview = sc.text.replace("\n", " ")[:120]
            print(f" {idx:02d}. score={sc.score:.4f} | {preview}…")

    # Extract plain texts for prompt construction.
    context_chunks = [sc.text for sc in scored_chunks]

    # ---------- 3) Prepare the prompt and payload -------------------------------------------------
    prompt_text = build_prompt(question, context_chunks)

    model_name = OLLAMA_MODEL
    # alternative: use the first available model from the server
    # model_name = _detect_ollama_model() or OLLAMA_MODEL
    base_url = _get_ollama_base_url()
    # Use the native Ollama generate endpoint which streams newline-delimited JSON
    url = f"{base_url.rstrip('/')}/api/generate"

    payload: dict[str, object] = {
        "model": model_name,
        "prompt": prompt_text,
        "stream": True,
        # You can tweak generation params here as desired.
    }
    if _ollama_context is not None:
        payload["context"] = _ollama_context

    # ---------- 4) Query the LLM -------------------------------------------------
    answer_text = ""
    try:
        resp = requests.post(url, json=payload, timeout=None, stream=True)
        for raw_chunk in resp.iter_lines():
            if not raw_chunk:
                continue

            # Ollama sends newline-separated JSON objects. Some builds prefix each
            # line with "data: " (SSE style) – strip it if present.
            line = raw_chunk.decode().strip()
            if line.startswith("data:"):
                line = line[len("data:") :].strip()

            # End-of-stream marker used by OpenAI-compatible endpoints.
            if line == "[DONE]":
                break

            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                # Skip malformed lines instead of crashing the whole loop.
                continue

            # The token field differs across Ollama endpoints / versions → handle all known keys.
            token_str: str = (
                data.get("response")
                or data.get("token")
                or (data.get("choices", [{}])[0].get("text") if "choices" in data else "")
            )

            answer_text += token_str
            sys.stdout.write(token_str)
            sys.stdout.flush()

            # Capture the conversation context if provided with the final chunk.
            if data.get("done"):
                _ollama_context = data.get("context", _ollama_context)
                break

        return answer_text or "(no response)"
    except (requests.exceptions.RequestException, httpx.HTTPError, httpx.ConnectError, ConnectionError):
        return "[Ollama server not reachable – please ensure it is running on the configured URL]"
    except Exception as exc:
        return f"[Unexpected error while querying Ollama: {exc}]"


# ---------- CLI --------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Interactive RAG console with optional metadata filtering.")
    parser.add_argument("--source", help="Filter chunks by source field (e.g. 'pdf')")
    parser.add_argument("--language", help="Filter chunks by detected language code (e.g. 'en', 'et')")
    parser.add_argument("--k", type=int, default=3, help="Number of top chunks to keep after re-ranking")
    args = parser.parse_args()

    # Build metadata filter dict (AND-combination of provided fields)
    meta_filter: Optional[Dict[str, Any]] = None
    if args.source or args.language:
        clauses = []
        if args.source:
            clauses.append({"path": ["source"], "operator": "Equal", "valueText": args.source})
        if args.language:
            clauses.append({"path": ["language"], "operator": "Equal", "valueText": args.language})

        if len(clauses) == 1:
            meta_filter = clauses[0]
        else:
            meta_filter = {"operator": "And", "operands": clauses}

    print("RAG console – type a question, Ctrl-D/Ctrl-C to quit")
    try:
        for line in sys.stdin:
            q = line.strip()
            if not q:
                continue

            sys.stdout.write("→ ")
            sys.stdout.flush()

            answer(q, k=args.k, debug=True, metadata_filter=meta_filter)

            print("\n")
    except (EOFError, KeyboardInterrupt):
        pass
