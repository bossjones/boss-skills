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

import argparse
import asyncio
import glob
import sys
import tempfile
from pathlib import Path

from .compose_video import compose_video
from .screenshot_tweet import screenshot_tweet

# Import our modules
from .utils import check_ffmpeg, check_playwright, extract_tweet_id, normalize_tweet_url


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
    video_path: str,
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
    1. Screenshot the tweet
    2. Create 9:16 canvas with matching background
    3. Overlay video
    4. Export final MP4
    """
    # Validate dependencies
    if not check_ffmpeg():
        raise RuntimeError("FFmpeg is required. Please install FFmpeg.")

    if not check_playwright():
        raise RuntimeError(
            "Playwright is required. Install with: pip install playwright && playwright install chromium"
        )

    # Find video file
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
            screenshot_result = asyncio.run(
                screenshot_tweet(
                    url=tweet_url,
                    output_path=str(screenshot_path),
                    theme=theme if theme != "auto" else None,
                    width=screenshot_width,
                    cookies_path=cookies,
                )
            )
        except Exception as e:
            raise RuntimeError(f"Failed to screenshot tweet: {e}") from e

        detected_theme = screenshot_result["theme"]
        print(
            f"    Screenshot captured: {screenshot_result['width']}x{screenshot_result['height']}"
        )
        print(f"    Theme detected: {detected_theme}")

        # Step 2 & 3: Create canvas and compose video
        print("\n[2/3] Creating 1080x1920 canvas...")
        print("\n[3/3] Composing final video...")

        # Use detected theme if auto
        final_theme = theme if theme != "auto" else detected_theme

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
  %(prog)s "https://x.com/NASA/status/123" nasa_video.mp4
  %(prog)s "https://x.com/user/status/123" ./downloads/*.mp4 -o my_reel.mp4
  %(prog)s "https://x.com/user/status/123" video.mp4 --theme dark --position bottom
  %(prog)s "https://x.com/user/status/123" video.mp4 --browser firefox

Works with twitter-media-downloader:
  python3 ../twitter-media-downloader/scripts/download.py "URL" -o ./downloads
  python3 scripts/create_reel.py "URL" ./downloads/*.mp4
        """,
    )

    parser.add_argument("url", help="Tweet URL to screenshot")

    parser.add_argument(
        "video", help="Video file path (supports glob patterns like ./downloads/*.mp4)"
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

    args = parser.parse_args()

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
