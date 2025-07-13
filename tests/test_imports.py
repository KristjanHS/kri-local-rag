#!/usr/bin/env python3

# Test relative import
try:
    from .config import OLLAMA_MODEL as RELATIVE_MODEL

    print("✓ Relative import works:", RELATIVE_MODEL)
except ImportError as e:
    print(f"✗ Relative import failed: {e}")

# Test absolute import
try:
    from config import OLLAMA_MODEL as ABSOLUTE_MODEL

    print("✓ Absolute import works:", ABSOLUTE_MODEL)
except ImportError as e:
    print(f"✗ Absolute import failed: {e}")
