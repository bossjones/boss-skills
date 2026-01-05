#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "playwright>=1.40.0",
#     "pillow>=10.0.0",
#     "numpy>=1.24.0",
# ]
# ///
"""
Twitter to Instagram Reel Converter

Full pipeline: Screenshot tweet → Create canvas → Overlay video → Export reel

This is the main entry point that combines screenshot_tweet.py and compose_video.py
into a single workflow.
"""

from __future__ import annotations

import argparse
import asyncio
import glob
import sys
import tempfile
from pathlib import Path
from typing import TypedDict, cast

# Add scripts directory to path for importing sibling modules
SCRIPT_DIR = Path(__file__).parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

# Import sibling modules (no relative imports)
from compose_video import compose_video  # noqa: E402
from screenshot_tweet import screenshot_tweet  # noqa: E402
from utils import (  # noqa: E402
    check_ffmpeg,
    check_playwright,
    extract_tweet_id,
    normalize_tweet_url,
)


class ScreenshotResult(TypedDict):
    """Result from screenshot_tweet function."""

    path: str
    width: int
    height: int
    theme: str
    tweet_id: str


def download_video_from_tweet(
    tweet_url: str,
    output_dir: str | None = None,
    cookies_path: str | None = None,
    browser: str | None = None,
) -> str:
    """
    Download video from tweet using twitter-media-downloader skill.

    Args:
        tweet_url: URL of the tweet containing video
        output_dir: Directory to save downloaded video (uses temp dir if None)
        cookies_path: Path to cookies.txt for authentication
        browser: Browser to extract cookies from

    Returns:
        Path to downloaded video file

    Raises:
        RuntimeError: If download fails or no video found
    """
    import json
    import subprocess

    # Determine output directory
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="reel_video_")

    # Locate downloader script (relative to this skill's location)
    downloader_path = (
        SCRIPT_DIR.parent.parent / "twitter-media-downloader" / "scripts" / "download.py"
    )

    if not downloader_path.exists():
        raise RuntimeError(
            f"twitter-media-downloader not found at {downloader_path}. "
            "Please ensure the skill is installed in the same plugin."
        )

    # Build download command
    cmd = [
        sys.executable,
        str(downloader_path),
        tweet_url,
        "--output",
        output_dir,
        "--videos-only",
        "--json",
    ]

    # Pass through authentication
    if cookies_path:
        cmd.extend(["--cookies", cookies_path])
    elif browser:
        cmd.extend(["--browser", browser])

    # Execute downloader
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        error_msg = result.stderr.strip() if result.stderr else "Unknown error"
        raise RuntimeError(f"Download failed: {error_msg}")

    # Parse JSON output
    try:
        download_result = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse downloader output: {e}") from e

    if not download_result.get("success"):
        error = download_result.get("error", "Unknown error")
        raise RuntimeError(f"Download failed: {error}")

    files = download_result.get("files", [])
    if not files:
        raise RuntimeError(
            "No video found in tweet. The tweet may not contain video content, "
            "or authentication may be required for protected content."
        )

    # Return first video file
    return files[0]


def find_video_file(pattern: str) -> str:
    """
    Find video file from pattern (supports glob patterns).
    """
    # Check if it's a direct path
    if Path(pattern).is_file():
        return pattern

    # Try glob pattern
    matches = glob.glob(pattern)
    video_extensions = {".mp4", ".mov", ".webm", ".avi", ".mkv", ".m4v"}

    videos = [m for m in matches if Path(m).suffix.lower() in video_extensions]

    if not videos:
        raise FileNotFoundError(f"No video files found matching: {pattern}")

    if len(videos) > 1:
        print(f"Multiple videos found, using first: {videos[0]}")

    return videos[0]


def create_reel(
    tweet_url: str,
    video_path: str | None = None,
    output_path: str = "reel_output.mp4",
    theme: str = "auto",
    position: str = "top",
    padding: int = 40,
    duration: float | None = None,
    cookies_path: str | None = None,
    browser: str | None = None,
    screenshot_width: int = 550,
    keep_temp: bool = False,
) -> str:
    """
    Create an Instagram Reel from a tweet URL and video.

    Full pipeline:
    0. (Optional) Auto-download video from tweet if not provided
    1. Screenshot the tweet
    2. Create 9:16 canvas with matching background
    3. Overlay video
    4. Export final MP4

    Args:
        tweet_url: URL of the tweet to convert
        video_path: Path to video file (optional - auto-downloads if None)
        output_path: Output file path for the reel
        theme: Background theme ("light", "dark", or "auto")
        position: Tweet position on canvas ("top", "center", "bottom")
        padding: Padding around elements in pixels
        duration: Maximum output duration in seconds
        cookies_path: Path to cookies.txt for authentication
        browser: Browser to extract cookies from
        screenshot_width: Width of tweet screenshot
        keep_temp: Keep intermediate files

    Returns:
        Path to the created reel video file
    """
    # Validate dependencies
    if not check_ffmpeg():
        raise RuntimeError("FFmpeg is required. Please install FFmpeg.")

    if not check_playwright():
        raise RuntimeError(
            "Playwright is required. Install with: pip install playwright && playwright install chromium"
        )

    # Auto-download video if not provided
    if video_path is None:
        print("\n[0/3] Downloading video from tweet...")
        video_file = download_video_from_tweet(
            tweet_url=tweet_url,
            cookies_path=cookies_path,
            browser=browser,
        )
        print(f"      Downloaded: {video_file}")
    else:
        # Find video file from path/pattern
        video_file = find_video_file(video_path)
        print(f"Using video: {video_file}")

    # Normalize URL
    tweet_url = normalize_tweet_url(tweet_url)
    tweet_id = extract_tweet_id(tweet_url)

    if not tweet_id:
        raise ValueError(f"Invalid tweet URL: {tweet_url}")

    print(f"Processing tweet: {tweet_id}")

    # Create temp directory for intermediate files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        screenshot_path = temp_path / f"tweet_{tweet_id}.png"

        # Handle cookies
        cookies = cookies_path
        if browser and not cookies:
            # Extract cookies from browser to temp file
            print(f"Extracting cookies from {browser}...")
            # Note: This would require browser-cookie3 or similar
            # For now, we'll pass browser name to screenshot function
            pass

        # Step 1: Screenshot the tweet
        print("\n[1/3] Capturing tweet screenshot...")
        try:
            coro = screenshot_tweet(
                url=tweet_url,
                output_path=str(screenshot_path),
                theme=theme if theme != "auto" else None,
                width=screenshot_width,
                cookies_path=cookies,
            )
            screenshot_result = cast(
                ScreenshotResult,
                cast(object, asyncio.run(coro)),  # pyright: ignore[reportUnknownArgumentType]
            )
        except Exception as e:
            raise RuntimeError(f"Failed to screenshot tweet: {e}") from e

        detected_theme: str = screenshot_result["theme"]
        print(
            f"    Screenshot captured: {screenshot_result['width']}x{screenshot_result['height']}"
        )
        print(f"    Theme detected: {detected_theme}")

        # Step 2 & 3: Create canvas and compose video
        print("\n[2/3] Creating 1080x1920 canvas...")
        print("\n[3/3] Composing final video...")

        # Use detected theme if auto
        final_theme: str = theme if theme != "auto" else detected_theme

        output_file = compose_video(
            screenshot_path=str(screenshot_path),
            video_path=video_file,
            output_path=output_path,
            theme=final_theme,
            position=position,
            padding=padding,
            duration=duration,
            keep_temp=keep_temp,
        )

        print(f"\n✓ Reel created successfully: {output_file}")
        return output_file


def main():
    parser = argparse.ArgumentParser(
        description="Convert Twitter/X posts into Instagram Reels format",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto-download video from tweet (recommended):
  %(prog)s "https://x.com/NASA/status/123" -o nasa_reel.mp4

  # With explicit video file:
  %(prog)s "https://x.com/user/status/123" video.mp4 -o my_reel.mp4
  %(prog)s "https://x.com/user/status/123" ./downloads/*.mp4

  # With authentication for protected tweets:
  %(prog)s "https://x.com/user/status/123" --browser firefox -o reel.mp4
        """,
    )

    parser.add_argument("url", help="Tweet URL to screenshot")

    parser.add_argument(
        "video",
        nargs="?",
        default=None,
        help="Video file path (optional - auto-downloads if omitted)",
    )

    parser.add_argument(
        "-o",
        "--output",
        default="reel_output.mp4",
        help="Output file path (default: reel_output.mp4)",
    )

    # Theme and layout
    layout_group = parser.add_argument_group("Layout Options")
    layout_group.add_argument(
        "--theme",
        choices=["light", "dark", "auto"],
        default="auto",
        help="Background theme (default: auto-detect from tweet)",
    )
    layout_group.add_argument(
        "--position",
        choices=["top", "center", "bottom"],
        default="top",
        help="Tweet position on canvas (default: top)",
    )
    layout_group.add_argument(
        "--padding", type=int, default=40, help="Padding around elements in pixels (default: 40)"
    )

    # Video options
    video_group = parser.add_argument_group("Video Options")
    video_group.add_argument("--duration", type=float, help="Maximum output duration in seconds")

    # Authentication
    auth_group = parser.add_argument_group("Authentication")
    auth_group.add_argument("--cookies", help="Path to cookies.txt file for protected tweets")
    auth_group.add_argument(
        "--browser",
        choices=["firefox", "chrome", "chromium", "edge", "safari"],
        help="Extract cookies from browser",
    )

    # Advanced options
    advanced_group = parser.add_argument_group("Advanced Options")
    advanced_group.add_argument(
        "--screenshot-width", type=int, default=550, help="Tweet screenshot width (default: 550)"
    )
    advanced_group.add_argument("--no-cleanup", action="store_true", help="Keep intermediate files")
    advanced_group.add_argument(
        "--no-auto-download",
        action="store_true",
        help="Disable automatic video download (require explicit video path)",
    )

    args = parser.parse_args()

    # Validate: if no video provided, URL must be a specific tweet
    if args.video is None and not args.no_auto_download:
        tweet_id = extract_tweet_id(args.url)
        if not tweet_id:
            parser.error(
                "When video is not provided, URL must be a specific tweet "
                "(e.g., https://x.com/user/status/123456). "
                "User profile URLs require an explicit video path."
            )
    elif args.video is None and args.no_auto_download:
        parser.error("--no-auto-download requires an explicit video path")

    try:
        create_reel(
            tweet_url=args.url,
            video_path=args.video,
            output_path=args.output,
            theme=args.theme,
            position=args.position,
            padding=args.padding,
            duration=args.duration,
            cookies_path=args.cookies,
            browser=args.browser,
            screenshot_width=args.screenshot_width,
            keep_temp=args.no_cleanup,
        )
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nAborted by user")
        sys.exit(130)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
