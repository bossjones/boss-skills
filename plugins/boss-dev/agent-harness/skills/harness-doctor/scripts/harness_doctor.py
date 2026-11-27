#!/usr/bin/env -S uv run --script --quiet
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Report agent-harness environment and runtime-storage health without changes."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from functools import lru_cache
from pathlib import Path
from typing import Any

PLUGIN_ROOT = Path(__file__).resolve().parents[3]
PLUGIN_MANIFEST = PLUGIN_ROOT / ".claude-plugin" / "plugin.json"
SETTINGS_PATHS = (Path(".claude") / "settings.local.json", Path(".claude") / "settings.json")
DEFAULT_NAMESPACE = "boss-skills"
_MARKETPLACE_MANIFEST = Path(".claude-plugin") / "marketplace.json"
_NON_ALPHANUMERIC = re.compile(r"[^a-z0-9]+")
_TOOL_HINTS = {
    "uv": "install uv: https://docs.astral.sh/uv/",
    "python3": "install Python 3.11+",
    "git": "install Git: https://git-scm.com/",
    "ruff": "install Ruff: https://docs.astral.sh/ruff/installation/",
    "tmux": "install tmux to enable terminal-session features",
}


def slug(value: str) -> str:
    """Return a filesystem-safe, lowercase name derived from ``value``."""
    normalized = _NON_ALPHANUMERIC.sub("-", value.lower()).strip(".-")
    return normalized or DEFAULT_NAMESPACE


def namespace_from(start: Path | str) -> tuple[str, Path | None]:
    """Return the namespace for ``start`` and the marketplace root it came from."""
    try:
        resolved = Path(start).resolve()
    except OSError:
        return DEFAULT_NAMESPACE, None

    for ancestor in resolved.parents:
        try:
            if (ancestor / _MARKETPLACE_MANIFEST).is_file():
                return slug(ancestor.name), ancestor
        except OSError:
            continue

    for ancestor in resolved.parents:
        if ancestor.parent.name == "cache" and ancestor.parent.parent.name == "plugins":
            return slug(ancestor.name), None
    return DEFAULT_NAMESPACE, None


@lru_cache(maxsize=1)
def plugin_namespace() -> str:
    """Return the namespace for the installed copy of this plugin."""
    return namespace_from(Path(__file__))[0]


def namespace_source() -> Path | None:
    """Return the marketplace root this plugin resolves its namespace from."""
    return namespace_from(Path(__file__))[1]


def _tool_result(name: str) -> dict[str, bool | str | None]:
    installed = shutil.which(name) is not None
    return {
        "ok": installed,
        "hint": None if installed else _TOOL_HINTS[name],
    }


def _gh_result() -> dict[str, bool | str | None]:
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

    if not installed:
        hint: str | None = "install GitHub CLI: https://cli.github.com/"
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


def _preflight() -> dict[str, dict[str, bool | str | None]]:
    """Return the shared advisory checks."""
    return check_env()


def _namespace() -> tuple[str, Path | None]:
    """Return the plugin-repository namespace and the marketplace root it came from."""
    return plugin_namespace(), namespace_source()


def _legacy_project_root(repo_root: Path) -> Path:
    """Return the pre-namespace root this repository would have used."""
    return repo_root / f".{slug(repo_root.name)}"


def _project_dir(project_dir: Path | str | None = None) -> Path:
    if project_dir is not None:
        return Path(project_dir)
    if configured := os.environ.get("CLAUDE_PROJECT_DIR"):
        return Path(configured)
    return Path.cwd()


def _configured_path(configured: str, project: Path) -> Path:
    path = Path(configured)
    return path if path.is_absolute() else project / path


def resolve_harness_root(project_dir: Path | str | None = None) -> Path:
    """Resolve the shared harness root without creating directories."""
    project = _project_dir(project_dir)
    configured = (
        os.environ.get("CLAUDE_HARNESS_DIR")
        or os.environ.get("CLAUDE_PLUGIN_OPTION_HARNESS_DIR")
        or os.environ.get("HARNESS_DIR")
    )
    if configured:
        return _configured_path(configured, project)
    return project / f".{plugin_namespace()}"


def logs_root(project_dir: Path | str | None = None) -> Path:
    """Locate residual logs, honoring the legacy ``CLAUDE_HOOKS_LOG_DIR`` override (read-only)."""
    project = _project_dir(project_dir)
    if configured := os.environ.get("CLAUDE_HOOKS_LOG_DIR"):
        return _configured_path(configured, project)
    return resolve_harness_root(project) / "logs"


def data_dir(project_dir: Path | str | None = None) -> Path:
    return resolve_harness_root(project_dir) / "data"


def cache_dir(project_dir: Path | str | None = None) -> Path:
    return resolve_harness_root(project_dir) / "cache"


def _harness_root(repo_root: Path) -> Path:
    """Resolve the harness root through the canonical path helper."""
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
    namespace, namespace_source = _namespace()
    storage_paths = {
        "logs": logs_root(repo_root),
        "data": data_dir(repo_root),
        "cache": cache_dir(repo_root),
    }
    storage = {name: directory_size(path) for name, path in storage_paths.items()}

    stale: dict[str, Any] = {
        "logs": stale_artifact(repo_root / "logs"),
        "claude_data": stale_artifact(repo_root / ".claude" / "data"),
    }
    # A root named for this repository rather than for the plugin predates the
    # namespaced layout. Report it only when it exists and is not the live root.
    legacy_root = _legacy_project_root(repo_root)
    if legacy_root != root and legacy_root.is_dir() and not legacy_root.is_symlink():
        stale["legacy_project_root"] = stale_artifact(legacy_root)

    return {
        "repo_root": str(repo_root),
        "environment": _preflight(),
        "harness_root": {
            "path": str(root),
            "namespace": namespace,
            "namespace_source": str(namespace_source) if namespace_source else None,
            "storage": storage,
            "bytes": sum(details["bytes"] for details in storage.values()),
        },
        "stale_artifacts": stale,
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
