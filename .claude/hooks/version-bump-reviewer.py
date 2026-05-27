#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""PostToolUse hook. Nudges Claude to invoke the `version-bump-reviewer` skill
whenever Edit/Write/MultiEdit touches a file that drives a version bump in this repo.

Three change classes are in scope:

  * Plugin skill / component — plugins/<category>/<plugin>/{skills/<name>/SKILL.md,
                                commands/*.md, agents/*.md, hooks/hooks.json,
                                .lsp.json, .mcp.json, monitors/monitors.json,
                                settings.json, bin/*, .claude-plugin/plugin.json}
                                (bumps the owning plugin's plugin.json + marketplace.json)
  * Repo-internal skill      — .claude/skills/<name>/SKILL.md
                                (bumps a per-skill metadata.version in its own frontmatter)
  * New plugin publish       — .claude-plugin/marketplace.json
                                (detects a new plugins[] entry; initial-publish commit)

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


def classify_versioned_artifact(rel_parts: tuple[str, ...]) -> str | None:
    """Return a short label describing why a path drives a version bump, or None.

    Labels are human-readable strings the hook embeds in its feedback so Claude
    knows which artifact class triggered the nudge.

    Plugin-rooted shapes (all under `plugins/<category>/<plugin>/`):
      - skills/<name>/SKILL.md            → "plugin skill SKILL.md"
      - commands/*.md                     → "plugin command"
      - agents/*.md                       → "plugin agent"
      - hooks/hooks.json                  → "plugin hooks.json"
      - .lsp.json                         → "plugin .lsp.json"
      - .mcp.json                         → "plugin .mcp.json"
      - monitors/monitors.json            → "plugin monitors.json"
      - settings.json                     → "plugin settings.json"
      - bin/<anything>                    → "plugin bin/ executable"
      - .claude-plugin/plugin.json        → "plugin manifest"

    Other shapes:
      - .claude/skills/<name>/SKILL.md    → "repo-internal skill SKILL.md"
      - .claude-plugin/marketplace.json   → "marketplace.json"
    """
    if not rel_parts:
        return None

    # Repo-internal skill: .claude/skills/<name>/SKILL.md
    if (
        len(rel_parts) == 4
        and rel_parts[0] == ".claude"
        and rel_parts[1] == "skills"
        and rel_parts[-1] == "SKILL.md"
    ):
        return "repo-internal skill SKILL.md"

    # Top-level marketplace registry
    if (
        len(rel_parts) == 2
        and rel_parts[0] == ".claude-plugin"
        and rel_parts[1] == "marketplace.json"
    ):
        return "marketplace.json"

    # Plugin-rooted shapes: plugins/<category>/<plugin>/<...>
    if len(rel_parts) >= 4 and rel_parts[0] == "plugins":
        # plugins/<category>/<plugin>/skills/<name>/SKILL.md
        if (
            len(rel_parts) >= 6
            and rel_parts[3] == "skills"
            and rel_parts[-1] == "SKILL.md"
        ):
            return "plugin skill SKILL.md"

        # plugins/<category>/<plugin>/commands/<file>.md
        if (
            len(rel_parts) == 5
            and rel_parts[3] == "commands"
            and rel_parts[-1].endswith(".md")
        ):
            return "plugin command"

        # plugins/<category>/<plugin>/agents/<file>.md
        if (
            len(rel_parts) == 5
            and rel_parts[3] == "agents"
            and rel_parts[-1].endswith(".md")
        ):
            return "plugin agent"

        # plugins/<category>/<plugin>/hooks/hooks.json
        if (
            len(rel_parts) == 5
            and rel_parts[3] == "hooks"
            and rel_parts[-1] == "hooks.json"
        ):
            return "plugin hooks.json"

        # plugins/<category>/<plugin>/monitors/monitors.json
        if (
            len(rel_parts) == 5
            and rel_parts[3] == "monitors"
            and rel_parts[-1] == "monitors.json"
        ):
            return "plugin monitors.json"

        # plugins/<category>/<plugin>/bin/<anything> (any depth under bin/)
        if len(rel_parts) >= 5 and rel_parts[3] == "bin":
            return "plugin bin/ executable"

        # plugins/<category>/<plugin>/.claude-plugin/plugin.json
        if (
            len(rel_parts) == 5
            and rel_parts[3] == ".claude-plugin"
            and rel_parts[-1] == "plugin.json"
        ):
            return "plugin manifest"

        # plugins/<category>/<plugin>/.lsp.json
        if len(rel_parts) == 4 and rel_parts[-1] == ".lsp.json":
            return "plugin .lsp.json"

        # plugins/<category>/<plugin>/.mcp.json
        if len(rel_parts) == 4 and rel_parts[-1] == ".mcp.json":
            return "plugin .mcp.json"

        # plugins/<category>/<plugin>/settings.json
        if len(rel_parts) == 4 and rel_parts[-1] == "settings.json":
            return "plugin settings.json"

    return None


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

    label = classify_versioned_artifact(rel.parts)
    if label is None:
        return 0

    reason = (
        f"You just edited {rel.as_posix()} ({label}). Before continuing, invoke the "
        "`version-bump-reviewer` skill to verify whether this change needs a version "
        "bump and at what semver tier. Plugin skill or plugin component change "
        "(commands, agents, hooks, .lsp.json, .mcp.json, monitors, settings, bin, "
        "plugin.json) bumps the owning plugin's version in "
        "plugins/<category>/<plugin>/.claude-plugin/plugin.json AND the matching entry "
        "in .claude-plugin/marketplace.json. A new plugins[] entry in marketplace.json "
        "is an initial publish — validate parity, no bump. A repo-internal skill "
        "(.claude/skills/<name>/SKILL.md) bumps metadata.version in the SKILL.md "
        "frontmatter. Then commit with a conventional message. If skill-review "
        "reported critical or high findings, address those first."
    )
    sys.stdout.write(json.dumps({"decision": "block", "reason": reason}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
