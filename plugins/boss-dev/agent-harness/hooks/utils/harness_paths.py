"""Resolve the project-local roots used by agent-harness hook artifacts."""

from __future__ import annotations

import os
import re
from pathlib import Path

from utils.config import _option

DEFAULT_HARNESS_DIR = ".agent-harness"

_NON_ALPHANUMERIC = re.compile(r"[^a-z0-9]+")


def slug(value: str) -> str:
    """Return a filesystem-safe, lowercase name derived from ``value``."""
    normalized = _NON_ALPHANUMERIC.sub("-", value.lower()).strip(".-")
    return normalized or "agent-harness"


def _project_dir(project_dir: Path | str | None) -> Path | None:
    """Return the explicit, environment-provided, or current project directory."""
    if project_dir is not None:
        return Path(project_dir)

    configured = os.environ.get("CLAUDE_PROJECT_DIR")
    if configured:
        return Path(configured)

    try:
        return Path(os.getcwd())
    except OSError:
        return None


def _configured_path(value: str, project_dir: Path) -> Path:
    """Resolve a configured path relative to its project without creating it."""
    path = Path(value)
    return path if path.is_absolute() else project_dir / path


def resolve_harness_root(project_dir: Path | str | None = None) -> Path:
    """Resolve the shared harness root without creating directories.

    ``project_dir`` explicitly selects the project anchor. It therefore takes
    precedence over ``CLAUDE_PROJECT_DIR`` and the process working directory;
    configured harness directories remain relative to that selected project.
    """
    resolved_project_dir = _project_dir(project_dir)
    configured = os.environ.get("CLAUDE_HARNESS_DIR")
    if configured:
        return Path(configured) if resolved_project_dir is None else _configured_path(configured, resolved_project_dir)

    configured = _option("HARNESS_DIR")
    if configured:
        return Path(configured) if resolved_project_dir is None else _configured_path(configured, resolved_project_dir)

    if resolved_project_dir is None:
        return Path(DEFAULT_HARNESS_DIR)

    return resolved_project_dir / f".{slug(resolved_project_dir.name)}"


def logs_root(project_dir: Path | str | None = None) -> Path:
    """Return the log root, honoring the narrow legacy log-directory override."""
    resolved_project_dir = _project_dir(project_dir)
    configured = os.environ.get("CLAUDE_HOOKS_LOG_DIR")
    if configured:
        return Path(configured) if resolved_project_dir is None else _configured_path(configured, resolved_project_dir)
    return resolve_harness_root(project_dir) / "logs"


def data_dir(project_dir: Path | str | None = None) -> Path:
    """Return the runtime data directory without creating it."""
    return resolve_harness_root(project_dir) / "data"


def cache_dir(project_dir: Path | str | None = None) -> Path:
    """Return the regenerable cache directory without creating it."""
    return resolve_harness_root(project_dir) / "cache"


def session_log_dir(session_id: str, project_dir: Path | str | None = None) -> Path:
    """Return the directory for a single session's event logs."""
    return logs_root(project_dir) / session_id
