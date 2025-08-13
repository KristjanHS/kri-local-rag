#!/usr/bin/env python3
"""RAG CLI: Interactive console for Retrieval-Augmented Generation."""

# External libraries
from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# Local .py imports
from backend.config import OLLAMA_MODEL
from backend.console import console, get_logger
from backend.ollama_client import ensure_model_available, generate_response
from backend.retriever import get_top_k

# Set up logging for this module
logger = get_logger(__name__)


# ---------- cross-encoder helpers --------------------------------------------------
@dataclass
class ScoredChunk:
    """A context *chunk* paired with its relevance *score*."""

    text: str
    score: float


# Note: Do not eagerly check/import heavy deps at module import time. We'll lazily
# attempt to import inside the getter and gracefully fall back if unavailable.

# Cross-encoder is optional and heavy; import lazily inside the getter.
# Provide a patch seam for tests.
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
    # Lazily attempt to import the cross-encoder implementation; if unavailable, return None.

    # Determine constructor: prefer patched module-level `CrossEncoder` if provided
    ctor = CrossEncoder
    if ctor is None:
        try:
            from sentence_transformers import CrossEncoder as _CE  # type: ignore

            ctor = _CE
        except Exception:
            return None
    if _cross_encoder is None:
        try:
            _cross_encoder = ctor(model_name)
            # Apply PyTorch CPU optimizations (skip in testing environments)
            # New preferred flag: RERANKER_CROSS_ENCODER_OPTIMIZATIONS (true enables opts)
            enable_opts_str = os.getenv("RERANKER_CROSS_ENCODER_OPTIMIZATIONS", "true").lower()
            enable_opts = enable_opts_str == "true"
            skip_optimization = ("pytest" in sys.modules) or (not enable_opts)

            if not skip_optimization:
                # Set optimal threading for current environment
                try:
                    import torch  # defer heavy import

                    torch.set_num_threads(12)  # Oversubscribe lightly to hide I/O stalls
                except Exception as _threads_e:  # noqa: F841
                    pass
                # Apply torch.compile with max-autotune for 5-25% speed-ups on CPU GEMM-heavy models
                try:
                    import torch  # defer heavy import

                    logger.info("torch.compile: optimizing cross-encoder – first run may take ~1 min…")
                    _cross_encoder = torch.compile(_cross_encoder, backend="inductor", mode="max-autotune")
                    logger.info("torch.compile optimization completed for cross-encoder")
                except Exception as compile_e:
                    logger.warning("Failed to apply torch.compile optimization to cross-encoder: %s", compile_e)
            else:
                logger.debug("Skipping torch optimizations (test environment detected)")

        except Exception:
            # Any issue loading the model (e.g. no internet) – skip re-ranking.
            _cross_encoder = None
    return _cross_encoder


# ---------- Scoring of retrieved chunks --------------------------------------------------
def _score_chunks(question: str, chunks: List[str]) -> List[ScoredChunk]:
    """Return *chunks* each paired with a relevance score for *question*."""

    # Strategy 1: Try cross-encoder (best quality)
    try:
        encoder = _get_cross_encoder()
        if encoder is not None:
            logger.debug("Attempting cross-encoder scoring.")
            pairs: List[Tuple[str, str]] = [(question, c) for c in chunks]
            scores = encoder.predict(pairs)  # logits, pos > relevant
            return [ScoredChunk(text=c, score=float(s)) for c, s in zip(chunks, scores)]
        else:
            # This is a controlled fallback, not an exception.
            logger.warning("Cross-encoder model not available, falling back.")
            raise RuntimeError("Encoder not available")
    except Exception as e:
        logger.warning(f"Cross-encoder scoring failed: {e}, falling back to keyword overlap.")

    # Strategy 2: Fallback to keyword overlap
    try:
        logger.debug("Attempting keyword overlap scoring.")

        def preprocess(text: str) -> set:
            words = re.findall(r"\b\w+\b", text.lower())
            return set(words)

        question_words = preprocess(question)
        scored_chunks = []
        for chunk in chunks:
            chunk_words = preprocess(chunk)
            intersection = len(question_words.intersection(chunk_words))
            union = len(question_words.union(chunk_words))
            score = max(0.0, intersection / union if union > 0 else 0.0)
            scored_chunks.append(ScoredChunk(text=chunk, score=score))
        return scored_chunks
    except Exception as e:
        logger.error(f"Keyword overlap scoring failed: {e}. Returning neutral scores.")

    # Final fallback: neutral scores
    return [ScoredChunk(text=c, score=0.0) for c in chunks]


# ---------- Reranking of retrieved chunks --------------------------------------------------
def _rerank(question: str, chunks: List[str], k_keep: int) -> List[ScoredChunk]:
    """Return the top *k_keep* chunks from *chunks* after re-ranking by relevance to *question*."""

    if not chunks:
        return []

    # Score all chunks
    scored_chunks = _score_chunks(question, chunks)

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
    k: int = 3,
    *,
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

    # Test hook: deterministic fake answer (used by CLI/UI e2e tests)
    fake_answer = os.getenv("RAG_FAKE_ANSWER")
    if fake_answer is not None:
        # Stream tokens if a callback is provided to emulate real-time output
        if on_token is not None:
            for ch in fake_answer:
                if stop_event is not None and stop_event.is_set():
                    break
                on_token(ch)
        return fake_answer

    # ---------- 1) Retrieve -----------------------------------------------------
    # Ask vector DB for more than we eventually keep to improve re-ranking quality
    initial_k = k * 20
    candidates = get_top_k(question, k=initial_k, metadata_filter=metadata_filter)
    if not candidates:
        return "I found no relevant context to answer that question. The database may be empty. Ingest a PDF first."

    # ---------- 2) Re-rank ------------------------------------------------------
    logger.debug("Re-ranking the top %d candidates...", len(candidates))
    scored_chunks = _rerank(question, candidates, k_keep=k)

    logger.debug("Reranked context chunks:")
    for idx, sc in enumerate(scored_chunks, 1):
        preview = sc.text.replace("\n", " ")[:120]
        logger.debug(" %02d. score=%.4f | %s…", idx, sc.score, preview)

    # Extract plain texts for prompt construction.
    context_chunks = [sc.text for sc in scored_chunks]

    # ---------- 3) Prepare the prompt and payload -------------------------------------------------
    prompt_text = build_prompt(question, context_chunks)
    logger.debug("Prompt being sent to Ollama:")
    logger.debug(prompt_text)

    # ---------- 4) Query the LLM -------------------------------------------------
    # Use a simple print callback for CLI debug mode
    def cli_on_debug(msg):
        logger.debug("[Ollama Debug] %s", msg)

    # Collect tokens for CLI output
    collected_tokens = []
    first_token_processed = False

    def cli_on_token(token):
        nonlocal first_token_processed

        # Trim leading whitespace from the first token only
        if not first_token_processed:
            token = token.lstrip()
            first_token_processed = True

        # Only output if token has content (avoid empty first tokens)
        if token:
            collected_tokens.append(token)
            # Print tokens immediately for better UX
            console.print(token, end="")

    if on_debug is None:
        on_debug = cli_on_debug
    if on_token is None:
        on_token = cli_on_token

    # Show "Answer: " before streaming starts (for CLI mode)
    if on_token is not None:
        console.print("Answer: ", end="")

    answer_text, updated_context = generate_response(
        prompt_text,
        OLLAMA_MODEL,
        _ollama_context,
        on_token=on_token,
        on_debug=on_debug,
        stop_event=stop_event,
        context_tokens=context_tokens,
    )

    # Add newline after streaming completes to position cursor properly
    if on_token is not None:
        console.print()

    # Update context for next interaction
    _ollama_context = updated_context

    # Ensure no leading whitespace in the final answer
    return answer_text.lstrip()


# ---------- CLI --------------------------------------------------
import argparse
from urllib.parse import urlparse

import weaviate
from weaviate.classes.query import Filter
from weaviate.exceptions import WeaviateConnectionError

from backend.config import COLLECTION_NAME, WEAVIATE_URL


def ensure_weaviate_ready_and_populated():
    logger.info("--- Checking Weaviate status and collection ---")
    client = None  # explicit reference to avoid dynamic locals()/globals() access
    try:
        parsed_url = urlparse(WEAVIATE_URL)
        http_host = parsed_url.hostname or "localhost"
        grpc_host = parsed_url.hostname or "localhost"
        client = weaviate.connect_to_custom(
            http_host=http_host,
            http_port=parsed_url.port or 80,
            grpc_host=grpc_host,
            grpc_port=50051,
            http_secure=parsed_url.scheme == "https",
            grpc_secure=parsed_url.scheme == "https",
        )
        logger.info("1. Attempting to connect to Weaviate at %s...", WEAVIATE_URL)
        client.is_ready()  # Raises if not ready
        logger.info("   ✓ Connection successful.")

        # Check if collection exists
        logger.info("2. Checking if collection '%s' exists...", COLLECTION_NAME)
        if not client.collections.exists(COLLECTION_NAME):
            # First-time setup: create the collection, ingest examples, then clean up.
            logger.info("   → Collection does not exist. Running one-time initialization...")
            # Defer heavy import to avoid torch initialization during module import
            from backend.ingest import create_collection_if_not_exists, ingest

            create_collection_if_not_exists(client, COLLECTION_NAME)

            # Ingest example data to ensure all modules are warm; hard-fail if it's missing.
            # Get the absolute path to the project root, which is the parent of the 'backend' directory
            project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            logger.debug("Resolved project_root: %s", project_root)
            # Only accept project-root example_data when running outside Docker
            example_data_path = os.path.join(project_root, "example_data")
            logger.debug(
                "Checking example_data_path: %s (exists=%s)",
                example_data_path,
                os.path.isdir(example_data_path),
            )
            if not os.path.isdir(example_data_path):
                raise FileNotFoundError(f"Directory not found: '{example_data_path}'")

            # Prefer a minimal warmup using only the example PDF to avoid heavy markdown deps
            test_pdf_path = os.path.join(example_data_path, "test.pdf")
            if not os.path.isfile(test_pdf_path):
                raise FileNotFoundError(f"File not found: '{test_pdf_path}'")

            logger.info("   → Ingesting example test PDF from %s", test_pdf_path)
            ingest(test_pdf_path, collection_name=COLLECTION_NAME)

            # Clean up the example data now that the schema is created.
            # This check is important in case the example_data folder was empty.
            try:
                collection = client.collections.use(COLLECTION_NAME)
            except Exception:
                collection = client.collections.get(COLLECTION_NAME)
            # Use the robust iterator method to check for objects
            try:
                next(collection.iterator())
                has_objects = True
            except StopIteration:
                has_objects = False

            if has_objects:
                collection.data.delete_many(where=Filter.by_property("source_file").equal("test.pdf"))
                logger.info("   ✓ Example data removed, leaving a clean collection for the user.")

            return

        # If the collection already exists, we do nothing. This avoids checking if it's empty
        # and re-populating, which could be slow on large user databases.
        logger.info("   ✓ Collection '%s' exists.", COLLECTION_NAME)

    except WeaviateConnectionError:
        raise WeaviateConnectionError(
            "Failed to connect to Weaviate. "
            "Please ensure Weaviate is running and accessible before starting the backend."
        ) from None
    except Exception as e:
        raise Exception(f"An unexpected error occurred during Weaviate check: {e}") from e
    finally:
        try:
            if client is not None and hasattr(client, "is_connected") and client.is_connected():
                client.close()
        except Exception:
            pass
    logger.info("--- Weaviate check complete ---")


def qa_loop(question: str, k: int = 3, metadata_filter: Optional[Dict[str, Any]] = None):
    """
    Perform a single question-answering loop.
    This function is a refactoring of the original __main__ block to be reusable.
    """
    ensure_weaviate_ready_and_populated()

    # Ensure the required Ollama model is available locally before accepting questions
    if not ensure_model_available(OLLAMA_MODEL):
        logger.error("Required Ollama model %s is not available. Exiting.", OLLAMA_MODEL)
        sys.exit(1)

    result = answer(question, k=k, metadata_filter=metadata_filter)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Interactive RAG console with optional metadata filtering.")
    parser.add_argument("--source", help="Filter chunks by source field (e.g. 'pdf')")
    parser.add_argument("--language", help="Filter chunks by detected language code (e.g. 'en', 'et')")
    parser.add_argument("--k", type=int, default=3, help="Number of top chunks to keep after re-ranking")
    parser.add_argument("--question", help="If provided, run a single query and exit.")
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

    if args.question:
        qa_loop(args.question, k=args.k, metadata_filter=meta_filter)
        sys.exit(0)

    # Interactive loop
    ensure_weaviate_ready_and_populated()
    if not ensure_model_available(OLLAMA_MODEL):
        logger.error("Required Ollama model %s is not available. Exiting.", OLLAMA_MODEL)
        sys.exit(1)

    logger.info("💬 RAG console ready – Ask me anything about your documents (Ctrl-D/Ctrl-C to quit)")
    console.print("→ ", end="")
    try:
        for line in sys.stdin:
            q = line.strip()
            if not q:
                # For empty input, just show the prompt again on a new line
                console.print("→ ", end="")
                continue

            result = qa_loop(q, k=args.k, metadata_filter=meta_filter)
            # result is already streamed to stdout, no need to print again

            console.print("─" * 50)
            console.print("💬 Ready for next question... (Ctrl-D/Ctrl-C to quit)")
            console.print("─" * 50)
            console.print()  # Extra newline for spacing
            console.print("→ ", end="")
    except (EOFError, KeyboardInterrupt):
        pass
