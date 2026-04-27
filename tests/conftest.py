"""Shared test helpers for check tests."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from denote_lint.models import Context, FrontMatter, Link, Note
from denote_lint.parser.filename import parse_filename


def make_note(
    name: str,
    *,
    path: Path | None = None,
    fm_title: str | None = None,
    fm_identifier: str | None = None,
    fm_date: datetime | None = None,
    fm_keywords: tuple[str, ...] = (),
    fm_parse_errors: tuple[str, ...] = (),
    no_front_matter: bool = False,
    body: str = "",
    links: tuple[Link, ...] = (),
    is_attachment: bool | None = None,
    read_error: str | None = None,
) -> Note:
    """Build a Note for tests, parsing the filename for realism."""
    pf = parse_filename(name)
    if is_attachment is None:
        is_attachment = pf.extension.lower() not in {"org", "md", "txt"}
    fm: FrontMatter | None
    if no_front_matter or is_attachment:
        fm = None
    else:
        fm = FrontMatter(
            title=fm_title,
            identifier=fm_identifier,
            date=fm_date,
            keywords=fm_keywords,
            parse_errors=fm_parse_errors,
        )
    return Note(
        path=path or Path(name),
        filename=pf,
        front_matter=fm,
        body=body,
        links=links,
        is_attachment=is_attachment,
        read_error=read_error,
    )


def make_context(notes: list[Note], **kwargs: object) -> Context:
    """Build a Context indexing the given notes."""
    notes_by_id: dict[str, list[Note]] = {}
    incoming: dict[str, list[Note]] = {}
    all_keywords: set[str] = set()
    for note in notes:
        ident = note.filename.identifier
        if ident:
            notes_by_id.setdefault(ident, []).append(note)
        for kw in note.filename.keywords:
            all_keywords.add(kw)
        if note.front_matter is not None:
            for kw in note.front_matter.keywords:
                all_keywords.add(kw)
        for link in note.links:
            if link.target_id:
                incoming.setdefault(link.target_id, []).append(note)
    ctx = Context(
        notes_by_id=notes_by_id,
        incoming_links=incoming,
        all_keywords=all_keywords,
    )
    for k, v in kwargs.items():
        setattr(ctx, k, v)
    return ctx
