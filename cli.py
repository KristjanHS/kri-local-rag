#!/usr/bin/env python3
"""
Main CLI entry point for the RAG system.
Follows Python best practices for command-line interfaces.
"""

import argparse
import sys
import os
from pathlib import Path

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent / "backend"))

from qa_loop import answer, ensure_weaviate_ready_and_populated


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="RAG System CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python cli.py                    # Start interactive mode
  python cli.py --question "What is AI?"  # Single question
  python cli.py --debug            # Enable debug logging
  python cli.py --help             # Show this help
        """,
    )

    parser.add_argument("--question", "-q", help="Ask a single question and exit")

    parser.add_argument("--debug", "-d", action="store_true", help="Enable debug logging")

    parser.add_argument("--k", "-k", type=int, default=3, help="Number of context chunks to retrieve (default: 3)")

    parser.add_argument("--version", "-v", action="version", version="RAG CLI v1.0.0")

    args = parser.parse_args()

    # Set debug logging if requested
    if args.debug:
        os.environ["LOG_LEVEL"] = "DEBUG"

    try:
        # Ensure Weaviate is ready
        ensure_weaviate_ready_and_populated()

        if args.question:
            # Single question mode
            print(f"Question: {args.question}")
            print("-" * 50)
            response = answer(args.question, k=args.k)
            print(f"Answer: {response}")
        else:
            # Interactive mode
            print("RAG System CLI - Interactive Mode")
            print("Type 'quit' or 'exit' to leave")
            print("=" * 50)

            while True:
                try:
                    question = input("\nQuestion: ").strip()

                    if question.lower() in ["quit", "exit", "q"]:
                        print("Goodbye!")
                        break

                    if not question:
                        continue

                    print("-" * 30)
                    response = answer(question, k=args.k)
                    print(f"Answer: {response}")

                except KeyboardInterrupt:
                    print("\nGoodbye!")
                    break
                except EOFError:
                    print("\nGoodbye!")
                    break

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
