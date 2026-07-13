#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""Grader: assert shared-context.md carries no live conversational boundary tags.

A PR body is attacker-controlled. If a boundary tag survives into the file that five
agents read, a PR description can impersonate a system turn. This grader is the
regression test for that.

Passing requires BOTH:
  - no boundary tag survives, AND
  - the surrounding prose survives (proving we stripped tags, not deleted the content)

Emits: {"score": 0.0-1.0, "details": "..."}
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

TAGS = (
    "system",
    "system-reminder",
    "instructions",
    "important",
    "assistant",
    "human",
    "user",
    "tool_use",
    "tool_result",
    "function_calls",
    "thinking",
)
TAG_RE = re.compile(rf"</?\s*(?:{'|'.join(TAGS)})(?:\s[^>]*)?/?>", re.IGNORECASE)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("context", type=Path, help="shared-context.md")
    p.add_argument("--must-contain", action="append", default=[], help="prose that must survive stripping")
    args = p.parse_args()

    if not args.context.is_file():
        print(json.dumps({"score": 0.0, "details": f"no shared-context at {args.context}"}))
        return 0

    text = args.context.read_text()
    failures: list[str] = []

    if survivors := TAG_RE.findall(text):
        failures.append(f"boundary tags survived stripping: {sorted(set(survivors))}")

    for needle in args.must_contain:
        if needle not in text:
            failures.append(f"prose {needle!r} was destroyed, not just de-tagged")

    if failures:
        print(json.dumps({"score": 0.0, "details": "; ".join(failures)}))
    else:
        print(json.dumps({"score": 1.0, "details": "no boundary tags survived; prose intact"}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
