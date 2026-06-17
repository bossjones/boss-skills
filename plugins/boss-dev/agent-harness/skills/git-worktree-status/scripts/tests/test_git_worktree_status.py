"""Tests for git_worktree_status.py — pure log-parsing and detection helpers."""

from __future__ import annotations

from git_worktree_status import (
    format_status_report,
    in_worktree,
    parse_log_status,
)


class TestInWorktree:
    def test_inside_worktree(self) -> None:
        assert in_worktree("/repo/.git/worktrees/boss-skills-auth") is True

    def test_main_repo(self) -> None:
        assert in_worktree("/repo/.git") is False

    def test_windows_separators(self) -> None:
        assert in_worktree(r"C:\repo\.git\worktrees\x") is True


class TestParseLogStatus:
    def test_empty_is_not_run(self) -> None:
        assert parse_log_status("") == "NOT_RUN"
        assert parse_log_status("   \n  ") == "NOT_RUN"

    def test_pytest_pass(self) -> None:
        assert parse_log_status("===== 12 passed in 0.3s =====") == "PASS"

    def test_pytest_fail(self) -> None:
        assert parse_log_status("== 2 failed, 3 passed in 0.4s ==") == "FAIL"

    def test_zero_failed_is_pass(self) -> None:
        assert parse_log_status("0 failed, 5 passed") == "PASS"

    def test_vitest_json_zero_failures(self) -> None:
        assert parse_log_status('{"numFailedTests":0,"numTotalTests":5}') == "PASS"

    def test_vitest_json_failures(self) -> None:
        assert parse_log_status('{"numFailedTests":3,"numTotalTests":5}') == "FAIL"

    def test_pyright_zero_errors(self) -> None:
        assert parse_log_status("0 errors, 0 warnings, 0 notes") == "PASS"

    def test_pyright_errors(self) -> None:
        assert parse_log_status("3 errors, 1 warning") == "FAIL"

    def test_tsc_error(self) -> None:
        assert parse_log_status("src/auth.ts:42 - error TS2345: bad") == "FAIL"

    def test_python_traceback(self) -> None:
        assert parse_log_status("Traceback (most recent call last):\n  ...") == "FAIL"

    def test_partial_output_is_running(self) -> None:
        assert parse_log_status("collecting tests ...") == "RUNNING"


class TestFormatStatusReport:
    def test_includes_branch_and_each_check(self) -> None:
        report = format_status_report(
            worktree_path="/repo/.claude/worktrees/boss-skills-auth",
            branch="worktree-auth",
            results={"tests": "PASS", "typecheck": "FAIL"},
        )
        assert "worktree-auth" in report
        assert "tests" in report
        assert "typecheck" in report
        assert "PASS" in report
        assert "FAIL" in report

    def test_handles_no_results(self) -> None:
        report = format_status_report(
            worktree_path="/repo/.claude/worktrees/boss-skills-auth",
            branch="worktree-auth",
            results={},
        )
        assert "NOT_RUN" in report or "No background" in report
