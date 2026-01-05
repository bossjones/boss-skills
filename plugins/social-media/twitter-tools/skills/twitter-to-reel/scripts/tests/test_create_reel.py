"""Tests for create_reel.py main script."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from create_reel import (
    download_video_from_tweet,
    find_video_file,
)


class TestFindVideoFile:
    """Tests for find_video_file function."""

    def test_returns_direct_path(self, sample_video_file: Path) -> None:
        """Should return path if it's a direct file path."""
        result = find_video_file(str(sample_video_file))
        assert result == str(sample_video_file)

    def test_finds_with_glob_pattern(self, tmp_path: Path) -> None:
        """Should find video with glob pattern."""
        video1 = tmp_path / "video1.mp4"
        video1.touch()

        pattern = str(tmp_path / "*.mp4")
        result = find_video_file(pattern)

        assert result == str(video1)

    def test_finds_first_of_multiple(self, tmp_path: Path) -> None:
        """Should return first video when multiple match."""
        video1 = tmp_path / "aaa_video.mp4"
        video2 = tmp_path / "bbb_video.mp4"
        video1.touch()
        video2.touch()

        pattern = str(tmp_path / "*.mp4")
        result = find_video_file(pattern)

        # Should return one of them (order may vary)
        assert result in [str(video1), str(video2)]

    def test_raises_for_no_match(self, tmp_path: Path) -> None:
        """Should raise FileNotFoundError when no videos match."""
        pattern = str(tmp_path / "*.mp4")

        with pytest.raises(FileNotFoundError, match="No video files found"):
            find_video_file(pattern)

    def test_filters_non_video_extensions(self, tmp_path: Path) -> None:
        """Should only return video file extensions."""
        txt_file = tmp_path / "file.txt"
        jpg_file = tmp_path / "image.jpg"
        txt_file.touch()
        jpg_file.touch()

        pattern = str(tmp_path / "*")

        with pytest.raises(FileNotFoundError, match="No video files found"):
            find_video_file(pattern)

    def test_accepts_various_video_extensions(self, tmp_path: Path) -> None:
        """Should accept various video extensions."""
        extensions = [".mp4", ".mov", ".webm", ".avi", ".mkv", ".m4v"]

        for ext in extensions:
            video = tmp_path / f"video{ext}"
            video.touch()

            result = find_video_file(str(video))
            assert result == str(video)

            video.unlink()


class TestDownloadVideoFromTweet:
    """Tests for download_video_from_tweet function."""

    @staticmethod
    def _setup_downloader_path(tmp_path: Path) -> Path:
        """Create the expected downloader path structure.

        The code does: SCRIPT_DIR.parent.parent / "twitter-media-downloader" / "scripts" / "download.py"
        So if SCRIPT_DIR is tmp_path/skill/scripts, we need downloader at tmp_path/twitter-media-downloader/scripts
        """
        # Create a fake skill structure: tmp_path/twitter-to-reel/scripts/
        scripts_dir = tmp_path / "twitter-to-reel" / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)

        # Create fake downloader at expected location relative to scripts_dir.parent.parent
        # scripts_dir.parent.parent = tmp_path
        downloader_dir = tmp_path / "twitter-media-downloader" / "scripts"
        downloader_dir.mkdir(parents=True, exist_ok=True)
        (downloader_dir / "download.py").touch()

        return scripts_dir

    @patch("subprocess.run")
    def test_calls_downloader_script(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Should call the twitter-media-downloader script."""
        scripts_dir = self._setup_downloader_path(tmp_path)

        # Create a mock video file that would be downloaded
        video_file = tmp_path / "downloaded.mp4"
        video_file.touch()

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"success": True, "files": [str(video_file)]}),
            stderr="",
        )

        with patch("create_reel.SCRIPT_DIR", scripts_dir):
            result = download_video_from_tweet(
                tweet_url="https://x.com/user/status/123",
                output_dir=str(tmp_path),
            )

        assert result == str(video_file)
        mock_run.assert_called_once()

        # Check command includes expected arguments
        cmd = mock_run.call_args[0][0]
        assert "--videos-only" in cmd
        assert "--json" in cmd

    @patch("subprocess.run")
    def test_raises_on_download_failure(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Should raise RuntimeError when download fails."""
        scripts_dir = self._setup_downloader_path(tmp_path)

        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Network error",
        )

        with (
            patch("create_reel.SCRIPT_DIR", scripts_dir),
            pytest.raises(RuntimeError, match="Download failed"),
        ):
            download_video_from_tweet(
                tweet_url="https://x.com/user/status/123",
                output_dir=str(tmp_path),
            )

    @patch("subprocess.run")
    def test_raises_on_no_video_found(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Should raise RuntimeError when no video in tweet."""
        scripts_dir = self._setup_downloader_path(tmp_path)

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"success": True, "files": []}),
            stderr="",
        )

        with (
            patch("create_reel.SCRIPT_DIR", scripts_dir),
            pytest.raises(RuntimeError, match="No video found"),
        ):
            download_video_from_tweet(
                tweet_url="https://x.com/user/status/123",
                output_dir=str(tmp_path),
            )

    @patch("subprocess.run")
    def test_raises_on_json_parse_error(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Should raise RuntimeError on invalid JSON output."""
        scripts_dir = self._setup_downloader_path(tmp_path)

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="not valid json",
            stderr="",
        )

        with (
            patch("create_reel.SCRIPT_DIR", scripts_dir),
            pytest.raises(RuntimeError, match="Failed to parse"),
        ):
            download_video_from_tweet(
                tweet_url="https://x.com/user/status/123",
                output_dir=str(tmp_path),
            )

    @patch("subprocess.run")
    def test_passes_cookies_option(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Should pass cookies path to downloader."""
        scripts_dir = self._setup_downloader_path(tmp_path)

        video_file = tmp_path / "downloaded.mp4"
        video_file.touch()
        cookies_file = tmp_path / "cookies.txt"
        cookies_file.touch()

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"success": True, "files": [str(video_file)]}),
            stderr="",
        )

        with patch("create_reel.SCRIPT_DIR", scripts_dir):
            download_video_from_tweet(
                tweet_url="https://x.com/user/status/123",
                cookies_path=str(cookies_file),
            )

        cmd = mock_run.call_args[0][0]
        assert "--cookies" in cmd
        assert str(cookies_file) in cmd

    @patch("subprocess.run")
    def test_passes_browser_option(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Should pass browser option to downloader."""
        scripts_dir = self._setup_downloader_path(tmp_path)

        video_file = tmp_path / "downloaded.mp4"
        video_file.touch()

        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"success": True, "files": [str(video_file)]}),
            stderr="",
        )

        with patch("create_reel.SCRIPT_DIR", scripts_dir):
            download_video_from_tweet(
                tweet_url="https://x.com/user/status/123",
                browser="firefox",
            )

        cmd = mock_run.call_args[0][0]
        assert "--browser" in cmd
        assert "firefox" in cmd

    def test_raises_if_downloader_not_found(self, tmp_path: Path) -> None:
        """Should raise RuntimeError if downloader script not found."""
        with (
            patch("create_reel.SCRIPT_DIR", tmp_path),
            pytest.raises(RuntimeError, match="twitter-media-downloader not found"),
        ):
            download_video_from_tweet(
                tweet_url="https://x.com/user/status/123",
            )


class TestCreateReel:
    """Tests for create_reel main function."""

    @patch("create_reel.check_ffmpeg")
    def test_raises_without_ffmpeg(self, mock_check: MagicMock) -> None:
        """Should raise RuntimeError if FFmpeg not available."""
        mock_check.return_value = False

        from create_reel import create_reel

        with pytest.raises(RuntimeError, match="FFmpeg is required"):
            create_reel(
                tweet_url="https://x.com/user/status/123",
                video_path="/some/video.mp4",
            )

    @patch("create_reel.check_playwright")
    @patch("create_reel.check_ffmpeg")
    def test_raises_without_playwright(
        self, mock_ffmpeg: MagicMock, mock_playwright: MagicMock
    ) -> None:
        """Should raise RuntimeError if Playwright not available."""
        mock_ffmpeg.return_value = True
        mock_playwright.return_value = False

        from create_reel import create_reel

        with pytest.raises(RuntimeError, match="Playwright is required"):
            create_reel(
                tweet_url="https://x.com/user/status/123",
                video_path="/some/video.mp4",
            )

    @patch("create_reel.check_playwright")
    @patch("create_reel.check_ffmpeg")
    def test_raises_for_invalid_url(
        self, mock_ffmpeg: MagicMock, mock_playwright: MagicMock, tmp_path: Path
    ) -> None:
        """Should raise ValueError for URL without tweet ID."""
        mock_ffmpeg.return_value = True
        mock_playwright.return_value = True

        video = tmp_path / "video.mp4"
        video.touch()

        from create_reel import create_reel

        with pytest.raises(ValueError, match="Invalid tweet URL"):
            create_reel(
                tweet_url="https://x.com/NASA",  # Profile URL
                video_path=str(video),
            )


class TestScreenshotResult:
    """Tests for ScreenshotResult TypedDict."""

    def test_screenshot_result_structure(self) -> None:
        """ScreenshotResult should have expected keys."""
        from create_reel import ScreenshotResult

        result: ScreenshotResult = {
            "path": "/path/to/screenshot.png",
            "width": 590,
            "height": 440,
            "theme": "light",
            "tweet_id": "123456789",
        }

        assert result["path"] == "/path/to/screenshot.png"
        assert result["width"] == 590
        assert result["height"] == 440
        assert result["theme"] == "light"
        assert result["tweet_id"] == "123456789"
