"""Top-level CLI entry point. Real argument parsing arrives in a later commit."""

from __future__ import annotations

import sys
from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] in {"-V", "--version"}:
        from denote_lint import __version__
        print(f"denote-lint {__version__}")
        return 0
    print(
        "denote-lint: not yet implemented. See denote-lint-spec.org for the design.",
        file=sys.stderr,
    )
    return 2
