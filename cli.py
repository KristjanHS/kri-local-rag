#!/usr/bin/env python3
"""Root CLI entry point for the RAG system.

This is the single CLI surface for the project: the ``kri-local-rag = cli:main``
console script, ``python cli.py``, the docker-compose ``/app/cli.py`` mount, and
``make cli``/``scripts/cli.sh``. It owns argument parsing, log-level resolution,
backend readiness, and the interactive loop. ``backend.qa_loop`` holds the
orchestration (``answer``) and the shared readiness bootstrap
(``ensure_weaviate_ready_and_populated``, also used by the Streamlit frontend).

Heavy imports (``backend.qa_loop``, ``backend.ollama_client``) are deferred until
needed so startup stays fast — especially in test paths that use fake answers and
skip readiness checks.
"""

from __future__ import annotations

import argparse
import os
import sys

from rich.rule import Rule

from backend.config import resolve_cli_log_level, set_log_level
from backend.console import console, get_logger

logger = get_logger(__name__)


def _build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser (canonical -v/-q/--log-level surface)."""
    parser = argparse.ArgumentParser(description="RAG System CLI")
    parser.add_argument("--question", help="Ask a single question and exit")
    parser.add_argument("--k", "-k", type=int, default=3, help="Number of context chunks to retrieve (default: 3)")
    parser.add_argument("-v", "--verbose", action="count", default=0, help="Increase verbosity (-v INFO, -vv DEBUG)")
    parser.add_argument("-q", "--quiet", action="count", default=0, help="Decrease verbosity (-q WARNING)")
    parser.add_argument("--log-level", help="Explicit log level (DEBUG/INFO/WARNING/ERROR); overrides -v/-q")
    return parser


def _flush_stdout() -> None:
    """Flush stdout promptly so piped/non-tty test environments see output."""
    try:
        sys.stdout.flush()
    except Exception as e:
        logger.debug("Failed to flush stdout: %s", e)


def _skip_startup_checks() -> bool:
    """Whether to bypass slow readiness checks (tests / explicit offline opt-in)."""
    return (
        os.getenv("RAG_SKIP_STARTUP_CHECKS", "0").lower() in ("1", "true", "yes")
        or os.getenv("PYTEST_CURRENT_TEST") is not None
    )


def ensure_backend_ready() -> None:
    """Block until Weaviate is ready/populated and the Ollama model is available.

    Single readiness door — the formerly-duplicated startup blocks (#22) collapse
    here. Exits the process with status 1 if the required Ollama model is missing.
    """
    import backend.qa_loop as qa
    from backend.config import OLLAMA_MODEL
    from backend.ollama_client import pull_if_missing

    with console.status("[bold green]Checking backend services...", spinner="dots"):
        qa.ensure_weaviate_ready_and_populated()
        if not pull_if_missing(OLLAMA_MODEL):
            logger.error("Required Ollama model %s is not available. Exiting.", OLLAMA_MODEL)
            sys.exit(1)


def main() -> int:
    """Main CLI entry point."""
    args = _build_parser().parse_args()
    set_log_level(resolve_cli_log_level(args.log_level, args.verbose, args.quiet))

    # Test hooks
    verbose_test = os.getenv("RAG_VERBOSE_TEST", "0").lower() in ("1", "true", "yes")
    fake_answer = os.getenv("RAG_FAKE_ANSWER")

    try:
        if verbose_test:
            console.print("PHASE: startup")
        if not _skip_startup_checks():
            ensure_backend_ready()
        elif verbose_test:
            console.print("PHASE: startup skipped")

        if args.question:
            # Single question mode
            if verbose_test:
                console.print("PHASE: single_question")
            console.print(f"Question: {args.question}")
            console.print("-" * 50)
            if fake_answer is not None:
                console.print(f"Answer: {fake_answer}")
            else:
                # Real path streams tokens to stdout; no extra final print to avoid duplication
                import backend.qa_loop as qa

                qa.answer(args.question, k=args.k)
            _flush_stdout()
            return 0

        # Interactive mode
        if verbose_test:
            console.print("PHASE: interactive")
        console.print(Rule(style="blue"))
        console.print("💬 RAG CLI Ready. Type 'quit' or 'exit' to leave.")
        console.print(Rule(style="blue"))

        while True:
            try:
                # stdout write + flush (not print) to support non-tty/piped stdin per lint rules
                sys.stdout.write("\nQuestion: ")
                sys.stdout.flush()
                question = input().strip()
            except (KeyboardInterrupt, EOFError):
                console.print("\nGoodbye!")
                break

            if question.lower() in ("quit", "exit", "q"):
                console.print("Goodbye!")
                break
            if not question:
                continue

            console.print("-" * 30)
            if fake_answer is not None:
                # Deterministic test path: print fake answer once
                console.print(fake_answer)
            else:
                # Real path streams tokens to stdout via qa.answer
                import backend.qa_loop as qa

                qa.answer(question, k=args.k)
            _flush_stdout()

        return 0
    except Exception as e:
        from rich.console import Console

        Console(file=sys.stderr).print(f"[bold red]Error:[/] {e}")
        sys.exit(1)
    finally:
        # Ensure the Weaviate client is closed to prevent resource leaks
        try:
            from backend.weaviate_client import close_weaviate_client

            close_weaviate_client()
        except Exception as e:
            logger.debug("Failed to close Weaviate client gracefully: %s", e)


if __name__ == "__main__":
    sys.exit(main())
