"""Denote-link and file-link extraction from note bodies.

Org denote syntax::

    [[denote:20240115T093000]]
    [[denote:20240115T093000][Description text]]
    [[denote:20240115T093000::*Some heading]]

Markdown denote syntax::

    [Description text](denote:20240115T093000)

The ``::SEARCH`` suffix is org-only; we strip it from the target id but
preserve nothing else about it.

Org ``file:`` links (handled by :func:`extract_file_links`) follow the
same bracket form::

    [[file:./other.org]]
    [[file:/abs/path.pdf][Description]]
    [[file:./notes.org::*Heading]]

Note: links inside code blocks or ``#+begin_example`` blocks are out of
scope for v0.1 -- the spec accepts this as a known false-positive
source. Regex runs over the whole body.
"""

from __future__ import annotations

import re

from denote_lint.models import FileLink, Link

_ORG_LINK_RE = re.compile(
    r"\[\[denote:(?P<target>[^\]\n]+?)\](?:\[(?P<desc>[^\]\n]+?)\])?\]"
)
_MD_LINK_RE = re.compile(
    r"\[(?P<desc>[^\]\n]*?)\]\(denote:(?P<target>[^)\n]+?)\)"
)
_ORG_FILE_LINK_RE = re.compile(
    r"\[\[file:(?P<target>[^\]\n]+?)\](?:\[(?P<desc>[^\]\n]+?)\])?\]"
)


def extract_links(extension: str, body: str) -> tuple[Link, ...]:
    """Return all denote: links found in ``body``.

    The choice of regex is driven by extension: org files use the org
    bracketed form; markdown files use the inline form. Plain text and
    attachments yield no links.
    """
    ext = extension.lower()
    if ext == "org":
        regex = _ORG_LINK_RE
    elif ext == "md":
        regex = _MD_LINK_RE
    else:
        return ()

    links: list[Link] = []
    for m in regex.finditer(body):
        target = m.group("target")
        desc = m.group("desc")
        target_id, _, _ = target.partition("::")
        target_id = target_id.strip()
        line, col = _line_col(body, m.start())
        links.append(
            Link(
                target_id=target_id,
                description=desc.strip() if desc else None,
                line=line,
                col=col,
            )
        )
    return tuple(links)


def extract_file_links(extension: str, body: str) -> tuple[FileLink, ...]:
    """Return all org ``[[file:...]]`` links found in ``body``.

    Markdown is intentionally not handled here: distinguishing local
    file links from URLs in arbitrary inline ``[text](path)`` syntax is
    out of scope for v0.1 (per the W006 spec note).

    The ``target`` field carries the raw path string with any
    ``::SEARCH`` suffix stripped. Filesystem resolution (relative paths,
    ``~`` expansion, existence) is the check's job, not the parser's.
    """
    if extension.lower() != "org":
        return ()

    links: list[FileLink] = []
    for m in _ORG_FILE_LINK_RE.finditer(body):
        target = m.group("target")
        desc = m.group("desc")
        path_part, _, _ = target.partition("::")
        path_part = path_part.strip()
        if not path_part:
            continue
        line, col = _line_col(body, m.start())
        links.append(
            FileLink(
                target=path_part,
                description=desc.strip() if desc else None,
                line=line,
                col=col,
            )
        )
    return tuple(links)


def _line_col(text: str, offset: int) -> tuple[int, int]:
    line_start = text.rfind("\n", 0, offset) + 1
    line = text.count("\n", 0, offset) + 1
    col = offset - line_start + 1
    return line, col
