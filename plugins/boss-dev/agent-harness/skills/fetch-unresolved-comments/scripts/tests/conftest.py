"""Pytest configuration for fetch-unresolved-comments script tests."""

from __future__ import annotations

import sys
from pathlib import Path

# Make the sibling fetch_unresolved_comments.py importable without packaging.
SCRIPTS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))
