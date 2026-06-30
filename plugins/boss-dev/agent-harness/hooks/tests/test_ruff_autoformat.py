"""Tests for the ruff_autoformat PostToolUse hook.

The hook is config-gated and availability-gated: it must only invoke ruff when the
edited file lives in a project with a ruff config AND ruff is runnable, and it must
never block or error the tool call.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest
from hook_loader import load_hook

ruff_autoformat = load_hook("ruff_autoformat.py")


# --- find_ruff_config -------------------------------------------------------


@pytest.mark.parametrize("config_name", ["ruff.toml", ".ruff.toml"])
def test_find_ruff_config_dedicated_files(tmp_path: Path, config_name: str) -> None:
    (tmp_path / config_name).write_text("line-length = 120\n", encoding="utf-8")
    py_file = tmp_path / "pkg" / "x.py"
    assert ruff_autoformat.find_ruff_config(py_file) == tmp_path


def test_find_ruff_config_pyproject_with_tool_ruff(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[tool.ruff]\nline-length = 120\n", encoding="utf-8")
    py_file = tmp_path / "src" / "deep" / "x.py"
    assert ruff_autoformat.find_ruff_config(py_file) == tmp_path


def test_find_ruff_config_none_when_configless(tmp_path: Path) -> None:
    # A pyproject.toml without a [tool.ruff] table must NOT count as a config.
    (tmp_path / "pyproject.toml").write_text("[tool.black]\nline-length = 88\n", encoding="utf-8")
    py_file = tmp_path / "x.py"
    assert ruff_autoformat.find_ruff_config(py_file) is None


# --- ruff_cmd ---------------------------------------------------------------


def test_ruff_cmd_prefers_path_ruff(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ruff_autoformat.shutil, "which", lambda name: f"/usr/bin/{name}" if name == "ruff" else None)
    assert ruff_autoformat.ruff_cmd() == ["ruff"]


def test_ruff_cmd_falls_back_to_uvx(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ruff_autoformat.shutil, "which", lambda name: f"/usr/bin/{name}" if name == "uvx" else None)
    assert ruff_autoformat.ruff_cmd() == ["uvx", "ruff"]


def test_ruff_cmd_none_when_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ruff_autoformat.shutil, "which", lambda name: None)
    assert ruff_autoformat.ruff_cmd() is None


# --- main no-op behavior ----------------------------------------------------


def _run_main(monkeypatch: pytest.MonkeyPatch, payload: dict[str, object]) -> list[list[str]]:
    """Drive main() with the given stdin payload; return the ruff commands it ran."""
    calls: list[list[str]] = []
    monkeypatch.setattr(ruff_autoformat.sys, "stdin", io.StringIO(json.dumps(payload)))
    monkeypatch.setattr(ruff_autoformat.subprocess, "run", lambda cmd, **kwargs: calls.append(cmd))
    monkeypatch.setattr(ruff_autoformat.shutil, "which", lambda name: f"/usr/bin/{name}")
    ruff_autoformat.main()
    return calls


def test_main_noop_for_non_python_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    target = tmp_path / "README.md"
    target.write_text("hi\n", encoding="utf-8")
    (tmp_path / "ruff.toml").write_text("", encoding="utf-8")
    assert _run_main(monkeypatch, {"tool_input": {"file_path": str(target)}}) == []


def test_main_noop_without_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    target = tmp_path / "x.py"
    target.write_text("x=1\n", encoding="utf-8")
    before = target.read_text(encoding="utf-8")
    assert _run_main(monkeypatch, {"tool_input": {"file_path": str(target)}}) == []
    assert target.read_text(encoding="utf-8") == before


def test_main_runs_ruff_with_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / "ruff.toml").write_text("line-length = 120\n", encoding="utf-8")
    target = tmp_path / "x.py"
    target.write_text("x=1\n", encoding="utf-8")
    calls = _run_main(monkeypatch, {"tool_input": {"file_path": str(target)}})
    assert [c[0] for c in calls] == ["ruff", "ruff"]
    assert calls[0][1:3] == ["check", "--fix"]
    assert calls[1][1] == "format"


def test_main_noop_when_ruff_unavailable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    (tmp_path / "ruff.toml").write_text("", encoding="utf-8")
    target = tmp_path / "x.py"
    target.write_text("x=1\n", encoding="utf-8")
    calls: list[list[str]] = []
    monkeypatch.setattr(
        ruff_autoformat.sys, "stdin", io.StringIO(json.dumps({"tool_input": {"file_path": str(target)}}))
    )
    monkeypatch.setattr(ruff_autoformat.subprocess, "run", lambda cmd, **kwargs: calls.append(cmd))
    monkeypatch.setattr(ruff_autoformat.shutil, "which", lambda name: None)
    ruff_autoformat.main()
    assert calls == []
