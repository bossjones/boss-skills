#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "pillow>=10.0.0",
#     "numpy>=1.24.0",
# ]
# ///
"""
Shared utilities for twitter-to-reel skill.
"""

import re
import subprocess

# Instagram Reels dimensions (9:16 aspect ratio)
REEL_WIDTH = 1080
REEL_HEIGHT = 1920

# Theme colors
THEME_COLORS = {
    "light": {
        "background": (255, 255, 255),
        "text": (15, 20, 25),
        "secondary": (83, 100, 113),
    },
    "dark": {
        "background": (0, 0, 0),
        "text": (231, 233, 234),
        "secondary": (113, 118, 123),
    },
}


def normalize_tweet_url(url: str) -> str:
    """Normalize Twitter/X URL to consistent format."""
    url = url.strip()
    # Convert twitter.com to x.com
    url = re.sub(r"https?://(www\.)?(twitter\.com|x\.com)", "https://x.com", url)
    # Remove query parameters and trailing slash
    url = re.sub(r"\?.*$", "", url)
    url = url.rstrip("/")
    return url


def extract_tweet_id(url: str) -> str | None:
    """Extract tweet ID from URL."""
    match = re.search(r"/status/(\d+)", url)
    return match.group(1) if match else None


def get_video_dimensions(video_path: str) -> tuple[int, int]:
    """Get video dimensions using ffprobe."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height",
        "-of",
        "csv=p=0:s=x",
        video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")

    width, height = result.stdout.strip().split("x")
    return int(width), int(height)


def get_video_duration(video_path: str) -> float:
    """Get video duration in seconds using ffprobe."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed: {result.stderr}")

    return float(result.stdout.strip())


def detect_dominant_color(image_path: str, sample_region: str = "corners") -> tuple[int, int, int]:
    """
    Detect dominant color from image corners/edges to determine theme.
    Returns RGB tuple.
    """
    import numpy as np
    from PIL import Image

    img = Image.open(image_path).convert("RGB")
    width, height = img.size

    # Sample from corners and edges
    sample_size = 50
    samples = []

    # Top-left corner
    samples.append(img.crop((0, 0, sample_size, sample_size)))
    # Top-right corner
    samples.append(img.crop((width - sample_size, 0, width, sample_size)))
    # Bottom-left corner
    samples.append(img.crop((0, height - sample_size, sample_size, height)))
    # Bottom-right corner
    samples.append(img.crop((width - sample_size, height - sample_size, width, height)))

    # Combine all samples and find most common color
    all_pixels = []
    for sample in samples:
        pixels = np.array(sample).reshape(-1, 3)
        all_pixels.extend(pixels.tolist())

    all_pixels = np.array(all_pixels)

    # Get average color
    avg_color = np.mean(all_pixels, axis=0).astype(int)

    return tuple(avg_color)


def detect_theme(image_path: str) -> str:
    """Detect if image uses light or dark theme."""
    color = detect_dominant_color(image_path)
    # Calculate luminance
    luminance = 0.299 * color[0] + 0.587 * color[1] + 0.114 * color[2]
    return "dark" if luminance < 128 else "light"


def check_ffmpeg() -> bool:
    """Check if ffmpeg is available."""
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True)
        return result.returncode == 0
    except FileNotFoundError:
        return False


def check_playwright() -> bool:
    """Check if playwright is available."""
    try:
        import playwright

        return True
    except ImportError:
        return False


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    """Convert RGB tuple to hex color string."""
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    """Convert hex color string to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))
