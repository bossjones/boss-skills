#!/usr/bin/env -S uv run --script --quiet
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""Resolve the name of the marketplace repository that ships this plugin.

Harness artifacts are namespaced to the plugin's source repository rather than
to whichever project a session happens to run in, so the same dot-directory
name appears in every project, worktree, and machine.

The namespace is derived from this file's own location: the nearest ancestor
holding a ``.claude-plugin/marketplace.json`` manifest is the marketplace
repository. Claude's global cache instead stores it in
``~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/``, so that
marketplace path segment is used when no manifest is available. Neither
strategy needs an environment variable — status lines and standalone skill
scripts do not reliably receive ``CLAUDE_PLUGIN_ROOT``.

This module deliberately imports nothing from ``utils``. Standalone consumers
(the ``harness-doctor`` and ``setup-agent-harness`` skill scripts) load it by
path with ``importlib``, which stays a two-line operation only while the module
has no intra-package imports.
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

DEFAULT_NAMESPACE = "agent-harness"
"""Namespace used when no marketplace manifest is found above this file."""

_MARKETPLACE_MANIFEST = Path(".claude-plugin") / "marketplace.json"

_NON_ALPHANUMERIC = re.compile(r"[^a-z0-9]+")


def slug(value: str) -> str:
    """Return a filesystem-safe, lowercase name derived from ``value``."""
    normalized = _NON_ALPHANUMERIC.sub("-", value.lower()).strip(".-")
    return normalized or DEFAULT_NAMESPACE


def namespace_from(start: Path | str) -> tuple[str, Path | None]:
    """Return the namespace for ``start`` and the marketplace root it came from.

    Walks the ancestors of ``start`` and stops at the first directory holding a
    marketplace manifest. The plugin's own ``.claude-plugin/`` contains only
    ``plugin.json``, so it never ends the walk early.

    Returns:
        The slugged marketplace directory name and its path, or
        ``(DEFAULT_NAMESPACE, None)`` when no manifest is found.
    """
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
    """Return the namespace for the installed copy of this plugin.

    Cached because status lines re-run on every assistant message and resolve
    this on their hot path.
    """
    return namespace_from(Path(__file__))[0]


def namespace_source() -> Path | None:
    """Return the marketplace root this plugin resolves its namespace from."""
    return namespace_from(Path(__file__))[1]
