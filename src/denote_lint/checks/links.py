"""Link checks: E004 (target missing), I005 (description out of sync with title).

W006 (local non-denote link missing file) is reserved but intentionally
not implemented in v0.1 -- extracting non-denote links from arbitrary
org/markdown bodies is out of scope for the first cut.
"""

from __future__ import annotations

from collections.abc import Iterable

from denote_lint.checks import register_per_note
from denote_lint.models import Context, Issue, Note


@register_per_note("E004", "error", "link")
def check_e004(note: Note, ctx: Context) -> Iterable[Issue]:
    for link in note.links:
        if not link.target_id:
            yield Issue(
                path=note.path,
                line=link.line,
                col=link.col,
                severity="error",
                code="E004",
                message="denote link has no identifier",
            )
            continue
        if link.target_id not in ctx.notes_by_id:
            yield Issue(
                path=note.path,
                line=link.line,
                col=link.col,
                severity="error",
                code="E004",
                message=f"denote link target {link.target_id} not found in corpus",
            )


@register_per_note("I005", "info", "link")
def check_i005(note: Note, ctx: Context) -> Iterable[Issue]:
    """Link description is out of sync with the target's current title.

    Skipped if the link has no description or the target is missing /
    has no title in its front matter. The check is intentionally
    informational -- many users write descriptive link text that
    intentionally differs from the title.
    """
    for link in note.links:
        if not link.description:
            continue
        targets = ctx.notes_by_id.get(link.target_id, [])
        if not targets:
            continue
        target = targets[0]
        if target.front_matter is None:
            continue
        title = target.front_matter.title
        if not title:
            continue
        if link.description != title:
            yield Issue(
                path=note.path,
                line=link.line,
                col=link.col,
                severity="info",
                code="I005",
                message=(
                    f"link description {link.description!r} differs from "
                    f"target title {title!r}"
                ),
            )
