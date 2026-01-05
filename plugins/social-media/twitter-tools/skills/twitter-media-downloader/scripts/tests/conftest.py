"""Pytest configuration for twitter-media-downloader tests."""

from __future__ import annotations

import sys
from pathlib import Path

# Add scripts directory to Python path for imports
SCRIPTS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))
