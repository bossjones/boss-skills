"""Behavioral tests for log_event.py's CLI entry point, in particular the
append-before-prune ordering that keeps a retention failure from dropping the
event record it guards."""

from __future__ import annotations

import io
import json
import sys
import types
from pathlib import Path

import pytest
from hook_loader import HOOKS_DIR, load_hook

log_event = load_hook("log_event.py")
harness_paths = load_hook("utils/harness_paths.py")

# hooks/utils/ has no __init__.py, so it only ever resolves as a PEP 420
# namespace package — and a namespace package always loses to a *regular*
# module of the same name found anywhere else on sys.path, regardless of
# path order. Other skills' scripts/ directories accumulate on sys.path over
# the test session and are never removed (e.g. twitter-to-reel ships a flat
# scripts/utils.py), so leaving them in place while resolving `utils.*` here
# would silently resolve to the wrong module. Only exclude them for the
# duration of the call below.
_REPO_ROOT = HOOKS_DIR.parents[3]


def _run_main(argv: list[str], stdin_payload: dict[str, object], monkeypatch: pytest.MonkeyPatch) -> int:
    """Invoke log_event.main() with only hooks/ importable, then undo the leak.

    log_event.main() imports ``utils.*`` lazily inside the function body so any
    import failure stays fail-open. Running it directly (not via subprocess)
    means we must control sys.path for the duration of the call and then
    remove any ``utils`` modules it pulled in, mirroring hook_loader's own
    isolation so this test can't shadow other suites' ``utils`` packages.
    """
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(stdin_payload)))
    saved_path = list(sys.path)
    pre_existing = set(sys.modules)
    external = [entry for entry in sys.path if not Path(entry).is_relative_to(_REPO_ROOT)]
    sys.path[:] = [str(HOOKS_DIR), *external]
    try:
        return log_event.main(argv)
    finally:
        sys.path[:] = saved_path
        for name in set(sys.modules) - pre_existing:
            if name == "utils" or name.startswith("utils."):
                del sys.modules[name]


def test_session_end_append_survives_a_prune_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(tmp_path))

    # Any stale `utils`/`utils.*` entry already in sys.modules would be used
    # as-is (sys.modules is checked before sys.path), so clear it before
    # calling main() and restore it afterward. Harmless to whichever suite
    # left it there — its own module-level `from utils import ...` names were
    # already bound at that suite's own collection time.
    stale_utils = {
        name: sys.modules.pop(name) for name in list(sys.modules) if name == "utils" or name.startswith("utils.")
    }

    def _raise_prune(*args: object, **kwargs: object) -> None:
        raise OSError("retention failure")

    fake_retention = types.ModuleType("utils.log_retention")
    fake_retention.prune_sessions = _raise_prune  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "utils.log_retention", fake_retention)

    try:
        exit_code = _run_main(["--event-type", "SessionEnd", "--prune"], {"session_id": "session-1"}, monkeypatch)
    finally:
        sys.modules.update(stale_utils)

    assert exit_code == 0
    record_path = harness_paths.session_log_dir("session-1", tmp_path) / "SessionEnd.jsonl"
    record = json.loads(record_path.read_text())
    assert record["hook_event_type"] == "SessionEnd"
    assert record["session_id"] == "session-1"
