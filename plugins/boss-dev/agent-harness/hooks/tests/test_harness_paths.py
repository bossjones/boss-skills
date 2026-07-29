"""Focused tests for the shared agent-harness artifact path resolver."""

from __future__ import annotations

from pathlib import Path

import pytest
from hook_loader import load_hook

harness_paths = load_hook("utils/harness_paths.py")


@pytest.fixture(autouse=True)
def _clear_path_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prevent ambient Claude configuration from selecting a test path."""
    for name in (
        "CLAUDE_PROJECT_DIR",
        "CLAUDE_HARNESS_DIR",
        "HARNESS_DIR",
        "CLAUDE_PLUGIN_OPTION_HARNESS_DIR",
        "CLAUDE_HOOKS_LOG_DIR",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("boss-skills", "boss-skills"),
        ("My Repo (v2)", "my-repo-v2"),
        (".dotted", "dotted"),
        ("UPPER", "upper"),
        ("---", "agent-harness"),
        ("", "agent-harness"),
        ("日本語", "agent-harness"),
    ],
)
def test_slug_normalizes_project_basenames(value: str, expected: str) -> None:
    assert harness_paths.slug(value) == expected


def test_explicit_project_dir_is_used_as_the_project_anchor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project_dir = tmp_path / "Explicit Project"
    other_dir = tmp_path / "other"
    project_dir.mkdir()
    other_dir.mkdir()
    monkeypatch.chdir(other_dir)
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(other_dir))

    assert harness_paths.resolve_harness_root(project_dir=project_dir) == project_dir / ".explicit-project"


def test_claude_harness_dir_overrides_derived_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project_dir = tmp_path / "project"
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project_dir))
    monkeypatch.setenv("CLAUDE_HARNESS_DIR", "runtime/harness")
    monkeypatch.setenv("CLAUDE_PLUGIN_OPTION_HARNESS_DIR", "plugin/harness")

    assert harness_paths.resolve_harness_root() == project_dir / "runtime/harness"


def test_plugin_option_harness_dir_precedes_bare_option(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project_dir = tmp_path / "project"
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project_dir))
    monkeypatch.setenv("HARNESS_DIR", "bare")
    monkeypatch.setenv("CLAUDE_PLUGIN_OPTION_HARNESS_DIR", "plugin")

    assert harness_paths.resolve_harness_root() == project_dir / "plugin"


def test_derivation_uses_project_environment_not_current_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_dir = tmp_path / "My Project"
    working_dir = tmp_path / "unrelated"
    project_dir.mkdir()
    working_dir.mkdir()
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project_dir))
    monkeypatch.chdir(working_dir)

    assert harness_paths.resolve_harness_root() == project_dir / ".my-project"


def test_unresolvable_project_directory_uses_the_single_default_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise_os_error() -> str:
        raise OSError("no current directory")

    monkeypatch.setattr(harness_paths.os, "getcwd", _raise_os_error)

    assert harness_paths.resolve_harness_root() == Path(harness_paths.DEFAULT_HARNESS_DIR)


def test_artifact_paths_are_side_effect_free_and_log_override_is_narrow(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    project_dir = tmp_path / "project"
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(project_dir))
    monkeypatch.setenv("CLAUDE_HOOKS_LOG_DIR", "compat-logs")

    root = harness_paths.resolve_harness_root()
    assert harness_paths.logs_root() == project_dir / "compat-logs"
    assert harness_paths.data_dir() == root / "data"
    assert harness_paths.cache_dir() == root / "cache"
    assert harness_paths.session_log_dir("session-1") == project_dir / "compat-logs" / "session-1"
    assert not root.exists()
    assert not (project_dir / "compat-logs").exists()


@pytest.mark.parametrize("bad_session_id", ["../../etc", "..", ".", "", "a/b", "a\\b"])
def test_session_log_dir_rejects_path_traversal(bad_session_id: str, tmp_path: Path) -> None:
    assert harness_paths.session_log_dir(bad_session_id, tmp_path) == harness_paths.logs_root(tmp_path) / "unknown"


@pytest.mark.parametrize("bad_agent_id", ["../../etc", "..", ".", "", "a/b", "a\\b"])
def test_agent_log_dir_rejects_path_traversal_in_agent_id(bad_agent_id: str, tmp_path: Path) -> None:
    expected = harness_paths.session_log_dir("session-1", tmp_path) / "agents" / "unknown"
    assert harness_paths.agent_log_dir("session-1", bad_agent_id, tmp_path) == expected


def test_agent_log_dir_rejects_path_traversal_in_session_id(tmp_path: Path) -> None:
    expected = harness_paths.logs_root(tmp_path) / "unknown" / "agents" / "agent-1"
    assert harness_paths.agent_log_dir("../../etc", "agent-1", tmp_path) == expected
