#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# ///
"""Append one fail-open, session-scoped JSONL record for a hook event."""

from __future__ import annotations

import argparse
import json
import sys
from typing import NoReturn


class _SilentArgumentParser(argparse.ArgumentParser):
    """Raise instead of writing parse errors to stderr."""

    def error(self, message: str) -> NoReturn:
        raise ValueError(message)


def _arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse the logger's intentionally small command-line interface."""
    parser = _SilentArgumentParser(add_help=False, allow_abbrev=False)
    parser.add_argument("--event-type", required=True)
    parser.add_argument("--prune", action="store_true")
    return parser.parse_args(argv)


def _session_id(payload: object) -> str:
    """Return a safe session directory name, using ``unknown`` as the fallback."""
    if not isinstance(payload, dict):
        return "unknown"

    session_id = payload.get("session_id")
    if not isinstance(session_id, str) or not session_id:
        return "unknown"
    if "/" in session_id or "\\" in session_id or session_id in {".", ".."}:
        return "unknown"
    return session_id


def main(argv: list[str] | None = None) -> int:
    """Write an event record without ever blocking the Claude hook lifecycle."""
    try:
        arguments = _arguments(argv)
        if not arguments.event_type.isidentifier():
            return 0

        from utils.harness_paths import session_log_dir
        from utils.log_retention import prune_sessions
        from utils.log_writer import append_jsonl, build_record

        payload = json.loads(sys.stdin.read())
        record = build_record(arguments.event_type, payload)
        append_jsonl(session_log_dir(_session_id(payload)) / f"{arguments.event_type}.jsonl", record)
        if arguments.prune:
            try:
                prune_sessions()
            except Exception:
                pass
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
