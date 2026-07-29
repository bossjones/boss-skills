#!/usr/bin/env -S uv run --script --quiet
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Report agent-harness environment and runtime-storage health without changes."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
HOOKS_DIR = PLUGIN_ROOT / "hooks"
PLUGIN_MANIFEST = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
SETTINGS_PATHS = (Path(".claude") / "settings.local.json", Path(".claude") / "settings.json")


def _load_hook_module(name: str) -> ModuleType:
    """Load a hook utility by path so this standalone skill has no package dependency."""
    module_name = f"_agent_harness_{name}"
    cached = sys.modules.get(module_name)
    if isinstance(cached, ModuleType):
        return cached

    path = HOOKS_DIR / "utils" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load agent-harness utility: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _preflight() -> dict[str, dict[str, bool | str | None]]:
    """Return the shared advisory checks."""
    check_env = getattr(_load_hook_module("preflight"), "check_env")
    return check_env()


def _harness_root(repo_root: Path) -> Path:
    """Resolve the harness root through the canonical path helper."""
    existing_utils = {
        name: module for name, module in sys.modules.items() if name == "utils" or name.startswith("utils.")
    }
    try:
        for module_name in existing_utils:
            del sys.modules[module_name]
        package = ModuleType("utils")
        package.__path__ = [str(HOOKS_DIR / "utils")]
        sys.modules["utils"] = package

        path = HOOKS_DIR / "utils" / "harness_paths.py"
        spec = importlib.util.spec_from_file_location("utils.harness_paths", path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Cannot load harness path helper: {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules["utils.harness_paths"] = module
        spec.loader.exec_module(module)
        resolve_harness_root = module.resolve_harness_root
    finally:
        for module_name in list(sys.modules):
            if module_name == "utils" or module_name.startswith("utils."):
                del sys.modules[module_name]
        sys.modules.update(existing_utils)
    return resolve_harness_root(project_dir=repo_root)


def directory_size(path: Path) -> dict[str, int]:
    """Return regular-file count and bytes below ``path`` without following links."""
    files = 0
    size_bytes = 0
    if not path.is_dir() or path.is_symlink():
        return {"files": files, "bytes": size_bytes}

    for directory, _dirnames, filenames in os.walk(path, followlinks=False):
        directory_path = Path(directory)
        for filename in filenames:
            candidate = directory_path / filename
            try:
                stat = candidate.lstat()
            except OSError:
                continue
            if candidate.is_symlink() or not candidate.is_file():
                continue
            files += 1
            size_bytes += stat.st_size
    return {"files": files, "bytes": size_bytes}


def stale_artifact(path: Path) -> dict[str, Any]:
    """Describe a legacy artifact directory without altering it."""
    details = directory_size(path)
    return {
        "path": str(path),
        "exists": path.is_dir() and not path.is_symlink(),
        **details,
        "advice": "safe to delete after review; harness doctor never deletes files"
        if path.is_dir() and not path.is_symlink()
        else None,
    }


def _manifest() -> dict[str, Any]:
    """Read the installed plugin manifest if it is available and valid."""
    try:
        data = json.loads(PLUGIN_MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def enabled_plugins(repo_root: Path) -> list[dict[str, str | None]]:
    """Return enabled plugin identities from project settings with known versions."""
    manifest = _manifest()
    plugin_name = manifest.get("name") if isinstance(manifest.get("name"), str) else None
    current_version = manifest.get("version") if isinstance(manifest.get("version"), str) else None
    found: list[dict[str, str | None]] = []

    for relative_path in SETTINGS_PATHS:
        path = repo_root / relative_path
        try:
            settings = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        plugins = settings.get("enabledPlugins") if isinstance(settings, dict) else None
        if not isinstance(plugins, dict):
            continue
        for identity, enabled in plugins.items():
            if enabled is True and isinstance(identity, str):
                found.append({
                    "identity": identity,
                    "version": current_version if plugin_name and identity.startswith(f"{plugin_name}@") else None,
                    "settings_path": str(relative_path),
                })
    return found


def build_report(repo_root: Path) -> dict[str, Any]:
    """Build the complete read-only doctor report."""
    root = _harness_root(repo_root)
    storage = {name: directory_size(root / name) for name in ("logs", "data", "cache")}
    return {
        "repo_root": str(repo_root),
        "environment": _preflight(),
        "harness_root": {
            "path": str(root),
            "storage": storage,
            "bytes": sum(details["bytes"] for details in storage.values()),
        },
        "stale_artifacts": {
            "logs": stale_artifact(repo_root / "logs"),
            "claude_data": stale_artifact(repo_root / ".claude" / "data"),
        },
        "enabled_plugins": enabled_plugins(repo_root),
        "advisory": True,
    }


def build_parser() -> argparse.ArgumentParser:
    """Build the doctor CLI parser."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=os.getcwd(), help="repository root to inspect")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Print a structured, read-only diagnostic report."""
    args = build_parser().parse_args(argv)
    report = build_report(Path(args.repo_root).resolve())
    json.dump(report, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
