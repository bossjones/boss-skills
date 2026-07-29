"""Structural contract for agent-harness hook registration."""

from __future__ import annotations

import json
import re
import stat

from hook_loader import HOOKS_DIR

SUPPORTED_EVENTS = {
    "Notification",
    "PermissionDenied",
    "PermissionRequest",
    "PostCompact",
    "PostToolBatch",
    "PostToolUse",
    "PostToolUseFailure",
    "PreCompact",
    "PreToolUse",
    "SessionEnd",
    "SessionStart",
    "Setup",
    "Stop",
    "StopFailure",
    "SubagentStart",
    "SubagentStop",
    "TaskCompleted",
    "TaskCreated",
    "UserPromptExpansion",
    "UserPromptSubmit",
}

_SCRIPT_PATTERN = re.compile(r"/hooks/([A-Za-z0-9_./-]+)")


def _configured_scripts(config: dict[str, object]) -> set[str]:
    scripts: set[str] = set()
    for matchers in config["hooks"].values():  # type: ignore[index,union-attr]
        for matcher in matchers:
            for hook in matcher["hooks"]:
                scripts.update(_SCRIPT_PATTERN.findall(hook["command"]))
    return scripts


def test_hooks_json_references_only_existing_executable_scripts() -> None:
    config = json.loads((HOOKS_DIR / "hooks.json").read_text(encoding="utf-8"))

    assert set(config["hooks"]) == SUPPORTED_EVENTS
    for rel_path in _configured_scripts(config):
        path = HOOKS_DIR / rel_path
        assert path.is_file(), rel_path
        assert path.stat().st_mode & stat.S_IXUSR, rel_path
        if path.suffix == ".py":
            assert "# /// script" in path.read_text(encoding="utf-8"), rel_path


def test_top_level_hook_scripts_are_registered_or_explicitly_exempt() -> None:
    config = json.loads((HOOKS_DIR / "hooks.json").read_text(encoding="utf-8"))
    registered = _configured_scripts(config)
    exempt = {"utils", "validators"}

    for path in HOOKS_DIR.iterdir():
        if path.is_dir() or path.name in exempt:
            continue
        if path.suffix in {".py", ".sh"}:
            assert path.name in registered, path.name
