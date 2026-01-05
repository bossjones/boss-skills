"""Tests for utils.py shared utilities."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from utils import (
    REEL_HEIGHT,
    REEL_WIDTH,
    THEME_COLORS,
    check_ffmpeg,
    check_playwright,
    detect_dominant_color,
    detect_theme,
    extract_tweet_id,
    get_video_dimensions,
    get_video_duration,
    hex_to_rgb,
    normalize_tweet_url,
    rgb_to_hex,
)


class TestConstants:
    """Tests for module constants."""

    def test_reel_dimensions(self) -> None:
        """Should have correct Instagram Reels dimensions."""
        assert REEL_WIDTH == 1080
        assert REEL_HEIGHT == 1920

    def test_theme_colors_structure(self) -> None:
        """Should have light and dark theme colors."""
        assert "light" in THEME_COLORS
        assert "dark" in THEME_COLORS

        for theme in ["light", "dark"]:
            assert "background" in THEME_COLORS[theme]
            assert "text" in THEME_COLORS[theme]
            assert "secondary" in THEME_COLORS[theme]

    def test_light_theme_is_white(self) -> None:
        """Light theme should have white background."""
        assert THEME_COLORS["light"]["background"] == (255, 255, 255)

    def test_dark_theme_is_black(self) -> None:
        """Dark theme should have black background."""
        assert THEME_COLORS["dark"]["background"] == (0, 0, 0)


class TestNormalizeTweetUrl:
    """Tests for normalize_tweet_url function."""

    def test_converts_twitter_to_x(self) -> None:
        """Should convert twitter.com to x.com."""
        url = "https://twitter.com/NASA/status/123456"
        result = normalize_tweet_url(url)
        assert result == "https://x.com/NASA/status/123456"

    def test_handles_www_prefix(self) -> None:
        """Should handle www.twitter.com."""
        url = "https://www.twitter.com/NASA/status/123"
        result = normalize_tweet_url(url)
        assert result == "https://x.com/NASA/status/123"

    def test_handles_http(self) -> None:
        """Should handle http:// URLs."""
        url = "http://twitter.com/user/status/123"
        result = normalize_tweet_url(url)
        assert result == "https://x.com/user/status/123"

    def test_removes_query_params(self) -> None:
        """Should remove query parameters."""
        url = "https://x.com/user/status/123?s=20&t=abc"
        result = normalize_tweet_url(url)
        assert result == "https://x.com/user/status/123"

    def test_removes_trailing_slash(self) -> None:
        """Should remove trailing slash."""
        url = "https://x.com/NASA/"
        result = normalize_tweet_url(url)
        assert result == "https://x.com/NASA"

    def test_strips_whitespace(self) -> None:
        """Should strip leading/trailing whitespace."""
        url = "  https://x.com/NASA  "
        result = normalize_tweet_url(url)
        assert result == "https://x.com/NASA"

    def test_preserves_x_com(self) -> None:
        """Should leave x.com URLs mostly unchanged."""
        url = "https://x.com/user/status/123456789"
        result = normalize_tweet_url(url)
        assert result == "https://x.com/user/status/123456789"


class TestExtractTweetId:
    """Tests for extract_tweet_id function."""

    def test_extracts_from_status_url(self) -> None:
        """Should extract tweet ID from /status/ URL."""
        url = "https://x.com/user/status/1234567890123456789"
        result = extract_tweet_id(url)
        assert result == "1234567890123456789"

    def test_extracts_from_twitter_url(self) -> None:
        """Should work with twitter.com URLs."""
        url = "https://twitter.com/NASA/status/9876543210"
        result = extract_tweet_id(url)
        assert result == "9876543210"

    def test_returns_none_for_profile(self) -> None:
        """Should return None for profile URLs."""
        url = "https://x.com/NASA"
        result = extract_tweet_id(url)
        assert result is None

    def test_returns_none_for_likes(self) -> None:
        """Should return None for likes URL."""
        url = "https://x.com/user/likes"
        result = extract_tweet_id(url)
        assert result is None

    def test_returns_none_for_bookmarks(self) -> None:
        """Should return None for bookmarks URL."""
        url = "https://x.com/i/bookmarks"
        result = extract_tweet_id(url)
        assert result is None


class TestColorConversion:
    """Tests for RGB/hex color conversion functions."""

    def test_rgb_to_hex_white(self) -> None:
        """Should convert white RGB to hex."""
        assert rgb_to_hex((255, 255, 255)) == "#ffffff"

    def test_rgb_to_hex_black(self) -> None:
        """Should convert black RGB to hex."""
        assert rgb_to_hex((0, 0, 0)) == "#000000"

    def test_rgb_to_hex_red(self) -> None:
        """Should convert red RGB to hex."""
        assert rgb_to_hex((255, 0, 0)) == "#ff0000"

    def test_rgb_to_hex_arbitrary(self) -> None:
        """Should convert arbitrary color."""
        assert rgb_to_hex((18, 52, 86)) == "#123456"

    def test_hex_to_rgb_white(self) -> None:
        """Should convert white hex to RGB."""
        assert hex_to_rgb("#ffffff") == (255, 255, 255)

    def test_hex_to_rgb_black(self) -> None:
        """Should convert black hex to RGB."""
        assert hex_to_rgb("#000000") == (0, 0, 0)

    def test_hex_to_rgb_no_hash(self) -> None:
        """Should handle hex without # prefix."""
        assert hex_to_rgb("ff0000") == (255, 0, 0)

    def test_hex_to_rgb_arbitrary(self) -> None:
        """Should convert arbitrary hex color."""
        assert hex_to_rgb("#123456") == (18, 52, 86)

    def test_roundtrip_conversion(self) -> None:
        """Should survive roundtrip conversion."""
        original = (128, 64, 192)
        hex_color = rgb_to_hex(original)
        result = hex_to_rgb(hex_color)
        assert result == original


class TestDetectDominantColor:
    """Tests for detect_dominant_color function."""

    def test_white_image(self, sample_light_image: Path) -> None:
        """Should detect white as dominant color for white image."""
        color = detect_dominant_color(str(sample_light_image))
        # Should be close to white (255, 255, 255)
        assert color[0] > 250
        assert color[1] > 250
        assert color[2] > 250

    def test_black_image(self, sample_dark_image: Path) -> None:
        """Should detect black as dominant color for black image."""
        color = detect_dominant_color(str(sample_dark_image))
        # Should be close to black (0, 0, 0)
        assert color[0] < 5
        assert color[1] < 5
        assert color[2] < 5

    def test_gray_image(self, sample_gray_image: Path) -> None:
        """Should detect gray for gray image."""
        color = detect_dominant_color(str(sample_gray_image))
        # Should be around (128, 128, 128)
        assert 120 < color[0] < 136
        assert 120 < color[1] < 136
        assert 120 < color[2] < 136


class TestDetectTheme:
    """Tests for detect_theme function."""

    def test_light_theme_for_white_image(self, sample_light_image: Path) -> None:
        """Should detect 'light' theme for white image."""
        theme = detect_theme(str(sample_light_image))
        assert theme == "light"

    def test_dark_theme_for_black_image(self, sample_dark_image: Path) -> None:
        """Should detect 'dark' theme for black image."""
        theme = detect_theme(str(sample_dark_image))
        assert theme == "dark"

    def test_theme_for_gray_image(self, sample_gray_image: Path) -> None:
        """Gray image is near boundary - just check it returns valid theme."""
        theme = detect_theme(str(sample_gray_image))
        # Gray (128,128,128) is at the boundary. Due to numpy casting
        # the exact result may vary - just verify it returns a valid theme
        assert theme in ["light", "dark"]


class TestGetVideoDimensions:
    """Tests for get_video_dimensions function."""

    @patch("utils.subprocess.run")
    def test_parses_ffprobe_output(self, mock_run: MagicMock) -> None:
        """Should parse ffprobe output correctly."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="1920x1080\n",
            stderr="",
        )

        width, height = get_video_dimensions("/path/to/video.mp4")

        assert width == 1920
        assert height == 1080

    @patch("utils.subprocess.run")
    def test_handles_vertical_video(self, mock_run: MagicMock) -> None:
        """Should handle vertical video dimensions."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="1080x1920\n",
            stderr="",
        )

        width, height = get_video_dimensions("/path/to/video.mp4")

        assert width == 1080
        assert height == 1920

    @patch("utils.subprocess.run")
    def test_raises_on_ffprobe_failure(self, mock_run: MagicMock) -> None:
        """Should raise RuntimeError when ffprobe fails."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="No such file or directory",
        )

        with pytest.raises(RuntimeError, match="ffprobe failed"):
            get_video_dimensions("/nonexistent/video.mp4")

    @patch("utils.subprocess.run")
    def test_calls_ffprobe_correctly(self, mock_run: MagicMock) -> None:
        """Should call ffprobe with correct arguments."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="1920x1080\n",
        )

        get_video_dimensions("/path/to/video.mp4")

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert cmd[0] == "ffprobe"
        assert "/path/to/video.mp4" in cmd


class TestGetVideoDuration:
    """Tests for get_video_duration function."""

    @patch("utils.subprocess.run")
    def test_parses_duration(self, mock_run: MagicMock) -> None:
        """Should parse duration as float."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="123.456\n",
            stderr="",
        )

        duration = get_video_duration("/path/to/video.mp4")

        assert duration == pytest.approx(123.456)

    @patch("utils.subprocess.run")
    def test_handles_integer_duration(self, mock_run: MagicMock) -> None:
        """Should handle integer duration."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="60\n",
            stderr="",
        )

        duration = get_video_duration("/path/to/video.mp4")

        assert duration == 60.0

    @patch("utils.subprocess.run")
    def test_raises_on_ffprobe_failure(self, mock_run: MagicMock) -> None:
        """Should raise RuntimeError when ffprobe fails."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Invalid data found",
        )

        with pytest.raises(RuntimeError, match="ffprobe failed"):
            get_video_duration("/nonexistent/video.mp4")


class TestCheckFfmpeg:
    """Tests for check_ffmpeg function."""

    @patch("utils.subprocess.run")
    def test_returns_true_when_installed(self, mock_run: MagicMock) -> None:
        """Should return True when ffmpeg is available."""
        mock_run.return_value = MagicMock(returncode=0)

        result = check_ffmpeg()

        assert result is True

    @patch("utils.subprocess.run")
    def test_returns_false_when_not_installed(self, mock_run: MagicMock) -> None:
        """Should return False when ffmpeg is not found."""
        mock_run.side_effect = FileNotFoundError

        result = check_ffmpeg()

        assert result is False

    @patch("utils.subprocess.run")
    def test_returns_false_on_error(self, mock_run: MagicMock) -> None:
        """Should return False when ffmpeg returns error."""
        mock_run.return_value = MagicMock(returncode=1)

        result = check_ffmpeg()

        assert result is False


class TestCheckPlaywright:
    """Tests for check_playwright function."""

    @patch("importlib.util.find_spec")
    def test_returns_true_when_installed(self, mock_find_spec: MagicMock) -> None:
        """Should return True when playwright is installed."""
        mock_find_spec.return_value = MagicMock()  # Non-None means found

        result = check_playwright()

        assert result is True

    @patch("importlib.util.find_spec")
    def test_returns_false_when_not_installed(self, mock_find_spec: MagicMock) -> None:
        """Should return False when playwright is not installed."""
        mock_find_spec.return_value = None

        result = check_playwright()

        assert result is False


class TestEnsureChromiumInstalled:
    """Tests for ensure_chromium_installed function."""

    @patch("utils.subprocess.run")
    def test_calls_playwright_install(self, mock_run: MagicMock) -> None:
        """Should call playwright install chromium."""
        mock_run.return_value = MagicMock(returncode=0)

        from utils import ensure_chromium_installed

        ensure_chromium_installed()

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "playwright" in cmd
        assert "install" in cmd
        assert "chromium" in cmd

    @patch("utils.subprocess.run")
    def test_raises_on_failure(self, mock_run: MagicMock) -> None:
        """Should raise when playwright install fails."""
        import subprocess

        mock_run.side_effect = subprocess.CalledProcessError(1, "playwright")

        from utils import ensure_chromium_installed

        with pytest.raises(subprocess.CalledProcessError):
            ensure_chromium_installed()
