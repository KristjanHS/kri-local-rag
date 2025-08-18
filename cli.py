#!/usr/bin/env python3
"""
Main CLI entry point for the RAG system.
Follows Python best practices for command-line interfaces.
"""

import logging
import os
import sys

from backend.console import console, get_logger

logger = get_logger(__name__)


# Defer heavy imports (qa_loop, ollama) until needed to keep CLI startup fast,
# especially in test paths that use fake answers and skip startup checks.


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
        # Test hooks
        verbose_test = os.getenv("RAG_VERBOSE_TEST", "0").lower() in ("1", "true", "yes")
        fake_answer = os.getenv("RAG_FAKE_ANSWER")

        if verbose_test:
            console.print("PHASE: startup")
        # Allow tests or offline runs to skip slow startup checks
        skip_startup_checks = (
            os.getenv("RAG_SKIP_STARTUP_CHECKS", "0").lower() in ("1", "true", "yes")
            or os.getenv("PYTEST_CURRENT_TEST") is not None
        )

        if not skip_startup_checks:
            # Ensure Weaviate is ready
            import backend.qa_loop as qa
            from backend.config import OLLAMA_MODEL
            from backend.ollama_client import ensure_model_available

            qa.ensure_weaviate_ready_and_populated()

            # Ensure the required Ollama model is available
            if not ensure_model_available(OLLAMA_MODEL):
                logger.error("Required Ollama model %s is not available. Exiting.", OLLAMA_MODEL)
                sys.exit(1)
        else:
            if verbose_test:
                console.print("PHASE: startup skipped")

        if args.question:
            # Single question mode
            if verbose_test:
                console.print("PHASE: single_question")
            console.print(f"Question: {args.question}")
            console.print("-" * 50)
            if fake_answer is not None:
                response = fake_answer
                console.print(f"Answer: {response}")
                # Ensure output is flushed promptly in test environments
                try:
                    sys.stdout.flush()
                except Exception as e:
                    logger.debug("Failed to flush stdout: %s", e)
                return 0
            else:
                # Real path streams tokens to stdout; no extra final print to avoid duplication
                import backend.qa_loop as qa

                qa.answer(args.question, k=args.k)
                try:
                    sys.stdout.flush()
                except Exception as e:
                    logger.debug("Failed to flush stdout: %s", e)
                return 0
        else:
            # Interactive mode
            if verbose_test:
                console.print("PHASE: interactive")
            console.print("RAG System CLI - Interactive Mode")
            console.print("Type 'quit' or 'exit' to leave")
            console.print("=" * 50)

            while True:
                try:
                    # Use stdout write + flush to support non-tty/piped stdin (avoid print per lint rules)
                    try:
                        sys.stdout.write("\nQuestion: ")
                        sys.stdout.flush()
                    except Exception as e:
                        logger.debug("Failed to flush stdout: %s", e)
                    question = input().strip()

                    if question.lower() in ["quit", "exit", "q"]:
                        console.print("Goodbye!")
                        break

                    if not question:
                        continue

                    console.print("-" * 30)
                    if fake_answer is not None:
                        # Deterministic test path: print fake answer once
                        console.print(fake_answer)
                        try:
                            sys.stdout.flush()
                        except Exception as e:
                            logger.debug("Failed to flush stdout: %s", e)
                    else:
                        # Real path streams tokens to stdout via qa.answer
                        import backend.qa_loop as qa

                        qa.answer(question, k=args.k)
                        try:
                            sys.stdout.flush()
                        except Exception as e:
                            logger.debug("Failed to flush stdout: %s", e)
                except KeyboardInterrupt:
                    console.print("\nGoodbye!")
                    break
                except EOFError:
                    console.print("\nGoodbye!")
                    break

        return 0
    except Exception as e:
        from rich.console import Console

        console_stderr = Console(file=sys.stderr)
        console_stderr.print(f"[bold red]Error:[/] {e}")
        sys.exit(1)


if __name__ == "__main__":
    sys.exit(main())
