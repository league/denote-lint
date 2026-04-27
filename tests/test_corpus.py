"""Corpus loader coverage."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import pytest

from denote_lint.corpus import (
    CorpusOptions,
    build_context,
    discover_files,
    load_note,
    read_file,
)


def _write(p: Path, content: str | bytes) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, str):
        p.write_text(content, encoding="utf-8")
    else:
        p.write_bytes(content)


class TestReadFile:
    def test_plain_utf8(self, tmp_path: Path) -> None:
        f = tmp_path / "x.org"
        f.write_text("hello\n", encoding="utf-8")
        text, err = read_file(f)
        assert err is None
        assert text == "hello\n"

    def test_strips_bom(self, tmp_path: Path) -> None:
        f = tmp_path / "x.org"
        f.write_bytes(b"\xef\xbb\xbfhello\n")
        text, err = read_file(f)
        assert err is None
        assert text == "hello\n"

    def test_normalises_crlf(self, tmp_path: Path) -> None:
        f = tmp_path / "x.org"
        f.write_bytes(b"line1\r\nline2\r\n")
        text, err = read_file(f)
        assert err is None
        assert text == "line1\nline2\n"

    def test_normalises_cr_only(self, tmp_path: Path) -> None:
        f = tmp_path / "x.org"
        f.write_bytes(b"line1\rline2\r")
        text, err = read_file(f)
        assert err is None
        assert text == "line1\nline2\n"

    def test_non_utf8_returns_error(self, tmp_path: Path) -> None:
        f = tmp_path / "x.org"
        f.write_bytes(b"\xff\xfe\xfd")
        text, err = read_file(f)
        assert text is None
        assert err is not None and "UTF-8" in err

    def test_missing_file(self, tmp_path: Path) -> None:
        text, err = read_file(tmp_path / "nope.org")
        assert text is None
        assert err is not None


class TestDiscoverFiles:
    def test_walks_nested(self, tmp_path: Path) -> None:
        _write(tmp_path / "a" / "20240115T093000--n1.org", "x")
        _write(tmp_path / "b" / "c" / "20240116T100000--n2.org", "x")
        _write(tmp_path / "ignore.txt", "x")  # no identifier-shaped name; still .txt note ext
        opts = CorpusOptions()
        found = sorted(p.name for p in discover_files([tmp_path], opts))
        assert "20240115T093000--n1.org" in found
        assert "20240116T100000--n2.org" in found
        assert "ignore.txt" in found

    def test_skips_unknown_extensions(self, tmp_path: Path) -> None:
        _write(tmp_path / "20240115T093000--note.org", "x")
        _write(tmp_path / "binary.exe", "x")
        opts = CorpusOptions()
        found = sorted(p.name for p in discover_files([tmp_path], opts))
        assert "20240115T093000--note.org" in found
        assert "binary.exe" not in found

    def test_includes_image_extensions(self, tmp_path: Path) -> None:
        _write(tmp_path / "20240115T093000--photo.jpg", b"\xff\xd8\xff")
        opts = CorpusOptions()
        found = list(discover_files([tmp_path], opts))
        assert any(p.name == "20240115T093000--photo.jpg" for p in found)

    def test_explicit_file_is_yielded(self, tmp_path: Path) -> None:
        f = tmp_path / "explicit.bak"
        _write(f, "x")
        opts = CorpusOptions()
        found = list(discover_files([f], opts))
        assert found == [f]

    def test_exclude_glob(self, tmp_path: Path) -> None:
        _write(tmp_path / "20240115T093000--note.org", "x")
        _write(tmp_path / "_drafts" / "20240116T100000--draft.org", "x")
        opts = CorpusOptions(exclude=("*_drafts*", "*/_drafts/*"))
        found = sorted(p.name for p in discover_files([tmp_path], opts))
        assert "20240115T093000--note.org" in found
        assert "20240116T100000--draft.org" not in found


class TestLoadNote:
    def test_org_with_links(self, tmp_path: Path) -> None:
        f = tmp_path / "20240115T093000--note__tag1.org"
        f.write_text(
            dedent(
                """\
                #+title:      Hello
                #+identifier: 20240115T093000

                Body with [[denote:20240116T100000][later]] link.
                """
            ),
            encoding="utf-8",
        )
        note = load_note(f, CorpusOptions())
        assert note.filename.identifier == "20240115T093000"
        assert note.front_matter is not None
        assert note.front_matter.title == "Hello"
        assert len(note.links) == 1
        assert note.links[0].target_id == "20240116T100000"
        assert note.links[0].description == "later"
        assert note.is_attachment is False

    def test_attachment_no_frontmatter_no_links(self, tmp_path: Path) -> None:
        f = tmp_path / "20240115T093000--photo.jpg"
        f.write_bytes(b"\xff\xd8\xff\xe0fake jpeg")
        note = load_note(f, CorpusOptions())
        assert note.is_attachment is True
        assert note.front_matter is None
        assert note.links == ()
        # Read error should not be set: read_file may or may not decode the
        # stub; even if it can't, an attachment doesn't need its body.
        # We just don't crash.

    def test_unreadable_file_records_read_error(self, tmp_path: Path) -> None:
        f = tmp_path / "20240115T093000--bad.org"
        f.write_bytes(b"\xff\xfe\xfd\x00")
        note = load_note(f, CorpusOptions())
        assert note.read_error is not None
        assert note.front_matter is None
        assert note.body == ""


class TestBuildContext:
    def _make(
        self, tmp_path: Path, name: str, content: str = ""
    ) -> Path:
        f = tmp_path / name
        f.write_text(content, encoding="utf-8")
        return f

    def test_indexes_by_identifier(self, tmp_path: Path) -> None:
        a = self._make(tmp_path, "20240115T093000--a.org", "")
        b = self._make(tmp_path, "20240115T093000--b.org", "")
        opts = CorpusOptions()
        notes = [load_note(a, opts), load_note(b, opts)]
        ctx = build_context(notes, opts)
        assert "20240115T093000" in ctx.notes_by_id
        assert len(ctx.notes_by_id["20240115T093000"]) == 2

    def test_collects_keywords_from_filename_and_frontmatter(
        self, tmp_path: Path
    ) -> None:
        f = self._make(
            tmp_path,
            "20240115T093000--n__tag1_tag2.org",
            "#+filetags: :tag2:tag3:\n",
        )
        opts = CorpusOptions()
        notes = [load_note(f, opts)]
        ctx = build_context(notes, opts)
        assert ctx.all_keywords == {"tag1", "tag2", "tag3"}

    def test_reverse_link_graph(self, tmp_path: Path) -> None:
        a = self._make(
            tmp_path,
            "20240115T093000--a.org",
            "[[denote:20240116T100000]]\n",
        )
        b = self._make(tmp_path, "20240116T100000--b.org", "")
        opts = CorpusOptions()
        notes = [load_note(a, opts), load_note(b, opts)]
        ctx = build_context(notes, opts)
        assert "20240116T100000" in ctx.incoming_links
        assert ctx.incoming_links["20240116T100000"][0].path == a


@pytest.mark.skipif(
    not hasattr(Path, "symlink_to"), reason="symlinks unsupported"
)
class TestSymlinkLoops:
    def test_symlink_loop_does_not_recurse_forever(self, tmp_path: Path) -> None:
        d = tmp_path / "real"
        d.mkdir()
        (d / "20240115T093000--n.org").write_text("", encoding="utf-8")
        try:
            (tmp_path / "loop").symlink_to(d, target_is_directory=True)
            (d / "back").symlink_to(tmp_path, target_is_directory=True)
        except OSError:
            pytest.skip("symlinks not permitted on this filesystem")
        opts = CorpusOptions(follow_symlinks=True)
        # Just assert termination, not a particular set of files.
        found = list(discover_files([tmp_path], opts))
        assert any(p.name == "20240115T093000--n.org" for p in found)
