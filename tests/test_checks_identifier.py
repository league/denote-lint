"""E001 (duplicate identifier) coverage."""

from __future__ import annotations

from denote_lint.checks.identifier import check_e001
from tests.conftest import make_context, make_note


def test_strict_two_notes_fires() -> None:
    a = make_note("20240115T093000--a.org")
    b = make_note("20240115T093000--b.org")
    ctx = make_context([a, b])
    out = list(check_e001(ctx))
    assert len(out) == 1
    assert out[0].code == "E001"
    assert "20240115T093000" in out[0].message
    assert "--a.org" in out[0].message
    assert "--b.org" in out[0].message


def test_strict_attachment_alias_still_fires() -> None:
    note = make_note("20240115T093000--n.org")
    photo = make_note("20240115T093000--n.jpg")
    ctx = make_context([note, photo])
    assert ctx.allow_attachment_aliases is False
    out = list(check_e001(ctx))
    assert [i.code for i in out] == ["E001"]


def test_alias_mode_one_note_one_attachment_silent() -> None:
    note = make_note("20240115T093000--n.org")
    photo = make_note("20240115T093000--n.jpg")
    ctx = make_context([note, photo], allow_attachment_aliases=True)
    assert list(check_e001(ctx)) == []


def test_alias_mode_two_notes_still_fires() -> None:
    a = make_note("20240115T093000--a.org")
    b = make_note("20240115T093000--b.org")
    ctx = make_context([a, b], allow_attachment_aliases=True)
    out = list(check_e001(ctx))
    assert [i.code for i in out] == ["E001"]


def test_alias_mode_two_attachments_still_fires() -> None:
    a = make_note("20240115T093000--photo.jpg")
    b = make_note("20240115T093000--diagram.png")
    ctx = make_context([a, b], allow_attachment_aliases=True)
    out = list(check_e001(ctx))
    assert [i.code for i in out] == ["E001"]


def test_silent_on_distinct_ids() -> None:
    a = make_note("20240115T093000--a.org")
    b = make_note("20240116T100000--b.org")
    ctx = make_context([a, b])
    assert list(check_e001(ctx)) == []


def test_one_issue_per_group() -> None:
    a = make_note("20240115T093000--a.org")
    b = make_note("20240115T093000--b.org")
    c = make_note("20240115T093000--c.org")
    ctx = make_context([a, b, c])
    out = list(check_e001(ctx))
    assert len(out) == 1
