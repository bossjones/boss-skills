"""Tests for the validate_file_contains Stop-hook validator.

``check_file_contains`` is pure; ``find_newest_file`` / ``validate_file_contains``
combine git (faked via ``fake_process``) with filesystem checks (``in_tmp_cwd``).
"""

from __future__ import annotations

import os
import time
from pathlib import Path

from hook_loader import load_hook

vfc = load_hook("validators/validate_file_contains.py")


def _make_file(path: Path, content: str = "content", *, age_seconds: float = 0.0) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    if age_seconds:
        old = time.time() - age_seconds
        os.utime(path, (old, old))


class TestCheckFileContains:
    def test_all_strings_present(self, tmp_path: Path) -> None:
        f = tmp_path / "spec.md"
        f.write_text("## Task Description\nbody\n## Objective\nmore")

        all_found, found, missing = vfc.check_file_contains(str(f), ["## Task Description", "## Objective"])

        assert all_found is True
        assert set(found) == {"## Task Description", "## Objective"}
        assert missing == []

    def test_partial_match_reports_missing(self, tmp_path: Path) -> None:
        f = tmp_path / "spec.md"
        f.write_text("## Task Description\nonly this")

        all_found, found, missing = vfc.check_file_contains(str(f), ["## Task Description", "## Objective"])

        assert all_found is False
        assert found == ["## Task Description"]
        assert missing == ["## Objective"]

    def test_case_sensitive(self, tmp_path: Path) -> None:
        f = tmp_path / "spec.md"
        f.write_text("## task description")

        all_found, _, missing = vfc.check_file_contains(str(f), ["## Task Description"])

        assert all_found is False
        assert missing == ["## Task Description"]

    def test_missing_file_reports_all_missing(self, tmp_path: Path) -> None:
        all_found, found, missing = vfc.check_file_contains(str(tmp_path / "nope.md"), ["x"])

        assert all_found is False
        assert found == []
        assert missing == ["x"]


class TestFindNewestFile:
    def test_returns_most_recently_modified(self, fake_process, in_tmp_cwd: Path) -> None:  # noqa: ANN001
        fake_process.register(["git", "status", "--porcelain", "specs/"], stdout="")
        _make_file(in_tmp_cwd / "specs" / "old.md", age_seconds=120)
        _make_file(in_tmp_cwd / "specs" / "new.md")

        newest = vfc.find_newest_file("specs", ".md", max_age_minutes=5)

        assert newest == "specs/new.md"

    def test_returns_none_when_empty(self, fake_process, in_tmp_cwd: Path) -> None:  # noqa: ANN001
        fake_process.register(["git", "status", "--porcelain", "specs/"], stdout="")
        assert vfc.find_newest_file("specs", ".md", max_age_minutes=5) is None


class TestValidateFileContains:
    def test_pass_when_all_sections_present(self, fake_process, in_tmp_cwd: Path) -> None:  # noqa: ANN001
        fake_process.register(["git", "status", "--porcelain", "specs/"], stdout="")
        _make_file(in_tmp_cwd / "specs" / "plan.md", "## Task Description\n## Objective\n")

        ok, message = vfc.validate_file_contains("specs", ".md", 5, ["## Task Description", "## Objective"])

        assert ok is True
        assert "all 2 required sections" in message

    def test_block_when_section_missing(self, fake_process, in_tmp_cwd: Path) -> None:  # noqa: ANN001
        fake_process.register(["git", "status", "--porcelain", "specs/"], stdout="")
        _make_file(in_tmp_cwd / "specs" / "plan.md", "## Task Description\n")

        ok, message = vfc.validate_file_contains("specs", ".md", 5, ["## Task Description", "## Objective"])

        assert ok is False
        assert "## Objective" in message
        assert "VALIDATION FAILED" in message

    def test_no_file_fails_closed(self, fake_process, in_tmp_cwd: Path) -> None:  # noqa: ANN001
        fake_process.register(["git", "status", "--porcelain", "specs/"], stdout="")

        ok, message = vfc.validate_file_contains("specs", ".md", 5, ["## Task Description"])

        assert ok is False
        assert "VALIDATION FAILED" in message

    def test_file_found_with_no_content_checks(self, fake_process, in_tmp_cwd: Path) -> None:  # noqa: ANN001
        fake_process.register(["git", "status", "--porcelain", "specs/"], stdout="")
        _make_file(in_tmp_cwd / "specs" / "plan.md", "anything")

        ok, message = vfc.validate_file_contains("specs", ".md", 5, [])

        assert ok is True
        assert "no content checks specified" in message
