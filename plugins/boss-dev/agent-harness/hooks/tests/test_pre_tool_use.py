"""Tests for the pre_tool_use security guard hook.

Covers the two security-critical pure functions:
- ``is_dangerous_rm_command`` — blocks destructive ``rm -rf`` style commands.
- ``is_env_file_access`` — blocks reads/writes of real ``.env`` secret files
  while allowing the committed ``.env.sample`` / ``.env.example`` templates.
"""

from __future__ import annotations

import pytest
from hook_loader import load_hook

pre_tool_use = load_hook("pre_tool_use.py")


class TestIsDangerousRmCommand:
    @pytest.mark.parametrize(
        "command",
        [
            "rm -rf /",
            "rm -rf /home/user",
            "rm -rf /*",
            "rm -fr ~",
            "rm -rf ~/projects",
            "rm -rf *",
            "rm -rf .",
            "rm --recursive --force /tmp",
            "rm --force --recursive /tmp",
            "rm -r -f ./anything",
            "rm -f -r ./anything",
            "rm -rf ./build",  # any -rf is blocked, even a subdir
            "RM -RF /",  # case-insensitive
            "rm -rf $HOME",
            "rm -rf ../..",  # parent-dir traversal
        ],
    )
    def test_flags_dangerous_commands(self, command: str) -> None:
        assert pre_tool_use.is_dangerous_rm_command(command) is True

    @pytest.mark.parametrize(
        "command",
        [
            "rm file.txt",
            "rm -i file.txt",
            "rm -r ./build/output",  # recursive but not force, ordinary subdir
            "ls -la",
            "git status",
        ],
    )
    def test_allows_safe_commands(self, command: str) -> None:
        assert pre_tool_use.is_dangerous_rm_command(command) is False

    def test_fails_closed_on_embedded_rm(self) -> None:
        # The matcher is intentionally conservative: a dangerous ``rm -rf``
        # substring is blocked even inside an otherwise harmless ``echo``.
        # Blocking this false positive is preferable to weakening the guard.
        assert pre_tool_use.is_dangerous_rm_command("echo rm -rf /") is True


class TestIsEnvFileAccess:
    @pytest.mark.parametrize("tool_name", ["Read", "Edit", "MultiEdit", "Write"])
    def test_blocks_real_env_file_for_file_tools(self, tool_name: str) -> None:
        assert pre_tool_use.is_env_file_access(tool_name, {"file_path": ".env"}) is True

    @pytest.mark.parametrize("tool_name", ["Read", "Edit", "MultiEdit", "Write"])
    def test_blocks_nested_and_local_env_files(self, tool_name: str) -> None:
        assert pre_tool_use.is_env_file_access(tool_name, {"file_path": "config/.env"}) is True
        assert pre_tool_use.is_env_file_access(tool_name, {"file_path": ".env.local"}) is True

    @pytest.mark.parametrize("suffix", [".env.sample", ".env.example"])
    def test_allows_env_templates(self, suffix: str) -> None:
        assert pre_tool_use.is_env_file_access("Read", {"file_path": suffix}) is False

    def test_allows_non_env_files(self) -> None:
        assert pre_tool_use.is_env_file_access("Read", {"file_path": "src/config.py"}) is False

    def test_blocks_bash_reads_of_env(self) -> None:
        assert pre_tool_use.is_env_file_access("Bash", {"command": "cat .env"}) is True
        assert pre_tool_use.is_env_file_access("Bash", {"command": "source ./.env"}) is True

    def test_allows_bash_env_templates_and_lookalikes(self) -> None:
        assert pre_tool_use.is_env_file_access("Bash", {"command": "cat .env.example"}) is False
        # ``config.env`` is a different file, not the secret ``.env``.
        assert pre_tool_use.is_env_file_access("Bash", {"command": "cat config.env"}) is False
        assert pre_tool_use.is_env_file_access("Bash", {"command": "echo hello"}) is False

    def test_unhandled_tool_is_not_flagged(self) -> None:
        # Grep is not in the guarded tool set, so it is never treated as env access.
        assert pre_tool_use.is_env_file_access("Grep", {"file_path": ".env"}) is False
