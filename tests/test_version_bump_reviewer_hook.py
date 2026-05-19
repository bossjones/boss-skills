"""Tests for the boss-skills PostToolUse SKILL.md hooks' path matcher.

Both `.claude/hooks/version-bump-reviewer.py` and
`.claude/hooks/skill-edit-review.py` are PEP 723 scripts (not installed
modules) that share an identical `is_versioned_skill_md` matcher. They are
loaded by path and exercised against the same accept/reject path sets so the
two PostToolUse nudges stay in lockstep.
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

MATCHING_PATHS = [
    "plugins/social-media/twitter-tools/skills/twitter-to-reel/SKILL.md",
    "plugins/boss-homelab/proxmox/skills/proxmox-admin/SKILL.md",
    ".claude/skills/doc-generator/SKILL.md",
    ".claude/skills/version-bump-reviewer/SKILL.md",
]

NON_MATCHING_PATHS = [
    # Old Adobe layout the port wrongly targeted — must NOT match.
    "skills/1p/foo/SKILL.md",
    "skills/3p/adobe-fill-template/SKILL.md",
    "skills/shared/helper/SKILL.md",
    # Not a SKILL.md.
    "plugins/social-media/twitter-tools/skills/twitter-to-reel/README.md",
    ".claude/skills/doc-generator/scripts/gen.py",
    # Too shallow / wrong shape.
    ".claude/skills/SKILL.md",
    "plugins/twitter-tools/SKILL.md",
    "SKILL.md",
    # A plugin file that is not under a skills/ segment.
    "plugins/social-media/twitter-tools/.claude-plugin/plugin.json",
]


@pytest.mark.parametrize("hook_name", list(HOOKS))
@pytest.mark.parametrize("path", MATCHING_PATHS)
def test_matches_versioned_skill_md(hook_name: str, path: str) -> None:
    assert HOOKS[hook_name].is_versioned_skill_md(Path(path).parts) is True


@pytest.mark.parametrize("hook_name", list(HOOKS))
@pytest.mark.parametrize("path", NON_MATCHING_PATHS)
def test_rejects_non_versioned_paths(hook_name: str, path: str) -> None:
    assert HOOKS[hook_name].is_versioned_skill_md(Path(path).parts) is False


def test_both_hooks_agree_on_every_path() -> None:
    """The two matchers must be byte-for-byte equivalent in behavior."""
    vbr = HOOKS["version-bump-reviewer"]
    ser = HOOKS["skill-edit-review"]
    for path in MATCHING_PATHS + NON_MATCHING_PATHS:
        parts = Path(path).parts
        assert vbr.is_versioned_skill_md(parts) == ser.is_versioned_skill_md(parts), path
