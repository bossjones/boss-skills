"""Pytest configuration for git-worktree script tests."""

from __future__ import annotations

import sys
from pathlib import Path

# Make the sibling git_worktree.py importable without packaging the skill.
SCRIPTS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))
