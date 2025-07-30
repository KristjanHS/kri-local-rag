#!/usr/bin/env python3
"""Debug script to test the RAG system components step by step."""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))
sys.path.insert(0, str(Path(__file__).parent))
# Explicitly add venv site-packages
sys.path.insert(0, str(Path(__file__).parent / ".venv/lib/python3.12/site-packages"))
print("Python path:", sys.path)

print("1. Testing imports...")
try:
    from backend.config import OLLAMA_MODEL, OLLAMA_URL, WEAVIATE_URL, get_logger

    print(f"   ✓ Config loaded - OLLAMA_URL: {OLLAMA_URL}, WEAVIATE_URL: {WEAVIATE_URL}")
except Exception as e:
    print(f"   ✗ Config import failed: {e}")
    sys.exit(1)

print("2. Testing Ollama client...")
try:
    from ollama_client import _get_ollama_base_url, test_ollama_connection

    ollama_url = _get_ollama_base_url()
    print(f"   ✓ Ollama URL resolved to: {ollama_url}")
except Exception as e:
    print(f"   ✗ Ollama client import failed: {e}")
    sys.exit(1)

print("3. Testing Weaviate connection...")
try:
    from qa_loop import ensure_weaviate_ready_and_populated

    print("   → Checking Weaviate...")
    ensure_weaviate_ready_and_populated()
    print("   ✓ Weaviate connection successful")
except Exception as e:
    print(f"   ✗ Weaviate connection failed: {e}")
    sys.exit(1)

print("4. Testing simple Ollama request...")
try:
    import httpx

    response = httpx.get(f"{ollama_url}/api/tags", timeout=5)
    print(f"   ✓ Ollama API accessible - Status: {response.status_code}")
except Exception as e:
    print(f"   ✗ Ollama API test failed: {e}")
    sys.exit(1)

print("\n✓ All components are working! The issue might be in the answer generation.")
