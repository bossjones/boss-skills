#!/usr/bin/env python3
"""
Twitter/X Media Downloader

A wrapper script for gallery-dl to download images and videos from X/Twitter.
Supports tweets, user profiles, timelines, likes, bookmarks, and lists.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


class DebugConsole:
    """Debug output console with flush support for subprocess environments."""

    enabled = False

    @classmethod
    def debug(cls, msg: str) -> None:
        """Print debug message only when debug mode is enabled."""
        if not cls.enabled:
            return

        print(f"[DEBUG] {msg}", file=sys.stderr)
        sys.stderr.flush()

    @classmethod
    def debug_dict(cls, label: str, data: dict[str, object]) -> None:
        """Pretty print a dict in debug mode."""
        if not cls.enabled:
            return

        print(f"[DEBUG] {label}:", file=sys.stderr)
        for key, value in data.items():
            print(f"        {key}: {value}", file=sys.stderr)
        sys.stderr.flush()

    @classmethod
    def debug_cmd(cls, cmd: list[str]) -> None:
        """Print command that will be executed."""
        if not cls.enabled:
            return

        print("[DEBUG] Executing command:", file=sys.stderr)
        print(f"        {' '.join(cmd)}", file=sys.stderr)
        sys.stderr.flush()

    @classmethod
    def debug_subprocess(cls, result: subprocess.CompletedProcess[str]) -> None:
        """Print subprocess result details."""
        if not cls.enabled:
            return

        print("[DEBUG] Subprocess result:", file=sys.stderr)
        print(f"        returncode: {result.returncode}", file=sys.stderr)
        if result.stdout:
            stdout_preview = result.stdout[:1000]
            if len(result.stdout) > 1000:
                stdout_preview += "..."
            print(f"        stdout: {stdout_preview}", file=sys.stderr)
        if result.stderr:
            stderr_preview = result.stderr[:1000]
            if len(result.stderr) > 1000:
                stderr_preview += "..."
            print(f"        stderr: {stderr_preview}", file=sys.stderr)
        sys.stderr.flush()


def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        result = subprocess.run(["gallery-dl", "--version"], capture_output=True, text=True)
        if result.returncode != 0:
            raise FileNotFoundError
    except FileNotFoundError:
        print("Error: gallery-dl is not installed.")
        print("Install it with: pip install gallery-dl")
        sys.exit(1)

    # Check for yt-dlp (optional but recommended for videos)
    try:
        subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True)
    except FileNotFoundError:
        print("Warning: yt-dlp is not installed. Video downloads may not work.")
        print("Install it with: pip install yt-dlp")


def normalize_url(url: str) -> str:
    """Normalize Twitter/X URLs to a consistent format."""
    url = url.strip()
    # Convert twitter.com to x.com (gallery-dl handles both)
    url = url.replace("twitter.com", "x.com")
    # Remove trailing slashes
    url = url.rstrip("/")
    return url


def extract_tweet_id(url: str) -> str | None:
    """Extract tweet ID from Twitter/X URL."""
    match = re.search(r"/status/(\d+)", url)
    return match.group(1) if match else None


def parse_downloaded_paths(stdout: str) -> list[str]:
    """Parse downloaded file paths from gallery-dl --print output."""
    files: list[str] = []
    for line in stdout.strip().split("\n"):
        line = line.strip()
        if line and Path(line).exists():
            files.append(line)
    return files


def download_with_json_output(args: argparse.Namespace) -> dict[str, Any]:
    """Execute download and return structured JSON result.

    Returns:
        Dictionary with keys: files, tweet_id, output_dir, url, success, error
    """
    output_dir = Path(args.output).resolve()
    tweet_id = extract_tweet_id(args.url)
    normalized_url = normalize_url(args.url)

    DebugConsole.debug_dict(
        "download_with_json_output called with",
        {
            "url": args.url,
            "output": args.output,
            "videos_only": getattr(args, "videos_only", False),
            "images_only": getattr(args, "images_only", False),
            "cookies": getattr(args, "cookies", None),
            "browser": getattr(args, "browser", None),
        },
    )

    result: dict[str, Any] = {
        "files": [],
        "tweet_id": tweet_id,
        "output_dir": str(output_dir),
        "url": normalized_url,
        "success": False,
        "error": None,
    }

    # Check dependencies first
    try:
        dep_result = subprocess.run(["gallery-dl", "--version"], capture_output=True, text=True)
        DebugConsole.debug(f"gallery-dl version check: returncode={dep_result.returncode}")
        if dep_result.stdout:
            DebugConsole.debug(f"gallery-dl version: {dep_result.stdout.strip()}")
        if dep_result.returncode != 0:
            result["error"] = "gallery-dl is not installed"
            return result
    except FileNotFoundError:
        result["error"] = "gallery-dl is not installed"
        return result

    # Build command without custom config (use user's default gallery-dl config)
    # Note: We don't use --print or custom config as they can interfere with downloads
    cmd = build_command(args, config_file=None)
    DebugConsole.debug_cmd(cmd)

    try:
        # Run gallery-dl and capture output
        proc_result = subprocess.run(cmd, capture_output=True, text=True)
        DebugConsole.debug_subprocess(proc_result)

        # Scan output directory for downloaded files (more reliable than --print)
        DebugConsole.debug("Scanning output directory for downloaded files...")
        files = find_downloaded_files(
            output_dir,
            videos_only=getattr(args, "videos_only", False),
            images_only=getattr(args, "images_only", False),
        )

        DebugConsole.debug(f"Found files: {files}")

        result["files"] = files
        result["success"] = proc_result.returncode == 0

        if proc_result.returncode != 0 and proc_result.stderr:
            result["error"] = proc_result.stderr.strip()

        # If success but no files, add diagnostic info
        if result["success"] and not files:
            DebugConsole.debug("WARNING: gallery-dl succeeded but no files were found")
            if proc_result.stderr:
                DebugConsole.debug(f"stderr (may contain info): {proc_result.stderr}")

    except Exception as e:
        DebugConsole.debug(f"Exception during download: {e}")
        result["error"] = str(e)

    DebugConsole.debug_dict("Final result", result)
    return result


def build_config(args: argparse.Namespace) -> dict[str, Any]:
    """Build gallery-dl configuration based on arguments."""
    config: dict[str, Any] = {
        "extractor": {
            "twitter": {
                "retweets": args.retweets,
                "replies": args.replies,
                "text-tweets": False,
                "quoted": True,
                "videos": not args.images_only,
                "cards": True,
            }
        },
        "downloader": {
            "rate": args.rate_limit if args.rate_limit else None,
        },
        "output": {
            "mode": "terminal",
            "progress": True,
        },
    }

    # Add sleep interval if specified
    if args.sleep:
        extractor_twitter = config["extractor"]["twitter"]
        assert isinstance(extractor_twitter, dict)
        extractor_twitter["sleep"] = args.sleep
        extractor_twitter["sleep-request"] = args.sleep

    return config


def build_command(
    args: argparse.Namespace,
    config_file: str | None = None,
) -> list[str]:
    """Build the gallery-dl command.

    Args:
        args: Parsed command line arguments
        config_file: Path to temporary gallery-dl config file (optional)

    Note:
        - We don't use --print because it can interfere with downloads
        - Filtering (--videos-only, --images-only) is done post-download
        - We scan the output directory to find downloaded files
    """
    cmd: list[str] = ["gallery-dl"]

    # Output directory
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd.extend(["-d", str(output_dir)])

    # Config file (optional - omit to use user's default config)
    if config_file:
        cmd.extend(["-c", config_file])

    # Authentication
    if args.cookies:
        cmd.extend(["--cookies", args.cookies])
    elif args.browser:
        cmd.extend(["--cookies-from-browser", args.browser])

    # Limit
    if args.limit:
        cmd.extend(["--range", f"1-{args.limit}"])

    # Filename format
    filename_format = "twitter_{username}_{tweet_id}_{num}.{extension}"
    cmd.extend(["-f", filename_format])

    # Verbosity
    if args.verbose:
        cmd.append("-v")

    # Simulate mode (don't download)
    if args.simulate:
        cmd.append("-s")

    # Get URLs only
    if args.get_urls:
        cmd.append("-g")

    # URL
    cmd.append(normalize_url(args.url))

    return cmd


# File extension sets for post-download filtering
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov", ".m4v", ".avi", ".mkv"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


def filter_files_by_type(
    files: list[str],
    videos_only: bool = False,
    images_only: bool = False,
) -> list[str]:
    """Filter downloaded files by media type.

    Args:
        files: List of file paths
        videos_only: If True, keep only video files
        images_only: If True, keep only image files

    Returns:
        Filtered list of file paths
    """
    if not videos_only and not images_only:
        return files

    filtered = []
    for f in files:
        ext = Path(f).suffix.lower()
        if videos_only and ext in VIDEO_EXTENSIONS or images_only and ext in IMAGE_EXTENSIONS:
            filtered.append(f)

    DebugConsole.debug(f"Filtered {len(files)} files to {len(filtered)} matching type filter")
    return filtered


def find_downloaded_files(
    output_dir: Path, videos_only: bool = False, images_only: bool = False
) -> list[str]:
    """Scan output directory for downloaded media files.

    This is a fallback when --print doesn't capture paths correctly.

    Args:
        output_dir: Directory to scan
        videos_only: If True, return only video files
        images_only: If True, return only image files

    Returns:
        List of file paths found
    """
    if not output_dir.exists():
        return []

    all_extensions = VIDEO_EXTENSIONS | IMAGE_EXTENSIONS
    if videos_only:
        target_extensions = VIDEO_EXTENSIONS
    elif images_only:
        target_extensions = IMAGE_EXTENSIONS
    else:
        target_extensions = all_extensions

    files = []
    for f in output_dir.rglob("*"):
        if f.is_file() and f.suffix.lower() in target_extensions:
            files.append(str(f))

    DebugConsole.debug(f"Found {len(files)} files in output directory matching filter")
    return files


def main():
    parser = argparse.ArgumentParser(
        description="Download images and videos from X/Twitter using gallery-dl",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "https://x.com/NASA"
  %(prog)s "https://x.com/user/status/1234567890" --output ./downloads
  %(prog)s "https://x.com/username" --videos-only --limit 50
  %(prog)s "https://x.com/i/bookmarks" --browser firefox
        """,
    )

    parser.add_argument("url", help="Twitter/X URL (tweet, user profile, likes, bookmarks, etc.)")

    parser.add_argument(
        "-o", "--output", default="./downloads", help="Output directory (default: ./downloads)"
    )

    # Authentication options
    auth_group = parser.add_argument_group("Authentication")
    auth_group.add_argument("--cookies", help="Path to cookies.txt file for authentication")
    auth_group.add_argument(
        "--browser",
        choices=["firefox", "chrome", "chromium", "opera", "edge", "brave", "vivaldi", "safari"],
        help="Extract cookies from browser",
    )

    # Filter options
    filter_group = parser.add_argument_group("Filters")
    filter_group.add_argument("--videos-only", action="store_true", help="Download only videos")
    filter_group.add_argument("--images-only", action="store_true", help="Download only images")
    filter_group.add_argument("--limit", type=int, help="Limit number of items to download")
    filter_group.add_argument(
        "--retweets", action="store_true", help="Include retweets when downloading user timeline"
    )
    filter_group.add_argument(
        "--replies", action="store_true", help="Include replies when downloading user timeline"
    )

    # Rate limiting
    rate_group = parser.add_argument_group("Rate Limiting")
    rate_group.add_argument("--sleep", type=float, help="Seconds to sleep between requests")
    rate_group.add_argument("--rate-limit", help="Download rate limit (e.g., '1M' for 1MB/s)")

    # Output options
    output_group = parser.add_argument_group("Output Options")
    output_group.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    output_group.add_argument(
        "-s",
        "--simulate",
        action="store_true",
        help="Simulate download without actually downloading",
    )
    output_group.add_argument(
        "-g", "--get-urls", action="store_true", help="Print URLs instead of downloading"
    )
    output_group.add_argument(
        "--json",
        action="store_true",
        help="Output JSON with downloaded file paths (for programmatic use)",
    )
    output_group.add_argument(
        "--debug",
        action="store_true",
        help="Enable verbose debug output for troubleshooting",
    )

    args = parser.parse_args()

    # Enable debug mode if requested
    if args.debug:
        DebugConsole.enabled = True
        DebugConsole.debug("Debug mode enabled")

    # Validate mutually exclusive options
    if args.videos_only and args.images_only:
        parser.error("--videos-only and --images-only are mutually exclusive")

    # JSON mode: structured output for programmatic use
    if args.json:
        result = download_with_json_output(args)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result["success"] else 1)

    # Normal mode: interactive output
    check_dependencies()

    # Build configuration
    config = build_config(args)

    # Write config to temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(config, f, indent=2)
        config_file = f.name

    try:
        # Build and execute command
        cmd = build_command(args, config_file)

        if args.verbose:
            print(f"Running: {' '.join(cmd)}")

        result = subprocess.run(cmd)
        sys.exit(result.returncode)

    finally:
        # Clean up temp config file
        with contextlib.suppress(OSError):
            os.unlink(config_file)


if __name__ == "__main__":
    main()
