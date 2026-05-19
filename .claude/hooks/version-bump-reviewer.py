#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""PostToolUse hook. Nudges Claude to invoke the `version-bump-reviewer` skill
whenever Edit/Write/MultiEdit touches a SKILL.md that drives a version bump in
this repo.

Two skill classes are in scope:

  * Plugin skill   — plugins/<category>/<plugin>/skills/<name>/SKILL.md
                     (bumps the owning plugin's plugin.json + marketplace.json)
  * Repo-internal  — .claude/skills/<name>/SKILL.md
                     (bumps a per-skill metadata.version in its own frontmatter)

This runs alongside skill-edit-review.py; both fire independently. The edit
always commits (PostToolUse runs after the tool succeeds). The
`decision: "block"` reason is feedback Claude is expected to address before
continuing — it does not undo the edit.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def is_versioned_skill_md(rel_parts: tuple[str, ...]) -> bool:
    """True when the path is a SKILL.md this repo versions.

    Plugin skill:  plugins/<category>/<plugin>/skills/<name>/SKILL.md
                   (>= 6 parts, first part "plugins", a "skills" segment).
    Repo-internal: .claude/skills/<name>/SKILL.md (exactly 4 parts).
    """
    if not rel_parts or rel_parts[-1] != "SKILL.md":
        return False

    # Repo-internal skill: .claude/skills/<name>/SKILL.md
    if len(rel_parts) == 4 and rel_parts[0] == ".claude" and rel_parts[1] == "skills":
        return True

    # Plugin skill: plugins/<category>/<plugin>/skills/<name>/SKILL.md
    if (
        len(rel_parts) >= 6
        and rel_parts[0] == "plugins"
        and "skills" in rel_parts[1:-1]
    ):
        return True

    return False


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0

    if payload.get("tool_name") not in {"Edit", "Write", "MultiEdit"}:
        return 0

    file_path = (payload.get("tool_input") or {}).get("file_path")
    if not isinstance(file_path, str) or not file_path:
        return 0

    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    try:
        resolved_project = Path(project_dir).resolve()
        rel = Path(resolved_project, file_path).resolve().relative_to(resolved_project)
    except (ValueError, OSError):
        return 0

    if not is_versioned_skill_md(rel.parts):
        return 0

    reason = (
        f"You just edited {rel.as_posix()}. Before continuing, invoke the "
        "`version-bump-reviewer` skill to verify whether this change needs a "
        "version bump and at what semver tier. For a plugin skill "
        "(plugins/<category>/<plugin>/skills/<name>/SKILL.md) it bumps the "
        "owning plugin's version in plugins/<category>/<plugin>/.claude-plugin/"
        "plugin.json and the matching entry in .claude-plugin/marketplace.json; "
        "for a repo-internal skill (.claude/skills/<name>/SKILL.md) it bumps "
        "metadata.version in the SKILL.md frontmatter. Then commit with a "
        "conventional message. If skill-review reported critical or high "
        "findings, address those first."
    )
    sys.stdout.write(json.dumps({"decision": "block", "reason": reason}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
