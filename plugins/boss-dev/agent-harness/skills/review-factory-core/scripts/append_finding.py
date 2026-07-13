#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""The only sanctioned write path for specialist findings.

A specialist that improvises its own write mechanism works by luck: the ``Write`` tool
truncates instead of appending, and shell redirection trips the Bash permission matcher —
which, in a headless subagent with no UI to render a prompt, is not a prompt but a
deadlock. This CLI gives the agent exactly one deterministic command shape, runs under the
already-allowlisted ``uv run``, and preserves the incremental-append durability the JSONL
design prizes: each call commits one record, so an agent cut off mid-review loses nothing
it had already written.

It is also the anchor gate, moved to write time. ``validate_findings.py`` rejects a
hallucinated anchor after the fact; this rejects it *before it lands*, with the reason on
stderr, so the agent can correct itself instead of poisoning the judge's input.

Usage::

    append_finding.py <workspace> --role security \
        --file src/db/queries.py --line 7 --side RIGHT --severity critical \
        --title "SQL injection" --body "..." [--confidence high] [--suggestion-patch ...]

    append_finding.py <workspace> --role security --done

Exit codes, aligned with ``validate_findings.py`` so an agent can branch on them:

    0  the record (or done-record) was appended
    1  the record was rejected — the reason is on stderr; fix it and retry
    2  the workspace itself is unusable (no manifest)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Sibling module in the same scripts/ directory: resolvable both as a script (the
# interpreter puts the script's directory on sys.path) and under pytest (conftest shim).
import validate_findings as vf  # pyright: ignore[reportImplicitRelativeImport]


def findings_path(workspace: Path, role: str) -> Path:
    return workspace / "findings" / f"{role}.jsonl"


def counts_from_disk(path: Path) -> dict[str, int]:
    """Severity counts computed from what was actually written — never trusted from argv.

    Every record in the file already passed the write-time gate, so this is a plain
    tally; malformed or foreign lines are simply not counted.
    """
    counts = dict.fromkeys(sorted(vf.SEVERITIES), 0)
    if not path.is_file():
        return counts
    for line in path.read_text().splitlines():
        try:
            record: object = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(record, dict):
            continue
        typed: dict[str, Any] = record
        severity = typed.get("severity")
        if isinstance(severity, str) and severity in vf.SEVERITIES:
            counts[severity] += 1
    return counts


def append_line(path: Path, record: dict[str, Any]) -> None:
    """Append exactly one JSON object as one line. The only write in this file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record) + "\n")


def build_record(args: argparse.Namespace) -> dict[str, Any]:
    record: dict[str, Any] = {
        "role": args.role,
        "file": args.file,
        "line": args.line,
        "side": args.side,
        "severity": args.severity,
        "title": args.title,
        "body": args.body,
    }
    if args.confidence:
        record["confidence"] = args.confidence
    if args.suggestion_patch:
        record["suggestion_patch"] = args.suggestion_patch
    return record


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Append one validated finding to a specialist's JSONL file.")
    parser.add_argument("workspace", type=Path, help="review workspace (.review/<slug>)")
    parser.add_argument("--role", required=True, help="your role — must be on the review's roster")
    parser.add_argument("--done", action="store_true", help="append the terminal done-record and finish")
    parser.add_argument("--file", help="path from the repo root, exactly as it appears in the diff")
    parser.add_argument("--line", type=int, help="an anchor line that exists in the diff")
    parser.add_argument("--side", default="RIGHT", help="RIGHT for added/new lines, LEFT for deleted (default: RIGHT)")
    parser.add_argument("--severity", help="critical | moderate | nit")
    parser.add_argument("--title", help="one line, specific")
    parser.add_argument("--body", help="what is wrong, why it matters, what to do instead")
    parser.add_argument(
        "--confidence", choices=["high", "medium", "low"], help="be honest; low asks the judge to verify"
    )
    parser.add_argument(
        "--suggestion-patch", dest="suggestion_patch", help="complete replacement text for the anchored line(s)"
    )
    args = parser.parse_args(argv)

    try:
        manifest = vf.load_manifest(args.workspace)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    roles: list[str] = manifest.get("roles", [])
    if args.role not in roles:
        print(
            f"rejected: role {args.role!r} is not on this review's roster ({', '.join(roles)})",
            file=sys.stderr,
        )
        return 1

    path = findings_path(args.workspace, args.role)

    if args.done:
        counts = counts_from_disk(path)
        append_line(path, {"type": "done", "counts": counts})
        summary = " ".join(f"{sev}={n}" for sev, n in counts.items())
        print(f"done: {args.role} {summary}")
        return 0

    if missing := [
        flag
        for flag, value in (
            ("--file", args.file),
            ("--line", args.line),
            ("--severity", args.severity),
            ("--title", args.title),
            ("--body", args.body),
        )
        if value is None
    ]:
        print(f"rejected: missing {', '.join(missing)} (or pass --done to finish)", file=sys.stderr)
        return 1

    record = build_record(args)
    anchors: vf.Anchors = manifest.get("anchors", {})
    if error := vf.validate_record(record, anchors, args.role):
        print(f"rejected: {error}", file=sys.stderr)
        return 1

    append_line(path, record)
    print(f"appended: {args.role} {args.file}:{args.line} ({args.side}, {args.severity})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
