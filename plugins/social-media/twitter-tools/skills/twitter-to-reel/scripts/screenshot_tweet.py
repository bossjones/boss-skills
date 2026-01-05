#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "playwright>=1.40.0",
# ]
# ///
from __future__ import annotations

"""
Screenshot Twitter/X tweets using Playwright.

Captures just the tweet content (username, text, media) with proper cropping.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from playwright.async_api import (
    TimeoutError as PlaywrightTimeout,  # pyright: ignore[reportMissingImports]
)
from playwright.async_api import async_playwright  # pyright: ignore[reportMissingImports]

# Add scripts directory to path for importing sibling modules
SCRIPT_DIR = Path(__file__).parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from utils import (  # noqa: E402
    detect_theme,
    ensure_chromium_installed,
    extract_tweet_id,
    normalize_tweet_url,
)

# CSS selectors for tweet elements
TWEET_SELECTORS = {
    # Main tweet article
    "tweet": 'article[data-testid="tweet"]',
    # Tweet text content
    "text": '[data-testid="tweetText"]',
    # User info
    "user": '[data-testid="User-Name"]',
    # Media container
    "media": '[data-testid="tweetPhoto"], [data-testid="videoPlayer"]',
    # Like/retweet bar (to exclude)
    "actions": '[role="group"]',
}

# JavaScript to inject for cleaner screenshots
CLEANUP_JS = """
() => {
    // Hide non-essential elements
    const selectorsToHide = [
        '[data-testid="primaryColumn"] > div > div:first-child',  // Header
        '[data-testid="sidebarColumn"]',  // Sidebar
        '[aria-label="Timeline: Conversation"]',  // Replies
        'nav',  // Navigation
        '[data-testid="BottomBar"]',  // Bottom bar
        '[role="group"]',  // Action buttons (like, retweet, etc)
    ];
    
    selectorsToHide.forEach(selector => {
        document.querySelectorAll(selector).forEach(el => {
            if (el) el.style.display = 'none';
        });
    });
    
    // Remove any fixed/sticky elements
    document.querySelectorAll('[style*="position: fixed"], [style*="position: sticky"]').forEach(el => {
        el.style.display = 'none';
    });
    
    // Clean up tweet display
    const tweet = document.querySelector('article[data-testid="tweet"]');
    if (tweet) {
        // Make sure the tweet is visible
        tweet.style.borderRadius = '0';
        tweet.style.border = 'none';
    }
}
"""


async def load_cookies(page: Any, cookies_path: str) -> None:  # pyright: ignore[reportUnknownParameterType]
    """Load cookies from file into browser context."""
    cookies_file = Path(cookies_path)
    if not cookies_file.exists():
        print(f"Warning: Cookies file not found: {cookies_path}")
        return

    # Parse Netscape/Mozilla cookies.txt format
    cookies: list[dict[str, Any]] = []
    with open(cookies_file) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split("\t")
            if len(parts) >= 7:
                domain, _, path, secure, _expires, name, value = parts[:7]
                cookies.append(
                    {
                        "name": name,
                        "value": value,
                        "domain": domain,
                        "path": path,
                        "secure": secure.lower() == "true",
                        "httpOnly": False,
                    }
                )

    if cookies:
        await page.context.add_cookies(cookies)  # pyright: ignore[reportUnknownMemberType]
        print(f"Loaded {len(cookies)} cookies")


async def screenshot_tweet(
    url: str,
    output_path: str,
    theme: str | None = None,
    width: int = 550,
    cookies_path: str | None = None,
    full_thread: bool = False,  # pyright: ignore[reportUnusedParameter]
    timeout: int = 30000,
) -> dict[str, str | int]:
    """
    Screenshot a tweet and return metadata.

    Returns:
        dict with keys: path, width, height, theme, tweet_id
    """
    url = normalize_tweet_url(url)
    tweet_id = extract_tweet_id(url)

    if not tweet_id:
        raise ValueError(f"Could not extract tweet ID from URL: {url}")

    async with async_playwright() as p:  # pyright: ignore[reportUnknownVariableType]
        # Configure browser
        browser_args = ["--disable-blink-features=AutomationControlled"]

        # Set color scheme based on theme
        color_scheme = "dark" if theme == "dark" else "light"

        browser = await p.chromium.launch(headless=True, args=browser_args)  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]

        context = await browser.new_context(  # pyright: ignore[reportUnknownMemberType, reportUnknownVariableType]
            viewport={"width": width, "height": 1200},
            color_scheme=color_scheme,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        )

        page = await context.new_page()  # pyright: ignore[reportUnknownMemberType]

        # Load cookies if provided
        if cookies_path:
            await load_cookies(page, cookies_path)

        try:
            # Navigate to tweet
            print(f"Loading tweet: {url}")
            await page.goto(url, wait_until="networkidle", timeout=timeout)  # pyright: ignore[reportUnknownMemberType]

            # Wait for tweet to load
            await page.wait_for_selector(TWEET_SELECTORS["tweet"], timeout=timeout)  # pyright: ignore[reportUnknownMemberType]

            # Additional wait for media to load
            await asyncio.sleep(2)

            # Run cleanup JavaScript
            await page.evaluate(CLEANUP_JS)  # pyright: ignore[reportUnknownMemberType]

            # Find the main tweet element
            tweet_element = await page.query_selector(TWEET_SELECTORS["tweet"])  # pyright: ignore[reportUnknownMemberType]

            if not tweet_element:
                raise RuntimeError("Could not find tweet element on page")

            # Get bounding box
            box = await tweet_element.bounding_box()  # pyright: ignore[reportUnknownMemberType]

            if not box:
                raise RuntimeError("Could not get tweet bounding box")

            # Adjust screenshot area
            # Add some padding
            padding = 20
            box_x = float(box["x"])  # pyright: ignore[reportUnknownArgumentType]
            box_y = float(box["y"])  # pyright: ignore[reportUnknownArgumentType]
            box_width = float(box["width"])  # pyright: ignore[reportUnknownArgumentType]
            box_height = float(box["height"])  # pyright: ignore[reportUnknownArgumentType]
            clip = {
                "x": max(0, box_x - padding),
                "y": max(0, box_y - padding),
                "width": box_width + (padding * 2),
                "height": box_height + (padding * 2),
            }

            # Take screenshot
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)

            await page.screenshot(path=str(output_file), clip=clip, type="png")  # pyright: ignore[reportUnknownMemberType]

            print(f"Screenshot saved: {output_path}")

            # Detect actual theme from screenshot
            detected_theme = detect_theme(str(output_file))

            return {
                "path": str(output_file),
                "width": int(clip["width"]),  # pyright: ignore[reportArgumentType]
                "height": int(clip["height"]),  # pyright: ignore[reportArgumentType]
                "theme": detected_theme,
                "tweet_id": tweet_id,
            }

        except PlaywrightTimeout:
            raise RuntimeError(
                "Timeout loading tweet. The tweet may be protected or deleted."
            ) from None
        finally:
            await browser.close()  # pyright: ignore[reportUnknownMemberType]


def main():
    parser = argparse.ArgumentParser(
        description="Screenshot a Twitter/X tweet",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("url", help="Tweet URL to screenshot")

    parser.add_argument(
        "-o",
        "--output",
        default="tweet_screenshot.png",
        help="Output file path (default: tweet_screenshot.png)",
    )

    parser.add_argument("--theme", choices=["light", "dark"], help="Force light or dark theme")

    parser.add_argument(
        "--width", type=int, default=550, help="Browser viewport width (default: 550)"
    )

    parser.add_argument("--full", action="store_true", help="Capture full tweet thread")

    parser.add_argument("--cookies", help="Path to cookies.txt file for protected tweets")

    parser.add_argument(
        "--timeout", type=int, default=30000, help="Timeout in milliseconds (default: 30000)"
    )

    parser.add_argument("--json", action="store_true", help="Output metadata as JSON")

    args = parser.parse_args()

    try:
        ensure_chromium_installed()
    except Exception as e:
        print(f"Error installing Chromium: {e}", file=sys.stderr)
        sys.exit(1)

    try:
        result = asyncio.run(
            screenshot_tweet(
                url=args.url,
                output_path=args.output,
                theme=args.theme,
                width=args.width,
                cookies_path=args.cookies,
                full_thread=args.full,
                timeout=args.timeout,
            )
        )

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Theme detected: {result['theme']}")
            print(f"Dimensions: {result['width']}x{result['height']}")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
