#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""PostToolUse auto-format hook: run ruff on edited Python files.

Triggered after ``Edit``/``MultiEdit``/``Write``. It is a deliberate **no-op**
unless the edited ``.py`` file belongs to a project that has a ruff config *and*
ruff is actually runnable. It never blocks or errors the tool call — it always
exits 0 and prints nothing.

Gating rationale:
- **Config gate** — without a ruff config (``ruff.toml``, ``.ruff.toml``, or a
  ``[tool.ruff]`` table in ``pyproject.toml``), ruff would run with built-in
  defaults and silently rewrite files in a project that never opted in. We refuse
  to touch such files.
- **Availability gate** — prefer ``ruff`` on ``PATH``, else ``uvx ruff``. We
  deliberately avoid ``uv run ruff``: that resolves ruff from the *project's*
  dependencies and hard-fails ("Failed to spawn: ruff") in projects that don't
  declare it.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

CONFIG_FILENAMES = ("ruff.toml", ".ruff.toml")


def find_ruff_config(path: Path) -> Path | None:
    """Return the first ancestor directory of ``path`` that holds a ruff config.

    Walks the file's parent directories upward, looking for ``ruff.toml``,
    ``.ruff.toml``, or a ``pyproject.toml`` containing a ``[tool.ruff`` table.
    Returns ``None`` when no config is found.
    """
    for directory in path.parents:
        for name in CONFIG_FILENAMES:
            if (directory / name).is_file():
                return directory
        pyproject = directory / "pyproject.toml"
        if pyproject.is_file():
            try:
                if "[tool.ruff" in pyproject.read_text(encoding="utf-8"):
                    return directory
            except OSError:
                pass
    return None


def ruff_cmd() -> list[str] | None:
    """Return the command prefix used to invoke ruff, or ``None`` if unavailable.

    Prefers a ``ruff`` already on ``PATH``; falls back to ``uvx ruff``. Avoids
    ``uv run ruff`` on purpose (it requires ruff in the project's dependencies).
    """
    if shutil.which("ruff"):
        return ["ruff"]
    if shutil.which("uvx"):
        return ["uvx", "ruff"]
    return None


def main() -> None:
    try:
        data = json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return

    file_path = data.get("tool_input", {}).get("file_path", "")
    if not file_path.endswith(".py"):
        return

    path = Path(file_path)
    if not path.is_file():
        return
    path = path.resolve()

    if find_ruff_config(path) is None:
        # No ruff config in the project tree — don't touch the file.
        return

    cmd = ruff_cmd()
    if cmd is None:
        # ruff isn't available — silently skip rather than erroring the edit.
        return

    for args in (["check", "--fix", str(path)], ["format", str(path)]):
        try:
            subprocess.run([*cmd, *args], capture_output=True, timeout=120, check=False)
        except (subprocess.TimeoutExpired, OSError):
            return


if __name__ == "__main__":
    main()
