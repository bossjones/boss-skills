"""Load agent-harness PEP 723 hook modules by path for testing.

The hook scripts under ``plugins/boss-dev/agent-harness/hooks`` are standalone
PEP 723 scripts (``#!/usr/bin/env -S uv run --script``), not installed modules.
They are loaded here via ``importlib.util.spec_from_file_location`` — the same
approach used by ``tests/test_version_bump_reviewer_hook.py`` at the repo root.

Isolation matters: some hooks (e.g. ``subagent_stop.py``) insert the hooks
directory onto ``sys.path`` at import time and pull in a top-level ``utils``
namespace package. Left in place, that ``utils`` would shadow other test suites
that have their own top-level ``utils`` module (e.g. twitter-to-reel). So each
load snapshots ``sys.path`` / ``sys.modules`` and rolls back any global mutation
the hook performed, keeping the hooks' nested imports from leaking out.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

HOOKS_DIR = Path(__file__).resolve().parent.parent

_CACHE: dict[str, ModuleType] = {}


def load_hook(rel_path: str) -> ModuleType:
    """Load (and cache) a hook module under ``hooks/`` by its relative path.

    Args:
        rel_path: Path relative to the hooks directory, e.g. ``"pre_tool_use.py"``
            or ``"utils/tts/tts_queue.py"``.

    Returns:
        The imported module object.
    """
    if rel_path in _CACHE:
        return _CACHE[rel_path]

    path = HOOKS_DIR / rel_path
    name = "agent_harness_hook_" + rel_path.replace("/", "_").removesuffix(".py")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load hook module: {rel_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module

    saved_path = list(sys.path)
    pre_existing = set(sys.modules)
    try:
        # Utility modules use the same absolute ``utils`` imports as hook
        # scripts. Make the hooks root available only while loading so those
        # sibling imports work without leaking a top-level namespace package.
        if str(HOOKS_DIR) not in sys.path:
            sys.path.insert(0, str(HOOKS_DIR))
        spec.loader.exec_module(module)
    finally:
        # Undo any sys.path entry the hook self-inserted, and drop top-level
        # ``utils`` namespace packages it created so they can't shadow other
        # suites' imports.
        sys.path[:] = saved_path
        for mod_name in set(sys.modules) - pre_existing:
            if mod_name == "utils" or mod_name.startswith("utils."):
                del sys.modules[mod_name]

    _CACHE[rel_path] = module
    return module
