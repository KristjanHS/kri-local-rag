"""Validate presence and minimal contents of .env.example.

Covers the launch prep checklist requirement that a template env file exists
with the key variables for local bring-up.
"""

from __future__ import annotations

from pathlib import Path


def test_env_example_exists_and_has_minimal_keys() -> None:
    project_root = Path(__file__).resolve().parents[2]
    env_example = project_root / ".env.example"
    assert env_example.exists(), ".env.example should exist at project root"

    content = env_example.read_text(encoding="utf-8")
    # Minimal keys required for local setup
    required_keys = [
        "OLLAMA_MODEL",
        "OLLAMA_URL",
        "WEAVIATE_URL",
    ]
    for key in required_keys:
        assert f"{key}=" in content or f"{key}=" in content.replace(" ", ""), f"Missing key in .env.example: {key}"
