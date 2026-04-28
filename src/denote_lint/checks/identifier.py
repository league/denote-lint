"""Corpus-level identifier check: E001 (duplicate identifier).

Default mode is strict: any two files sharing an identifier triggers
E001. With ``--allow-attachment-aliases`` the constraint is relaxed:
one note plus one attachment may share an identifier; two notes still
trigger, two attachments still trigger.
"""

from __future__ import annotations

from collections.abc import Iterable

from denote_lint.checks import register_corpus
from denote_lint.models import Context, Issue


@register_corpus("E001", "error", "identifier")
def check_e001(ctx: Context) -> Iterable[Issue]:
    for ident, notes in sorted(ctx.notes_by_id.items()):
        if not ident or len(notes) <= 1:
            continue

        if ctx.allow_attachment_aliases:
            note_files = [n for n in notes if not n.is_attachment]
            attachments = [n for n in notes if n.is_attachment]
            if len(note_files) <= 1 and len(attachments) <= 1:
                continue

        sorted_paths = sorted(str(n.path) for n in notes)
        checked = [n for n in notes if not n.indexed_only]
        anchor_pool = checked if checked else notes
        first = min(anchor_pool, key=lambda n: str(n.path))
        yield Issue(
            path=first.path,
            line=1,
            col=1,
            severity="error",
            code="E001",
            message=(
                f"duplicate identifier {ident}: "
                + ", ".join(sorted_paths)
            ),
        )
