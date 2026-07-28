"""Safely prune aged and oversized agent-harness logs and caches."""

from __future__ import annotations

import shutil
import stat
import time
from dataclasses import dataclass
from pathlib import Path

from utils.config import _option
from utils.harness_paths import cache_dir, data_dir, logs_root

DEFAULT_MAX_AGE_DAYS = 7
DEFAULT_MAX_TOTAL_MB = 100.0


@dataclass(frozen=True)
class PruneResult:
    """Summarize entries deleted by a retention pass."""

    logs_deleted: int = 0
    cache_deleted: int = 0
    data_sessions_deleted: int = 0
    bytes_freed: int = 0


@dataclass(frozen=True)
class _Entry:
    path: Path
    modified_at: float
    size: int
    kind: str


def _configured_number(key: str, default: float) -> float:
    """Read a non-negative numeric plugin option, falling back on invalid input."""
    value = _option(key)
    if value is None:
        return default
    try:
        return max(float(value), 0)
    except ValueError:
        return default


def _is_real_directory(path: Path) -> bool:
    try:
        return stat.S_ISDIR(path.lstat().st_mode)
    except OSError:
        return False


def _path_size(path: Path) -> int:
    """Return regular-file bytes below ``path`` without traversing symlinks."""
    try:
        mode = path.lstat().st_mode
    except OSError:
        return 0

    if stat.S_ISREG(mode):
        return path.lstat().st_size
    if not stat.S_ISDIR(mode):
        return 0

    try:
        children = list(path.iterdir())
    except OSError:
        return 0
    return sum(_path_size(child) for child in children)


def _entries(root: Path, *, directories_only: bool, kind: str) -> list[_Entry]:
    """List eligible direct children without following root or child symlinks."""
    if not _is_real_directory(root):
        return []

    entries: list[_Entry] = []
    try:
        children = list(root.iterdir())
    except OSError:
        return entries
    for child in children:
        try:
            child_stat = child.lstat()
        except OSError:
            continue
        if stat.S_ISLNK(child_stat.st_mode):
            continue
        if directories_only and not stat.S_ISDIR(child_stat.st_mode):
            continue
        entries.append(_Entry(child, child_stat.st_mtime, _path_size(child), kind))
    return entries


def _delete_entry(entry: _Entry) -> int | None:
    """Delete a non-symlink entry and return its previously measured byte count."""
    try:
        mode = entry.path.lstat().st_mode
    except OSError:
        return None
    if stat.S_ISLNK(mode):
        return None

    try:
        if stat.S_ISDIR(mode):
            shutil.rmtree(entry.path)
        else:
            entry.path.unlink()
    except OSError:
        return None
    return entry.size


def _prune_by_age(entries: list[_Entry], cutoff: float) -> tuple[list[_Entry], int, int]:
    """Delete aged entries and return the survivors, count, and freed bytes."""
    survivors: list[_Entry] = []
    deleted = 0
    bytes_freed = 0
    for entry in entries:
        if entry.modified_at >= cutoff:
            survivors.append(entry)
            continue
        deleted_bytes = _delete_entry(entry)
        if deleted_bytes is None:
            survivors.append(entry)
            continue
        deleted += 1
        bytes_freed += deleted_bytes
    return survivors, deleted, bytes_freed


def _prune_to_size(entries: list[_Entry], max_total_bytes: float) -> tuple[int, int, int]:
    """Evict the oldest entries until their combined size fits the cap."""
    total_size = sum(entry.size for entry in entries)
    logs_deleted = 0
    cache_deleted = 0
    bytes_freed = 0
    for entry in sorted(entries, key=lambda candidate: candidate.modified_at):
        if total_size <= max_total_bytes:
            break
        deleted_bytes = _delete_entry(entry)
        if deleted_bytes is None:
            continue
        total_size -= entry.size
        bytes_freed += deleted_bytes
        if entry.kind == "logs":
            logs_deleted += 1
        else:
            cache_deleted += 1
    return logs_deleted, cache_deleted, bytes_freed


def _prune_orphaned_session_data(logs_dir: Path, sessions_dir: Path) -> int:
    """Remove session state only after its corresponding log directory is absent."""
    deleted = 0
    for entry in _entries(sessions_dir, directories_only=False, kind="data"):
        if entry.path.suffix != ".json":
            continue
        session_id = entry.path.stem
        if _is_real_directory(logs_dir / session_id):
            continue
        if _delete_entry(entry) is not None:
            deleted += 1
    return deleted


def prune_sessions(
    max_age_days: float | None = None,
    max_total_mb: float | None = None,
    *,
    project_dir: Path | str | None = None,
    now: float | None = None,
) -> PruneResult:
    """Prune aged log/cache entries and log-orphaned session data safely."""
    age_days = (
        _configured_number("HOOKS_LOG_RETENTION_DAYS", float(DEFAULT_MAX_AGE_DAYS))
        if max_age_days is None
        else max(max_age_days, 0)
    )
    total_mb = (
        _configured_number("HOOKS_LOG_RETENTION_MAX_MB", DEFAULT_MAX_TOTAL_MB)
        if max_total_mb is None
        else max(max_total_mb, 0)
    )
    current_time = time.time() if now is None else now
    cutoff = current_time - (age_days * 86_400)
    logs_dir = logs_root(project_dir)
    cache_root = cache_dir(project_dir)

    log_entries, logs_by_age, freed_by_log_age = _prune_by_age(
        _entries(logs_dir, directories_only=True, kind="logs"), cutoff
    )
    cache_entries, cache_by_age, freed_by_cache_age = _prune_by_age(
        _entries(cache_root, directories_only=False, kind="cache"), cutoff
    )
    logs_by_size, cache_by_size, freed_by_size = _prune_to_size([*log_entries, *cache_entries], total_mb * 1024 * 1024)
    data_deleted = _prune_orphaned_session_data(logs_dir, data_dir(project_dir) / "sessions")

    return PruneResult(
        logs_deleted=logs_by_age + logs_by_size,
        cache_deleted=cache_by_age + cache_by_size,
        data_sessions_deleted=data_deleted,
        bytes_freed=freed_by_log_age + freed_by_cache_age + freed_by_size,
    )
