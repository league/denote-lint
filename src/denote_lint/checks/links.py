"""Link checks: E004 (denote target missing), W006 (file: target
missing), I005 (description out of sync with title).

W006 covers org ``[[file:...]]`` links only. Markdown plain links are
deliberately not handled: distinguishing local file paths from URLs in
arbitrary ``[text](path)`` text remains out of scope.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

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


@register_per_note("W006", "warning", "link")
def check_w006(note: Note, ctx: Context) -> Iterable[Issue]:
    """Org ``[[file:...]]`` link points to a missing file inside the corpus.

    Resolution rules:

    - Strip any ``::SEARCH`` suffix (handled by the parser).
    - Expand a leading ``~`` against the user's home directory.
    - Resolve relative paths against the linking note's parent.
    - Follow symlinks via :meth:`Path.resolve` so that the existence
      check and the in-corpus check see the same canonical form.

    Scope: only file-links whose resolved target sits under one of the
    configured corpus roots are validated. Out-of-corpus targets
    (``/etc/passwd``, ``~/Documents/report.pdf``, ...) are silently
    skipped -- denote-lint does not know whether those files are
    expected to exist on the current machine.
    """
    if not note.file_links or not ctx.corpus_roots:
        return

    note_dir = note.path.parent
    for link in note.file_links:
        resolved = _resolve_link_target(link.target, note_dir)
        if resolved is None:
            continue
        if not _under_any_root(resolved, ctx.corpus_roots):
            continue
        if resolved.exists():
            continue
        yield Issue(
            path=note.path,
            line=link.line,
            col=link.col,
            severity="warning",
            code="W006",
            message=f"file: link target does not exist: {link.target}",
        )


def _resolve_link_target(target: str, note_dir: Path) -> Path | None:
    """Resolve a raw ``file:`` link target to an absolute, canonical path.

    Returns ``None`` if the target is structurally not a local
    filesystem path (e.g. has a URL-like scheme).
    """
    if not target:
        return None
    # Bail on obvious URL-shaped targets like ``file://host/...`` or
    # anything that has a non-trivial scheme. The org file: prefix is
    # already stripped by the regex; what remains should be a plain
    # path.
    if target.startswith("//"):
        return None
    expanded = Path(target).expanduser()
    if not expanded.is_absolute():
        expanded = note_dir / expanded
    try:
        return expanded.resolve()
    except OSError:
        return expanded.absolute()


def _under_any_root(path: Path, roots: tuple[Path, ...]) -> bool:
    for root in roots:
        try:
            path.relative_to(root)
        except ValueError:
            continue
        return True
    return False


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
