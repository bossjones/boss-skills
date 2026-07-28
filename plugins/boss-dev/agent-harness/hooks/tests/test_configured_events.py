"""Subprocess coverage for artifact-producing events wired in ``hooks.json``."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

from hook_loader import HOOKS_DIR, load_hook

harness_paths = load_hook("utils/harness_paths.py")
STATUS_LINES_DIR = HOOKS_DIR.parent / "status_lines"


def _run_hook(
    script: str, project_dir: Path, payload: Mapping[str, object], *args: str
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(HOOKS_DIR / script), *args],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=project_dir,
        env={"PATH": os.environ.get("PATH", os.defpath), "CLAUDE_PROJECT_DIR": str(project_dir)},
        check=False,
    )


def _event_commands(event_name: str) -> list[str]:
    config = json.loads((HOOKS_DIR / "hooks.json").read_text())
    return [
        hook["command"]
        for matcher in config["hooks"][event_name]
        for hook in matcher["hooks"]
        if hook["type"] == "command"
    ]


def _run_status_line(script: str, project_dir: Path, payload: Mapping[str, object]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(STATUS_LINES_DIR / script)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=project_dir,
        env={"PATH": os.environ.get("PATH", os.defpath), "CLAUDE_PROJECT_DIR": str(project_dir)},
        check=False,
    )


def test_every_registered_event_writes_a_parseable_session_record(tmp_path: Path) -> None:
    session_id = "all-events-session"
    config = json.loads((HOOKS_DIR / "hooks.json").read_text())
    payload = {
        "session_id": session_id,
        "cwd": str(tmp_path),
        "tool_name": "Bash",
        "tool_use_id": "tool-1",
        "task_id": "task-1",
    }

    for event_name in config["hooks"]:
        arguments = ["--event-type", event_name]
        if event_name == "SessionEnd":
            arguments.append("--prune")
        result = _run_hook("log_event.py", tmp_path, payload, *arguments)
        assert result.returncode == 0, event_name
        record = json.loads((harness_paths.session_log_dir(session_id, tmp_path) / f"{event_name}.jsonl").read_text())
        assert record["schema_version"] == 1
        assert record["hook_event_type"] == event_name
        assert record["session_id"] == session_id


def test_configured_event_artifacts_are_session_scoped(tmp_path: Path) -> None:
    session_id = "session-abc"
    payload = {"session_id": session_id, "tool_name": "Bash", "tool_input": {"command": "pwd"}}

    assert any("log_event.py --event-type PreToolUse" in command for command in _event_commands("PreToolUse"))
    assert _run_hook("log_event.py", tmp_path, payload, "--event-type", "PreToolUse").returncode == 0

    event_log = harness_paths.session_log_dir(session_id, tmp_path) / "PreToolUse.jsonl"
    assert json.loads(event_log.read_text())["session_id"] == session_id

    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(json.dumps({"type": "user", "message": {"content": "Hello"}}) + "\n")
    stop_payload = {"session_id": session_id, "transcript_path": str(transcript)}

    assert any("stop.py --chat" in command for command in _event_commands("Stop"))
    assert _run_hook("stop.py", tmp_path, stop_payload, "--chat").returncode == 0

    chat_file = harness_paths.session_log_dir(session_id, tmp_path) / "chat.json"
    assert json.loads(chat_file.read_text()) == [{"type": "user", "message": {"content": "Hello"}}]
    assert not (tmp_path / "logs").exists()
    assert not (tmp_path / ".claude" / "data").exists()


def test_configured_pre_tool_safety_hook_blocks_dangerous_rm(tmp_path: Path) -> None:
    payload = {"tool_name": "Bash", "tool_input": {"command": "rm -rf /"}}

    assert any("pre_tool_use.py" in command for command in _event_commands("PreToolUse"))
    result = _run_hook("pre_tool_use.py", tmp_path, payload)

    assert result.returncode == 2
    assert "BLOCKED: Dangerous rm command" in result.stderr


def test_status_lines_read_explicit_project_state_without_logging(tmp_path: Path) -> None:
    session_id = "session-abc"
    sessions_dir = harness_paths.data_dir(tmp_path) / "sessions"
    sessions_dir.mkdir(parents=True)
    (sessions_dir / f"{session_id}.json").write_text(
        json.dumps({"session_id": session_id, "agent_name": "Builder", "prompts": ["Implement artifact paths"]})
    )
    payload = {
        "session_id": session_id,
        "model": {"display_name": "Claude"},
        "workspace": {"project_dir": str(tmp_path)},
    }

    for script in ("status_line_v2.py", "status_line_v3.py", "status_line_v4.py"):
        result = _run_status_line(script, tmp_path, payload)
        assert result.returncode == 0
        assert "Implement artifact paths" in result.stdout

    timer_result = _run_status_line("status_line_v7.py", tmp_path, payload)
    assert timer_result.returncode == 0
    assert (harness_paths.data_dir(tmp_path) / "session_times.json").exists()
    assert not (tmp_path / "logs").exists()
