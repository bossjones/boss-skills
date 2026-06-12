"""Tests for the fcntl-based TTS lock queue.

The lock lives at ``.claude/data/tts_queue/tts.lock`` relative to the CWD, so all
tests run inside an isolated tmp directory (``in_tmp_cwd``). The module keeps the
held descriptor in a module global, reset between tests.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterator
from datetime import datetime, timedelta

import pytest
from hook_loader import load_hook

tts_queue = load_hook("utils/tts/tts_queue.py")


@pytest.fixture(autouse=True)
def _reset_lock_handle() -> Iterator[None]:
    tts_queue._lock_file_handle = None
    yield
    # Best-effort release so a leaked descriptor can't bleed into the next test.
    try:
        tts_queue.release_tts_lock("teardown")
    except OSError:
        pass
    tts_queue._lock_file_handle = None


def _write_lock_file(*, agent_id: str, timestamp: str, pid: int) -> None:
    lock_file = tts_queue._LOCK_FILE
    lock_file.parent.mkdir(parents=True, exist_ok=True)
    lock_file.write_text(json.dumps({"agent_id": agent_id, "timestamp": timestamp, "pid": pid}))


@pytest.mark.usefixtures("in_tmp_cwd")
class TestLockLifecycle:
    def test_acquire_marks_locked_then_release_frees(self) -> None:
        assert tts_queue.is_tts_locked() is False
        assert tts_queue.acquire_tts_lock("agent-1", timeout=2) is True
        assert tts_queue.is_tts_locked() is True

        tts_queue.release_tts_lock("agent-1")
        assert tts_queue.is_tts_locked() is False

    def test_lock_info_round_trips_agent_and_pid(self) -> None:
        tts_queue.acquire_tts_lock("agent-xyz", timeout=2)
        info = tts_queue.get_lock_info()
        assert info is not None
        assert info["agent_id"] == "agent-xyz"
        assert info["pid"] == os.getpid()
        tts_queue.release_tts_lock("agent-xyz")

    def test_second_acquire_times_out_while_held(self) -> None:
        assert tts_queue.acquire_tts_lock("holder", timeout=2) is True
        # A different agent cannot acquire while the lock is held; it should give
        # up at the timeout rather than block forever.
        assert tts_queue.acquire_tts_lock("contender", timeout=1) is False
        tts_queue.release_tts_lock("holder")


@pytest.mark.usefixtures("in_tmp_cwd")
class TestCleanupStaleLocks:
    def test_removes_aged_lock_for_dead_process(self) -> None:
        old = (datetime.now() - timedelta(hours=1)).isoformat()
        _write_lock_file(agent_id="ghost", timestamp=old, pid=999_999)  # PID unlikely to exist

        tts_queue.cleanup_stale_locks(max_age_seconds=1)

        assert tts_queue._LOCK_FILE.exists() is False

    def test_keeps_lock_for_live_process(self) -> None:
        old = (datetime.now() - timedelta(hours=1)).isoformat()
        _write_lock_file(agent_id="alive", timestamp=old, pid=os.getpid())

        tts_queue.cleanup_stale_locks(max_age_seconds=1)

        # Our own PID is alive, so the (aged) lock must be preserved.
        assert tts_queue._LOCK_FILE.exists() is True

    def test_recent_lock_is_not_removed(self) -> None:
        now = datetime.now().isoformat()
        _write_lock_file(agent_id="fresh", timestamp=now, pid=999_999)

        tts_queue.cleanup_stale_locks(max_age_seconds=3600)

        assert tts_queue._LOCK_FILE.exists() is True
