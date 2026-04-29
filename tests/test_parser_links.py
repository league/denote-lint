"""Link parser coverage."""

from __future__ import annotations

from textwrap import dedent

from denote_lint.parser.links import extract_file_links, extract_links


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


class TestFileLinks:
    def test_relative_path(self) -> None:
        out = extract_file_links("org", "See [[file:./other.org]] for context.\n")
        assert len(out) == 1
        assert out[0].target == "./other.org"
        assert out[0].description is None

    def test_absolute_path(self) -> None:
        out = extract_file_links("org", "[[file:/home/me/note.org]]\n")
        assert len(out) == 1
        assert out[0].target == "/home/me/note.org"

    def test_with_description(self) -> None:
        out = extract_file_links("org", "[[file:./img.png][An image]]\n")
        assert len(out) == 1
        assert out[0].target == "./img.png"
        assert out[0].description == "An image"

    def test_search_suffix_stripped(self) -> None:
        out = extract_file_links("org", "[[file:./foo.org::*Heading]]\n")
        assert len(out) == 1
        assert out[0].target == "./foo.org"

    def test_search_suffix_with_description(self) -> None:
        out = extract_file_links("org", "[[file:./foo.org::*Heading][Desc]]\n")
        assert len(out) == 1
        assert out[0].target == "./foo.org"
        assert out[0].description == "Desc"

    def test_multiple_links_line_tracking(self) -> None:
        body = dedent(
            """\
            First [[file:./a.org]].
            No link here.
            Last [[file:./b.org][b]].
            """
        )
        out = extract_file_links("org", body)
        assert [link.target for link in out] == ["./a.org", "./b.org"]
        assert [link.line for link in out] == [1, 3]

    def test_denote_link_ignored(self) -> None:
        assert extract_file_links("org", "[[denote:20240115T093000]]\n") == ()

    def test_url_ignored(self) -> None:
        assert extract_file_links("org", "[[https://example.com][site]]\n") == ()

    def test_org_bracket_form_in_md_ignored(self) -> None:
        # ``[[file:./other.org]]`` is org bracket syntax, not markdown
        # syntax. Markdown extraction should not pick it up.
        assert extract_file_links("md", "[[file:./other.org]]") == ()

    def test_empty_target_skipped(self) -> None:
        # ``::`` with nothing in front isn't a meaningful path.
        assert extract_file_links("org", "[[file:::*Heading]]\n") == ()


class TestOrgBareFileLinks:
    """Bare-path org links (no ``file:`` prefix) recognised when the
    target has an unambiguous path prefix.
    """

    def test_relative_dot_slash(self) -> None:
        out = extract_file_links("org", "[[./other.org][Other]]\n")
        assert len(out) == 1
        assert out[0].target == "./other.org"
        assert out[0].description == "Other"

    def test_relative_dotdot(self) -> None:
        out = extract_file_links("org", "[[../parent/note.org]]\n")
        assert len(out) == 1
        assert out[0].target == "../parent/note.org"

    def test_absolute(self) -> None:
        out = extract_file_links("org", "[[/abs/note.org]]\n")
        assert len(out) == 1
        assert out[0].target == "/abs/note.org"

    def test_home(self) -> None:
        out = extract_file_links("org", "[[~/notes/foo.org]]\n")
        assert len(out) == 1
        assert out[0].target == "~/notes/foo.org"

    def test_search_suffix_stripped(self) -> None:
        out = extract_file_links("org", "[[./foo.org::*Heading]]\n")
        assert len(out) == 1
        assert out[0].target == "./foo.org"

    def test_internal_heading_link_skipped(self) -> None:
        assert extract_file_links("org", "[[*Some heading]]\n") == ()

    def test_internal_anchor_link_skipped(self) -> None:
        assert extract_file_links("org", "[[#custom-id]]\n") == ()

    def test_search_term_link_skipped(self) -> None:
        # Bare names without a path prefix are org search-term links.
        # Treating them as paths would produce W006 false positives.
        assert extract_file_links("org", "[[search-term]]\n") == ()

    def test_filename_in_cwd_without_prefix_skipped(self) -> None:
        # Conservative: ambiguous with org search. User must write
        # ``./foo.org`` or ``file:foo.org`` to opt in.
        assert extract_file_links("org", "[[foo.org]]\n") == ()


class TestMarkdownFileLinks:
    def test_relative_dot_slash(self) -> None:
        out = extract_file_links("md", "See [other](./other.md).\n")
        assert len(out) == 1
        assert out[0].target == "./other.md"
        assert out[0].description == "other"

    def test_relative_no_prefix(self) -> None:
        # CommonMark accepts plain ``foo.md`` as relative-to-document.
        out = extract_file_links("md", "[other](other.md)\n")
        assert len(out) == 1
        assert out[0].target == "other.md"

    def test_image_syntax_extracted(self) -> None:
        # ``![alt](path)`` -- the regex matches the ``[alt](path)``
        # tail; image targets are real files we want to verify.
        out = extract_file_links("md", "![diagram](./img/foo.png)\n")
        assert len(out) == 1
        assert out[0].target == "./img/foo.png"

    def test_url_skipped(self) -> None:
        assert extract_file_links("md", "[site](https://example.com)\n") == ()

    def test_mailto_skipped(self) -> None:
        assert extract_file_links("md", "[me](mailto:me@example.com)\n") == ()

    def test_denote_link_skipped(self) -> None:
        assert extract_file_links("md", "[note](denote:20240115T093000)\n") == ()

    def test_strips_double_quoted_title(self) -> None:
        out = extract_file_links("md", '[other](./other.md "A title")\n')
        assert len(out) == 1
        assert out[0].target == "./other.md"

    def test_strips_single_quoted_title(self) -> None:
        out = extract_file_links("md", "[other](./other.md 'A title')\n")
        assert len(out) == 1
        assert out[0].target == "./other.md"

    def test_strips_url_fragment(self) -> None:
        out = extract_file_links("md", "[other](./other.md#section)\n")
        assert len(out) == 1
        assert out[0].target == "./other.md"

    def test_strips_url_query(self) -> None:
        out = extract_file_links("md", "[other](./other.md?v=2)\n")
        assert len(out) == 1
        assert out[0].target == "./other.md"


class TestFenceMasking:
    """Code-fence regions must be skipped by both extract_links and
    extract_file_links so they don't produce false-positive E004 / I005
    / W006 inside example/source blocks.
    """

    def test_org_src_block_hides_denote_link(self) -> None:
        body = dedent(
            """\
            #+begin_src text
            [[denote:20240115T093000]]
            #+end_src
            """
        )
        assert extract_links("org", body) == ()

    def test_org_src_block_hides_file_link(self) -> None:
        body = dedent(
            """\
            #+begin_src python
            [[file:./should-not-warn.py]]
            #+end_src
            """
        )
        assert extract_file_links("org", body) == ()

    def test_org_example_block_hides_links(self) -> None:
        body = dedent(
            """\
            #+begin_example
            [[denote:20240115T093000]]
            [[./bare.org]]
            #+end_example
            """
        )
        assert extract_links("org", body) == ()
        assert extract_file_links("org", body) == ()

    def test_org_quote_block_links_still_extracted(self) -> None:
        # Quote blocks carry meaningful prose; we deliberately do not
        # mask them out.
        body = dedent(
            """\
            #+begin_quote
            See [[denote:20240115T093000]] for context.
            #+end_quote
            """
        )
        out = extract_links("org", body)
        assert len(out) == 1

    def test_org_link_outside_block_still_extracted(self) -> None:
        body = dedent(
            """\
            Before [[denote:20240115T093000]].
            #+begin_src text
            [[denote:20990101T000000]]
            #+end_src
            After [[denote:20240116T100000]].
            """
        )
        out = extract_links("org", body)
        assert [link.target_id for link in out] == [
            "20240115T093000",
            "20240116T100000",
        ]

    def test_org_block_case_insensitive(self) -> None:
        body = dedent(
            """\
            #+BEGIN_SRC python
            [[denote:20240115T093000]]
            #+END_SRC
            """
        )
        assert extract_links("org", body) == ()

    def test_md_fence_hides_denote_link(self) -> None:
        body = dedent(
            """\
            ```
            [text](denote:20240115T093000)
            ```
            """
        )
        assert extract_links("md", body) == ()

    def test_md_fence_hides_file_link(self) -> None:
        body = dedent(
            """\
            ```python
            [text](./should-not-warn.py)
            ```
            """
        )
        assert extract_file_links("md", body) == ()

    def test_md_tilde_fence_hides_links(self) -> None:
        body = dedent(
            """\
            ~~~
            [text](./hidden.md)
            ~~~
            """
        )
        assert extract_file_links("md", body) == ()

    def test_md_fence_close_must_match_opener_char(self) -> None:
        # Tilde line inside a backtick fence is *not* a closing fence;
        # the link on that next line stays masked.
        body = dedent(
            """\
            ```
            [text](./hidden.md)
            ~~~
            [also-hidden](./other.md)
            ```
            """
        )
        assert extract_file_links("md", body) == ()

    def test_md_link_outside_fence_still_extracted(self) -> None:
        body = dedent(
            """\
            Before [a](./a.md).
            ```
            [hidden](./hidden.md)
            ```
            After [b](./b.md).
            """
        )
        out = extract_file_links("md", body)
        assert [link.target for link in out] == ["./a.md", "./b.md"]

    def test_line_col_unaffected_by_masking(self) -> None:
        # Masking must preserve byte offsets so line/col stays correct
        # for links *after* a fenced region.
        body = dedent(
            """\
            line1
            #+begin_src text
            [[denote:20990101T000000]]
            #+end_src
            tail [[denote:20240115T093000]] here
            """
        )
        out = extract_links("org", body)
        assert len(out) == 1
        assert out[0].line == 5
        assert out[0].col == 6  # 1-based; "tail " is 5 chars
