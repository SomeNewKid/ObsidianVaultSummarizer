"""Command-line interface for the application."""

from __future__ import annotations

from otto_agent.utilities import pretty_print

from .agent import run_obsidian_vault_summarizer

VERBOSE_LOGGING = True


def main(argv: list[str] | None = None) -> int:
    """Run the command-line interface."""
    _ensure_no_arguments(argv)
    result = run_obsidian_vault_summarizer()
    if VERBOSE_LOGGING:
        pretty_print(result)
        print("-" * 20)
    answer = result.details.get("summary", "")
    if answer:
        print(answer)
    else:
        print("No summary was generated.")
    return 0


def _ensure_no_arguments(argv: list[str] | None) -> None:
    args = [] if argv is None else argv
    if args:
        raise SystemExit("Usage: python -m obsidian_vault_summarizer")
