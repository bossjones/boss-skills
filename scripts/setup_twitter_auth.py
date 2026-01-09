#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "playwright>=1.40.0",
# ]
# ///
"""
Twitter/X Authentication Setup - Manual Login & Cookie Saver.

One-time setup script that opens a browser for manual Twitter/X login, then
automatically saves the authentication cookies for use by other automation scripts
(e.g., gallery-dl, twitter-to-reel, or custom API clients).

Workflow:
    1. Opens a Chromium browser window with anti-bot-detection settings
    2. Navigates to Twitter/X login page
    3. Waits 60 seconds for you to log in manually
    4. Extracts session cookies from the browser
    5. Saves cookies to a JSON file for other scripts to load

File Locations (resolved on macOS/Linux):
    Browser Profile:
        Path: ~/.boss-skills/twitter_browser/
        Resolves to: /Users/<username>/.boss-skills/twitter_browser/
        Contains: Chromium user data directory with persistent login session.
                  This allows the browser to "remember" your login across runs.

    Cookies Export:
        Path: ~/.boss-skills/twitter_auth.json
        Resolves to: /Users/<username>/.boss-skills/twitter_auth.json
        Contains: JSON with extracted cookies and user agent string.
                  Other scripts load this file to authenticate API requests.

Important Cookies Captured:
    - auth_token: Primary authentication token for Twitter/X session
    - ct0: CSRF token required for POST requests to Twitter API

Usage:
    # Run directly (uv auto-installs playwright)
    ./scripts/setup_twitter_auth.py

    # Or via uv
    uv run scripts/setup_twitter_auth.py

    # First time: Install playwright browsers
    uv run playwright install chromium

Note:
    This script requires manual interaction - you must enter your credentials
    in the browser window that opens. It cannot automate the login itself.

Based on: https://github.com/LiuLucian/uniapi/blob/main/backend/setup_twitter_auth.py
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from playwright.async_api import async_playwright  # pyright: ignore[reportMissingImports]


async def save_twitter_auth() -> None:
    """Open browser for manual Twitter login, then save cookies to disk.

    This function:
    1. Creates a persistent browser profile directory
    2. Launches Chromium with settings to avoid bot detection
    3. Waits for manual login completion
    4. Exports cookies to JSON for use by other scripts
    """
    # Print setup instructions for the user
    print("=" * 60)
    print("Twitter Authentication Setup")
    print("=" * 60)
    print("\nThis will:")
    print("1. Open a browser window")
    print("2. Navigate to Twitter login")
    print("3. Wait for you to login manually")
    print("4. Save cookies automatically")
    print("\nStarting browser...")

    async with async_playwright() as p:  # pyright: ignore[reportUnknownVariableType]
        # =====================================================================
        # BROWSER PROFILE DIRECTORY
        # =====================================================================
        # Path: ~/.boss-skills/twitter_browser/
        # On macOS: /Users/<username>/.boss-skills/twitter_browser/
        # On Linux: /home/<username>/.boss-skills/twitter_browser/
        #
        # This directory stores Chromium's user data (cookies, localStorage,
        # session data). Using a persistent context means:
        # - Login state persists between script runs
        # - You only need to solve CAPTCHAs once
        # - Twitter sees a "returning user" rather than fresh browser
        # =====================================================================
        user_data_dir = Path.home() / ".boss-skills/twitter_browser"
        user_data_dir.mkdir(parents=True, exist_ok=True)

        # =====================================================================
        # LAUNCH BROWSER WITH ANTI-BOT-DETECTION SETTINGS
        # =====================================================================
        # launch_persistent_context() creates a browser that saves state to disk.
        # Parameters explained:
        #   - str(user_data_dir): Where to store browser profile data
        #   - headless=False: Show the browser window (required for manual login)
        #   - viewport: Standard desktop resolution to appear legitimate
        #   - user_agent: Mimics real Chrome browser to avoid detection
        #   - args: Disables automation detection flags that sites check for
        # =====================================================================
        context = await p.chromium.launch_persistent_context(
            str(user_data_dir),
            headless=False,  # Must be visible for manual login
            viewport={"width": 1280, "height": 720},  # Standard desktop size
            # Chrome user agent - makes requests look like normal browser traffic
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            # Disable automation detection - prevents "navigator.webdriver" flag
            # that sites use to detect Playwright/Selenium
            args=["--disable-blink-features=AutomationControlled"],
        )

        # Get existing page or create new one from the persistent context
        page = context.pages[0] if context.pages else await context.new_page()

        # =====================================================================
        # NAVIGATE TO TWITTER LOGIN
        # =====================================================================
        print("\nOpening Twitter...")
        await page.goto("https://twitter.com/login")

        # =====================================================================
        # WAIT FOR MANUAL LOGIN
        # =====================================================================
        # The script pauses here while you:
        # 1. Enter your username/email
        # 2. Enter your password
        # 3. Complete any 2FA or CAPTCHA challenges
        # 60 seconds should be enough for most logins
        # =====================================================================
        print("\nPlease login to Twitter manually in the browser window")
        print("(I'll wait 60 seconds for you to login...)")
        await asyncio.sleep(60)

        # =====================================================================
        # VERIFY LOGIN SUCCESS
        # =====================================================================
        # After login, Twitter redirects to /home. Check the URL to confirm.
        # Note: Twitter rebranded to X, so we check both domains.
        # =====================================================================
        current_url = page.url
        if "twitter.com/home" in current_url or "x.com/home" in current_url:
            print("\nLogin detected!")
        else:
            print(f"\nCurrent URL: {current_url}")
            print("If you're logged in, that's fine. Continuing...")

        # =====================================================================
        # EXTRACT COOKIES FROM BROWSER
        # =====================================================================
        # context.cookies() returns all cookies for the browser session.
        # This includes authentication tokens that let us make API requests
        # as the logged-in user from other scripts.
        # =====================================================================
        cookies = await context.cookies()

        # =====================================================================
        # SAVE COOKIES TO JSON FILE
        # =====================================================================
        # Path: ~/.boss-skills/twitter_auth.json
        # On macOS: /Users/<username>/.boss-skills/twitter_auth.json
        # On Linux: /home/<username>/.boss-skills/twitter_auth.json
        #
        # The JSON structure contains:
        # {
        #   "cookies": [...],     # List of cookie objects from browser
        #   "user_agent": "..."   # User agent string for consistent requests
        # }
        #
        # Other scripts load this file to:
        # 1. Set cookies on their HTTP client
        # 2. Use matching user agent to avoid fingerprint mismatch
        # =====================================================================
        auth_dir = Path.home() / ".boss-skills"
        auth_dir.mkdir(exist_ok=True)

        auth_file = auth_dir / "twitter_auth.json"
        auth_data = {
            "cookies": cookies,
            # Shortened user agent for the JSON export
            # Full version used in browser, truncated here for readability
            "user_agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"),
        }

        with open(auth_file, "w") as f:
            json.dump(auth_data, f, indent=2)

        print(f"\nCookies saved to: {auth_file}")
        print(f"Saved {len(cookies)} cookies")

        # =====================================================================
        # VERIFY IMPORTANT COOKIES CAPTURED
        # =====================================================================
        # Twitter authentication requires specific cookies:
        #   - auth_token: The main session token (proves you're logged in)
        #   - ct0: CSRF token (required for POST/mutation requests)
        #
        # If these are missing, the export likely won't work for API access.
        # Common reasons for missing cookies:
        #   - Login wasn't completed before timeout
        #   - Twitter's cookie structure changed
        #   - Browser blocked cookie storage
        # =====================================================================
        cookie_names = [c["name"] for c in cookies]
        important_cookies = ["auth_token", "ct0"]
        found_important = [name for name in important_cookies if name in cookie_names]

        if found_important:
            print(f"Found important cookies: {', '.join(found_important)}")
        else:
            print("Warning: Didn't find expected cookies (auth_token, ct0)")
            print("This might still work, or you may need to login again")

        # Close browser context (saves final state to user_data_dir)
        await context.close()

        print("\nSetup complete!")
        print("You can now test the API with: python3 test_twitter_api.py")


if __name__ == "__main__":
    asyncio.run(save_twitter_auth())
