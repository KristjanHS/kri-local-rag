#!/usr/bin/env python3
"""Interactive console for Retrieval-Augmented Generation."""

# External libraries
from __future__ import annotations
import sys
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any

# Local .py imports
from config import OLLAMA_MODEL
from retriever import get_top_k
from ollama_client import test_ollama_connection, generate_response, set_debug_level


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
    on_token=None,
    on_debug=None,
    stop_event=None,
    context_tokens: int = 8192,
) -> str:
    """Return an answer from the LLM using RAG with optional debug output and streaming callbacks.
    Can be interrupted with stop_event.
    """

    global _ollama_context

    # ---------- 1) Retrieve -----------------------------------------------------
    initial_k = max(k * 20, 100)  # ask vector DB for more than we eventually keep
    candidates = get_top_k(question, k=initial_k, debug=debug, metadata_filter=metadata_filter)
    if not candidates:
        return "I found no relevant context to answer that question."

    # ---------- 2) Re-rank ------------------------------------------------------
    scored_chunks = _rerank(question, candidates, k_keep=k, debug=debug)

    if debug:
        msg = "\n[Debug] Reranked context chunks:"
        if on_debug:
            on_debug(msg)
        else:
            print(msg)
        for idx, sc in enumerate(scored_chunks, 1):
            preview = sc.text.replace("\n", " ")[:120]
            msg = f" {idx:02d}. score={sc.score:.4f} | {preview}…"
            if on_debug:
                on_debug(msg)
            else:
                print(msg)

    # Extract plain texts for prompt construction.
    context_chunks = [sc.text for sc in scored_chunks]

    # ---------- 3) Prepare the prompt and payload -------------------------------------------------
    prompt_text = build_prompt(question, context_chunks)

    # ---------- 4) Query the LLM -------------------------------------------------
    answer_text, updated_context = generate_response(
        prompt_text,
        OLLAMA_MODEL,
        _ollama_context,
        on_token=on_token,
        on_debug=on_debug,
        stop_event=stop_event,
        context_tokens=context_tokens,
    )

    # Update context for next interaction
    _ollama_context = updated_context

    return answer_text


# ---------- CLI --------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Interactive RAG console with optional metadata filtering.")
    parser.add_argument("--source", help="Filter chunks by source field (e.g. 'pdf')")
    parser.add_argument("--language", help="Filter chunks by detected language code (e.g. 'en', 'et')")
    parser.add_argument("--k", type=int, default=3, help="Number of top chunks to keep after re-ranking")
    parser.add_argument(
        "--debug-level",
        type=int,
        default=2,
        choices=[0, 1, 2, 3],
        help="Debug level: 0=off, 1=basic, 2=detailed, 3=verbose (default: 1)",
    )
    args = parser.parse_args()

    # Set debug level
    set_debug_level(args.debug_level)

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

    # Run Ollama connection test before starting
    if not test_ollama_connection():
        print("Failed to establish Ollama connection. Please check your setup.")
        sys.exit(1)

    print("\nReady for questions!")
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
