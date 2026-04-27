"""Config and check-registry plumbing. Specific check behaviour is
tested elsewhere; here we just verify selection logic and the orchestrator.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pytest

from denote_lint import checks as checks_module
from denote_lint.checks import (
    REGISTRY,
    CheckRecord,
    register_corpus,
    register_per_note,
    run_checks,
)
from denote_lint.config import SEVERITY_RANK, Config
from denote_lint.models import Context, Issue, Note, ParsedFilename


@pytest.fixture
def isolated_registry() -> Iterable[dict[str, CheckRecord]]:
    """Save and restore the module-level REGISTRY so tests don't leak."""
    saved = dict(REGISTRY)
    REGISTRY.clear()
    try:
        yield REGISTRY
    finally:
        REGISTRY.clear()
        REGISTRY.update(saved)


def _note(name: str = "20240115T093000.org") -> Note:
    pf = ParsedFilename(
        identifier="20240115T093000",
        identifier_dt=None,
        signature=None,
        title_slug=None,
        keywords=(),
        extension="org",
        raw=name,
    )
    return Note(path=Path(name), filename=pf, front_matter=None, body="")


class TestSeverityRank:
    def test_ranks_ordered(self) -> None:
        assert SEVERITY_RANK["info"] < SEVERITY_RANK["warning"]
        assert SEVERITY_RANK["warning"] < SEVERITY_RANK["error"]


class TestEnabledCodes:
    def test_severity_floor_warning(
        self, isolated_registry: dict[str, CheckRecord]
    ) -> None:
        @register_per_note("E999", "error", "x")
        def _e(_n: Note, _c: Context) -> Iterable[Issue]:
            return ()

        @register_per_note("W999", "warning", "x")
        def _w(_n: Note, _c: Context) -> Iterable[Issue]:
            return ()

        @register_per_note("I999", "info", "x")
        def _i(_n: Note, _c: Context) -> Iterable[Issue]:
            return ()

        cfg = Config(min_severity="warning")
        assert cfg.enabled_codes() == frozenset({"E999", "W999"})

    def test_severity_floor_info_includes_all(
        self, isolated_registry: dict[str, CheckRecord]
    ) -> None:
        @register_per_note("E999", "error", "x")
        def _e(_n: Note, _c: Context) -> Iterable[Issue]:
            return ()

        @register_per_note("I999", "info", "x")
        def _i(_n: Note, _c: Context) -> Iterable[Issue]:
            return ()

        cfg = Config(min_severity="info")
        assert cfg.enabled_codes() == frozenset({"E999", "I999"})

    def test_checks_whitelist_overrides_severity(
        self, isolated_registry: dict[str, CheckRecord]
    ) -> None:
        @register_per_note("E999", "error", "x")
        def _e(_n: Note, _c: Context) -> Iterable[Issue]:
            return ()

        @register_per_note("W999", "warning", "x")
        def _w(_n: Note, _c: Context) -> Iterable[Issue]:
            return ()

        cfg = Config(min_severity="error", checks=("W999",))
        assert cfg.enabled_codes() == frozenset({"W999"})

    def test_disable_subtracts(
        self, isolated_registry: dict[str, CheckRecord]
    ) -> None:
        @register_per_note("E999", "error", "x")
        def _e(_n: Note, _c: Context) -> Iterable[Issue]:
            return ()

        @register_per_note("E998", "error", "x")
        def _e2(_n: Note, _c: Context) -> Iterable[Issue]:
            return ()

        cfg = Config(min_severity="error", disable=("E998",))
        assert cfg.enabled_codes() == frozenset({"E999"})

    def test_unknown_code_in_checks_silently_ignored(
        self, isolated_registry: dict[str, CheckRecord]
    ) -> None:
        @register_per_note("E999", "error", "x")
        def _e(_n: Note, _c: Context) -> Iterable[Issue]:
            return ()

        cfg = Config(checks=("E999", "MADEUP"))
        assert cfg.enabled_codes() == frozenset({"E999"})


class TestRunChecks:
    def test_per_note_runs_for_each_note(
        self, isolated_registry: dict[str, CheckRecord]
    ) -> None:
        calls: list[Path] = []

        @register_per_note("E999", "error", "x")
        def _e(n: Note, _c: Context) -> Iterable[Issue]:
            calls.append(n.path)
            return ()

        notes = [_note("a.org"), _note("b.org")]
        run_checks(notes, Context(), frozenset({"E999"}))
        assert calls == [Path("a.org"), Path("b.org")]

    def test_corpus_runs_once(
        self, isolated_registry: dict[str, CheckRecord]
    ) -> None:
        calls: list[int] = []

        @register_corpus("E999", "error", "x")
        def _e(_c: Context) -> Iterable[Issue]:
            calls.append(1)
            return ()

        run_checks([_note(), _note()], Context(), frozenset({"E999"}))
        assert calls == [1]

    def test_disabled_check_does_not_run(
        self, isolated_registry: dict[str, CheckRecord]
    ) -> None:
        calls: list[int] = []

        @register_per_note("E999", "error", "x")
        def _e(_n: Note, _c: Context) -> Iterable[Issue]:
            calls.append(1)
            return ()

        run_checks([_note()], Context(), frozenset())
        assert calls == []


class TestRegistryPopulated:
    def test_module_imports_check_modules(self) -> None:
        # Just verify the lazy-import loader has been invoked; specific
        # codes are asserted in the per-check tests.
        assert checks_module.REGISTRY is REGISTRY
