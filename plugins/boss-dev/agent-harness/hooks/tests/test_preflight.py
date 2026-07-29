"""Tests for shared advisory environment checks."""

from __future__ import annotations

import subprocess

from hook_loader import load_hook

preflight = load_hook("utils/preflight.py")


def test_check_env_reports_all_harness_tools() -> None:
    result = preflight.check_env()

    assert set(result) == {"uv", "python3", "git", "gh", "ruff", "tmux"}
    assert {"installed", "authenticated", "hint"} <= set(result["gh"])


def test_gh_auth_uses_fifteen_second_timeout(monkeypatch) -> None:
    monkeypatch.setattr(preflight.shutil, "which", lambda _name: "/tool")
    called: dict[str, object] = {}

    def fake_run(*_args, **kwargs):
        called.update(kwargs)
        return subprocess.CompletedProcess(args=[], returncode=0)

    monkeypatch.setattr(preflight.subprocess, "run", fake_run)

    assert preflight.check_env()["gh"]["authenticated"] is True
    assert called["timeout"] == 15
