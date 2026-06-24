#!/usr/bin/env python3
"""Ollama client utilities for model management and inference."""

import json
from typing import Optional, Callable
import threading

import httpx

from backend.config import OLLAMA_CONTEXT_TOKENS, OLLAMA_MODEL, get_logger, get_service_url

# Set up logging for this module
logger = get_logger(__name__)


def _check_model_exists(model_name: str, models: list[dict[str, str]]) -> bool:
    """Check if a model exists in the list of available models."""
    for model in models:
        model_name_from_list = model.get("name", "")
        # Check for exact match or prefix match (e.g., "model" matches "model:latest")
        if model_name == model_name_from_list or model_name_from_list.startswith(model_name + ":"):
            return True
    return False


def _download_model_with_progress(model_name: str, base_url: str, timeout_seconds: int = 300) -> bool:
    """Download a model with progress tracking."""
    logger.info("Model '%s' not found. Downloading...", model_name)
    logger.debug("Pulling from %s/api/pull with timeout=%ds", base_url.rstrip("/"), timeout_seconds)
    logger.info("This may take several minutes depending on your internet speed.")

    try:
        with httpx.stream(
            "POST",
            f"{base_url.rstrip('/')}/api/pull",
            json={"name": model_name},
            timeout=timeout_seconds,  # Use configurable timeout
        ) as response:
            response.raise_for_status()

            # Track progress from Ollama's well-defined /api/pull frames.
            last_logged_percent = -10  # force first update
            for line in response.iter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                total = data.get("total")
                completed = data.get("completed")
                if total and completed is not None:
                    percent = int(completed / total * 100)
                    if percent - last_logged_percent >= 10:  # throttle to every 10%
                        last_logged_percent = percent
                        logger.info("Downloading… %d%%", percent)

                if data.get("status") == "complete":
                    logger.info("✓ Model download completed!")
                    break
        return True
    except Exception as e:
        logger.error("Download failed: %s", e)
        return False


def pull_if_missing(model_name: str, timeout_seconds: int = 300) -> bool:
    """Ensure a model is available; pull only if it's missing.

    - First attempts to list available models via GET /api/tags
    - If the model is present (exact or tag-prefixed match), returns immediately
    - Otherwise, triggers a pull with progress via POST /api/pull
    """
    base_url = get_service_url("ollama")

    # Quick existence check
    try:
        resp = httpx.get(f"{base_url.rstrip('/')}/api/tags", timeout=5)
        resp.raise_for_status()
        models = resp.json().get("models", [])
        if _check_model_exists(model_name, models):
            logger.info("Model '%s' already available.", model_name)
            return True
    except Exception as e:
        # Do not fail on detection issues; proceed to pull which is idempotent
        logger.debug("Model presence check failed, proceeding to pull. Error: %s", e)

    # Pull (idempotent on server side)
    return _download_model_with_progress(model_name, base_url, timeout_seconds=timeout_seconds)


def generate_response(
    prompt: str,
    model_name: str = OLLAMA_MODEL,
    context: Optional[list[int]] = None,
    on_token: Optional[Callable[[str], None]] = None,
    stop_event: Optional[threading.Event] = None,
    context_tokens: Optional[int] = 8192,
) -> tuple[str, Optional[list[int]]]:
    """Generate a response from Ollama for the given prompt, optionally streaming tokens via a callback.

    Diagnostic progress is emitted via ``logger.debug``; the Streamlit UI surfaces it by attaching a
    logging handler to this module's logger (see ``frontend/rag_app.py``). Can be interrupted with stop_event.
    """
    import sys

    if context_tokens is None:
        context_tokens = OLLAMA_CONTEXT_TOKENS

    base_url = get_service_url("ollama")
    url = f"{base_url.rstrip('/')}/api/generate"
    logger.debug("generate_response: base_url=%s url=%s", base_url, url)

    payload: dict[str, object] = {
        "model": model_name,
        "prompt": prompt,
        "stream": True,
        "options": {"num_ctx": context_tokens},
    }
    if context is not None:
        payload["context"] = context

    logger.debug("Calling Ollama at: %s", url)
    logger.debug("Model: %s", model_name)
    logger.debug("Ollama context window: %d tokens", context_tokens)
    logger.debug("Prompt length: %d characters", len(prompt))
    logger.debug("Context provided: %s", context is not None)
    approx_tokens = len(prompt) // 4
    if approx_tokens > context_tokens:
        logger.warning(
            "WARNING: Prompt is estimated at %d tokens, which exceeds the context window (%d). "
            "Ollama will truncate the prompt and you may lose context.",
            approx_tokens,
            context_tokens,
        )
    elif approx_tokens > context_tokens * 0.9:
        logger.debug(
            "NOTE: Prompt is estimated at %d tokens, which is close to the context window (%d).",
            approx_tokens,
            context_tokens,
        )

    try:
        logger.debug("Making HTTP request to Ollama...")
        logger.debug("httpx.stream POST timeout=300 json_keys=%s", list(payload.keys()))
        with httpx.stream("POST", url, json=payload, timeout=300) as resp:  # 5 minute timeout
            logger.debug("Response status: %d", resp.status_code)

            response_text = ""
            updated_context = context
            line_count = 0
            first_token = True

            logger.debug("Waiting for Ollama to start streaming response...")
            for line in resp.iter_lines():
                if stop_event is not None and stop_event.is_set():
                    logger.debug("Stop event set, aborting stream.")
                    break
                line_count += 1
                if not line:
                    logger.debug("Empty line received, continuing...")
                    continue

                # Ollama /api/generate streams newline-separated JSON objects.
                line_str = line.strip()
                logger.debug("Processing line: %s", line_str[:100])  # Log first 100 chars

                try:
                    data = json.loads(line_str)
                except json.JSONDecodeError as e:
                    logger.debug("Failed to parse JSON: %s... Error: %s", line_str[:50], e)
                    continue

                token_str = data.get("response", "")

                if first_token and token_str:
                    logger.debug("Ollama started streaming tokens...")
                    first_token = False

                response_text += token_str
                if on_token:
                    on_token(token_str)
                else:
                    sys.stdout.write(token_str)
                    sys.stdout.flush()

                # Capture the conversation context if provided with the final chunk.
                if data.get("done"):
                    logger.debug("Received 'done' flag")
                    updated_context = data.get("context", context)
                    break

            logger.debug("Processed %d lines from response", line_count)

            # Validate response
            if not response_text.strip():
                logger.warning("Received empty response from Ollama")
                return "(No response generated)", updated_context

            return response_text, updated_context
    except Exception as e:
        logger.error("Exception in generate_response: %s", e)
        return f"[Error generating response: {e}]", context
