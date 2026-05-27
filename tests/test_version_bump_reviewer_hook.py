"""Tests for the boss-skills PostToolUse hooks' path matchers.

Both `.claude/hooks/version-bump-reviewer.py` and
`.claude/hooks/skill-edit-review.py` are PEP 723 scripts (not installed modules)
loaded by path. They share the same set of SKILL.md trigger paths, but
version-bump-reviewer additionally fires on plugin-component files
(commands, agents, hooks, .lsp.json, .mcp.json, monitors, settings, bin,
plugin.json) and on the top-level marketplace.json — those component-only
paths must NOT trigger skill-edit-review.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest

HOOKS_DIR = Path(__file__).resolve().parent.parent / ".claude" / "hooks"
HOOK_FILES = {
    "version-bump-reviewer": HOOKS_DIR / "version-bump-reviewer.py",
    "skill-edit-review": HOOKS_DIR / "skill-edit-review.py",
}


def _load_hook(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(path.stem.replace("-", "_"), path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


HOOKS = {name: _load_hook(path) for name, path in HOOK_FILES.items()}

# Paths both hooks must accept — SKILL.md files in the two supported shapes.
SKILL_MD_MATCHING_PATHS = [
    "plugins/social-media/twitter-tools/skills/twitter-to-reel/SKILL.md",
    "plugins/boss-homelab/proxmox-infra/skills/proxmox-infrastructure/SKILL.md",
    ".claude/skills/doc-generator/SKILL.md",
    ".claude/skills/version-bump-reviewer/SKILL.md",
]

# Paths only the version-bump-reviewer hook accepts — feature-bearing plugin
# component files plus the top-level marketplace.json. skill-edit-review must
# reject all of these because it only cares about SKILL.md edits.
COMPONENT_ONLY_MATCHING_PATHS = [
    "plugins/boss-dev/basedpyright-lsp/.lsp.json",
    "plugins/boss-dev/agent-harness/commands/new-cmd.md",
    "plugins/boss-dev/agent-harness/agents/new-agent.md",
    "plugins/boss-dev/agent-harness/hooks/hooks.json",
    "plugins/boss-dev/agent-harness/.mcp.json",
    "plugins/boss-dev/agent-harness/monitors/monitors.json",
    "plugins/boss-dev/agent-harness/settings.json",
    "plugins/boss-dev/agent-harness/bin/foo",
    "plugins/boss-dev/agent-harness/bin/nested/deep/exec",
    "plugins/social-media/twitter-tools/.claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
]

# Paths both hooks must reject.
NON_MATCHING_PATHS = [
    # Old Adobe layout the port wrongly targeted — must NOT match.
    "skills/1p/foo/SKILL.md",
    "skills/3p/adobe-fill-template/SKILL.md",
    "skills/shared/helper/SKILL.md",
    # Not a SKILL.md and not a feature-bearing component.
    "plugins/social-media/twitter-tools/skills/twitter-to-reel/README.md",
    "plugins/boss-dev/basedpyright-lsp/README.md",
    ".claude/skills/doc-generator/scripts/gen.py",
    # Too shallow / wrong shape.
    ".claude/skills/SKILL.md",
    "plugins/twitter-tools/SKILL.md",
    "SKILL.md",
    # Top-level files unrelated to versioning.
    "README.md",
    "Makefile",
    "pyproject.toml",
]


@pytest.mark.parametrize("path", SKILL_MD_MATCHING_PATHS)
def test_skill_edit_review_matches_skill_md(path: str) -> None:
    assert HOOKS["skill-edit-review"].is_versioned_skill_md(Path(path).parts) is True


@pytest.mark.parametrize("path", COMPONENT_ONLY_MATCHING_PATHS + NON_MATCHING_PATHS)
def test_skill_edit_review_rejects_non_skill_md(path: str) -> None:
    assert HOOKS["skill-edit-review"].is_versioned_skill_md(Path(path).parts) is False


@pytest.mark.parametrize("path", SKILL_MD_MATCHING_PATHS + COMPONENT_ONLY_MATCHING_PATHS)
def test_version_bump_reviewer_matches_artifact(path: str) -> None:
    label = HOOKS["version-bump-reviewer"].classify_versioned_artifact(Path(path).parts)
    assert label is not None, f"expected match but got None for {path}"
    assert isinstance(label, str) and label, f"expected non-empty label for {path}"


@pytest.mark.parametrize("path", NON_MATCHING_PATHS)
def test_version_bump_reviewer_rejects_non_artifact(path: str) -> None:
    assert HOOKS["version-bump-reviewer"].classify_versioned_artifact(Path(path).parts) is None


def test_version_bump_reviewer_is_superset_of_skill_edit_review() -> None:
    """Every path skill-edit-review accepts must also be accepted by
    version-bump-reviewer. The reverse is not required: vbr intentionally
    fires on component-only paths that skill-edit-review ignores.
    """
    vbr = HOOKS["version-bump-reviewer"]
    ser = HOOKS["skill-edit-review"]
    for path in SKILL_MD_MATCHING_PATHS + COMPONENT_ONLY_MATCHING_PATHS + NON_MATCHING_PATHS:
        parts = Path(path).parts
        if ser.is_versioned_skill_md(parts):
            assert vbr.classify_versioned_artifact(parts) is not None, (
                f"version-bump-reviewer must match every path skill-edit-review matches, "
                f"but missed: {path}"
            )


def test_component_labels_are_distinct() -> None:
    """Each component class returns a recognizable label so the hook's
    feedback can mention what triggered it.
    """
    vbr = HOOKS["version-bump-reviewer"]
    labels = {
        path: vbr.classify_versioned_artifact(Path(path).parts)
        for path in COMPONENT_ONLY_MATCHING_PATHS + SKILL_MD_MATCHING_PATHS
    }
    # Sanity: every matching path produced a label.
    assert all(labels.values()), labels
    # Sanity: more than one distinct label is used across the corpus.
    assert len(set(labels.values())) > 1
