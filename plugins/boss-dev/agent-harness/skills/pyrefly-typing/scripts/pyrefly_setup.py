#!/usr/bin/env -S uv run --script --quiet
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Adopt Pyrefly into a target ``uv`` Python project as a non-blocking checker.

Standalone PEP 723 script — stdlib only, run it with::

    uv run pyrefly_setup.py detect [--repo-root <path>]
    uv run pyrefly_setup.py apply  [flags...]

The script does all deterministic work: detecting the project's source/test
layout, Python version floor, existing type checkers (``ty``, ``basedpyright``,
``mypy``, ``pyright``), and task runner (``justfile``, ``Makefile``, or
``package.json``); writing a ``[tool.pyrefly]`` table without touching any
other tool's config; adding non-blocking ``check-pyrefly`` /
``pyrefly-baseline`` / ``pyrefly-coverage`` task-runner targets; optionally
merging a ``Stop`` hook entry into the target repo's ``.claude/settings.json``;
and running ``uv add --dev pyrefly`` plus the initial baseline generation.

It never decides whether to touch the target repo's existing lint/check/CI
config — it only ever adds new, standalone targets and leaves everything else
byte-for-byte unchanged.

Two modes:

- ``detect`` — prints a JSON report of current state to stdout. Read-only.
- ``apply`` — backup -> edit -> validate, driven by explicit flags.

Every modified file is copied to ``<file>.backup.<YYYYMMDD-HHMMSS>`` before
being written.
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import tomllib

# --- Constants -----------------------------------------------------------------

CANDIDATE_INCLUDE_DIRS: tuple[str, ...] = ("src", "tests")
TYPE_CHECKER_TOOL_KEYS: tuple[str, ...] = ("ty", "basedpyright", "mypy", "pyright")
BASELINE_FILENAME = "pyrefly-baseline.json"
SETTINGS_REL_PATH = Path(".claude") / "settings.json"
TASK_RUNNER_MARKER = "check-pyrefly:"


# --- Helpers ---------------------------------------------------------------


def timestamp() -> str:
    """Return a filesystem-safe timestamp like ``20260623-153012``."""
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def backup(path: Path) -> Path:
    """Copy ``path`` to ``<path>.backup.<timestamp>`` and return the new path.

    Only call this when a real change is about to be written.
    """
    dest = path.with_name(f"{path.name}.backup.{timestamp()}")
    shutil.copy2(path, dest)
    return dest


def _unified_diff(old: str, new: str, rel_path: str) -> str:
    """Return a git-style unified diff from ``old`` to ``new`` for ``rel_path``.

    Returns an empty string when the two texts are identical.
    """
    diff = difflib.unified_diff(
        old.splitlines(keepends=True),
        new.splitlines(keepends=True),
        fromfile=f"a/{rel_path}",
        tofile=f"b/{rel_path}",
    )
    return "".join(diff)


# --- Detection (pure) --------------------------------------------------------


def detect_python_version(python_version_file_text: str | None, requires_python: str | None) -> str | None:
    """Prefer ``.python-version``; else extract the floor from ``requires-python``."""
    if python_version_file_text:
        candidate = python_version_file_text.strip()
        if candidate:
            return candidate
    if requires_python:
        match = re.search(r"\d+\.\d+", requires_python)
        if match:
            return match.group(0)
    return None


def detect_project_includes(existing_dirnames: set[str]) -> list[str]:
    """Return the real source/test dirs present at the repo root, or ``["."]``."""
    found = [d for d in CANDIDATE_INCLUDE_DIRS if d in existing_dirnames]
    return found or ["."]


def detect_existing_type_checkers(pyproject_data: dict[str, Any]) -> list[str]:
    """Return which known type-checker tool tables are already configured."""
    tool = pyproject_data.get("tool", {})
    return [key for key in TYPE_CHECKER_TOOL_KEYS if key in tool]


def detect_legacy_type_checker(pyproject_data: dict[str, Any], top_level_names: set[str]) -> str | None:
    """Return ``"mypy"`` / ``"pyright"`` if a migratable legacy config exists, else ``None``.

    Checked in the same order ``pyrefly init --migrate-from auto`` tries them.
    """
    tool = pyproject_data.get("tool", {})
    if "mypy" in tool or "mypy.ini" in top_level_names:
        return "mypy"
    if "pyright" in tool or "pyrightconfig.json" in top_level_names:
        return "pyright"
    return None


def detect_task_runner(top_level_names: set[str]) -> str | None:
    """Return ``"just"`` / ``"make"`` / ``"npm"`` from top-level marker files."""
    if "justfile" in top_level_names or "Justfile" in top_level_names:
        return "just"
    if "Makefile" in top_level_names or "makefile" in top_level_names:
        return "make"
    if "package.json" in top_level_names:
        return "npm"
    return None


def has_pyrefly_dependency(pyproject_data: dict[str, Any]) -> bool:
    """Return ``True`` if ``pyrefly`` is already a dev dependency (PEP 735 or legacy uv)."""
    for group in pyproject_data.get("dependency-groups", {}).values():
        if isinstance(group, list) and any(isinstance(dep, str) and dep.lower().startswith("pyrefly") for dep in group):
            return True
    dev_deps = pyproject_data.get("tool", {}).get("uv", {}).get("dev-dependencies", [])
    return any(isinstance(dep, str) and dep.lower().startswith("pyrefly") for dep in dev_deps)


def pyproject_has_pyrefly_section(pyproject_text: str) -> bool:
    """Return ``True`` if ``[tool.pyrefly]`` already appears in the raw text."""
    return "[tool.pyrefly]" in pyproject_text


# --- Config block builders (pure) -------------------------------------------


def build_pyrefly_toml_block(project_includes: list[str], python_version: str) -> str:
    """Render a ``[tool.pyrefly]`` table (kebab-case keys, per the real Pyrefly config schema)."""
    includes_literal = json.dumps(project_includes)
    return f'[tool.pyrefly]\nproject-includes = {includes_literal}\npython-version = "{python_version}"\n'


def append_pyproject_section(pyproject_text: str, block: str) -> str:
    """Append ``block`` as a new table at EOF, never touching existing tables."""
    prefix = pyproject_text
    if prefix and not prefix.endswith("\n"):
        prefix += "\n"
    if prefix and not prefix.endswith("\n\n"):
        prefix += "\n"
    return prefix + block


def justfile_has_pyrefly_targets(text: str) -> bool:
    return TASK_RUNNER_MARKER in text


def build_justfile_block(includes: list[str]) -> str:
    coverage_paths = " ".join(includes)
    return (
        "\n# pyrefly type check (standalone; only fails on errors new since the baseline)\n"
        "check-pyrefly:\n"
        f"    uv run pyrefly check --baseline {BASELINE_FILENAME} --summarize-errors\n"
        "\n"
        "# refresh the committed baseline after fixing/introducing errors\n"
        "pyrefly-baseline:\n"
        f"    uv run pyrefly check --baseline {BASELINE_FILENAME} --update-baseline\n"
        "\n"
        "# type-coverage report (typed / Any / untyped) as JSON\n"
        "pyrefly-coverage:\n"
        f"    uv run pyrefly coverage report {coverage_paths}\n"
    )


def makefile_has_pyrefly_targets(text: str) -> bool:
    return TASK_RUNNER_MARKER in text


def build_makefile_block(includes: list[str]) -> str:
    coverage_paths = " ".join(includes)
    return (
        "\n.PHONY: check-pyrefly pyrefly-baseline pyrefly-coverage\n"
        "\n"
        "check-pyrefly:\n"
        f"\tuv run pyrefly check --baseline {BASELINE_FILENAME} --summarize-errors\n"
        "\n"
        "pyrefly-baseline:\n"
        f"\tuv run pyrefly check --baseline {BASELINE_FILENAME} --update-baseline\n"
        "\n"
        "pyrefly-coverage:\n"
        f"\tuv run pyrefly coverage report {coverage_paths}\n"
    )


def merge_npm_scripts(package_data: dict[str, Any], includes: list[str]) -> tuple[dict[str, Any], list[str]]:
    """Return ``(merged, added_script_names)`` — additive ``package.json`` scripts merge."""
    merged = json.loads(json.dumps(package_data))  # deep copy
    scripts = merged.setdefault("scripts", {})
    desired = {
        "check-pyrefly": f"uv run pyrefly check --baseline {BASELINE_FILENAME} --summarize-errors",
        "pyrefly-baseline": f"uv run pyrefly check --baseline {BASELINE_FILENAME} --update-baseline",
        "pyrefly-coverage": f"uv run pyrefly coverage report {' '.join(includes)}",
    }
    added = [name for name, cmd in desired.items() if scripts.get(name) != cmd]
    scripts.update(desired)
    return merged, added


def build_stop_hook_entry() -> dict[str, Any]:
    """Render the Stop-hook group per ``specs/pyrefly.md`` / the Pyrefly agentic-loop post."""
    return {
        "hooks": [
            {
                "type": "command",
                "command": (
                    f'cd "$CLAUDE_PROJECT_DIR" && uv run pyrefly check --baseline {BASELINE_FILENAME} >&2 || exit 2'
                ),
                "timeout": 30,
            }
        ]
    }


def merge_stop_hook(settings: dict[str, Any], entry: dict[str, Any]) -> tuple[dict[str, Any], bool]:
    """Append ``entry`` to ``settings["hooks"]["Stop"]`` unless an identical command exists.

    Never removes or replaces existing ``Stop`` entries — additive only.
    """
    merged: dict[str, Any] = json.loads(json.dumps(settings))  # deep copy
    hooks: dict[str, Any] = merged.setdefault("hooks", {})
    stop_list: list[Any] = hooks.setdefault("Stop", [])
    existing_commands: set[Any] = set()
    for group in stop_list:
        if not isinstance(group, dict):
            continue
        group_dict: dict[str, Any] = group
        for h in group_dict.get("hooks", []):
            if isinstance(h, dict):
                h_dict: dict[str, Any] = h
                existing_commands.add(h_dict.get("command"))
    entry_commands = {h["command"] for h in entry["hooks"]}
    if entry_commands & existing_commands:
        return merged, False
    stop_list.append(entry)
    return merged, True


# --- settings.json load (validated) -----------------------------------------


class SettingsError(RuntimeError):
    """Raised when settings cannot be safely loaded or written."""


def load_settings(path: Path) -> dict[str, Any]:
    """Parse existing settings or return ``{}``; abort on invalid JSON."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SettingsError(
            f"{path} contains invalid JSON ({exc}); refusing to overwrite. Fix or remove the file and re-run."
        ) from exc
    if not isinstance(data, dict):
        raise SettingsError(f"{path} must contain a JSON object, got {type(data).__name__}.")
    return data


def load_pyproject(path: Path) -> tuple[str, dict[str, Any]]:
    """Return ``(raw_text, parsed)``; ``parsed`` is ``{}`` when the file is absent."""
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    data = tomllib.loads(text) if text else {}
    return text, data


# --- environment readiness ---------------------------------------------------


def check_env() -> dict[str, Any]:
    """Report (never block) on whether ``uv`` is available."""
    uv_ok = shutil.which("uv") is not None
    return {"uv": {"ok": uv_ok, "hint": None if uv_ok else "install uv: https://docs.astral.sh/uv/"}}


# --- IO-driving apply steps ---------------------------------------------------


def ensure_pyrefly_dependency(repo_root: Path, already_present: bool, dry_run: bool) -> dict[str, Any]:
    if already_present:
        return {"changed": False, "already_present": True}
    cmd = ["uv", "add", "--dev", "pyrefly"]
    if dry_run:
        return {"changed": True, "dry_run": True, "command": " ".join(cmd)}
    proc = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, check=False)  # noqa: S603
    return {
        "changed": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def apply_pyrefly_config(
    pyproject_path: Path, current_text: str, includes: list[str], python_version: str, dry_run: bool
) -> dict[str, Any]:
    if pyproject_has_pyrefly_section(current_text):
        return {"changed": False, "already_present": True}
    block = build_pyrefly_toml_block(includes, python_version)
    new_text = append_pyproject_section(current_text, block)
    if dry_run:
        return {"changed": True, "dry_run": True, "diff": _unified_diff(current_text, new_text, "pyproject.toml")}
    backup_path = backup(pyproject_path) if pyproject_path.exists() else None
    pyproject_path.write_text(new_text, encoding="utf-8")
    return {"changed": True, "backup": str(backup_path) if backup_path else None}


def run_pyrefly_init_migrate(repo_root: Path, migrate_from: str, dry_run: bool) -> dict[str, Any]:
    cmd = ["uv", "run", "pyrefly", "init", "--migrate-from", migrate_from]
    if dry_run:
        return {"changed": True, "dry_run": True, "command": " ".join(cmd), "migrated_from": migrate_from}
    proc = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, check=False)  # noqa: S603
    return {
        "changed": proc.returncode == 0,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
        "migrated_from": migrate_from,
    }


def apply_task_runner(repo_root: Path, task_runner: str, includes: list[str], dry_run: bool) -> dict[str, Any]:
    if task_runner == "npm":
        return apply_npm_scripts(repo_root, includes, dry_run)

    if task_runner == "just":
        path = repo_root / "justfile"
        if not path.exists() and (repo_root / "Justfile").exists():
            path = repo_root / "Justfile"
        marker_check, block_builder = justfile_has_pyrefly_targets, build_justfile_block
    elif task_runner == "make":
        path = repo_root / "Makefile"
        if not path.exists() and (repo_root / "makefile").exists():
            path = repo_root / "makefile"
        marker_check, block_builder = makefile_has_pyrefly_targets, build_makefile_block
    else:
        return {"changed": False, "skipped": True, "reason": f"unsupported task runner {task_runner!r}"}

    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if marker_check(text):
        return {"changed": False, "already_present": True}
    block = block_builder(includes)
    new_text = text + ("\n" if text and not text.endswith("\n") else "") + block
    if dry_run:
        return {"changed": True, "dry_run": True, "diff": _unified_diff(text, new_text, path.name)}
    backup_path = backup(path) if path.exists() else None
    path.write_text(new_text, encoding="utf-8")
    return {"changed": True, "backup": str(backup_path) if backup_path else None}


def apply_npm_scripts(repo_root: Path, includes: list[str], dry_run: bool) -> dict[str, Any]:
    path = repo_root / "package.json"
    text = path.read_text(encoding="utf-8") if path.exists() else "{}"
    data = json.loads(text)
    merged, added = merge_npm_scripts(data, includes)
    if not added:
        return {"changed": False, "already_present": True}
    new_text = json.dumps(merged, indent=2) + "\n"
    if dry_run:
        return {"changed": True, "dry_run": True, "diff": _unified_diff(text, new_text, "package.json"), "added": added}
    backup_path = backup(path) if path.exists() else None
    path.write_text(new_text, encoding="utf-8")
    return {"changed": True, "backup": str(backup_path) if backup_path else None, "added": added}


def apply_stop_hook(repo_root: Path, dry_run: bool) -> dict[str, Any]:
    path = repo_root / SETTINGS_REL_PATH
    current = load_settings(path)
    entry = build_stop_hook_entry()
    merged, changed = merge_stop_hook(current, entry)
    if not changed:
        return {"changed": False, "already_present": True}
    payload = json.dumps(merged, indent=2) + "\n"
    if dry_run:
        old_text = path.read_text(encoding="utf-8") if path.exists() else ""
        return {"changed": True, "dry_run": True, "diff": _unified_diff(old_text, payload, str(SETTINGS_REL_PATH))}
    path.parent.mkdir(parents=True, exist_ok=True)
    backup_path = backup(path) if path.exists() else None
    path.write_text(payload, encoding="utf-8")
    return {"changed": True, "backup": str(backup_path) if backup_path else None}


def run_pyrefly_baseline(repo_root: Path, dry_run: bool) -> dict[str, Any]:
    cmd = ["uv", "run", "pyrefly", "check", "--baseline", BASELINE_FILENAME, "--update-baseline"]
    if dry_run:
        return {"changed": True, "dry_run": True, "command": " ".join(cmd)}
    proc = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, check=False)  # noqa: S603
    baseline_path = repo_root / BASELINE_FILENAME
    return {
        "changed": baseline_path.exists(),
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip()[-4000:],
        "stderr": proc.stderr.strip()[-2000:],
    }


# --- detect / apply commands --------------------------------------------------


def _settings_has_stop_hook(repo_root: Path) -> bool | None:
    """Return whether a pyrefly Stop-hook entry already exists, or ``None`` if unreadable."""
    try:
        settings = load_settings(repo_root / SETTINGS_REL_PATH)
    except SettingsError:
        return None
    _, changed = merge_stop_hook(settings, build_stop_hook_entry())
    return not changed


def cmd_detect(repo_root: Path) -> int:
    pyproject_path = repo_root / "pyproject.toml"
    pyproject_text, pyproject_data = load_pyproject(pyproject_path)
    python_version_file = repo_root / ".python-version"
    pv_text = python_version_file.read_text(encoding="utf-8") if python_version_file.exists() else None
    requires_python = pyproject_data.get("project", {}).get("requires-python")
    top_level_names = {p.name for p in repo_root.iterdir()} if repo_root.exists() else set[str]()

    report = {
        "repo_root": str(repo_root),
        "pyproject_exists": pyproject_path.exists(),
        "python_version": detect_python_version(pv_text, requires_python),
        "project_includes": detect_project_includes(top_level_names),
        "existing_type_checkers": detect_existing_type_checkers(pyproject_data),
        "legacy_config": detect_legacy_type_checker(pyproject_data, top_level_names),
        "has_pyrefly_config": pyproject_has_pyrefly_section(pyproject_text),
        "pyrefly_dev_dependency": has_pyrefly_dependency(pyproject_data),
        "task_runner": detect_task_runner(top_level_names),
        "has_baseline": (repo_root / BASELINE_FILENAME).exists(),
        "settings_path_exists": (repo_root / SETTINGS_REL_PATH).exists(),
        "has_stop_hook": _settings_has_stop_hook(repo_root),
        "env": check_env(),
    }
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def cmd_apply(args: argparse.Namespace) -> int:
    repo_root = Path(args.repo_root).resolve()
    pyproject_path = repo_root / "pyproject.toml"
    if not pyproject_path.exists():
        print(f"error: {pyproject_path} not found — this skill targets uv Python projects", file=sys.stderr)
        return 1

    pyproject_text, pyproject_data = load_pyproject(pyproject_path)
    python_version_file = repo_root / ".python-version"
    pv_text = python_version_file.read_text(encoding="utf-8") if python_version_file.exists() else None
    requires_python = pyproject_data.get("project", {}).get("requires-python")
    top_level_names = {p.name for p in repo_root.iterdir()}

    includes = (
        [d.strip() for d in args.project_includes.split(",")]
        if args.project_includes
        else detect_project_includes(top_level_names)
    )
    python_version = args.python_version or detect_python_version(pv_text, requires_python) or "3.11"

    task_runner: str | None = args.task_runner
    if task_runner == "auto":
        task_runner = detect_task_runner(top_level_names)
    elif task_runner == "none":
        task_runner = None

    legacy = detect_legacy_type_checker(pyproject_data, top_level_names)
    migrate_from: str | None = args.migrate_from
    if migrate_from == "auto":
        migrate_from = legacy
    elif migrate_from == "none":
        migrate_from = None

    summary: dict[str, Any] = {"repo_root": str(repo_root), "dry_run": args.dry_run}
    backups: list[str] = []

    try:
        # Fail fast on unreadable target settings before mutating anything else.
        if args.with_stop_hook:
            load_settings(repo_root / SETTINGS_REL_PATH)

        already_dep = has_pyrefly_dependency(pyproject_data)
        summary["dependency"] = ensure_pyrefly_dependency(repo_root, already_dep, args.dry_run)

        if migrate_from:
            config_result = run_pyrefly_init_migrate(repo_root, migrate_from, args.dry_run)
        else:
            config_result = apply_pyrefly_config(pyproject_path, pyproject_text, includes, python_version, args.dry_run)
            if config_result.get("backup"):
                backups.append(str(config_result["backup"]))
        summary["config"] = config_result

        if task_runner:
            tr_result = apply_task_runner(repo_root, task_runner, includes, args.dry_run)
            if tr_result.get("backup"):
                backups.append(str(tr_result["backup"]))
        else:
            tr_result = {"changed": False, "skipped": True, "reason": "no task runner detected"}
        summary["task_runner"] = tr_result

        if args.with_stop_hook:
            hook_result = apply_stop_hook(repo_root, args.dry_run)
            if hook_result.get("backup"):
                backups.append(str(hook_result["backup"]))
        else:
            hook_result = {"changed": False, "skipped": True}
        summary["stop_hook"] = hook_result

        if args.skip_baseline:
            summary["baseline"] = {"changed": False, "skipped": True}
        else:
            summary["baseline"] = run_pyrefly_baseline(repo_root, args.dry_run)
    except SettingsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    summary["backups"] = backups
    json.dump(summary, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p_detect = sub.add_parser("detect", help="print current state as JSON (read-only)")
    p_detect.add_argument("--repo-root", default=os.getcwd())

    p_apply = sub.add_parser("apply", help="adopt pyrefly: config, task-runner targets, optional hook, baseline")
    p_apply.add_argument("--repo-root", default=os.getcwd())
    p_apply.add_argument(
        "--project-includes", default=None, help="comma-separated dirs, e.g. src,tests (default: auto-detect)"
    )
    p_apply.add_argument(
        "--python-version", default=None, help="e.g. 3.12 (default: auto-detect from .python-version/requires-python)"
    )
    p_apply.add_argument("--task-runner", choices=["auto", "just", "make", "npm", "none"], default="auto")
    p_apply.add_argument(
        "--migrate-from",
        choices=["auto", "mypy", "pyright", "none"],
        default="auto",
        help="use `pyrefly init --migrate-from` instead of hand-writing config when a legacy checker is detected",
    )
    p_apply.add_argument("--with-stop-hook", action="store_true", help="merge a Stop hook into .claude/settings.json")
    p_apply.add_argument(
        "--skip-baseline", action="store_true", help="skip `uv add --dev pyrefly` and baseline generation"
    )
    p_apply.add_argument("--dry-run", action="store_true", help="report intended changes without writing or running uv")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "detect":
        return cmd_detect(Path(args.repo_root).resolve())
    if args.command == "apply":
        return cmd_apply(args)
    return 2  # pragma: no cover


if __name__ == "__main__":
    raise SystemExit(main())
