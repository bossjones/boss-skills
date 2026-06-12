"""Tests for the validate_new_file Stop-hook validator.

Git is faked via pytest-subprocess (``fake_process``); filesystem checks run in
an isolated tmp directory (``in_tmp_cwd``).
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from hook_loader import load_hook

validate_new_file = load_hook("validators/validate_new_file.py")


def _make_file(path: Path, *, age_seconds: float = 0.0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("content")
    if age_seconds:
        old = time.time() - age_seconds
        os.utime(path, (old, old))


class TestGetRecentFiles:
    def test_includes_recent_excludes_old(self, in_tmp_cwd: Path) -> None:
        _make_file(in_tmp_cwd / "specs" / "fresh.md")
        _make_file(in_tmp_cwd / "specs" / "stale.md", age_seconds=3600)

        recent = validate_new_file.get_recent_files("specs", ".md", max_age_minutes=5)

        assert recent == ["specs/fresh.md"]

    def test_missing_directory_returns_empty(self, in_tmp_cwd: Path) -> None:
        assert validate_new_file.get_recent_files("nope", ".md", max_age_minutes=5) == []

    def test_extension_filter(self, in_tmp_cwd: Path) -> None:
        _make_file(in_tmp_cwd / "specs" / "doc.md")
        _make_file(in_tmp_cwd / "specs" / "data.json")

        recent = validate_new_file.get_recent_files("specs", ".md", max_age_minutes=5)

        assert recent == ["specs/doc.md"]


class TestGetGitUntrackedFiles:
    def test_parses_new_and_added_statuses(self, fake_process) -> None:  # noqa: ANN001
        fake_process.register(
            ["git", "status", "--porcelain", "specs/"],
            stdout="?? specs/new.md\n M specs/changed.md\nA  specs/added.md\n?? specs/ignore.txt\n",
        )

        result = validate_new_file.get_git_untracked_files("specs", ".md")

        assert result == ["specs/new.md", "specs/added.md"]

    def test_non_zero_exit_returns_empty(self, fake_process) -> None:  # noqa: ANN001
        fake_process.register(["git", "status", "--porcelain", "specs/"], returncode=128, stdout="")
        assert validate_new_file.get_git_untracked_files("specs", ".md") == []


class TestValidateNewFile:
    def test_git_new_file_passes(self, fake_process, in_tmp_cwd: Path) -> None:  # noqa: ANN001
        fake_process.register(["git", "status", "--porcelain", "specs/"], stdout="?? specs/new.md\n")

        ok, message = validate_new_file.validate_new_file("specs", ".md", max_age_minutes=5)

        assert ok is True
        assert "specs/new.md" in message

    def test_falls_back_to_recent_file(self, fake_process, in_tmp_cwd: Path) -> None:  # noqa: ANN001
        fake_process.register(["git", "status", "--porcelain", "specs/"], stdout="")
        _make_file(in_tmp_cwd / "specs" / "fresh.md")

        ok, message = validate_new_file.validate_new_file("specs", ".md", max_age_minutes=5)

        assert ok is True
        assert "Recently created" in message

    def test_no_file_fails_closed(self, fake_process, in_tmp_cwd: Path) -> None:  # noqa: ANN001
        fake_process.register(["git", "status", "--porcelain", "specs/"], stdout="")

        ok, message = validate_new_file.validate_new_file("specs", ".md", max_age_minutes=5)

        assert ok is False
        assert "VALIDATION FAILED" in message
