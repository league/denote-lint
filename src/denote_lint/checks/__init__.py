"""Check registry and orchestrator.

Each check is registered with a stable code, a severity, a category,
and a scope. The CLI filter operates on codes; severity is metadata
used to derive default code lists from ``--severity``.

Two scopes:

- ``per_note`` -- the function takes ``(note, ctx)`` and is called
  once per note.
- ``corpus`` -- the function takes ``(ctx,)`` and is called once for
  the whole corpus (used by E001, I001, I003).
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Literal

from denote_lint.models import Context, Issue, Note, Severity

PerNoteCheck = Callable[[Note, Context], Iterable[Issue]]
CorpusCheck = Callable[[Context], Iterable[Issue]]
CheckScope = Literal["per_note", "corpus"]


@dataclass(frozen=True)
class CheckRecord:
    code: str
    severity: Severity
    category: str
    scope: CheckScope
    func: PerNoteCheck | CorpusCheck


REGISTRY: dict[str, CheckRecord] = {}


def register_per_note(
    code: str, severity: Severity, category: str
) -> Callable[[PerNoteCheck], PerNoteCheck]:
    def deco(fn: PerNoteCheck) -> PerNoteCheck:
        if code in REGISTRY:
            raise RuntimeError(f"check {code} already registered")
        REGISTRY[code] = CheckRecord(code, severity, category, "per_note", fn)
        return fn

    return deco


def register_corpus(
    code: str, severity: Severity, category: str
) -> Callable[[CorpusCheck], CorpusCheck]:
    def deco(fn: CorpusCheck) -> CorpusCheck:
        if code in REGISTRY:
            raise RuntimeError(f"check {code} already registered")
        REGISTRY[code] = CheckRecord(code, severity, category, "corpus", fn)
        return fn

    return deco


def run_checks(
    notes: list[Note], ctx: Context, enabled: frozenset[str]
) -> list[Issue]:
    """Run every enabled check, returning issues in deterministic order.

    Per-note checks iterate notes in input order; corpus checks run
    after all per-note checks. Within each scope, codes run in sorted
    order.
    """
    issues: list[Issue] = []
    sorted_codes = sorted(REGISTRY)

    for code in sorted_codes:
        record = REGISTRY[code]
        if code not in enabled or record.scope != "per_note":
            continue
        fn_per_note: PerNoteCheck = record.func  # type: ignore[assignment]
        for note in notes:
            issues.extend(fn_per_note(note, ctx))

    for code in sorted_codes:
        record = REGISTRY[code]
        if code not in enabled or record.scope != "corpus":
            continue
        fn_corpus: CorpusCheck = record.func  # type: ignore[assignment]
        issues.extend(fn_corpus(ctx))

    return issues


def _import_checks() -> None:
    """Import every check module so registrations happen at startup.

    Keeping this in a function (rather than top-level import) means
    importing :mod:`denote_lint.checks` doesn't carry the cost of
    loading every check module just to read REGISTRY -- but the CLI
    calls this at startup, so all codes are present by the time
    Config.enabled_codes() runs.
    """
    from denote_lint.checks import filename, frontmatter, hygiene, identifier, links  # noqa: F401


_import_checks()
