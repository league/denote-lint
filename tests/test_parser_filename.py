"""Filename parser coverage."""

from __future__ import annotations

from datetime import datetime

import pytest

from denote_lint.parser.filename import parse_filename


class TestWellFormed:
    def test_identifier_only(self) -> None:
        pf = parse_filename("20240115T093000.org")
        assert pf.identifier == "20240115T093000"
        assert pf.identifier_dt == datetime(2024, 1, 15, 9, 30, 0)
        assert pf.signature is None
        assert pf.title_slug is None
        assert pf.keywords == ()
        assert pf.extension == "org"
        assert pf.parse_errors == ()

    def test_title_only(self) -> None:
        pf = parse_filename("20240115T093000--my-note.org")
        assert pf.title_slug == "my-note"
        assert pf.keywords == ()
        assert pf.parse_errors == ()

    def test_keywords_only(self) -> None:
        pf = parse_filename("20240115T093000__tag1_tag2.org")
        assert pf.title_slug is None
        assert pf.keywords == ("tag1", "tag2")
        assert pf.parse_errors == ()

    def test_title_and_keywords(self) -> None:
        pf = parse_filename("20240115T093000--my-note__tag1_tag2.org")
        assert pf.title_slug == "my-note"
        assert pf.keywords == ("tag1", "tag2")
        assert pf.parse_errors == ()

    def test_full_form_with_signature(self) -> None:
        pf = parse_filename("20240115T093000==sig01--my-note__tag1.org")
        assert pf.signature == "sig01"
        assert pf.title_slug == "my-note"
        assert pf.keywords == ("tag1",)
        assert pf.parse_errors == ()

    def test_signature_only(self) -> None:
        pf = parse_filename("20240115T093000==sig01.org")
        assert pf.signature == "sig01"
        assert pf.title_slug is None
        assert pf.keywords == ()
        assert pf.parse_errors == ()

    @pytest.mark.parametrize(
        "ext", ["org", "md", "txt", "png", "jpg", "pdf", "tar"]
    )
    def test_various_extensions(self, ext: str) -> None:
        pf = parse_filename(f"20240115T093000--note.{ext}")
        assert pf.extension == ext
        assert pf.parse_errors == ()


class TestIdentifier:
    def test_e002_too_short(self) -> None:
        pf = parse_filename("2024.org")
        assert "E002" in pf.parse_errors

    def test_e002_no_t_separator(self) -> None:
        pf = parse_filename("20240115093000.org")
        assert "E002" in pf.parse_errors

    def test_e002_lowercase_t(self) -> None:
        pf = parse_filename("20240115t093000.org")
        # lowercase t is allowed in stem charset, but identifier regex is uppercase T
        assert "E002" in pf.parse_errors

    def test_e003_invalid_date(self) -> None:
        pf = parse_filename("20240230T093000.org")
        assert "E003" in pf.parse_errors
        assert pf.identifier_dt is None

    def test_e003_invalid_time(self) -> None:
        pf = parse_filename("20240115T253000.org")
        assert "E003" in pf.parse_errors

    def test_valid_identifier_dt(self) -> None:
        pf = parse_filename("20240115T093000.org")
        assert pf.identifier_dt == datetime(2024, 1, 15, 9, 30, 0)


class TestDisallowedChars:
    @pytest.mark.parametrize(
        "name",
        [
            "20240115T093000--Bad-Title.org",
            "20240115T093000--my note.org",
            "20240115T093000--my.note.org",
            "20240115T093000--my!note.org",
        ],
    )
    def test_e009_uppercase_or_space_or_punctuation(self, name: str) -> None:
        pf = parse_filename(name)
        assert "E009" in pf.parse_errors


class TestSeparatorEdges:
    def test_e010_trailing_double_underscore(self) -> None:
        pf = parse_filename("20240115T093000__tag1__.org")
        assert "E010" in pf.parse_errors

    def test_e010_empty_keyword_block(self) -> None:
        pf = parse_filename("20240115T093000__.org")
        assert "E010" in pf.parse_errors
        assert pf.keywords == ()

    def test_e010_empty_title(self) -> None:
        pf = parse_filename("20240115T093000--.org")
        assert "E010" in pf.parse_errors
        assert pf.title_slug is None

    def test_e010_empty_signature(self) -> None:
        pf = parse_filename("20240115T093000==.org")
        assert "E010" in pf.parse_errors
        assert pf.signature is None

    def test_e010_double_underscore_inside_keywords(self) -> None:
        pf = parse_filename("20240115T093000__tag1__tag2.org")
        assert "E010" in pf.parse_errors


class TestKeywordHygiene:
    def test_w007_dash_in_keyword(self) -> None:
        pf = parse_filename("20240115T093000__multi-word_tag2.org")
        assert "W007" in pf.parse_errors
        assert pf.keywords == ("multi-word", "tag2")


class TestNoExtension:
    def test_no_extension_attachment_like(self) -> None:
        pf = parse_filename("20240115T093000")
        assert pf.extension == ""
        assert pf.parse_errors == ()


class TestFreshnessOfRaw:
    def test_raw_preserved(self) -> None:
        raw = "20240115T093000--My-Bad-Title.org"
        pf = parse_filename(raw)
        assert pf.raw == raw
