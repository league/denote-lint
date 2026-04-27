"""Output reporters: compilation, json, text.

The compilation format is the default and is consumed by Emacs'
``compilation-mode``. The text format groups by file and is meant for
direct terminal reading; it colors output when stdout is a TTY and
``NO_COLOR`` / ``--no-color`` aren't set. The json format is for
tooling.
"""

from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from denote_lint.models import Issue

_ANSI: dict[str, str] = {
    "red": "\x1b[31m",
    "yellow": "\x1b[33m",
    "blue": "\x1b[34m",
    "bold": "\x1b[1m",
    "reset": "\x1b[0m",
}

_SEVERITY_COLOR: dict[str, str] = {
    "error": "red",
    "warning": "yellow",
    "info": "blue",
}

_SEVERITY_RANK_FOR_SORT: dict[str, int] = {"error": 0, "warning": 1, "info": 2}


@dataclass
class Report:
    issues: list[Issue]
    scanned: int
    elapsed: float


def sort_issues(issues: Iterable[Issue]) -> list[Issue]:
    return sorted(
        issues,
        key=lambda i: (
            str(i.path),
            i.line,
            i.col,
            _SEVERITY_RANK_FOR_SORT.get(i.severity, 99),
            i.code,
        ),
    )


def format_compilation(report: Report) -> str:
    out: list[str] = []
    for issue in sort_issues(report.issues):
        out.append(
            f"{issue.path}:{issue.line}:{issue.col}: "
            f"{issue.severity}[{issue.code}]: {issue.message}"
        )
    return "\n".join(out)


def format_json(report: Report, version: str) -> str:
    return json.dumps(
        {
            "version": version,
            "scanned": report.scanned,
            "issues": [
                {
                    "path": str(i.path),
                    "line": i.line,
                    "col": i.col,
                    "severity": i.severity,
                    "code": i.code,
                    "message": i.message,
                }
                for i in sort_issues(report.issues)
            ],
        },
        indent=2,
    )


def format_text(report: Report, *, use_color: bool) -> str:
    by_file: dict[Path, list[Issue]] = defaultdict(list)
    for issue in sort_issues(report.issues):
        by_file[issue.path].append(issue)

    chunks: list[str] = []
    for path in sorted(by_file, key=str):
        chunks.append(_color(str(path), "bold", use_color))
        for issue in by_file[path]:
            sev_color = _SEVERITY_COLOR.get(issue.severity, "")
            sev_painted = (
                _color(issue.severity, sev_color, use_color)
                if sev_color
                else issue.severity
            )
            chunks.append(
                f"  {issue.line}:{issue.col}: {sev_painted}[{issue.code}]: "
                f"{issue.message}"
            )
        chunks.append("")
    return "\n".join(chunks).rstrip("\n")


def format_summary(report: Report) -> str:
    counts = {"error": 0, "warning": 0, "info": 0}
    for issue in report.issues:
        if issue.severity in counts:
            counts[issue.severity] += 1
    return (
        f"denote-lint: scanned {report.scanned} files, "
        f"found {counts['error']} errors, "
        f"{counts['warning']} warnings, "
        f"{counts['info']} info "
        f"in {report.elapsed:.1f}s"
    )


def color_enabled(*, no_color_flag: bool, stream: object | None = None) -> bool:
    """Return True iff colored output should be emitted.

    Disabled if ``no_color_flag`` is set, the ``NO_COLOR`` environment
    variable is set (per https://no-color.org), or the target stream
    isn't a TTY.
    """
    if no_color_flag:
        return False
    if os.environ.get("NO_COLOR"):
        return False
    target = stream if stream is not None else sys.stdout
    isatty = getattr(target, "isatty", None)
    return bool(isatty()) if callable(isatty) else False


def _color(s: str, name: str, enabled: bool) -> str:
    if not enabled or name not in _ANSI:
        return s
    return f"{_ANSI[name]}{s}{_ANSI['reset']}"
