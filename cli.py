#!/usr/bin/env python3
"""
Main CLI entry point for the RAG system.
Follows Python best practices for command-line interfaces.
"""

import logging
import sys

from backend.console import console, get_logger
from backend.qa_loop import answer, ensure_weaviate_ready_and_populated

logger = get_logger(__name__)


from backend.config import OLLAMA_MODEL
from backend.ollama_client import ensure_model_available


def main():
    """Main CLI entry point."""
    import argparse

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
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        # Ensure Weaviate is ready
        ensure_weaviate_ready_and_populated()

        # Ensure the required Ollama model is available
        if not ensure_model_available(OLLAMA_MODEL):
            logger.error("Required Ollama model %s is not available. Exiting.", OLLAMA_MODEL)
            sys.exit(1)

        if args.question:
            # Single question mode
            console.print(f"Question: {args.question}")
            console.print("-" * 50)
            response = answer(args.question, k=args.k)
            console.print(f"Answer: {response}")
        else:
            # Interactive mode
            console.print("RAG System CLI - Interactive Mode")
            console.print("Type 'quit' or 'exit' to leave")
            console.print("=" * 50)

            while True:
                try:
                    question = input("\nQuestion: ").strip()

                    if question.lower() in ["quit", "exit", "q"]:
                        console.print("Goodbye!")
                        break

                    if not question:
                        continue

                    console.print("-" * 30)
                    response = answer(question, k=args.k)
                    # The answer is now streamed, so we don't print it here.
                    # A newline is added in the answer function.
                except KeyboardInterrupt:
                    console.print("\nGoodbye!")
                    break
                except EOFError:
                    console.print("\nGoodbye!")
                    break

    except Exception as e:
        from rich.console import Console

        console_stderr = Console(file=sys.stderr)
        console_stderr.print(f"[bold red]Error:[/] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
