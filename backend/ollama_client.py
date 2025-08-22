#!/usr/bin/env python3
"""Ollama client utilities for model management and inference."""

import json
import os
from typing import Optional

import httpx

from backend.config import OLLAMA_CONTEXT_TOKENS, OLLAMA_MODEL, OLLAMA_URL, get_logger
from backend.windows_ip_in_wsl import get_windows_host_ip

# Set up logging for this module
logger = get_logger(__name__)


def _get_ollama_base_url() -> str:
    """Return the Ollama base URL accessible from WSL.

    Prefers the Windows host IP if available, otherwise falls back to the
    default URL from config.
    """
    # When running outside Docker, use localhost directly
    if not os.getenv("DOCKER_ENV"):
        return OLLAMA_URL

    # When running inside Docker, try to get Windows host IP
    ip = get_windows_host_ip()
    if ip:
        return f"http://{ip}:11434"
    return OLLAMA_URL


def _detect_ollama_model() -> Optional[str]:
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
    except Exception as e:
        # Any issue (network, JSON, etc.) – silently ignore and let caller fall back.
        logger.debug("Failed to detect Ollama model, falling back. Error: %s", e)
    return None


def _check_model_exists(model_name: str, models: list) -> bool:
    """Check if a model exists in the list of available models."""
    for model in models:
        model_name_from_list = model.get("name", "")
        # Check for exact match or prefix match (e.g., "model" matches "model:latest")
        if model_name == model_name_from_list or model_name_from_list.startswith(model_name + ":"):
            return True
    return False


def _download_model_with_progress(model_name: str, base_url: str) -> bool:
    """Download a model with progress tracking."""
    logger.info("Model '%s' not found. Downloading...", model_name)
    logger.info("This may take several minutes depending on your internet speed.")

    try:
        with httpx.stream(
            "POST",
            f"{base_url.rstrip('/')}/api/pull",
            json={"name": model_name},
            timeout=300,  # 5 minutes timeout for download
        ) as response:
            response.raise_for_status()

            # Track progress from streaming response
            last_logged_percent = -5  # force first update
            for line in response.iter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                status = data.get("status", "")

                # 1. Show percentage progress if total / completed present
                total = data.get("total")
                completed = data.get("completed")
                if (
                    total
                    and completed
                    and isinstance(total, (int, float))
                    and isinstance(completed, (int, float))
                    and total > 0
                ):
                    percent = int(completed / total * 100)
                    if percent - last_logged_percent >= 5:  # log every 5%
                        last_logged_percent = percent
                        logger.info("Downloading… %d%%", percent)

                # 2. Fallback status messages
                if status == "verifying":
                    logger.info("Verifying model integrity…")
                elif status == "writing":
                    logger.info("Writing model to disk…")
                elif status == "complete":
                    logger.info("✓ Model download completed!")
                    break
        return True
    except Exception as e:
        logger.error("Download failed: %s", e)
        return False


def _verify_model_download(model_name: str, base_url: str) -> bool:
    """Verify that a model was successfully downloaded."""
    import time

    time.sleep(2)  # Wait for model to be registered

    # Re-check if model is now available
    verify_resp = httpx.get(f"{base_url.rstrip('/')}/api/tags", timeout=2)
    verify_resp.raise_for_status()
    verify_models = verify_resp.json().get("models", [])

    model_verified = _check_model_exists(model_name, verify_models)

    if model_verified:
        logger.info("Model '%s' downloaded and verified successfully!", model_name)
    else:
        logger.warning("Model '%s' download completed but verification failed.", model_name)

    return model_verified


def ensure_model_available(model_name: str) -> bool:
    """Ensure the specified model is available, download if needed."""
    try:
        base_url = _get_ollama_base_url()

        # Check if model exists
        try:
            resp = httpx.get(f"{base_url.rstrip('/')}/api/tags", timeout=2)
            resp.raise_for_status()
            models = resp.json().get("models", [])
        except httpx.ConnectError as e:
            logger.error(
                "Cannot connect to Ollama server at %s. Please ensure Ollama is running and accessible.", base_url
            )
            logger.debug("Connection error details: %s", e)
            return False
        except httpx.TimeoutException:
            logger.error("Timeout connecting to Ollama server at %s. Please check if Ollama is running.", base_url)
            return False
        except Exception as e:
            logger.error("Unexpected error connecting to Ollama server: %s", e)
            return False

        # Check if our model is in the list
        model_exists = _check_model_exists(model_name, models)

        if not model_exists:
            logger.info("Model '%s' not found in Ollama. Attempting to download...", model_name)
            # Download the model with progress tracking
            if not _download_model_with_progress(model_name, base_url):
                logger.error(
                    "Failed to download model '%s'. Please check your internet connection and try again.", model_name
                )
                return False

            # Verify the download was successful
            if not _verify_model_download(model_name, base_url):
                logger.error("Model '%s' download verification failed.", model_name)
                return False

            logger.info("Model '%s' successfully downloaded and verified.", model_name)
            return True
        else:
            logger.info("Model '%s' is already available.", model_name)
            return True

    except Exception as e:
        logger.error("Unexpected error ensuring model availability: %s", e)
        return False


def test_ollama_connection() -> bool:
    """Test Ollama connection and model with a simple dry-run."""
    try:
        base_url = _get_ollama_base_url()
        model_name = OLLAMA_MODEL

        logger.info("Testing Ollama connection...")

        # Test 1: Check if Ollama is reachable
        try:
            resp = httpx.get(f"{base_url.rstrip('/')}/api/tags", timeout=5)
            resp.raise_for_status()
            logger.info("✓ Ollama server is reachable")
        except Exception as e:
            logger.error("✗ Ollama server not reachable: %s", e)
            return False

        # Test 2: Ensure model is available
        if not ensure_model_available(model_name):
            return False

        # Test 3: Quick inference test
        logger.info("Running quick inference test...")
        test_payload = {
            "model": model_name,
            "prompt": "Hello",
            "stream": True,
            "options": {"num_predict": 5},  # Limit to 5 tokens for speed
        }

        test_resp = httpx.stream(
            "POST",
            f"{base_url.rstrip('/')}/api/generate",
            json=test_payload,
            timeout=10,
        )
        with test_resp as resp:
            resp.raise_for_status()
            # Just read a few lines to confirm it's working
            for i, _ in enumerate(resp.iter_lines()):
                if i >= 3:  # Only read first 3 lines
                    break

        logger.info("✓ Ollama inference test successful")
        return True

    except Exception as e:
        logger.error("✗ Ollama test failed: %s", e)
        return False


def generate_response(
    prompt: str,
    model_name: str = OLLAMA_MODEL,
    context: Optional[list] = None,
    on_token=None,
    on_debug=None,
    stop_event=None,
    context_tokens: int = 8192,
) -> tuple[str, Optional[list]]:
    """Generate a response from Ollama for the given prompt, optionally streaming tokens and debug info via callbacks.
    Can be interrupted with stop_event."""
    import sys

    if context_tokens is None:
        context_tokens = OLLAMA_CONTEXT_TOKENS

    base_url = _get_ollama_base_url()
    url = f"{base_url.rstrip('/')}/api/generate"

    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": True,
        "options": {"num_ctx": context_tokens},
    }
    if context is not None:
        payload["context"] = context

    logger.debug("Calling Ollama at: %s", url)
    if on_debug:
        on_debug(f"Calling Ollama at: {url}")
    logger.debug("Model: %s", model_name)
    if on_debug:
        on_debug(f"Model: {model_name}")
    logger.debug("Ollama context window: %d tokens", context_tokens)
    if on_debug:
        on_debug(f"Ollama context window: {context_tokens} tokens")
    logger.debug("Prompt length: %d characters", len(prompt))
    if on_debug:
        on_debug(f"Prompt length: {len(prompt)} characters")
    logger.debug("Context provided: %s", context is not None)
    if on_debug:
        on_debug(f"Context provided: {context is not None}")
    approx_tokens = len(prompt) // 4
    if approx_tokens > context_tokens:
        warning_msg = (
            f"WARNING: Prompt is estimated at {approx_tokens} tokens, "
            f"which exceeds the context window ({context_tokens}). "
            "Ollama will truncate the prompt and you may lose context."
        )
        logger.warning(warning_msg)
        if on_debug:
            on_debug(warning_msg)
    elif approx_tokens > context_tokens * 0.9:
        note_msg = (
            f"NOTE: Prompt is estimated at {approx_tokens} tokens, "
            f"      which is close to the context window ({context_tokens})."
        )
        logger.debug(note_msg)
        if on_debug:
            on_debug(note_msg)

    try:
        logger.debug("Making HTTP request to Ollama...")
        if on_debug:
            on_debug("Making HTTP request to Ollama...")
        with httpx.stream("POST", url, json=payload, timeout=300) as resp:  # 5 minute timeout
            logger.debug("Response status: %d", resp.status_code)
            if on_debug:
                on_debug(f"Response status: {resp.status_code}")

            response_text = ""
            updated_context = context
            line_count = 0
            first_token = True

            logger.debug("Waiting for Ollama to start streaming response...")
            if on_debug:
                on_debug("Waiting for Ollama to start streaming response...")
            for line in resp.iter_lines():
                if stop_event is not None and stop_event.is_set():
                    logger.debug("Stop event set, aborting stream.")
                    if on_debug:
                        on_debug("Stop event set, aborting stream.")
                    break
                line_count += 1
                if not line:
                    logger.debug("Empty line received, continuing...")
                    continue

                # Ollama sends newline-separated JSON objects
                line_str = line.strip()
                logger.debug("Processing line: %s", line_str[:100])  # Log first 100 chars
                if line_str.startswith("data:"):
                    line_str = line_str[len("data:") :].strip()

                if line_str == "[DONE]":
                    logger.debug("Received [DONE] marker")
                    if on_debug:
                        on_debug("Received [DONE] marker")
                    break

                try:
                    data = json.loads(line_str)
                except json.JSONDecodeError as e:
                    logger.debug("Failed to parse JSON: %s... Error: %s", line_str[:50], e)
                    if on_debug:
                        on_debug(f"Failed to parse JSON: {line_str[:50]}... Error: {e}")
                    continue

                # Extract token from response
                token_str = (
                    data.get("response")
                    or data.get("token")
                    or (data.get("choices", [{}])[0].get("text") if "choices" in data else "")
                )

                if first_token and token_str:
                    logger.debug("Ollama started streaming tokens...")
                    if on_debug:
                        on_debug("Ollama started streaming tokens...")
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
                    if on_debug:
                        on_debug("Received 'done' flag")
                    updated_context = data.get("context", context)
                    break

            logger.debug("Processed %d lines from response", line_count)
            if on_debug:
                on_debug(f"Processed {line_count} lines from response")

            # Validate response
            if not response_text.strip():
                logger.warning("Received empty response from Ollama")
                if on_debug:
                    on_debug("Received empty response from Ollama")
                return "(No response generated)", updated_context

            return response_text, updated_context
    except Exception as e:
        logger.error("Exception in generate_response: %s", e)
        if on_debug:
            on_debug(f"Exception in generate_response: {e}")
        return f"[Error generating response: {e}]", context
