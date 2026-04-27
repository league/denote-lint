"""Denote-link extraction from note bodies.

Org syntax::

    [[denote:20240115T093000]]
    [[denote:20240115T093000][Description text]]
    [[denote:20240115T093000::*Some heading]]

Markdown syntax::

    [Description text](denote:20240115T093000)

The ``::SEARCH`` suffix is org-only; we strip it from the target id but
preserve nothing else about it.

Note: links inside code blocks or ``#+begin_example`` blocks are out of
scope for v0.1 -- the spec accepts this as a known false-positive
source. Regex runs over the whole body.
"""

from __future__ import annotations

import re

from denote_lint.models import Link

_ORG_LINK_RE = re.compile(
    r"\[\[denote:(?P<target>[^\]\n]+?)\](?:\[(?P<desc>[^\]\n]+?)\])?\]"
)
_MD_LINK_RE = re.compile(
    r"\[(?P<desc>[^\]\n]*?)\]\(denote:(?P<target>[^)\n]+?)\)"
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


def _line_col(text: str, offset: int) -> tuple[int, int]:
    line_start = text.rfind("\n", 0, offset) + 1
    line = text.count("\n", 0, offset) + 1
    col = offset - line_start + 1
    return line, col
