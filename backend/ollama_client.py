#!/usr/bin/env python3
"""Ollama client utilities for model management and inference."""

import httpx
import json
from typing import Optional

from config import OLLAMA_MODEL, OLLAMA_URL
from windows_ip_in_wsl import get_windows_host_ip

# Debug levels: 0=off, 1=basic, 2=detailed, 3=verbose
DEBUG_LEVEL = 1


def debug_print(message: str, level: int = 1):
    """Print debug message only if current debug level is sufficient."""
    if DEBUG_LEVEL >= level:
        print(f"[DEBUG-{level}] {message}")


def set_debug_level(level: int):
    """Set the debug level (0=off, 1=basic, 2=detailed, 3=verbose)."""
    global DEBUG_LEVEL
    DEBUG_LEVEL = max(0, min(3, level))


def _get_ollama_base_url() -> str:
    """Return the Ollama base URL accessible from WSL.

    Prefers the Windows host IP if available, otherwise falls back to the
    default URL from config.
    """
    ip = get_windows_host_ip()
    if ip:
        return f"http://{ip}:11434"
    return OLLAMA_URL


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


def _check_model_exists(model_name: str, models: list) -> bool:
    """Check if a model exists in the list of available models."""
    for model in models:
        model_name_from_list = model.get("name", "")
        # Check exact match or if our model is a prefix
        # (e.g., "cas/mistral-7b-instruct-v0.3" matches "cas/mistral-7b-instruct-v0.3:latest")
        if model_name_from_list == model_name or model_name_from_list.startswith(model_name + ":"):
            return True
    return False


def _download_model_with_progress(model_name: str, base_url: str) -> bool:
    """Download a model with progress tracking."""
    print(f"Model '{model_name}' not found. Downloading...")
    print("This may take several minutes depending on your internet speed.")

    try:
        with httpx.stream(
            "POST",
            f"{base_url.rstrip('/')}/api/pull",
            json={"name": model_name},
            timeout=300,  # 5 minutes timeout for download
        ) as response:
            response.raise_for_status()

            # Track progress from streaming response
            for line in response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if "status" in data:
                            status = data["status"]
                            if status == "downloading":
                                if "digest" in data:
                                    print(f"Downloading layer: {data['digest'][:12]}...")
                            elif status == "verifying":
                                print("Verifying model integrity...")
                            elif status == "writing":
                                print("Writing model to disk...")
                            elif status == "complete":
                                print("✓ Model download completed!")
                                break
                    except json.JSONDecodeError:
                        continue
        return True
    except Exception as e:
        print(f"Download failed: {e}")
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
        print(f"Model '{model_name}' downloaded and verified successfully!")
    else:
        print(f"Model '{model_name}' download completed but verification failed.")

    return model_verified


def ensure_model_available(model_name: str) -> bool:
    """Ensure the specified model is available, download if needed."""
    try:
        base_url = _get_ollama_base_url()

        # Check if model exists
        resp = httpx.get(f"{base_url.rstrip('/')}/api/tags", timeout=2)
        resp.raise_for_status()
        models = resp.json().get("models", [])

        # Check if our model is in the list
        model_exists = _check_model_exists(model_name, models)

        if not model_exists:
            # Download the model with progress tracking
            if not _download_model_with_progress(model_name, base_url):
                return False

            # Verify the download was successful
            return _verify_model_download(model_name, base_url)
        else:
            print(f"Model '{model_name}' is already available.")
            return True

    except Exception as e:
        print(f"Error ensuring model availability: {e}")
        return False


def test_ollama_connection() -> bool:
    """Test Ollama connection and model with a simple dry-run."""
    try:
        base_url = _get_ollama_base_url()
        model_name = OLLAMA_MODEL

        debug_print("Testing Ollama connection...", 1)

        # Test 1: Check if Ollama is reachable
        try:
            resp = httpx.get(f"{base_url.rstrip('/')}/api/tags", timeout=5)
            resp.raise_for_status()
            debug_print("✓ Ollama server is reachable", 1)
        except Exception as e:
            debug_print(f"✗ Ollama server not reachable: {e}", 1)
            return False

        # Test 2: Ensure model is available
        if not ensure_model_available(model_name):
            return False

        # Test 3: Quick inference test
        debug_print("Running quick inference test...", 1)
        test_payload = {
            "model": model_name,
            "prompt": "Hello",
            "stream": False,
            "options": {"num_predict": 5},  # Limit to 5 tokens for speed
        }

        test_resp = httpx.post(f"{base_url.rstrip('/')}/api/generate", json=test_payload, timeout=30)
        test_resp.raise_for_status()

        debug_print("✓ Ollama inference test successful", 1)
        return True

    except Exception as e:
        debug_print(f"✗ Ollama test failed: {e}", 1)
        return False


def generate_response(
    prompt: str, model_name: str = OLLAMA_MODEL, context: Optional[list] = None
) -> tuple[str, Optional[list]]:
    """Generate a response from Ollama for the given prompt.

    Returns:
        tuple: (response_text, updated_context)
    """
    import sys

    base_url = _get_ollama_base_url()
    url = f"{base_url.rstrip('/')}/api/generate"

    payload = {
        "model": model_name,
        "prompt": prompt,
        "stream": True,
    }
    if context is not None:
        payload["context"] = context

    debug_print(f"Calling Ollama at: {url}", 2)
    debug_print(f"Model: {model_name}", 2)
    debug_print(f"Prompt length: {len(prompt)} characters", 2)
    debug_print(f"Context provided: {context is not None}", 2)

    try:
        debug_print("Making HTTP request to Ollama...", 2)
        with httpx.stream("POST", url, json=payload, timeout=None) as resp:
            debug_print(f"Response status: {resp.status_code}", 2)

            response_text = ""
            updated_context = context
            line_count = 0

            debug_print("Starting to read response stream...", 2)
            for line in resp.iter_lines():
                line_count += 1
                if not line:
                    continue

                # Ollama sends newline-separated JSON objects
                line_str = line.strip()
                if line_str.startswith("data:"):
                    line_str = line_str[len("data:") :].strip()

                if line_str == "[DONE]":
                    debug_print("Received [DONE] marker", 2)
                    break

                try:
                    data = json.loads(line_str)
                except json.JSONDecodeError:
                    debug_print(f"Failed to parse JSON: {line_str[:50]}...", 2)
                    continue

                # Extract token from response
                token_str = (
                    data.get("response")
                    or data.get("token")
                    or (data.get("choices", [{}])[0].get("text") if "choices" in data else "")
                )

                response_text += token_str
                # Stream token to stdout like original code
                sys.stdout.write(token_str)
                sys.stdout.flush()

                # Capture the conversation context if provided with the final chunk.
                if data.get("done"):
                    debug_print("Received 'done' flag", 2)
                    updated_context = data.get("context", context)
                    break

            debug_print(f"Processed {line_count} lines from response", 2)
            return response_text or "(no response)", updated_context
    except Exception as e:
        debug_print(f"Exception in generate_response: {e}", 2)
        return f"[Error generating response: {e}]", context
