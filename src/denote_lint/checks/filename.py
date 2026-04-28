"""Filename-level checks: E002, E003, E009, E010, W001, W007.

E002/E003/E009/E010/W007 simply lift codes the filename parser already
raised onto :attr:`ParsedFilename.parse_errors`. W001 (alphabetical
keyword ordering) is computed here, since the parser only structurally
validates keywords.
"""

from __future__ import annotations

from collections.abc import Iterable

from denote_lint.checks import register_per_note
from denote_lint.models import Context, Issue, Note

_MESSAGES: dict[str, str] = {
    "E002": "identifier does not match YYYYMMDDTHHMMSS",
    "E003": "identifier parses to an invalid date/time",
    "E009": (
        "filename contains characters Denote's sluggifier would strip "
        "(uppercase, whitespace, punctuation such as '.', '!', '?', ...)"
    ),
    "E010": "filename has an empty or missing component (check separators)",
    "W007": "keyword contains characters that should have been stripped (e.g. '-')",
}


def _issue(note: Note, code: str, severity: str, message: str) -> Issue:
    return Issue(
        path=note.path,
        line=1,
        col=1,
        severity=severity,  # type: ignore[arg-type]
        code=code,
        message=message,
    )


@register_per_note("E002", "error", "filename")
def check_e002(note: Note, _ctx: Context) -> Iterable[Issue]:
    if "E002" in note.filename.parse_errors:
        yield _issue(note, "E002", "error", _MESSAGES["E002"])


@register_per_note("E003", "error", "filename")
def check_e003(note: Note, _ctx: Context) -> Iterable[Issue]:
    if "E003" in note.filename.parse_errors:
        yield _issue(note, "E003", "error", _MESSAGES["E003"])


@register_per_note("E009", "error", "filename")
def check_e009(note: Note, _ctx: Context) -> Iterable[Issue]:
    if "E009" in note.filename.parse_errors:
        yield _issue(note, "E009", "error", _MESSAGES["E009"])


@register_per_note("E010", "error", "filename")
def check_e010(note: Note, _ctx: Context) -> Iterable[Issue]:
    if "E010" in note.filename.parse_errors:
        yield _issue(note, "E010", "error", _MESSAGES["E010"])


@register_per_note("W001", "warning", "filename")
def check_w001(note: Note, _ctx: Context) -> Iterable[Issue]:
    keywords = note.filename.keywords
    if len(keywords) < 2:
        return
    expected = tuple(sorted(keywords))
    if keywords != expected:
        yield _issue(
            note,
            "W001",
            "warning",
            f"keywords not alphabetical: {list(keywords)} -> {list(expected)}",
        )


@register_per_note("W007", "warning", "filename")
def check_w007(note: Note, _ctx: Context) -> Iterable[Issue]:
    if "W007" in note.filename.parse_errors:
        yield _issue(note, "W007", "warning", _MESSAGES["W007"])
