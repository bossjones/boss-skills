#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""Grader: assert what the specialists actually found (suite 2 — seeded defects).

Emits the eval-harness contract: {"score": 0.0-1.0, "details": "..."} on stdout, exit 0.

Two modes:

    check_findings.py <workspace> --anchor src/db/queries.py:7 --within 2 --severity critical
    check_findings.py <workspace> --expect-none

`--expect-none` is the whole point of the `clean-no-defects` task: every other task rewards
finding things, so a factory that flags everything would ace them all. Only the clean diff
distinguishes a real reviewer from a plausible-sounding noisy one.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_findings(workspace: Path) -> tuple[list[dict[str, Any]], list[str]]:
    """Every finding across every role's JSONL file, plus any malformed-line notes.

    JSONL tolerance is deliberate: one bad line must not discard the good findings around
    it, and a specialist killed mid-write still leaves everything it had already committed.
    """
    findings: list[dict[str, Any]] = []
    notes: list[str] = []
    findings_dir = workspace / "findings"
    if not findings_dir.is_dir():
        return findings, [f"no findings/ directory in {workspace}"]

    for path in sorted(findings_dir.glob("*.jsonl")):
        for n, line in enumerate(path.read_text().splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rec: Any = json.loads(line)
            except json.JSONDecodeError:
                notes.append(f"{path.name}:{n} malformed")
                continue
            if not isinstance(rec, dict):
                notes.append(f"{path.name}:{n} not an object")
                continue
            typed: dict[str, Any] = rec
            if typed.get("type") == "done":  # terminal record, not a finding
                continue
            typed.setdefault("role", path.stem)
            findings.append(typed)
    return findings, notes


def describe(f: dict[str, Any]) -> str:
    return f"{f.get('role')}:{f.get('file')}:{f.get('line')}[{f.get('severity')}]"


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("workspace", type=Path, help="review workspace (.review/<slug>)")
    p.add_argument("--anchor", metavar="FILE:LINE", help="the planted defect")
    p.add_argument("--within", type=int, default=2, help="how many lines off the anchor may be")
    p.add_argument("--severity", help="severity the finding must carry")
    p.add_argument("--role", help="role that must have found it")
    p.add_argument("--expect-none", action="store_true", help="assert ZERO findings (clean diff)")
    args = p.parse_args()

    findings, notes = load_findings(args.workspace)

    if args.expect_none:
        if findings:
            listed = ", ".join(describe(f) for f in findings[:6])
            print(
                json.dumps({
                    "score": 0.0,
                    "details": f"clean diff, but {len(findings)} finding(s) were reported: {listed}",
                })
            )
        else:
            print(json.dumps({"score": 1.0, "details": "clean diff, zero findings — correct"}))
        return 0

    if not args.anchor:
        print(json.dumps({"score": 0.0, "details": "--anchor or --expect-none is required"}))
        return 0

    want_file, _, want_line_raw = args.anchor.rpartition(":")
    try:
        want_line = int(want_line_raw)
    except ValueError:
        print(json.dumps({"score": 0.0, "details": f"malformed --anchor {args.anchor!r}, want FILE:LINE"}))
        return 0

    on_file = [f for f in findings if f.get("file") == want_file]
    near = [f for f in on_file if isinstance(f.get("line"), int) and abs(f["line"] - want_line) <= args.within]
    hits = [f for f in near if not args.severity or f.get("severity") == args.severity]
    if args.role:
        hits = [f for f in hits if f.get("role") == args.role]

    if hits:
        detail = f"found {describe(hits[0])} (planted {want_file}:{want_line})"
        if notes:
            detail += f"; {len(notes)} malformed line(s)"
        print(json.dumps({"score": 1.0, "details": detail}))
        return 0

    if near:
        got = ", ".join(f"{f.get('severity')} by {f.get('role')}" for f in near)
        why = f"anchored correctly but wanted severity={args.severity!r} role={args.role!r}; got: {got}"
    elif on_file:
        got = ", ".join(str(f.get("line")) for f in on_file)
        why = f"findings on {want_file} at line(s) {got}, none within {args.within} of {want_line}"
    else:
        why = f"no finding on {want_file} at all ({len(findings)} finding(s) elsewhere)"
    print(json.dumps({"score": 0.0, "details": why}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
