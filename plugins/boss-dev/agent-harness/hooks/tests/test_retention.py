"""Focused retention tests for session logs, cache entries, and session state."""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest
from hook_loader import load_hook

harness_paths = load_hook("utils/harness_paths.py")
log_retention = load_hook("utils/log_retention.py")


@pytest.fixture
def project_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))
    return tmp_path


def _backdate(path: Path, *, days: int) -> None:
    timestamp = time.time() - (days * 86_400)
    os.utime(path, (timestamp, timestamp))


def test_age_pruning_removes_old_logs_and_cache_but_keeps_log_backed_session_data(project_dir: Path) -> None:
    logs_root = harness_paths.logs_root()
    cache_dir = harness_paths.cache_dir()
    sessions_dir = harness_paths.data_dir() / "sessions"
    old_log = logs_root / "old-session"
    active_log = logs_root / "active-session"
    old_log.mkdir(parents=True)
    active_log.mkdir(parents=True)
    (old_log / "event.jsonl").write_text("{}\n")
    (active_log / "event.jsonl").write_text("{}\n")
    old_cache = cache_dir / "old-cache.json"
    old_cache.parent.mkdir(parents=True)
    old_cache.write_text("{}")
    sessions_dir.mkdir(parents=True)
    (sessions_dir / "old-session.json").write_text("{}")
    active_data = sessions_dir / "active-session.json"
    active_data.write_text("{}")

    _backdate(old_log, days=8)
    _backdate(old_cache, days=8)
    _backdate(active_data, days=8)

    result = log_retention.prune_sessions(max_age_days=7, max_total_mb=100)

    assert not old_log.exists()
    assert not old_cache.exists()
    assert not (sessions_dir / "old-session.json").exists()
    assert active_data.exists()
    assert result.logs_deleted == 1
    assert result.cache_deleted == 1
    assert result.data_sessions_deleted == 1


def test_size_cap_evicts_oldest_log_entries_first(project_dir: Path) -> None:
    logs_root = harness_paths.logs_root()
    oldest = logs_root / "oldest"
    newest = logs_root / "newest"
    oldest.mkdir(parents=True)
    newest.mkdir(parents=True)
    (oldest / "event.jsonl").write_bytes(b"x" * 700_000)
    (newest / "event.jsonl").write_bytes(b"x" * 700_000)
    _backdate(oldest, days=2)

    result = log_retention.prune_sessions(max_age_days=7, max_total_mb=1)

    assert not oldest.exists()
    assert newest.exists()
    assert result.logs_deleted == 1


def test_pruning_never_follows_symlinks_outside_artifact_roots(project_dir: Path) -> None:
    logs_root = harness_paths.logs_root()
    logs_root.mkdir(parents=True)
    outside = project_dir / "outside-session"
    outside.mkdir()
    protected = outside / "protected.jsonl"
    protected.write_text("{}\n")
    (logs_root / "escape").symlink_to(outside, target_is_directory=True)

    log_retention.prune_sessions(max_age_days=0, max_total_mb=0)

    assert protected.exists()
    assert (logs_root / "escape").is_symlink()
