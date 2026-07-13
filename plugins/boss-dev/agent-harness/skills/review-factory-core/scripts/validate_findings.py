#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""Gate between the specialists and the judge.

Specialists are language models writing JSONL. They will occasionally emit a
malformed line, an invented severity, or — the expensive one — a **line number that
does not exist in the diff**. A hallucinated anchor is uniquely bad: it looks
authoritative, it survives a human skim, and if posted it lands a review comment on
an unrelated line of someone's code.

So findings are validated against ``manifest.json``'s anchor table (built by
``prepare_review.py`` from the annotated diff itself) *before* the judge ever reads
them. The judge then only ever sees findings that cite real lines.

Usage::

    validate_findings.py <workspace>            # validate every specialist
    validate_findings.py <workspace> --role security --strict

Exit codes, chosen so an orchestrator can branch on them:

    0  every expected findings file is present, terminated, and fully valid
    1  a findings file is missing, unterminated, or contained rejected records
    2  the workspace itself is unusable (no manifest)

Rejected records are reported and dropped; valid ones are still counted. A specialist
that produced nine good findings and one bad line has not failed — but the bad line
does not get to reach the judge.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SEVERITIES = frozenset({"critical", "moderate", "nit"})
SIDES = frozenset({"LEFT", "RIGHT"})
REQUIRED_FIELDS = ("file", "line", "severity", "title", "body")

Manifest = dict[str, Any]
Anchors = dict[str, dict[str, list[int]]]


@dataclass
class RoleResult:
    """What one specialist actually produced."""

    role: str
    present: bool = False
    done: bool = False
    valid: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.present and self.done and not self.errors

    def counts(self) -> dict[str, int]:
        return {sev: sum(1 for f in self.valid if f["severity"] == sev) for sev in sorted(SEVERITIES)}


# --------------------------------------------------------------------------- #
# Pure core (unit tested — no IO)
# --------------------------------------------------------------------------- #
def anchor_exists(anchors: Anchors, file: str, line: int, side: str) -> bool:
    """True only if (file, side, line) is a line that genuinely exists in the diff."""
    sides = anchors.get(file)
    if not sides:
        return False
    return line in sides.get(side, [])


def validate_record(record: dict[str, Any], anchors: Anchors, role: str) -> str | None:
    """Return an error string if the record is unusable, else None.

    Rejecting is the point. A finding that cannot be anchored cannot be posted, so
    letting it through only defers the failure to somewhere less visible.
    """
    for key in REQUIRED_FIELDS:
        if key not in record:
            return f"missing required field '{key}'"

    severity = record["severity"]
    if severity not in SEVERITIES:
        return f"invalid severity {severity!r} (expected one of: {', '.join(sorted(SEVERITIES))})"

    side = record.get("side", "RIGHT")
    if side not in SIDES:
        return f"invalid side {side!r} (expected LEFT or RIGHT)"

    line = record["line"]
    if not isinstance(line, int) or isinstance(line, bool) or line < 1:
        return f"line must be a positive integer, got {line!r}"

    file = record["file"]
    if not anchor_exists(anchors, file, line, side):
        return f"anchor {file}:{line} ({side}) is not in the diff — hallucinated or stale line number"

    if record.get("role") and record["role"] != role:
        return f"role {record['role']!r} does not match its findings file ({role!r})"

    return None


def parse_findings(text: str, anchors: Anchors, role: str) -> RoleResult:
    """Parse one specialist's JSONL, keeping the good and reporting the bad.

    Tolerant by design: a single malformed line must not discard the findings around
    it. That tolerance is why the format is JSONL and not one JSON blob — a specialist
    killed mid-write still leaves everything it had already committed.
    """
    result = RoleResult(role=role, present=True)

    for n, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue

        try:
            parsed: object = json.loads(line)
        except json.JSONDecodeError as exc:
            result.errors.append(f"line {n}: not valid JSON ({exc.msg})")
            continue

        if not isinstance(parsed, dict):
            result.errors.append(f"line {n}: expected a JSON object")
            continue
        record: dict[str, Any] = parsed

        if record.get("type") == "done":
            result.done = True
            continue

        if error := validate_record(record, anchors, role):
            result.errors.append(f"line {n}: {error}")
            continue

        result.valid.append(record)

    if not result.done:
        result.errors.append("no terminal done-record — the specialist did not finish")

    return result


def summarize(results: list[RoleResult]) -> str:
    """A funnel a human can read at a glance."""
    lines = ["role                  status    critical  moderate  nit   rejected"]
    lines.append("-" * 68)
    for r in results:
        if not r.present:
            status = "MISSING"
        elif not r.done:
            status = "UNFINISHED"
        elif r.errors:
            status = "PARTIAL"
        else:
            status = "ok"
        c = r.counts()
        lines.append(
            f"{r.role:<21} {status:<9} {c['critical']:>8}  {c['moderate']:>8}  {c['nit']:>3}   {len(r.errors):>8}"
        )
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# IO layer
# --------------------------------------------------------------------------- #
def load_manifest(workspace: Path) -> Manifest:
    path = workspace / "manifest.json"
    try:
        raw: object = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"{path} must be a JSON object")
    return raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate specialist findings against the diff's real anchors.")
    parser.add_argument("workspace", type=Path, help="review workspace (.review/<slug>)")
    parser.add_argument("--role", action="append", help="validate only this role (repeatable)")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="exit non-zero if ANY record was rejected (default: only on missing/unfinished)",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable results")
    args = parser.parse_args(argv)

    try:
        manifest = load_manifest(args.workspace)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    anchors: Anchors = manifest.get("anchors", {})
    roles: list[str] = args.role or list(manifest.get("roles", []))

    results: list[RoleResult] = []
    for role in roles:
        path = args.workspace / "findings" / f"{role}.jsonl"
        if not path.is_file():
            results.append(RoleResult(role=role, errors=[f"{path} does not exist"]))
            continue
        results.append(parse_findings(path.read_text(), anchors, role))

    if args.json:
        print(
            json.dumps(
                {
                    "roles": {
                        r.role: {
                            "ok": r.ok,
                            "present": r.present,
                            "done": r.done,
                            "counts": r.counts(),
                            "valid": len(r.valid),
                            "errors": r.errors,
                        }
                        for r in results
                    }
                },
                indent=2,
            )
        )
    else:
        print(summarize(results))
        for r in results:
            for err in r.errors:
                print(f"  {r.role}: {err}", file=sys.stderr)

    incomplete = [r for r in results if not r.present or not r.done]
    rejected = [r for r in results if r.errors and r.present and r.done]

    if incomplete:
        return 1
    if args.strict and rejected:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
