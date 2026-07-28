"""Tests for the filesystem / subprocess helper logic across lifecycle hooks.

Grouped one class per module. Git and dependency probes are faked with
``fake_process``; artifact writers run under ``in_tmp_cwd``.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from hook_loader import HOOKS_DIR, load_hook

pre_compact = load_hook("pre_compact.py")
session_end = load_hook("session_end.py")
session_start = load_hook("session_start.py")
setup = load_hook("setup.py")
stop = load_hook("stop.py")
subagent_stop = load_hook("subagent_stop.py")


class TestPreCompactBackupTranscript:
    def test_creates_named_backup(self, in_tmp_cwd: Path) -> None:
        transcript = in_tmp_cwd / "session-abc.jsonl"
        transcript.write_text('{"type":"user"}\n')

        backup_path = pre_compact.backup_transcript("session-abc", str(transcript), "manual")

        assert backup_path is not None
        backup = Path(backup_path)
        assert backup.exists()
        assert backup.parent == pre_compact.session_log_dir("session-abc") / "transcript_backups"
        assert not (in_tmp_cwd / "logs").exists()
        assert backup.name.startswith("session-abc_pre_compact_manual_")
        assert backup.suffix == ".jsonl"

    def test_missing_transcript_returns_none(self, in_tmp_cwd: Path) -> None:
        assert pre_compact.backup_transcript("session-abc", str(in_tmp_cwd / "gone.jsonl"), "auto") is None


class TestSessionEndCleanup:
    def test_removes_tmp_files_and_stale_chat(self, in_tmp_cwd: Path) -> None:
        logs = session_end.session_log_dir("session-abc")
        logs.mkdir(parents=True)
        (logs / "scratch.tmp").write_text("x")
        chat = logs / "chat.json"
        chat.write_text("[]")
        old = time.time() - 90_000  # > 24h
        import os

        os.utime(chat, (old, old))

        actions = session_end.perform_cleanup("session-abc")

        assert (logs / "scratch.tmp").exists() is False
        assert chat.exists() is False
        assert any("scratch.tmp" in a for a in actions)
        assert any("chat.json" in a for a in actions)

    def test_recent_chat_is_preserved(self, in_tmp_cwd: Path) -> None:
        logs = session_end.session_log_dir("session-abc")
        logs.mkdir(parents=True)
        (logs / "chat.json").write_text("[]")

        session_end.perform_cleanup("session-abc")

        assert (logs / "chat.json").exists() is True

    def test_no_logs_dir_returns_empty(self, in_tmp_cwd: Path) -> None:
        assert session_end.perform_cleanup("session-abc") == []


class TestSessionStartGitStatus:
    def test_reports_branch_and_change_count(self, fake_process) -> None:  # noqa: ANN001
        fake_process.register(["git", "rev-parse", "--abbrev-ref", "HEAD"], stdout="feature-x\n")
        fake_process.register(["git", "status", "--porcelain"], stdout=" M a.py\n?? b.py\n")

        branch, count = session_start.get_git_status()

        assert branch == "feature-x"
        assert count == 2

    def test_unknown_branch_when_rev_parse_fails(self, fake_process) -> None:  # noqa: ANN001
        fake_process.register(["git", "rev-parse", "--abbrev-ref", "HEAD"], returncode=128, stdout="")
        fake_process.register(["git", "status", "--porcelain"], stdout="")

        branch, count = session_start.get_git_status()

        assert branch == "unknown"
        assert count == 0


class TestSessionStartLoadContext:
    def test_includes_git_source_and_context_file(self, in_tmp_cwd: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(session_start, "get_git_status", lambda: ("main", 3))
        monkeypatch.setattr(session_start, "get_recent_issues", lambda: None)
        claude = in_tmp_cwd / ".claude"
        claude.mkdir()
        (claude / "CONTEXT.md").write_text("PROJECT NORTH STAR")

        context = session_start.load_development_context("startup")

        assert "Session source: startup" in context
        assert "Git branch: main" in context
        assert "Uncommitted changes: 3 files" in context
        assert "PROJECT NORTH STAR" in context


class TestSetupHelpers:
    def test_persist_env_variable_appends_export(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        env_file = tmp_path / "env.sh"
        monkeypatch.setenv("CLAUDE_ENV_FILE", str(env_file))

        assert setup.persist_env_variable("PROJECT_ROOT", "/repo") is True
        assert env_file.read_text() == 'export PROJECT_ROOT="/repo"\n'

    def test_persist_env_variable_without_target_returns_false(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("CLAUDE_ENV_FILE", raising=False)
        assert setup.persist_env_variable("X", "y") is False

    def test_check_dependencies_reports_per_tool(self, fake_process) -> None:  # noqa: ANN001
        fake_process.register(["node", "--version"], returncode=1, stdout="")
        fake_process.register(["python3", "--version"], stdout="Python 3.13.5")
        fake_process.register(["uv", "--version"], stdout="uv 0.5.0")
        fake_process.register(["git", "--version"], stdout="git version 2.40.0")

        deps = setup.check_dependencies()

        assert deps["node"] is None
        assert deps["python"] == "Python 3.13.5"
        assert deps["uv"] == "uv 0.5.0"
        assert deps["git"] == "git version 2.40.0"

    def test_get_project_info_detects_files_and_branch(self, fake_process, tmp_path: Path) -> None:  # noqa: ANN001
        fake_process.register(["git", "rev-parse", "--abbrev-ref", "HEAD"], stdout="main\n")
        (tmp_path / "package.json").write_text("{}")
        (tmp_path / "pyproject.toml").write_text("")
        claude = tmp_path / ".claude"
        claude.mkdir()
        (claude / "CLAUDE.md").write_text("# guide")

        info = setup.get_project_info(str(tmp_path))

        assert "Git branch: main" in info
        assert "Detected: Node.js project" in info
        assert "Detected: Python project (pyproject.toml)" in info
        assert "Claude Code configuration directory present" in info
        assert "Found CLAUDE.md in .claude/" in info


class TestStopHelpers:
    def test_completion_messages_are_non_empty_strings(self) -> None:
        messages = stop.get_completion_messages()
        assert len(messages) >= 1
        assert all(isinstance(m, str) and m for m in messages)

    def test_llm_completion_falls_back_to_canned_message(self, fake_process, no_llm_keys: None) -> None:  # noqa: ANN001
        # No API keys -> only the local ollama probe runs; make it fail so the
        # function falls back to a predefined message.
        ollama_script = str(HOOKS_DIR / "utils" / "llm" / "ollama.py")
        fake_process.register(["uv", "run", ollama_script, "--completion"], returncode=1, stdout="")

        message = stop.get_llm_completion_message()

        assert message in stop.get_completion_messages()

    def test_tts_script_path_resolves_to_pyttsx3(self) -> None:
        path = stop.get_tts_script_path()
        assert path is not None
        assert path.endswith("pyttsx3_tts.py")
        assert Path(path).exists()


class TestSubagentStop:
    def test_extracts_user_task_from_transcript(self, tmp_path: Path) -> None:
        transcript = tmp_path / "agent.jsonl"
        transcript.write_text(json.dumps({"type": "user", "message": {"content": "Build the auth system"}}) + "\n")

        result = subagent_stop.extract_task_context({"agent_transcript_path": str(transcript)})

        assert result == "Build the auth system"

    def test_missing_transcript_returns_default(self) -> None:
        assert subagent_stop.extract_task_context({}) == "completed a task"

    def test_tts_script_path_resolves_to_pyttsx3(self) -> None:
        path = subagent_stop.get_tts_script_path()
        assert path is not None
        assert path.endswith("pyttsx3_tts.py")
