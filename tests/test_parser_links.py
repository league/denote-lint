"""Link parser coverage."""

from __future__ import annotations

from textwrap import dedent

from denote_lint.parser.links import extract_links


class TestOrg:
    def test_bare_link(self) -> None:
        links = extract_links("org", "See [[denote:20240115T093000]] now.\n")
        assert len(links) == 1
        assert links[0].target_id == "20240115T093000"
        assert links[0].description is None
        assert links[0].line == 1
        assert links[0].col == 5  # 1-based; "See " is 4 chars

    def test_link_with_description(self) -> None:
        links = extract_links(
            "org", "[[denote:20240115T093000][My note]]\n"
        )
        assert len(links) == 1
        assert links[0].target_id == "20240115T093000"
        assert links[0].description == "My note"

    def test_link_with_search_suffix(self) -> None:
        links = extract_links(
            "org", "[[denote:20240115T093000::*Some heading]]\n"
        )
        assert len(links) == 1
        assert links[0].target_id == "20240115T093000"
        assert links[0].description is None

    def test_link_with_search_and_description(self) -> None:
        body = "[[denote:20240115T093000::*Heading][Desc]]\n"
        links = extract_links("org", body)
        assert len(links) == 1
        assert links[0].target_id == "20240115T093000"
        assert links[0].description == "Desc"

    def test_multiple_links(self) -> None:
        body = dedent(
            """\
            First [[denote:20240115T093000]].
            Second [[denote:20240116T100000][later]].
            Third line no link.
            Fourth [[denote:20240117T120000]].
            """
        )
        links = extract_links("org", body)
        assert [link.target_id for link in links] == [
            "20240115T093000",
            "20240116T100000",
            "20240117T120000",
        ]
        assert [link.line for link in links] == [1, 2, 4]

    def test_no_links_when_extension_md(self) -> None:
        # The org form should not match in markdown.
        links = extract_links("md", "[[denote:20240115T093000]]")
        assert links == ()

    def test_no_match_when_no_denote_links(self) -> None:
        assert extract_links("org", "Just prose. No links.") == ()

    def test_non_denote_org_link_ignored(self) -> None:
        body = "[[https://example.com][site]]\n"
        assert extract_links("org", body) == ()


class TestMarkdown:
    def test_basic_link(self) -> None:
        links = extract_links("md", "See [my note](denote:20240115T093000).\n")
        assert len(links) == 1
        assert links[0].target_id == "20240115T093000"
        assert links[0].description == "my note"

    def test_empty_description(self) -> None:
        links = extract_links("md", "[](denote:20240115T093000)\n")
        assert len(links) == 1
        assert links[0].target_id == "20240115T093000"
        assert links[0].description is None

    def test_no_match_for_org_in_md(self) -> None:
        assert extract_links("md", "[[denote:20240115T093000]]") == ()

    def test_non_denote_md_link_ignored(self) -> None:
        assert extract_links("md", "[name](https://example.com)") == ()


class TestNonNoteExtensions:
    def test_txt_no_links(self) -> None:
        assert extract_links("txt", "[[denote:20240115T093000]]") == ()

    def test_attachment_no_links(self) -> None:
        assert extract_links("png", "anything") == ()


class TestLineCol:
    def test_link_on_third_line(self) -> None:
        body = "line1\nline2\nlink [[denote:20240115T093000]] here\n"
        links = extract_links("org", body)
        assert len(links) == 1
        assert links[0].line == 3
        assert links[0].col == 6  # 1-based; "link " is 5 chars
