"""Tests for screenshot_tweet.py script."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestLoadCookies:
    """Tests for load_cookies function."""

    @pytest.mark.asyncio
    async def test_parses_netscape_format(self, sample_cookies_file: Path, tmp_path: Path) -> None:
        """Should parse Netscape cookies.txt format correctly."""
        # We need to import after mocking playwright
        from screenshot_tweet import load_cookies

        mock_page = MagicMock()
        mock_context = MagicMock()
        mock_context.add_cookies = AsyncMock()
        mock_page.context = mock_context

        await load_cookies(mock_page, str(sample_cookies_file))

        # Should have called add_cookies with parsed cookies
        mock_context.add_cookies.assert_called_once()
        cookies = mock_context.add_cookies.call_args[0][0]

        assert len(cookies) == 2
        assert cookies[0]["name"] == "auth_token"
        assert cookies[0]["value"] == "abc123"
        assert cookies[0]["domain"] == ".x.com"

    @pytest.mark.asyncio
    async def test_handles_empty_file(self, empty_cookies_file: Path) -> None:
        """Should handle empty cookies file gracefully."""
        from screenshot_tweet import load_cookies

        mock_page = MagicMock()
        mock_context = MagicMock()
        mock_context.add_cookies = AsyncMock()
        mock_page.context = mock_context

        await load_cookies(mock_page, str(empty_cookies_file))

        # Should not call add_cookies for empty file
        mock_context.add_cookies.assert_not_called()

    @pytest.mark.asyncio
    async def test_ignores_comments(self, cookies_with_comments: Path) -> None:
        """Should ignore comment lines starting with #."""
        from screenshot_tweet import load_cookies

        mock_page = MagicMock()
        mock_context = MagicMock()
        mock_context.add_cookies = AsyncMock()
        mock_page.context = mock_context

        await load_cookies(mock_page, str(cookies_with_comments))

        # Should not call add_cookies when only comments present
        mock_context.add_cookies.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_missing_file(self, tmp_path: Path) -> None:
        """Should handle missing cookies file gracefully."""
        from screenshot_tweet import load_cookies

        mock_page = MagicMock()
        mock_context = MagicMock()
        mock_context.add_cookies = AsyncMock()
        mock_page.context = mock_context

        nonexistent = str(tmp_path / "nonexistent.txt")
        await load_cookies(mock_page, nonexistent)

        # Should not raise, just skip
        mock_context.add_cookies.assert_not_called()

    @pytest.mark.asyncio
    async def test_parses_secure_flag(self, tmp_path: Path) -> None:
        """Should correctly parse the secure flag."""
        cookies_content = ".x.com\tTRUE\t/\tTRUE\t1735689600\tsecure_cookie\tvalue1\n"
        cookies_file = tmp_path / "secure_cookies.txt"
        cookies_file.write_text(cookies_content)

        from screenshot_tweet import load_cookies

        mock_page = MagicMock()
        mock_context = MagicMock()
        mock_context.add_cookies = AsyncMock()
        mock_page.context = mock_context

        await load_cookies(mock_page, str(cookies_file))

        cookies = mock_context.add_cookies.call_args[0][0]
        assert cookies[0]["secure"] is True


class TestScreenshotTweet:
    """Tests for screenshot_tweet async function."""

    @pytest.mark.asyncio
    async def test_raises_for_invalid_url(self) -> None:
        """Should raise ValueError for URL without tweet ID."""
        from screenshot_tweet import screenshot_tweet

        with pytest.raises(ValueError, match="Could not extract tweet ID"):
            await screenshot_tweet(
                url="https://x.com/NASA",  # Profile URL, no status
                output_path="/tmp/output.png",
            )

    def test_url_normalization_called(self) -> None:
        """Verify normalize_tweet_url is imported and available.

        The actual URL normalization logic is tested in test_utils.py.
        Here we just verify the screenshot module uses the utility.
        """
        from screenshot_tweet import normalize_tweet_url

        # Test the imported function directly
        result = normalize_tweet_url("https://twitter.com/user/status/123456")
        assert "x.com" in result
        assert "twitter.com" not in result


class TestScreenshotTweetMetadata:
    """Tests for screenshot result metadata."""

    @pytest.mark.asyncio
    async def test_returns_expected_structure(self, tmp_path: Path) -> None:
        """Should return dict with expected keys."""
        from screenshot_tweet import screenshot_tweet

        # Create mock screenshot file
        screenshot_file = tmp_path / "screenshot.png"

        # Create a light image for theme detection
        from PIL import Image

        img = Image.new("RGB", (590, 440), color=(255, 255, 255))
        img.save(screenshot_file)

        # Setup comprehensive mocking
        mock_playwright = MagicMock()
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()

        mock_playwright.__aenter__ = AsyncMock(return_value=mock_playwright)
        mock_playwright.__aexit__ = AsyncMock(return_value=None)
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)

        # Mock page methods
        mock_page.goto = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        mock_page.evaluate = AsyncMock()
        mock_page.context = mock_context
        mock_context.add_cookies = AsyncMock()

        # Mock tweet element with bounding box
        mock_element = AsyncMock()
        mock_element.bounding_box = AsyncMock(
            return_value={"x": 0, "y": 0, "width": 550, "height": 400}
        )
        mock_page.query_selector = AsyncMock(return_value=mock_element)

        # Mock screenshot to actually create the file
        async def create_screenshot(**kwargs: Any) -> None:
            # Copy our pre-made image to the output path
            import shutil

            shutil.copy(screenshot_file, kwargs["path"])

        mock_page.screenshot = create_screenshot

        with patch("screenshot_tweet.async_playwright", return_value=mock_playwright):
            result = await screenshot_tweet(
                url="https://x.com/user/status/123456789",
                output_path=str(tmp_path / "output.png"),
            )

        # Verify result structure
        assert "path" in result
        assert "width" in result
        assert "height" in result
        assert "theme" in result
        assert "tweet_id" in result

        assert result["tweet_id"] == "123456789"
        assert result["theme"] in ["light", "dark"]


class TestTweetSelectors:
    """Tests for CSS selectors constants."""

    def test_tweet_selectors_defined(self) -> None:
        """Should have tweet selectors defined."""
        from screenshot_tweet import TWEET_SELECTORS

        assert "tweet" in TWEET_SELECTORS
        assert "text" in TWEET_SELECTORS
        assert "user" in TWEET_SELECTORS
        assert "media" in TWEET_SELECTORS
        assert "actions" in TWEET_SELECTORS

    def test_tweet_selector_is_article(self) -> None:
        """Main tweet selector should target article element."""
        from screenshot_tweet import TWEET_SELECTORS

        assert "article" in TWEET_SELECTORS["tweet"]
        assert "tweet" in TWEET_SELECTORS["tweet"]


class TestCleanupJs:
    """Tests for cleanup JavaScript constant."""

    def test_cleanup_js_defined(self) -> None:
        """Should have cleanup JavaScript defined."""
        from screenshot_tweet import CLEANUP_JS

        assert CLEANUP_JS is not None
        assert len(CLEANUP_JS) > 0

    def test_cleanup_js_hides_elements(self) -> None:
        """Cleanup JS should hide non-essential elements."""
        from screenshot_tweet import CLEANUP_JS

        assert "display" in CLEANUP_JS
        assert "none" in CLEANUP_JS

    def test_cleanup_js_targets_sidebar(self) -> None:
        """Cleanup JS should target sidebar."""
        from screenshot_tweet import CLEANUP_JS

        assert "sidebar" in CLEANUP_JS.lower()
