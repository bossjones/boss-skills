#!/usr/bin/env -S uv run --script --quiet
# /// script
# requires-python = ">=3.13"
# dependencies = ["jsonschema"]
# ///
"""Validate a pr-review JSON payload against ``review-payload.schema.json``.

Standalone PEP 723 script — run it with::

    uv run validate_review.py /tmp/review-payload.json

By default the schema is the ``review-payload.schema.json`` that sits next to
this skill's ``scripts/`` directory; override it with ``--schema``.

Adapted from the mlflow ``pr-review`` skill (Apache-2.0).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

# The schema is a sibling of this script's parent (the skill root):
#   pr-review/review-payload.schema.json   <- DEFAULT_SCHEMA
#   pr-review/scripts/validate_review.py   <- this file
DEFAULT_SCHEMA = Path(__file__).resolve().parent.parent / "review-payload.schema.json"


def format_path(path: list[str | int]) -> str:
    """Render a JSON error path like ``['comments', 0, 'body']`` as ``comments[0].body``."""
    if not path:
        return "<root>"
    out = ""
    for part in path:
        if isinstance(part, int):
            out += f"[{part}]"
        else:
            out += f".{part}" if out else str(part)
    return out


def validate_payload(payload: Any, schema: dict[str, Any]) -> list[str]:
    """Return a sorted list of human-readable validation errors (empty == valid)."""
    validator = Draft202012Validator(schema)
    errors = sorted(
        validator.iter_errors(payload),  # pyright: ignore[reportUnknownMemberType]
        key=lambda e: list(e.absolute_path),
    )
    return [f"{format_path(list(e.absolute_path))}: {e.message}" for e in errors]


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Validate a pr-review payload against the JSON schema.",
    )
    parser.add_argument("payload", type=Path, help="Path to the review payload JSON file")
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA,
        help=f"Path to the JSON schema (default: {DEFAULT_SCHEMA})",
    )
    args = parser.parse_args()

    schema = json.loads(args.schema.read_text())
    payload = json.loads(args.payload.read_text())

    if errors := validate_payload(payload, schema):
        print(f"ERROR: {args.payload} failed schema validation", file=sys.stderr)
        for err in errors:
            print(f"  {err}", file=sys.stderr)
        sys.exit(1)

    n = len(payload.get("comments", []))
    print(f"OK: event={payload['event']}, comments={n}")


if __name__ == "__main__":
    main()
