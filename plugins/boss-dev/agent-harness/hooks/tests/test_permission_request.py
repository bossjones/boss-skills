"""Tests for the permission_request auto-allow hook.

Covers the read-only allow-listing logic and the JSON decision builders.
"""

from __future__ import annotations

import pytest
from hook_loader import load_hook

permission_request = load_hook("permission_request.py")


class TestIsSafeBashCommand:
    @pytest.mark.parametrize(
        "command",
        [
            "ls",
            "ls -la",
            "pwd",
            "git status",
            "git log --oneline",
            "git diff HEAD~1",
            "git branch",  # bare listing
            "npm ls",
            "npm outdated",
            "cat README.md",  # no redirection
            "pip list",
            "which python",
        ],
    )
    def test_allows_read_only_commands(self, command: str) -> None:
        assert permission_request.is_safe_bash_command(command) is True

    @pytest.mark.parametrize(
        "command",
        [
            "",  # empty is never safe
            "rm -rf /",
            "curl https://evil.example",
            "git branch -D feature",  # flags are not bare listing
            "ls; rm -rf /",  # chained command
            "ls && pwd",
            "ls || pwd",
            "ls | grep foo",
            "cat secrets > out.txt",  # redirection
            "cat < in.txt",
            "echo $(whoami)",
            "echo `whoami`",
        ],
    )
    def test_rejects_unsafe_or_chained_commands(self, command: str) -> None:
        assert permission_request.is_safe_bash_command(command) is False


class TestShouldAutoAllow:
    @pytest.mark.parametrize("tool_name", ["Read", "Glob", "Grep"])
    def test_read_only_tools_always_allowed(self, tool_name: str) -> None:
        assert permission_request.should_auto_allow(tool_name, {}) is True

    def test_safe_bash_allowed(self) -> None:
        assert permission_request.should_auto_allow("Bash", {"command": "ls -la"}) is True

    def test_unsafe_bash_not_allowed(self) -> None:
        assert permission_request.should_auto_allow("Bash", {"command": "rm -rf /"}) is False

    def test_mutating_tool_not_allowed(self) -> None:
        assert permission_request.should_auto_allow("Write", {"file_path": "x.py"}) is False
        assert permission_request.should_auto_allow("Edit", {"file_path": "x.py"}) is False


class TestGetAutoAllowReason:
    def test_read_reason_includes_path(self) -> None:
        reason = permission_request.get_auto_allow_reason("Read", {"file_path": "/a/b.py"})
        assert reason == "Read operation auto-allowed: /a/b.py"

    def test_glob_and_grep_reasons_include_pattern(self) -> None:
        assert "*.py" in permission_request.get_auto_allow_reason("Glob", {"pattern": "*.py"})
        assert "TODO" in permission_request.get_auto_allow_reason("Grep", {"pattern": "TODO"})

    def test_bash_reason_truncates_command(self) -> None:
        reason = permission_request.get_auto_allow_reason("Bash", {"command": "ls -la"})
        assert reason.startswith("Safe bash command auto-allowed: ")
        assert "ls -la" in reason

    def test_unknown_tool_has_generic_reason(self) -> None:
        reason = permission_request.get_auto_allow_reason("Frobnicate", {})
        assert reason == "Frobnicate auto-allowed (read-only operation)"


class TestDecisionBuilders:
    def test_allow_response_minimal(self) -> None:
        resp = permission_request.create_allow_response()
        decision = resp["hookSpecificOutput"]["decision"]
        assert resp["hookSpecificOutput"]["hookEventName"] == "PermissionRequest"
        assert decision == {"behavior": "allow"}

    def test_allow_response_with_reason_and_updated_input(self) -> None:
        resp = permission_request.create_allow_response(updated_input={"file_path": "x"}, reason="because")
        decision = resp["hookSpecificOutput"]["decision"]
        assert decision["behavior"] == "allow"
        assert decision["updatedInput"] == {"file_path": "x"}
        assert decision["reason"] == "because"

    def test_deny_response_defaults_to_no_interrupt(self) -> None:
        resp = permission_request.create_deny_response("not allowed")
        decision = resp["hookSpecificOutput"]["decision"]
        assert decision == {"behavior": "deny", "message": "not allowed", "interrupt": False}

    def test_deny_response_can_interrupt(self) -> None:
        resp = permission_request.create_deny_response("stop now", interrupt=True)
        assert resp["hookSpecificOutput"]["decision"]["interrupt"] is True
