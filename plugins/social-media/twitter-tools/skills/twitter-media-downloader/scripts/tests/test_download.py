"""Tests for download.py script."""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

from download import (
    build_command,
    build_config,
    download_with_json_output,
    extract_tweet_id,
    normalize_url,
    parse_downloaded_paths,
)


class TestNormalizeUrl:
    """Tests for normalize_url function."""

    def test_converts_twitter_to_x(self) -> None:
        """Should convert twitter.com URLs to x.com."""
        url = "https://twitter.com/NASA/status/123456"
        result = normalize_url(url)
        assert result == "https://x.com/NASA/status/123456"

    def test_removes_trailing_slash(self) -> None:
        """Should remove trailing slashes."""
        url = "https://x.com/NASA/"
        result = normalize_url(url)
        assert result == "https://x.com/NASA"

    def test_removes_multiple_trailing_slashes(self) -> None:
        """Should remove multiple trailing slashes."""
        url = "https://x.com/NASA///"
        result = normalize_url(url)
        assert result == "https://x.com/NASA"

    def test_preserves_path(self) -> None:
        """Should preserve URL path components."""
        url = "https://twitter.com/user/status/987654321"
        result = normalize_url(url)
        assert result == "https://x.com/user/status/987654321"

    def test_strips_whitespace(self) -> None:
        """Should strip leading and trailing whitespace."""
        url = "  https://x.com/NASA  "
        result = normalize_url(url)
        assert result == "https://x.com/NASA"

    def test_handles_www_prefix(self) -> None:
        """Should handle www.twitter.com."""
        url = "https://www.twitter.com/NASA"
        result = normalize_url(url)
        # Note: current impl replaces "twitter.com" only
        assert "x.com" in result


class TestExtractTweetId:
    """Tests for extract_tweet_id function."""

    def test_extracts_from_status_url(self) -> None:
        """Should extract tweet ID from /status/ URL."""
        url = "https://x.com/user/status/1234567890123456789"
        result = extract_tweet_id(url)
        assert result == "1234567890123456789"

    def test_extracts_from_twitter_url(self) -> None:
        """Should work with twitter.com URLs too."""
        url = "https://twitter.com/NASA/status/9876543210"
        result = extract_tweet_id(url)
        assert result == "9876543210"

    def test_returns_none_for_profile_url(self) -> None:
        """Should return None for profile URLs (no status)."""
        url = "https://x.com/NASA"
        result = extract_tweet_id(url)
        assert result is None

    def test_returns_none_for_likes_url(self) -> None:
        """Should return None for likes URL."""
        url = "https://x.com/user/likes"
        result = extract_tweet_id(url)
        assert result is None

    def test_handles_query_params(self) -> None:
        """Should extract ID even with query parameters."""
        url = "https://x.com/user/status/123456?s=20"
        result = extract_tweet_id(url)
        assert result == "123456"


class TestParseDownloadedPaths:
    """Tests for parse_downloaded_paths function."""

    def test_parses_single_path(self, tmp_path: Path) -> None:
        """Should parse a single file path."""
        test_file = tmp_path / "test.jpg"
        test_file.touch()

        stdout = str(test_file)
        result = parse_downloaded_paths(stdout)
        assert result == [str(test_file)]

    def test_parses_multiple_paths(self, tmp_path: Path) -> None:
        """Should parse multiple file paths."""
        file1 = tmp_path / "image1.jpg"
        file2 = tmp_path / "image2.png"
        file1.touch()
        file2.touch()

        stdout = f"{file1}\n{file2}"
        result = parse_downloaded_paths(stdout)
        assert result == [str(file1), str(file2)]

    def test_filters_nonexistent_paths(self, tmp_path: Path) -> None:
        """Should filter out paths that don't exist."""
        existing = tmp_path / "exists.jpg"
        existing.touch()

        stdout = f"{existing}\n/nonexistent/path/file.jpg"
        result = parse_downloaded_paths(stdout)
        assert result == [str(existing)]

    def test_handles_empty_output(self) -> None:
        """Should return empty list for empty output."""
        result = parse_downloaded_paths("")
        assert result == []

    def test_handles_whitespace_lines(self, tmp_path: Path) -> None:
        """Should ignore empty lines and whitespace."""
        test_file = tmp_path / "test.jpg"
        test_file.touch()

        stdout = f"\n  \n{test_file}\n  \n"
        result = parse_downloaded_paths(stdout)
        assert result == [str(test_file)]


class TestBuildConfig:
    """Tests for build_config function."""

    def create_args(self, **kwargs: Any) -> argparse.Namespace:
        """Create a mock args namespace with defaults."""
        defaults = {
            "url": "https://x.com/user/status/123",
            "output": "./downloads",
            "cookies": None,
            "browser": None,
            "videos_only": False,
            "images_only": False,
            "limit": None,
            "retweets": False,
            "replies": False,
            "sleep": None,
            "rate_limit": None,
            "verbose": False,
            "simulate": False,
            "get_urls": False,
            "json": False,
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def test_basic_config_structure(self) -> None:
        """Should create config with expected structure."""
        args = self.create_args()
        config = build_config(args)

        assert "extractor" in config
        assert "twitter" in config["extractor"]
        assert "downloader" in config
        assert "output" in config

    def test_retweets_setting(self) -> None:
        """Should set retweets based on args."""
        args_no = self.create_args(retweets=False)
        args_yes = self.create_args(retweets=True)

        config_no = build_config(args_no)
        config_yes = build_config(args_yes)

        assert config_no["extractor"]["twitter"]["retweets"] is False
        assert config_yes["extractor"]["twitter"]["retweets"] is True

    def test_replies_setting(self) -> None:
        """Should set replies based on args."""
        args_no = self.create_args(replies=False)
        args_yes = self.create_args(replies=True)

        config_no = build_config(args_no)
        config_yes = build_config(args_yes)

        assert config_no["extractor"]["twitter"]["replies"] is False
        assert config_yes["extractor"]["twitter"]["replies"] is True

    def test_images_only_disables_videos(self) -> None:
        """Should disable videos when images_only is set."""
        args = self.create_args(images_only=True)
        config = build_config(args)

        assert config["extractor"]["twitter"]["videos"] is False

    def test_sleep_setting(self) -> None:
        """Should set sleep intervals when specified."""
        args = self.create_args(sleep=2.5)
        config = build_config(args)

        assert config["extractor"]["twitter"]["sleep"] == 2.5
        assert config["extractor"]["twitter"]["sleep-request"] == 2.5

    def test_rate_limit_setting(self) -> None:
        """Should set rate limit when specified."""
        args = self.create_args(rate_limit="1M")
        config = build_config(args)

        assert config["downloader"]["rate"] == "1M"


class TestBuildCommand:
    """Tests for build_command function."""

    def create_args(self, **kwargs: Any) -> argparse.Namespace:
        """Create a mock args namespace with defaults."""
        defaults = {
            "url": "https://x.com/user/status/123",
            "output": "./downloads",
            "cookies": None,
            "browser": None,
            "videos_only": False,
            "images_only": False,
            "limit": None,
            "retweets": False,
            "replies": False,
            "sleep": None,
            "rate_limit": None,
            "verbose": False,
            "simulate": False,
            "get_urls": False,
            "json": False,
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    def test_basic_command_structure(self, tmp_path: Path) -> None:
        """Should create command with gallery-dl and essential args."""
        args = self.create_args(output=str(tmp_path))
        config_file = str(tmp_path / "config.json")

        cmd = build_command(args, config_file)

        assert cmd[0] == "gallery-dl"
        assert "-d" in cmd
        assert "-c" in cmd
        assert config_file in cmd

    def test_config_file_optional(self, tmp_path: Path) -> None:
        """Should work without config file (use user's default)."""
        args = self.create_args(output=str(tmp_path))

        cmd = build_command(args, config_file=None)

        assert cmd[0] == "gallery-dl"
        assert "-c" not in cmd

    def test_cookies_option(self, tmp_path: Path) -> None:
        """Should add --cookies when cookies path provided."""
        cookies_file = str(tmp_path / "cookies.txt")
        args = self.create_args(output=str(tmp_path), cookies=cookies_file)
        config_file = str(tmp_path / "config.json")

        cmd = build_command(args, config_file)

        assert "--cookies" in cmd
        assert cookies_file in cmd

    def test_browser_option(self, tmp_path: Path) -> None:
        """Should add --cookies-from-browser when browser specified."""
        args = self.create_args(output=str(tmp_path), browser="firefox")
        config_file = str(tmp_path / "config.json")

        cmd = build_command(args, config_file)

        assert "--cookies-from-browser" in cmd
        assert "firefox" in cmd

    def test_no_filter_in_command(self, tmp_path: Path) -> None:
        """Should NOT add --filter (filtering is done post-download)."""
        args = self.create_args(output=str(tmp_path), videos_only=True)
        config_file = str(tmp_path / "config.json")

        cmd = build_command(args, config_file)

        # We no longer use gallery-dl's --filter as it doesn't work reliably
        assert "--filter" not in cmd

    def test_limit_option(self, tmp_path: Path) -> None:
        """Should add --range when limit specified."""
        args = self.create_args(output=str(tmp_path), limit=50)
        config_file = str(tmp_path / "config.json")

        cmd = build_command(args, config_file)

        assert "--range" in cmd
        assert "1-50" in cmd

    def test_verbose_option(self, tmp_path: Path) -> None:
        """Should add -v when verbose is True."""
        args = self.create_args(output=str(tmp_path), verbose=True)
        config_file = str(tmp_path / "config.json")

        cmd = build_command(args, config_file)

        assert "-v" in cmd

    def test_simulate_option(self, tmp_path: Path) -> None:
        """Should add -s when simulate is True."""
        args = self.create_args(output=str(tmp_path), simulate=True)
        config_file = str(tmp_path / "config.json")

        cmd = build_command(args, config_file)

        assert "-s" in cmd

    def test_get_urls_option(self, tmp_path: Path) -> None:
        """Should add -g when get_urls is True."""
        args = self.create_args(output=str(tmp_path), get_urls=True)
        config_file = str(tmp_path / "config.json")

        cmd = build_command(args, config_file)

        assert "-g" in cmd

    def test_url_is_normalized(self, tmp_path: Path) -> None:
        """Should normalize URL in command."""
        args = self.create_args(
            url="https://twitter.com/user/status/123",
            output=str(tmp_path),
        )
        config_file = str(tmp_path / "config.json")

        cmd = build_command(args, config_file)

        # URL should be last argument
        assert cmd[-1] == "https://x.com/user/status/123"


class TestDownloadWithJsonOutput:
    """Tests for download_with_json_output function."""

    def create_args(self, **kwargs: Any) -> argparse.Namespace:
        """Create a mock args namespace with defaults."""
        defaults = {
            "url": "https://x.com/user/status/123",
            "output": "./downloads",
            "cookies": None,
            "browser": None,
            "videos_only": False,
            "images_only": False,
            "limit": None,
            "retweets": False,
            "replies": False,
            "sleep": None,
            "rate_limit": None,
            "verbose": False,
            "simulate": False,
            "get_urls": False,
            "json": True,
        }
        defaults.update(kwargs)
        return argparse.Namespace(**defaults)

    @patch("download.subprocess.run")
    def test_returns_error_when_gallerydl_missing(self, mock_run: MagicMock) -> None:
        """Should return error when gallery-dl not installed."""
        mock_run.side_effect = FileNotFoundError

        with tempfile.TemporaryDirectory() as tmp_dir:
            args = self.create_args(output=tmp_dir)
            result = download_with_json_output(args)

        assert result["success"] is False
        assert "gallery-dl" in result["error"]

    @patch("download.subprocess.run")
    def test_returns_error_when_gallerydl_fails_version(self, mock_run: MagicMock) -> None:
        """Should return error when gallery-dl version check fails."""
        mock_run.return_value = MagicMock(returncode=1)

        with tempfile.TemporaryDirectory() as tmp_dir:
            args = self.create_args(output=tmp_dir)
            result = download_with_json_output(args)

        assert result["success"] is False
        assert "gallery-dl" in result["error"]

    @patch("download.subprocess.run")
    def test_successful_download(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Should return success with downloaded files."""
        # Create a test file to simulate download
        test_file = tmp_path / "downloaded.jpg"
        test_file.touch()

        # Mock version check success, then download success
        mock_run.side_effect = [
            MagicMock(returncode=0),  # gallery-dl --version
            MagicMock(returncode=0, stdout=str(test_file), stderr=""),  # download
        ]

        args = self.create_args(
            url="https://x.com/user/status/123",
            output=str(tmp_path),
        )
        result = download_with_json_output(args)

        assert result["success"] is True
        assert result["files"] == [str(test_file)]
        assert result["tweet_id"] == "123"
        assert result["url"] == "https://x.com/user/status/123"

    @patch("download.subprocess.run")
    def test_download_failure_with_stderr(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Should capture error from stderr on failure."""
        mock_run.side_effect = [
            MagicMock(returncode=0),  # gallery-dl --version
            MagicMock(returncode=1, stdout="", stderr="Network error"),  # download fail
        ]

        args = self.create_args(output=str(tmp_path))
        result = download_with_json_output(args)

        assert result["success"] is False
        assert result["error"] == "Network error"

    @patch("download.subprocess.run")
    def test_extracts_tweet_id(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Should extract and include tweet ID in result."""
        mock_run.side_effect = [
            MagicMock(returncode=0),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]

        args = self.create_args(
            url="https://x.com/NASA/status/9876543210",
            output=str(tmp_path),
        )
        result = download_with_json_output(args)

        assert result["tweet_id"] == "9876543210"

    @patch("download.subprocess.run")
    def test_handles_profile_url_no_tweet_id(self, mock_run: MagicMock, tmp_path: Path) -> None:
        """Should handle profile URLs (no tweet ID)."""
        mock_run.side_effect = [
            MagicMock(returncode=0),
            MagicMock(returncode=0, stdout="", stderr=""),
        ]

        args = self.create_args(
            url="https://x.com/NASA",
            output=str(tmp_path),
        )
        result = download_with_json_output(args)

        assert result["tweet_id"] is None
        assert result["success"] is True


class TestCheckDependencies:
    """Tests for check_dependencies function."""

    @patch("download.subprocess.run")
    @patch("download.sys.exit")
    def test_exits_when_gallerydl_missing(self, mock_exit: MagicMock, mock_run: MagicMock) -> None:
        """Should exit when gallery-dl is not installed."""
        mock_run.side_effect = FileNotFoundError

        from download import check_dependencies

        check_dependencies()

        mock_exit.assert_called_once_with(1)

    @patch("download.subprocess.run")
    @patch("download.sys.exit")
    def test_exits_when_gallerydl_fails(self, mock_exit: MagicMock, mock_run: MagicMock) -> None:
        """Should exit when gallery-dl returns non-zero."""
        mock_run.return_value = MagicMock(returncode=1)

        from download import check_dependencies

        check_dependencies()

        mock_exit.assert_called_once_with(1)

    @patch("download.subprocess.run")
    @patch("download.print")
    def test_warns_when_ytdlp_missing(self, mock_print: MagicMock, mock_run: MagicMock) -> None:
        """Should warn but not exit when yt-dlp is missing."""

        def side_effect(cmd: list[str], **kwargs: Any) -> MagicMock:
            if cmd[0] == "gallery-dl":
                return MagicMock(returncode=0)
            raise FileNotFoundError

        mock_run.side_effect = side_effect

        from download import check_dependencies

        check_dependencies()

        # Should have printed warning about yt-dlp
        warning_calls = [c for c in mock_print.call_args_list if "yt-dlp" in str(c)]
        assert len(warning_calls) > 0

    @patch("download.subprocess.run")
    def test_succeeds_with_all_dependencies(self, mock_run: MagicMock) -> None:
        """Should not exit when all dependencies available."""
        mock_run.return_value = MagicMock(returncode=0)

        from download import check_dependencies

        # Should not raise or exit
        check_dependencies()


class TestFilterFilesByType:
    """Tests for filter_files_by_type function."""

    def test_returns_all_files_when_no_filter(self) -> None:
        """Should return all files when no filter applied."""
        from download import filter_files_by_type

        files = ["/path/to/video.mp4", "/path/to/image.jpg"]
        result = filter_files_by_type(files, videos_only=False, images_only=False)
        assert result == files

    def test_filters_videos_only(self) -> None:
        """Should return only video files when videos_only is True."""
        from download import filter_files_by_type

        files = ["/path/to/video.mp4", "/path/to/image.jpg", "/path/to/clip.webm"]
        result = filter_files_by_type(files, videos_only=True, images_only=False)
        assert result == ["/path/to/video.mp4", "/path/to/clip.webm"]

    def test_filters_images_only(self) -> None:
        """Should return only image files when images_only is True."""
        from download import filter_files_by_type

        files = ["/path/to/video.mp4", "/path/to/photo.png", "/path/to/pic.jpeg"]
        result = filter_files_by_type(files, videos_only=False, images_only=True)
        assert result == ["/path/to/photo.png", "/path/to/pic.jpeg"]

    def test_handles_empty_list(self) -> None:
        """Should handle empty file list."""
        from download import filter_files_by_type

        result = filter_files_by_type([], videos_only=True)
        assert result == []

    def test_case_insensitive_extensions(self) -> None:
        """Should handle mixed case extensions."""
        from download import filter_files_by_type

        files = ["/path/to/VIDEO.MP4", "/path/to/image.JPG"]
        result = filter_files_by_type(files, videos_only=True)
        assert result == ["/path/to/VIDEO.MP4"]


class TestFindDownloadedFiles:
    """Tests for find_downloaded_files function."""

    def test_finds_video_files(self, tmp_path: Path) -> None:
        """Should find video files in directory."""
        from download import find_downloaded_files

        (tmp_path / "video.mp4").touch()
        (tmp_path / "image.jpg").touch()

        result = find_downloaded_files(tmp_path, videos_only=True)
        assert len(result) == 1
        assert result[0].endswith("video.mp4")

    def test_finds_image_files(self, tmp_path: Path) -> None:
        """Should find image files in directory."""
        from download import find_downloaded_files

        (tmp_path / "video.mp4").touch()
        (tmp_path / "image.jpg").touch()
        (tmp_path / "photo.png").touch()

        result = find_downloaded_files(tmp_path, images_only=True)
        assert len(result) == 2

    def test_finds_all_media_by_default(self, tmp_path: Path) -> None:
        """Should find all media files when no filter specified."""
        from download import find_downloaded_files

        (tmp_path / "video.mp4").touch()
        (tmp_path / "image.jpg").touch()

        result = find_downloaded_files(tmp_path)
        assert len(result) == 2

    def test_searches_subdirectories(self, tmp_path: Path) -> None:
        """Should search recursively in subdirectories."""
        from download import find_downloaded_files

        subdir = tmp_path / "twitter" / "user"
        subdir.mkdir(parents=True)
        (subdir / "video.mp4").touch()

        result = find_downloaded_files(tmp_path, videos_only=True)
        assert len(result) == 1
        assert "video.mp4" in result[0]

    def test_handles_nonexistent_directory(self) -> None:
        """Should return empty list for nonexistent directory."""
        from download import find_downloaded_files

        result = find_downloaded_files(Path("/nonexistent/path"))
        assert result == []

    def test_ignores_non_media_files(self, tmp_path: Path) -> None:
        """Should ignore non-media files."""
        from download import find_downloaded_files

        (tmp_path / "video.mp4").touch()
        (tmp_path / "readme.txt").touch()
        (tmp_path / "data.json").touch()

        result = find_downloaded_files(tmp_path)
        assert len(result) == 1
