#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""Grader: assert facts about a prepare_review.py manifest.

Emits the eval-harness contract: {"score": 0.0-1.0, "details": "..."} on stdout.

Usage:
    check_manifest.py <manifest.json> --tier full
    check_manifest.py <manifest.json> --roles-include security --roles-exclude performance
    check_manifest.py <manifest.json> --reviewed db/migrations/0001.py --masked uv.lock
    check_manifest.py <manifest.json> --focus-include security=src/auth/login.py \
                                      --focus-exclude security=styles/app.css
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def split_focus(spec: str) -> tuple[str, str]:
    """Parse a ROLE=PATH focus assertion. Raises ValueError on a malformed spec."""
    role, sep, path = spec.partition("=")
    if not sep or not role or not path:
        raise ValueError(f"focus assertion {spec!r} must be ROLE=PATH")
    return role, path


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("manifest", type=Path)
    p.add_argument("--tier")
    p.add_argument("--roles-include", action="append", default=[])
    p.add_argument("--roles-exclude", action="append", default=[])
    p.add_argument("--reviewed", action="append", default=[], help="path that MUST be reviewed")
    p.add_argument("--masked", action="append", default=[], help="path that MUST be filtered as noise")
    p.add_argument(
        "--focus-include",
        action="append",
        default=[],
        metavar="ROLE=PATH",
        help="path that MUST be in that role's focus list",
    )
    p.add_argument(
        "--focus-exclude",
        action="append",
        default=[],
        metavar="ROLE=PATH",
        help="path that must NOT be in that role's focus list",
    )
    args = p.parse_args()

    if not args.manifest.is_file():
        print(json.dumps({"score": 0.0, "details": f"no manifest at {args.manifest}"}))
        return 0

    m: dict[str, Any] = json.loads(args.manifest.read_text())
    roles: list[str] = m.get("roles", [])
    reviewed: list[str] = m.get("files", {}).get("reviewed", [])
    masked: list[str] = m.get("files", {}).get("masked", [])
    focus: dict[str, list[str]] = m.get("focus", {})
    failures: list[str] = []

    try:
        focus_include = [split_focus(spec) for spec in args.focus_include]
        focus_exclude = [split_focus(spec) for spec in args.focus_exclude]
    except ValueError as exc:
        print(json.dumps({"score": 0.0, "details": str(exc)}))
        return 0

    if args.tier and m.get("tier") != args.tier:
        failures.append(f"tier is {m.get('tier')!r}, expected {args.tier!r}")

    for role in args.roles_include:
        if role not in roles:
            failures.append(f"role {role!r} missing from roster {roles}")
    for role in args.roles_exclude:
        if role in roles:
            failures.append(f"role {role!r} should have been pruned but is in {roles}")

    for path in args.reviewed:
        if path not in reviewed:
            failures.append(f"{path!r} should be reviewed but is not in {reviewed}")
    for path in args.masked:
        if path not in masked:
            failures.append(f"{path!r} should be filtered as noise but is not in {masked}")

    # A role that was pruned has no focus entry at all. That is a different failure from
    # "the role is on the roster but the path was scoped out", so say which one happened.
    for role, path in focus_include:
        if role not in focus:
            failures.append(f"role {role!r} has no focus entry (roster: {roles})")
        elif path not in focus[role]:
            failures.append(f"{path!r} should be in {role!r} focus but is not in {focus[role]}")
    for role, path in focus_exclude:
        if role in focus and path in focus[role]:
            failures.append(f"{path!r} should be scoped out of {role!r} focus but is in {focus[role]}")

    if failures:
        print(json.dumps({"score": 0.0, "details": "; ".join(failures)}))
    else:
        print(json.dumps({"score": 1.0, "details": f"tier={m.get('tier')} roles={roles}"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
