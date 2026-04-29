"""Core data model: parsed filename, front matter, link, note, issue."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Literal

Severity = Literal["error", "warning", "info"]


@dataclass(frozen=True)
class ParsedFilename:
    """Result of parsing a denote-style basename.

    Fields hold raw values even when malformed; ``parse_errors`` carries
    the codes that fired during parsing so the caller can decide how to
    react.
    """

    identifier: str
    identifier_dt: datetime | None
    signature: str | None
    title_slug: str | None
    keywords: tuple[str, ...]
    extension: str
    raw: str
    parse_errors: tuple[str, ...] = ()


@dataclass
class FrontMatter:
    """Normalised front-matter view, regardless of source flavour.

    ``parse_errors`` carries any structural-parse codes (e.g. E008) that
    fired while reading the front matter. Field-level absence is
    represented by ``None`` / empty tuples and is not itself a parse
    error — checks classify those.
    """

    title: str | None = None
    identifier: str | None = None
    date: datetime | None = None
    keywords: tuple[str, ...] = ()
    raw_lines: tuple[str, ...] = ()
    parse_errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class Link:
    """A denote: link extracted from a note body."""

    target_id: str
    description: str | None
    line: int
    col: int


@dataclass(frozen=True)
class FileLink:
    """An org ``[[file:PATH]]`` link extracted from a note body.

    ``target`` is the raw path string from the link, after stripping any
    org ``::SEARCH`` suffix but before any filesystem resolution.
    Resolution (relative-to-parent, ``~`` expansion) happens at check
    time so the parser stays I/O-free.
    """

    target: str
    description: str | None
    line: int
    col: int


@dataclass
class Note:
    """A single file in the corpus, parsed but not yet checked.

    ``indexed_only`` is True for notes that live under a directory marked
    with a ``.ignore`` file: they participate in the corpus index (so
    cross-tree denote links resolve) but no checks are run against them
    and no issues are reported about them.
    """

    path: Path
    filename: ParsedFilename
    front_matter: FrontMatter | None
    body: str
    links: tuple[Link, ...] = ()
    file_links: tuple[FileLink, ...] = ()
    is_attachment: bool = False
    read_error: str | None = None
    indexed_only: bool = False


@dataclass(frozen=True)
class Issue:
    """A single lint finding."""

    path: Path
    line: int
    col: int
    severity: Severity
    code: str
    message: str


@dataclass
class Context:
    """Corpus-level state passed to per-note check functions.

    Built once during the corpus pass and read-only thereafter.
    """

    notes_by_id: dict[str, list[Note]] = field(default_factory=dict)
    incoming_links: dict[str, list[Note]] = field(default_factory=dict)
    all_keywords: set[str] = field(default_factory=set)
    note_extensions: frozenset[str] = frozenset({"org", "md", "txt"})
    image_extensions: frozenset[str] = frozenset(
        {"png", "jpg", "jpeg", "gif", "svg", "webp"}
    )
    image_tag: str = "image"
    allow_attachment_aliases: bool = False
    # Resolved corpus roots (the input paths the user passed). W006 uses
    # these to scope file-link existence checks: only links resolving
    # under a root are validated; out-of-corpus paths are skipped.
    corpus_roots: tuple[Path, ...] = ()
