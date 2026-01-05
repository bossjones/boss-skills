"""Pytest configuration for twitter-to-reel tests."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import MagicMock

import pytest

# Mock Playwright before any script imports try to use it
# This prevents ImportError when playwright is not installed
sys.modules["playwright"] = MagicMock()
sys.modules["playwright.async_api"] = MagicMock()
sys.modules["playwright.sync_api"] = MagicMock()

# Add scripts directory to Python path for imports
SCRIPTS_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(SCRIPTS_DIR))

if TYPE_CHECKING:
    pass


@pytest.fixture
def sample_light_image(tmp_path: Path) -> Path:
    """Create a simple light-themed test image (white background)."""
    from PIL import Image

    img = Image.new("RGB", (200, 200), color=(255, 255, 255))
    path = tmp_path / "light_screenshot.png"
    img.save(path)
    return path


@pytest.fixture
def sample_dark_image(tmp_path: Path) -> Path:
    """Create a simple dark-themed test image (black background)."""
    from PIL import Image

    img = Image.new("RGB", (200, 200), color=(0, 0, 0))
    path = tmp_path / "dark_screenshot.png"
    img.save(path)
    return path


@pytest.fixture
def sample_gray_image(tmp_path: Path) -> Path:
    """Create a gray test image for edge case testing."""
    from PIL import Image

    img = Image.new("RGB", (200, 200), color=(128, 128, 128))
    path = tmp_path / "gray_screenshot.png"
    img.save(path)
    return path


@pytest.fixture
def sample_tweet_screenshot(tmp_path: Path) -> Path:
    """Create a realistic tweet-sized screenshot (550x400)."""
    from PIL import Image

    img = Image.new("RGB", (550, 400), color=(255, 255, 255))
    path = tmp_path / "tweet_screenshot.png"
    img.save(path)
    return path


@pytest.fixture
def sample_video_file(tmp_path: Path) -> Path:
    """Create a placeholder for a video file (just a marker, actual video ops are mocked)."""
    path = tmp_path / "sample_video.mp4"
    path.touch()
    return path


@pytest.fixture
def sample_cookies_file(tmp_path: Path) -> Path:
    """Create a sample Netscape cookies.txt file."""
    cookies_content = """# Netscape HTTP Cookie File
# https://curl.haxx.se/rfc/cookie_spec.html
# This is a generated file!  Do not edit.

.x.com\tTRUE\t/\tTRUE\t1735689600\tauth_token\tabc123
.x.com\tTRUE\t/\tFALSE\t1735689600\tct0\txyz789
"""
    path = tmp_path / "cookies.txt"
    path.write_text(cookies_content)
    return path


@pytest.fixture
def empty_cookies_file(tmp_path: Path) -> Path:
    """Create an empty cookies file."""
    path = tmp_path / "empty_cookies.txt"
    path.write_text("")
    return path


@pytest.fixture
def cookies_with_comments(tmp_path: Path) -> Path:
    """Create a cookies file with only comments."""
    cookies_content = """# Netscape HTTP Cookie File
# This file has only comments
# No actual cookies here
"""
    path = tmp_path / "comments_cookies.txt"
    path.write_text(cookies_content)
    return path
