"""RAG orchestration: answer(), prompt building, cross-encoder re-ranking, and the
shared Weaviate readiness/bootstrap (also used by the Streamlit frontend).

The CLI entrypoint (argparse, interactive loop, readiness driver) lives in the
repo-root `cli.py` — this module is no longer invoked directly."""

# External libraries
from __future__ import annotations

import os
import threading
from dataclasses import dataclass
from typing import Any, Callable, List, Optional, Tuple

# Local .py imports
from backend.config import OLLAMA_MODEL, get_logger
from backend.models import load_reranker
from backend.ollama_client import generate_response
from backend.retriever import get_top_k

# Set up logging for this module
logger = get_logger(__name__)


# Constants
MAX_RETRIES = 3


# ---------- cross-encoder helpers --------------------------------------------------
@dataclass
class ScoredChunk:
    """A context *chunk* paired with its relevance *score*."""

    text: str
    score: float


# Note: Do not eagerly check/import heavy deps at module import time. We'll lazily
# attempt to import inside the getter and gracefully fall back if unavailable.

# Keep Ollama context tokens between calls so the model retains conversation state
_ollama_context: list[int] | None = None

# ✅ Re-ranking of retrieved chunks implemented below using a cross-encoder (sentence-transformers).


# ---------- Cross-encoder helpers --------------------------------------------------
def _get_cross_encoder() -> Any:
    """Return a cached CrossEncoder instance using the offline-first loader."""
    try:
        return load_reranker()
    except Exception as e:
        logger.error("Failed to load CrossEncoder model: %s", e)
        return None


def _score_chunks(question: str, chunks: List[str], cross_encoder: Any) -> List[ScoredChunk]:
    """Return *chunks* each paired with a relevance score for *question*.

    Uses CrossEncoder for scoring. Raises RuntimeError if CrossEncoder is not available.
    """
    if cross_encoder is None:
        raise RuntimeError("CrossEncoder model is not available. Ensure the model is downloaded and accessible.")

    logger.debug("Scoring chunks using cross-encoder.")
    pairs: List[Tuple[str, str]] = [(question, c) for c in chunks]
    scores = cross_encoder.predict(pairs)  # logits, pos > relevant
    return [ScoredChunk(text=c, score=float(s)) for c, s in zip(chunks, scores)]


# ---------- Reranking of retrieved chunks --------------------------------------------------
def _rerank(question: str, chunks: List[str], k_keep: int, cross_encoder: Any) -> List[ScoredChunk]:
    """Return the top *k_keep* chunks from *chunks* after re-ranking by relevance to *question*."""

    if not chunks:
        return []

    # Score all chunks
    scored_chunks = _score_chunks(question, chunks, cross_encoder)

    # Sort by score (higher = more relevant) and keep top k
    scored_chunks.sort(key=lambda sc: sc.score, reverse=True)
    return scored_chunks[:k_keep]


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
    embedding_model: Optional[Any] = None,
    cross_encoder: Optional[Any] = None,
    k: int = 3,
    *,
    on_token: Optional[Callable[[str], None]] = None,
    on_debug: Optional[Callable[[str], None]] = None,
    stop_event: Optional[threading.Event] = None,
    context_tokens: int = 8192,
    collection_name: Optional[str] = None,
) -> str:
    """Return an answer from the LLM using RAG, streaming raw tokens via *on_token*.

    Pure orchestration: retrieve → re-rank → build prompt → generate. All user-facing
    presentation (the "Answer: " banner, the streaming display, trailing newline) lives
    in the caller — ``cli.py`` for the CLI, ``frontend/rag_app.py`` for the UI — so this
    function never touches the console. When *on_token* is supplied, every user-facing
    string (including the no-context message) is emitted through it. The fake-answer test
    hook also lives in the presentation layers, not here. Interruptible via *stop_event*.

    LLM-stream diagnostics are forwarded to *on_debug* when supplied (the UI debug panel);
    file/console logging is unaffected.
    """

    global _ollama_context

    # Lazily load the cross-encoder when the caller didn't supply one (e.g. the CLI
    # entrypoint), so answer() is self-sufficient for the real RAG path. Frontend and
    # tests pass an explicit cross_encoder, so this branch is CLI-only.
    if cross_encoder is None:
        cross_encoder = _get_cross_encoder()

    # ---------- 1) Retrieve -----------------------------------------------------
    # Ask vector DB for more than we eventually keep to improve re-ranking quality
    initial_k = k * 20
    candidates = get_top_k(
        question,
        k=initial_k,
        embedding_model=embedding_model,
        collection_name=collection_name,
    )
    if not candidates:
        msg = "I found no relevant context to answer that question. The database may be empty. Ingest a PDF first."
        if on_token is not None:
            on_token(msg)
        return msg

    # ---------- 2) Re-rank ------------------------------------------------------
    logger.debug("Re-ranking the top %d candidates...", len(candidates))
    scored_chunks = _rerank(question, candidates, k_keep=k, cross_encoder=cross_encoder)

    logger.debug("Reranked context chunks:")
    for idx, sc in enumerate(scored_chunks, 1):
        preview = sc.text.replace("\n", " ")[:120]
        logger.debug(" %02d. score=%.4f | %s…", idx, sc.score, preview)

    # Extract plain texts for prompt construction.
    context_chunks = [sc.text for sc in scored_chunks]

    # ---------- 3) Prepare the prompt and payload -------------------------------------------------
    prompt_text = build_prompt(question, context_chunks)
    logger.debug("Prompt being sent to Ollama (%d chars, %d chunks)", len(prompt_text), len(context_chunks))

    # ---------- 4) Query the LLM -------------------------------------------------
    logger.debug("About to call generate_response with model=%s context_tokens=%d", OLLAMA_MODEL, context_tokens)
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

    # Single leading-whitespace trim of the returned text. Display-side trimming of the
    # first streamed token is the caller's concern (see cli.py._print_streamed_answer).
    return answer_text.lstrip()


# ---------- Backend readiness / first-run bootstrap (shared with the Streamlit frontend) ----------
from backend import config as app_config
from backend.config import get_service_url
from backend.weaviate_client import close_weaviate_client, ensure_collection, get_weaviate_client


def ensure_weaviate_ready_and_populated():
    client = None
    try:
        # Resolve settings and get centralized client
        weaviate_url = get_service_url("weaviate")
        collection_name = os.getenv("COLLECTION_NAME", app_config.COLLECTION_NAME)
        client = get_weaviate_client()
        logger.debug("1. Attempting to connect to Weaviate at %s...", weaviate_url)
        client.is_ready()  # Raises if not ready
        logger.debug("   ✓ Connection successful.")

        # Check if collection exists; create an empty schema if it's missing.
        logger.debug("2. Checking if collection '%s' exists...", collection_name)
        if not client.collections.exists(collection_name):
            # First-time setup: create the empty collection schema only. The embedder and
            # other heavy modules load lazily on the first real query (load_embedder is an
            # idempotent in-process cache), so there is no need to "warm" them by ingesting
            # example_data/test.pdf and immediately deleting it — that round-trip only ran on
            # a fresh DB and added zero steady-state benefit. Creating the schema is all the
            # bootstrap owes the user.
            logger.info("   → Collection does not exist. Creating empty collection schema...")
            ensure_collection(client, collection_name)
            return

        # If the collection already exists, we do nothing. This avoids checking if it's empty
        # and re-populating, which could be slow on large user databases.
        logger.info("   ✓ Collection '%s' exists.", collection_name)
    finally:
        try:
            close_weaviate_client()
        except Exception as e:
            logger.debug("Failed to close Weaviate client gracefully: %s", e)


# NOTE: The CLI entrypoint (argparse, interactive loop, readiness driver, sys.exit)
# now lives in the repo-root `cli.py`. `qa_loop.py` is pure orchestration + the shared
# readiness/bootstrap above (also imported by the Streamlit frontend). See the A2
# resolution in docs/plans/2026-06-24-complexity-hotspots-simplification.md.
