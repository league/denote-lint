"""Trivial smoke test so the test suite has at least one passing test from day one."""

from __future__ import annotations

import denote_lint


def test_version_present() -> None:
    assert denote_lint.__version__
    assert denote_lint.__version__.count(".") >= 1
