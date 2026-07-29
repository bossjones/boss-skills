"""Advisory environment checks shared by agent-harness tools."""

from __future__ import annotations

import shutil
import subprocess

_TOOL_HINTS = {
    "uv": "install uv: https://docs.astral.sh/uv/",
    "python3": "install Python 3.11+",
    "git": "install Git: https://git-scm.com/",
    "ruff": "install Ruff: https://docs.astral.sh/ruff/installation/",
    "tmux": "install tmux to enable terminal-session features",
}


def _tool_result(name: str) -> dict[str, bool | str | None]:
    """Return an advisory availability result for a command-line tool."""
    installed = shutil.which(name) is not None
    return {
        "ok": installed,
        "hint": None if installed else _TOOL_HINTS[name],
    }


def _gh_result() -> dict[str, bool | str | None]:
    """Return GitHub CLI availability and authentication status without blocking."""
    installed = shutil.which("gh") is not None
    authenticated = False
    if installed:
        try:
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            authenticated = result.returncode == 0
        except (OSError, subprocess.SubprocessError):
            authenticated = False

    hint: str | None
    if not installed:
        hint = "install GitHub CLI: https://cli.github.com/"
    elif not authenticated:
        hint = "run `gh auth login` to authenticate"
    else:
        hint = None
    return {"installed": installed, "authenticated": authenticated, "hint": hint}


def check_env() -> dict[str, dict[str, bool | str | None]]:
    """Report harness prerequisites; all results are advisory."""
    return {
        "uv": _tool_result("uv"),
        "python3": _tool_result("python3"),
        "git": _tool_result("git"),
        "gh": _gh_result(),
        "ruff": _tool_result("ruff"),
        "tmux": _tool_result("tmux"),
    }
