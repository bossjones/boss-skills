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
        if dep_result.returncode != 0:
            result["error"] = "gallery-dl is not installed"
            return result
    except FileNotFoundError:
        result["error"] = "gallery-dl is not installed"
        return result

    # Build configuration
    config = build_config(args)

    # Write config to temporary file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(config, f, indent=2)
        config_file = f.name

    try:
        # Build and execute command with path capture
        cmd = build_command(args, config_file, capture_paths=True)

        # Run gallery-dl and capture output
        proc_result = subprocess.run(cmd, capture_output=True, text=True)

        # Parse downloaded file paths from stdout
        files = parse_downloaded_paths(proc_result.stdout)

        result["files"] = files
        result["success"] = proc_result.returncode == 0

        if proc_result.returncode != 0 and proc_result.stderr:
            result["error"] = proc_result.stderr.strip()

    except Exception as e:
        result["error"] = str(e)

    finally:
        # Clean up temp config file
        with contextlib.suppress(OSError):
            os.unlink(config_file)

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
    config_file: str,
    capture_paths: bool = False,
) -> list[str]:
    """Build the gallery-dl command.

    Args:
        args: Parsed command line arguments
        config_file: Path to temporary gallery-dl config file
        capture_paths: If True, add --print option to output downloaded file paths
    """
    cmd: list[str] = ["gallery-dl"]

    # Output directory
    output_dir = Path(args.output).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    cmd.extend(["-d", str(output_dir)])

    # Config file
    cmd.extend(["-c", config_file])

    # Print downloaded file paths to stdout (for JSON mode parsing)
    if capture_paths:
        cmd.extend(["--print", "after:{_path}"])

    # Authentication
    if args.cookies:
        cmd.extend(["--cookies", args.cookies])
    elif args.browser:
        cmd.extend(["--cookies-from-browser", args.browser])

    # Filtering
    if args.videos_only:
        cmd.extend(["--filter", "extension in ('mp4', 'webm', 'mov', 'm4v')"])
    elif args.images_only:
        cmd.extend(["--filter", "extension in ('jpg', 'jpeg', 'png', 'gif', 'webp')"])

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

    args = parser.parse_args()

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
