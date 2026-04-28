"""Filename grammar parser.

Grammar (denote canonical form)::

    IDENTIFIER [== SIGNATURE] [-- TITLE] [__ KEYWORDS] . EXTENSION

- IDENTIFIER: required, ``YYYYMMDDTHHMMSS`` (literal ``T``).
- SIGNATURE:  optional, prefixed ``==``. Anything Denote's
              ``denote-sluggify-signature`` would have left intact:
              lowercase, no whitespace, and none of the punctuation
              characters Denote strips (which for signatures includes
              ``-``).
- TITLE:      optional, prefixed ``--``. Anything Denote's
              ``denote-sluggify-title`` would have left intact:
              lowercase, no whitespace, no characters from Denote's
              title-strip set.
- KEYWORDS:   optional, prefixed ``__``, ``_``-joined keywords. Each
              keyword is what Denote's ``denote-sluggify-keyword`` would
              produce: lowercase, no whitespace, none of the keyword
              strip characters (which include ``-``, ``_``, ``=``).
- EXTENSION:  whatever follows the last dot (org/md/txt/anything-else).

Non-ASCII letters (``é``, ``ò``, Greek, Cyrillic, CJK, ...) are
*allowed*: Denote's default sluggifier preserves them. Only the
explicit punctuation blocklists are forbidden, plus uppercase and
whitespace.

Components must appear in the above order. Missing is fine; malformed is
not, and is reported by raising codes onto :class:`ParsedFilename.parse_errors`:

- E002: identifier doesn't match ``YYYYMMDDTHHMMSS``.
- E003: identifier matches the shape but isn't a valid date/time.
- E009: disallowed characters in a component (uppercase, whitespace,
        or any char in the relevant Denote strip set).
- E010: missing required separator content (e.g. trailing ``__`` with no
        keyword, ``__a__b`` with an empty middle keyword).
- W007: a keyword contains characters that should have been stripped
        (a ``-`` or other punctuation within a single keyword).

Note: this module only flags structural problems it can see at the
filename level. ``W001`` (alphabetical-keyword ordering) is enforced by
a separate check that consumes :class:`ParsedFilename`.
"""

from __future__ import annotations

import re
from datetime import datetime

from denote_lint.models import ParsedFilename

_IDENTIFIER_RE = re.compile(r"^\d{8}T\d{6}$")

# Punctuation that Denote's default sluggifier strips out per component.
# Mirrored from `denote-sluggify-title`, `denote-sluggify-signature`,
# and `denote-sluggify-keyword` in denote.el.
_TITLE_BLOCKLIST = frozenset("[]{}!@#$%^&*()+'\"?,.|;:~`‘’“”/=")
_SIGNATURE_BLOCKLIST = frozenset("[]{}!@#$%^&*()+'\"?,.|;:~`‘’“”/-")
_KEYWORD_BLOCKLIST = frozenset("[]{}!@#$%^&*()+'\"?,.|;:~`‘’“”/_ =-")


def parse_filename(basename: str) -> ParsedFilename:
    """Parse a denote-style basename into a :class:`ParsedFilename`.

    Always returns a value. Structural problems are surfaced via
    ``parse_errors`` rather than exceptions.
    """
    errors: list[str] = []

    if "." in basename:
        stem, _, extension = basename.rpartition(".")
    else:
        stem, extension = basename, ""

    if stem == "":
        _add(errors, "E009")

    sig_idx = stem.find("==")
    title_idx = stem.find("--")
    kw_idx = stem.find("__")
    marker_positions = [i for i in (sig_idx, title_idx, kw_idx) if i >= 0]
    first_marker = min(marker_positions) if marker_positions else len(stem)

    identifier = stem[:first_marker]
    rest = stem[first_marker:]

    identifier_dt: datetime | None = None
    if not _IDENTIFIER_RE.match(identifier):
        _add(errors, "E002")
    else:
        try:
            identifier_dt = datetime.strptime(identifier, "%Y%m%dT%H%M%S")
        except ValueError:
            _add(errors, "E003")

    signature, rest = _consume_component(rest, "==", terminators=("--", "__"))
    if signature is not None and signature == "":
        _add(errors, "E010")
        signature = None
    elif signature is not None and not _is_canonical(signature, _SIGNATURE_BLOCKLIST):
        _add(errors, "E009")

    title_slug, rest = _consume_component(rest, "--", terminators=("__",))
    if title_slug is not None and title_slug == "":
        _add(errors, "E010")
        title_slug = None
    elif title_slug is not None and not _is_canonical(title_slug, _TITLE_BLOCKLIST):
        _add(errors, "E009")

    keywords: tuple[str, ...] = ()
    if rest.startswith("__"):
        kw_block = rest[2:]
        rest = ""
        if kw_block == "":
            _add(errors, "E010")
        else:
            parts = kw_block.split("_")
            if any(p == "" for p in parts):
                _add(errors, "E010")
            valid_parts = [p for p in parts if p != ""]
            for kw in valid_parts:
                if not _is_canonical(kw, _KEYWORD_BLOCKLIST):
                    _add(errors, "W007")
                    break
            keywords = tuple(valid_parts)

    if rest != "":
        _add(errors, "E010")

    return ParsedFilename(
        identifier=identifier,
        identifier_dt=identifier_dt,
        signature=signature,
        title_slug=title_slug,
        keywords=keywords,
        extension=extension,
        raw=basename,
        parse_errors=tuple(errors),
    )


def _consume_component(
    rest: str, prefix: str, terminators: tuple[str, ...]
) -> tuple[str | None, str]:
    """If ``rest`` starts with ``prefix``, peel off the component up to the
    earliest terminator (or end of string). Otherwise return ``(None, rest)``.
    """
    if not rest.startswith(prefix):
        return None, rest
    body = rest[len(prefix) :]
    end_positions = [body.find(t) for t in terminators]
    end_positions = [p for p in end_positions if p >= 0]
    if end_positions:
        end = min(end_positions)
        return body[:end], body[end:]
    return body, ""


def _is_canonical(s: str, blocklist: frozenset[str]) -> bool:
    """True iff ``s`` is a Denote-canonical component value.

    Canonical means: lowercase, no whitespace, and no character drawn
    from ``blocklist`` (the punctuation Denote's sluggifier strips out
    for the relevant component). Non-ASCII letters are explicitly
    allowed; Denote preserves them by default.
    """
    if s == "":
        return False
    if s != s.lower():
        return False
    for ch in s:
        if ch.isspace():
            return False
        if ch in blocklist:
            return False
    return True


def _add(errors: list[str], code: str) -> None:
    if code not in errors:
        errors.append(code)
