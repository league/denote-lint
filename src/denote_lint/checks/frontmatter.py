"""Front-matter checks: E005-E008, W002-W004.

All issues are reported at line 1, col 1; the spec accepts that
front-matter problems aren't tied to a specific in-file location.
"""

from __future__ import annotations

from collections.abc import Iterable

from denote_lint.checks import register_per_note
from denote_lint.models import Context, Issue, Note
from denote_lint.sluggify import sluggify_title


def _issue(note: Note, code: str, severity: str, message: str) -> Issue:
    return Issue(
        path=note.path,
        line=1,
        col=1,
        severity=severity,  # type: ignore[arg-type]
        code=code,
        message=message,
    )


@register_per_note("E005", "error", "frontmatter")
def check_e005(note: Note, _ctx: Context) -> Iterable[Issue]:
    if note.is_attachment or note.front_matter is None:
        return
    fm_id = note.front_matter.identifier
    fn_id = note.filename.identifier
    if fm_id and fn_id and fm_id != fn_id:
        yield _issue(
            note,
            "E005",
            "error",
            f"front matter identifier {fm_id} does not match filename {fn_id}",
        )


@register_per_note("E006", "error", "frontmatter")
def check_e006(note: Note, _ctx: Context) -> Iterable[Issue]:
    if note.is_attachment or note.front_matter is None:
        return
    if not note.front_matter.identifier:
        yield _issue(note, "E006", "error", "front matter missing identifier")


@register_per_note("E007", "error", "frontmatter")
def check_e007(note: Note, _ctx: Context) -> Iterable[Issue]:
    if note.is_attachment or note.front_matter is None:
        return
    if not note.front_matter.title:
        yield _issue(note, "E007", "error", "front matter missing title")


@register_per_note("E008", "error", "frontmatter")
def check_e008(note: Note, _ctx: Context) -> Iterable[Issue]:
    if note.is_attachment:
        return
    if note.read_error is not None:
        yield _issue(note, "E008", "error", note.read_error)
        return
    if note.front_matter is None:
        return
    if "E008" in note.front_matter.parse_errors:
        yield _issue(note, "E008", "error", "front matter is unparseable")


@register_per_note("W002", "warning", "frontmatter")
def check_w002(note: Note, _ctx: Context) -> Iterable[Issue]:
    if note.is_attachment or note.front_matter is None:
        return
    fm_title = note.front_matter.title
    fn_slug = note.filename.title_slug
    if not fm_title or not fn_slug:
        return
    expected = sluggify_title(fm_title)
    if expected != fn_slug:
        yield _issue(
            note,
            "W002",
            "warning",
            f"front matter title slug {expected!r} does not match filename slug {fn_slug!r}",
        )


@register_per_note("W003", "warning", "frontmatter")
def check_w003(note: Note, _ctx: Context) -> Iterable[Issue]:
    if note.is_attachment or note.front_matter is None:
        return
    fm_kw = set(note.front_matter.keywords)
    fn_kw = set(note.filename.keywords)
    if fm_kw == fn_kw:
        return
    parts: list[str] = []
    only_fm = sorted(fm_kw - fn_kw)
    only_fn = sorted(fn_kw - fm_kw)
    if only_fm:
        parts.append(f"only in front matter: {only_fm}")
    if only_fn:
        parts.append(f"only in filename: {only_fn}")
    yield _issue(
        note,
        "W003",
        "warning",
        f"front matter and filename keywords differ ({'; '.join(parts)})",
    )


@register_per_note("W004", "warning", "frontmatter")
def check_w004(note: Note, _ctx: Context) -> Iterable[Issue]:
    if note.is_attachment or note.front_matter is None:
        return
    fm = note.front_matter
    if fm.date is None or note.filename.identifier_dt is None:
        return
    fm_day = fm.date.date()
    id_day = note.filename.identifier_dt.date()
    if fm_day != id_day:
        yield _issue(
            note,
            "W004",
            "warning",
            f"front matter date {fm_day} differs from identifier day {id_day}",
        )
