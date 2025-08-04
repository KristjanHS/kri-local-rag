#!/usr/bin/env python3

# Test relative import from within the same package (will fail if run as a script)
try:
    from .config import OLLAMA_MODEL as RELATIVE_MODEL

    print("✓ Relative import works:", RELATIVE_MODEL)
except ImportError as e:
    print(f"✗ Relative import failed as expected when run as script: {e}")

# Test absolute import from the project root
try:
    from backend.config import OLLAMA_MODEL as ABSOLUTE_MODEL

    print("✓ Absolute import works:", ABSOLUTE_MODEL)
except ImportError as e:
    print(f"✗ Absolute import failed: {e}")
