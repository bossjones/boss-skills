#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""PostToolUse hook. Nudges Claude to invoke the `skill-review` skill whenever
Edit/Write/MultiEdit touches a SKILL.md this repo cares about.

Ported from skill-edit-review.mjs: the Node version could not run as a hook
because `node` on this machine is supplied only by fnm via an ephemeral,
PID-specific multishell PATH entry that is absent from non-interactive hook
subprocesses (spawn failed with "No such file or directory"). `uv` resolves
reliably, so this is a Python PEP 723 script like every other hook here.

Scope matches `.claude/hooks/version-bump-reviewer.py` exactly (the old .mjs
matched a top-level `skills/` tree that does not exist in boss-skills, so it
never fired): a plugin skill under
plugins/<category>/<plugin>/skills/<name>/SKILL.md or a repo-internal skill
under .claude/skills/<name>/SKILL.md.

This runs alongside version-bump-reviewer.py; both fire independently. The edit
always commits (PostToolUse runs after the tool succeeds). The
`decision: "block"` reason is feedback Claude is expected to address before
continuing — it does not undo the edit. Address skill-review findings first,
then run version-bump-reviewer.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def is_versioned_skill_md(rel_parts: tuple[str, ...]) -> bool:
    """True when the path is a SKILL.md this repo reviews/versions.

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
        "`skill-review` skill to check this file against the Anthropic Software "
        "Directory Policy and Skill Authoring Best Practices. Report any "
        "critical or high findings to the user before making further edits. "
        "Resolve skill-review findings before running version-bump-reviewer."
    )
    sys.stdout.write(json.dumps({"decision": "block", "reason": reason}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
