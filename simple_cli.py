#!/usr/bin/env python3
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent / "backend"))
sys.path.insert(0, str(Path(__file__).parent))
# Explicitly add venv site-packages
sys.path.insert(0, str(Path(__file__).parent / ".venv/lib/python3.12/site-packages"))

from backend.qa_loop import answer

if __name__ == "__main__":
    question = "What is the capital of France?"
    print(f"Question: {question}")
    response = answer(question)
    print(f"Answer: {response}")
