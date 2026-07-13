"""Suite 1: replay every eval fixture through the pure core and pin what it decides.

This is the CI gate the eval suite cannot be. `eval/eval.yaml` drives the same fixtures
through the CLI so the *graders* get exercised, but it needs an agent session (or an API
key) to run, which makes it unusable as a per-commit gate and flaky when the driving agent
misbehaves on code that is perfectly correct. Everything asserted here is a pure function
of the diff and `review-tiers.json` — no agents, no git, no network — so it belongs in
pytest, where it runs free and deterministically on every commit.

The fixtures are shared with `eval/eval.yaml`. Changing one changes both, on purpose.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import prepare_review as pr
import pytest

CONFIG: dict[str, Any] = json.loads(Path(pr.DEFAULT_TIERS).read_text())
FIXTURES = Path(__file__).resolve().parents[2] / "eval" / "test-fixtures"


def load(name: str) -> list[pr.FileDiff]:
    return pr.parse_annotated_diff((FIXTURES / f"{name}.diff").read_text())


def tier_of(name: str) -> str:
    return pr.assess_risk_tier(load(name), CONFIG)


def roster_of(name: str) -> list[str]:
    files = load(name)
    return pr.roster_for(pr.assess_risk_tier(files, CONFIG), CONFIG, files)


class TestFixturesParse:
    """A fixture that no longer parses would silently weaken every assertion below."""

    @pytest.mark.parametrize(
        "name",
        [
            "tier-trivial",
            "tier-lite-11",
            "tier-lite-100",
            "tier-full-by-size",
            "tier-full-by-file-count",
            "security-glob-forces-full",
            "noise-filter-keeps-migrations",
            "scoping-security-not-css",
            "roster-pruning",
            "injection",
        ],
    )
    def test_fixture_parses_to_at_least_one_file(self, name: str) -> None:
        assert load(name), f"{name}.diff parsed to zero files — the annotated format drifted"


class TestTierBoundaries:
    @pytest.mark.parametrize(
        ("name", "expected"),
        [
            ("tier-trivial", "trivial"),  # exactly 10 lines — the trivial ceiling
            ("tier-lite-11", "lite"),  # one over trivial
            ("tier-lite-100", "lite"),  # exactly 100 — the lite ceiling
            ("tier-full-by-size", "full"),  # 101 — one over lite
        ],
    )
    def test_size_boundaries(self, name: str, expected: str) -> None:
        assert tier_of(name) == expected

    def test_many_small_files_are_full_by_blast_radius(self) -> None:
        """25 files x 1 line is under every line and file threshold, so only rule 5 saves it.

        A size-only heuristic waves this through; touching 25 files is its own risk signal.
        """
        files = load("tier-full-by-file-count")
        assert len(files) == 25
        assert sum(f.changed_lines for f in files) == 25
        assert tier_of("tier-full-by-file-count") == "full"

    def test_security_path_beats_size(self) -> None:
        """A 2-line CI-workflow edit is Full. This is the whole point of risk-tiering."""
        files = load("security-glob-forces-full")
        assert sum(f.changed_lines for f in files) == 2
        assert tier_of("security-glob-forces-full") == "full"


class TestNoiseFilter:
    def test_lock_is_masked_and_migration_is_reviewed(self) -> None:
        """A bad migration can destroy production data, so it must always reach a reviewer."""
        by_path = {f.path: f for f in load("noise-filter-keeps-migrations")}
        assert by_path["uv.lock"].masked is True
        assert by_path["db/migrations/0001_init.py"].masked is False

    def test_masked_files_do_not_inflate_the_tier(self) -> None:
        files = load("noise-filter-keeps-migrations")
        assert all(f.changed_lines == 0 for f in files if f.masked)


class TestScoping:
    def test_security_focuses_on_auth_code_not_stylesheets(self) -> None:
        files = load("scoping-security-not-css")
        focus = pr.focus_paths("security", files, CONFIG)
        assert "src/auth/login.py" in focus
        assert "styles/app.css" not in focus


class TestRosterPruning:
    def test_docs_only_change_does_not_pay_for_security_or_performance(self) -> None:
        """The fixture is >100 lines so it reaches Full and all five roles are candidates.

        Under 100 lines it would land `trivial` (roster = [generalist]) and the roles this
        claims to prune would never have been hired — the assertion would prove nothing.
        """
        assert tier_of("roster-pruning") == "full"
        roles = roster_of("roster-pruning")
        assert "security" not in roles
        assert "performance" not in roles
        assert "docs" in roles

    def test_roles_with_no_focus_globs_are_never_pruned(self) -> None:
        assert "code-quality" in roster_of("roster-pruning")


class TestInjectionDefense:
    def test_boundary_tags_are_stripped_but_prose_survives(self) -> None:
        raw = (FIXTURES / "injection-context.md").read_text()
        assert "<system>" in raw  # the fixture is actually hostile
        cleaned = pr.strip_boundary_tags(raw, CONFIG["boundary_tags"])
        for tag in ("<system>", "</system>", "<system-reminder>", "<instructions"):
            assert tag not in cleaned
        assert "shared token verifier" in cleaned
        assert "session-expiry path" in cleaned


class TestAnchors:
    def test_only_lines_present_in_the_diff_become_anchors(self) -> None:
        """The anchor table is what makes anchor rejection possible at all."""
        [f] = load("tier-trivial")
        assert f.right_lines == list(range(1, 11))
        assert f.left_lines == []
