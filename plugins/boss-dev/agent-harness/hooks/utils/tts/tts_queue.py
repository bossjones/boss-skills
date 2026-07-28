#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///

"""
TTS Queue Manager

Provides file-based locking for managing concurrent TTS announcements.
Uses fcntl.flock for cross-process synchronization.

Functions:
    acquire_tts_lock(agent_id, timeout) - Acquire exclusive TTS lock
    release_tts_lock(agent_id) - Release the TTS lock
    is_tts_locked() - Check if TTS is currently locked
    cleanup_stale_locks(max_age_seconds) - Remove stale locks
"""

import fcntl
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

HOOKS_DIR = Path(__file__).resolve().parents[2]
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))

from utils.harness_paths import data_dir

# Global file handle for the lock (must persist while lock is held)
_lock_file_handle: int | None = None


def _lock_dir() -> Path:
    """Return the project-scoped TTS lock directory."""
    return data_dir() / "tts_queue"


def _lock_file() -> Path:
    """Return the project-scoped TTS lock file."""
    return _lock_dir() / "tts.lock"


def _ensure_lock_dir() -> None:
    """Ensure the lock directory exists."""
    _lock_dir().mkdir(parents=True, exist_ok=True)


def _write_lock_info(agent_id: str) -> None:
    """Write lock metadata to the lock file."""
    lock_info = {"agent_id": agent_id, "timestamp": datetime.now().isoformat(), "pid": os.getpid()}
    with _lock_file().open("w") as f:
        json.dump(lock_info, f)


def _read_lock_info() -> dict | None:
    """Read lock metadata from the lock file."""
    lock_file = _lock_file()
    if not lock_file.exists():
        return None
    try:
        with lock_file.open() as f:
            content = f.read().strip()
            if not content:
                return None
            return json.loads(content)
    except (json.JSONDecodeError, OSError):
        return None


def acquire_tts_lock(agent_id: str, timeout: int = 30) -> bool:
    """
    Acquire exclusive TTS lock using fcntl file locking.

    Args:
        agent_id: Identifier for the agent acquiring the lock
        timeout: Maximum seconds to wait for lock (default 30)

    Returns:
        True if lock acquired, False if timeout reached
    """
    global _lock_file_handle

    _ensure_lock_dir()

    start_time = time.time()
    retry_interval = 0.1  # Start with 100ms
    max_retry_interval = 1.0  # Cap at 1 second

    while True:
        elapsed = time.time() - start_time
        if elapsed >= timeout:
            return False

        try:
            # Open file for writing (create if needed)
            fd = os.open(str(_lock_file()), os.O_RDWR | os.O_CREAT, 0o644)

            try:
                # Try to acquire exclusive lock (non-blocking)
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

                # Lock acquired - store handle globally so it persists
                _lock_file_handle = fd

                # Write lock info
                _write_lock_info(agent_id)

                return True

            except (OSError, BlockingIOError):
                # Lock is held by another process
                os.close(fd)

        except OSError:
            # File operation failed
            pass

        # Wait before retry with exponential backoff
        time.sleep(retry_interval)
        retry_interval = min(retry_interval * 1.5, max_retry_interval)


def release_tts_lock(agent_id: str) -> None:
    """
    Release the TTS lock.

    Args:
        agent_id: Identifier for the agent releasing the lock (for verification)
    """
    global _lock_file_handle

    if _lock_file_handle is None:
        return

    try:
        # Clear the lock metadata while still holding the lock, using the held
        # descriptor. Doing this before LOCK_UN avoids a race where the next
        # holder acquires and writes its metadata only for us to blank it.
        try:
            os.ftruncate(_lock_file_handle, 0)
        except OSError:
            pass
        # Release the lock and close the descriptor
        fcntl.flock(_lock_file_handle, fcntl.LOCK_UN)
        os.close(_lock_file_handle)
    except OSError:
        pass
    finally:
        _lock_file_handle = None


def is_tts_locked() -> bool:
    """
    Check if TTS is currently locked by another process.

    Returns:
        True if locked, False if available
    """
    _ensure_lock_dir()

    lock_file = _lock_file()
    if not lock_file.exists():
        return False

    try:
        fd = os.open(str(lock_file), os.O_RDWR | os.O_CREAT, 0o644)
        try:
            # Try non-blocking lock
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            # If we got here, lock was available - release it immediately
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)
            return False
        except (OSError, BlockingIOError):
            # Lock is held
            os.close(fd)
            return True
    except OSError:
        return False


def cleanup_stale_locks(max_age_seconds: int = 60) -> None:
    """
    Remove locks older than max age.

    This is a safety mechanism for orphaned locks where the process
    died without releasing. Uses file modification time as fallback
    when lock info cannot be read.

    Args:
        max_age_seconds: Maximum age in seconds before lock is considered stale
    """
    lock_file = _lock_file()
    if not lock_file.exists():
        return

    try:
        lock_info = _read_lock_info()

        if lock_info and "timestamp" in lock_info:
            # Check timestamp from lock info
            try:
                lock_time = datetime.fromisoformat(lock_info["timestamp"])
                age = (datetime.now() - lock_time).total_seconds()
            except (ValueError, TypeError):
                # Invalid timestamp, use file mtime
                age = time.time() - lock_file.stat().st_mtime
        else:
            # No valid lock info, use file modification time
            age = time.time() - lock_file.stat().st_mtime

        if age > max_age_seconds:
            # Check if the PID is still running
            if lock_info and "pid" in lock_info:
                pid = lock_info["pid"]
                try:
                    # Check if process exists (signal 0 doesn't kill)
                    os.kill(pid, 0)
                    # Process still running, don't cleanup
                    return
                except (OSError, ProcessLookupError):
                    # Process not running, safe to cleanup
                    pass

            # Remove stale lock file
            try:
                lock_file.unlink()
            except OSError:
                pass

    except OSError:
        pass


def get_lock_info() -> dict | None:
    """
    Get information about the current lock holder.

    Returns:
        Dict with agent_id, timestamp, pid or None if not locked
    """
    return _read_lock_info()


if __name__ == "__main__":
    import sys

    def print_usage():
        print("TTS Queue Manager")
        print("=" * 40)
        print("\nUsage:")
        print("  tts_queue.py status        - Check lock status")
        print("  tts_queue.py acquire <id>  - Acquire lock for agent")
        print("  tts_queue.py release <id>  - Release lock for agent")
        print("  tts_queue.py cleanup       - Cleanup stale locks")

    if len(sys.argv) < 2:
        print_usage()
        sys.exit(0)

    command = sys.argv[1].lower()

    if command == "status":
        if is_tts_locked():
            info = get_lock_info()
            if info:
                print(f"Locked by: {info.get('agent_id', 'unknown')}")
                print(f"Since: {info.get('timestamp', 'unknown')}")
                print(f"PID: {info.get('pid', 'unknown')}")
            else:
                print("Locked (no info available)")
        else:
            print("Available")

    elif command == "acquire":
        if len(sys.argv) < 3:
            print("Error: agent_id required")
            sys.exit(1)
        agent_id = sys.argv[2]
        timeout = int(sys.argv[3]) if len(sys.argv) > 3 else 30
        if acquire_tts_lock(agent_id, timeout):
            print(f"Lock acquired for {agent_id}")
        else:
            print(f"Failed to acquire lock within {timeout}s")
            sys.exit(1)

    elif command == "release":
        if len(sys.argv) < 3:
            print("Error: agent_id required")
            sys.exit(1)
        agent_id = sys.argv[2]
        release_tts_lock(agent_id)
        print(f"Lock released for {agent_id}")

    elif command == "cleanup":
        max_age = int(sys.argv[2]) if len(sys.argv) > 2 else 60
        cleanup_stale_locks(max_age)
        print(f"Cleaned up locks older than {max_age}s")

    else:
        print(f"Unknown command: {command}")
        print_usage()
        sys.exit(1)
