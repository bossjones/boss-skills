"""Tests for compose_video.py script."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from compose_video import (
    compose_video,
    compose_with_ffmpeg,
    create_reel_canvas,
)
from PIL import Image
from utils import REEL_HEIGHT, REEL_WIDTH


class TestCreateReelCanvas:
    """Tests for create_reel_canvas function."""

    def test_returns_correct_dimensions(self, sample_tweet_screenshot: Path) -> None:
        """Canvas should always be 1080x1920."""
        canvas, metadata = create_reel_canvas(str(sample_tweet_screenshot))

        assert canvas.size == (REEL_WIDTH, REEL_HEIGHT)
        assert canvas.size == (1080, 1920)

    def test_light_theme_white_background(self, sample_light_image: Path) -> None:
        """Light theme should use white background."""
        canvas, metadata = create_reel_canvas(str(sample_light_image), theme="light")

        assert metadata["theme"] == "light"
        assert metadata["background_color"] == (255, 255, 255)

        # Check corner pixel is white
        pixel = canvas.getpixel((0, 0))
        assert pixel == (255, 255, 255)

    def test_dark_theme_black_background(self, sample_dark_image: Path) -> None:
        """Dark theme should use black background."""
        canvas, metadata = create_reel_canvas(str(sample_dark_image), theme="dark")

        assert metadata["theme"] == "dark"
        assert metadata["background_color"] == (0, 0, 0)

        # Check corner pixel is black
        pixel = canvas.getpixel((0, 0))
        assert pixel == (0, 0, 0)

    def test_auto_theme_detects_light(self, sample_light_image: Path) -> None:
        """Auto theme should detect light from white image."""
        canvas, metadata = create_reel_canvas(str(sample_light_image), theme="auto")

        assert metadata["theme"] == "light"

    def test_auto_theme_detects_dark(self, sample_dark_image: Path) -> None:
        """Auto theme should detect dark from black image."""
        canvas, metadata = create_reel_canvas(str(sample_dark_image), theme="auto")

        assert metadata["theme"] == "dark"

    def test_position_top(self, sample_tweet_screenshot: Path) -> None:
        """Screenshot should be at top with position='top'."""
        canvas, metadata = create_reel_canvas(
            str(sample_tweet_screenshot), position="top", padding=40
        )

        bounds = metadata["screenshot_bounds"]
        # Should be near top (y close to padding)
        assert bounds["y"] == 40

    def test_position_center(self, sample_tweet_screenshot: Path) -> None:
        """Screenshot should be centered with position='center'."""
        canvas, metadata = create_reel_canvas(str(sample_tweet_screenshot), position="center")

        bounds = metadata["screenshot_bounds"]
        # Should be roughly centered
        expected_y = (REEL_HEIGHT - bounds["height"]) // 2
        assert bounds["y"] == expected_y

    def test_position_bottom(self, sample_tweet_screenshot: Path) -> None:
        """Screenshot should be at bottom with position='bottom'."""
        canvas, metadata = create_reel_canvas(
            str(sample_tweet_screenshot), position="bottom", padding=40
        )

        bounds = metadata["screenshot_bounds"]
        # Should be near bottom
        expected_y = REEL_HEIGHT - bounds["height"] - 40
        assert bounds["y"] == expected_y

    def test_video_area_calculated(self, sample_tweet_screenshot: Path) -> None:
        """Should calculate video area below screenshot for top position."""
        canvas, metadata = create_reel_canvas(
            str(sample_tweet_screenshot), position="top", padding=40
        )

        video_area = metadata["video_area"]
        screenshot_bounds = metadata["screenshot_bounds"]

        # Video area should be below screenshot
        assert video_area["y"] > screenshot_bounds["y"] + screenshot_bounds["height"]
        assert video_area["width"] == REEL_WIDTH - (40 * 2)
        assert video_area["height"] >= 400  # Minimum height

    def test_padding_respected(self, sample_tweet_screenshot: Path) -> None:
        """Padding should be respected in layout."""
        padding = 60
        canvas, metadata = create_reel_canvas(
            str(sample_tweet_screenshot), padding=padding, position="top"
        )

        bounds = metadata["screenshot_bounds"]
        video_area = metadata["video_area"]

        # X should be centered (canvas width - screenshot width) / 2
        # But screenshot should have padding on sides
        assert bounds["x"] >= 0
        assert video_area["x"] == padding

    def test_screenshot_scaled_to_fit(self, tmp_path: Path) -> None:
        """Wide screenshots should be scaled to fit canvas width."""
        # Create a wide image
        wide_img = Image.new("RGB", (1000, 200), color=(255, 255, 255))
        wide_path = tmp_path / "wide.png"
        wide_img.save(wide_path)

        canvas, metadata = create_reel_canvas(str(wide_path), padding=40)

        bounds = metadata["screenshot_bounds"]
        # Width should be scaled to fit: 1080 - (40 * 2) = 1000
        assert bounds["width"] == 1000

    def test_returns_image_object(self, sample_tweet_screenshot: Path) -> None:
        """Should return PIL Image object."""
        canvas, _ = create_reel_canvas(str(sample_tweet_screenshot))

        assert isinstance(canvas, Image.Image)
        assert canvas.mode == "RGB"

    def test_metadata_structure(self, sample_tweet_screenshot: Path) -> None:
        """Metadata should have expected structure."""
        _, metadata = create_reel_canvas(str(sample_tweet_screenshot))

        assert "theme" in metadata
        assert "background_color" in metadata
        assert "screenshot_bounds" in metadata
        assert "video_area" in metadata

        # Check nested structure
        assert "x" in metadata["screenshot_bounds"]
        assert "y" in metadata["screenshot_bounds"]
        assert "width" in metadata["screenshot_bounds"]
        assert "height" in metadata["screenshot_bounds"]

        assert "x" in metadata["video_area"]
        assert "y" in metadata["video_area"]
        assert "width" in metadata["video_area"]
        assert "height" in metadata["video_area"]


class TestComposeWithFfmpeg:
    """Tests for compose_with_ffmpeg function."""

    @patch("compose_video.subprocess.run")
    @patch("compose_video.get_video_duration")
    @patch("compose_video.get_video_dimensions")
    def test_calls_ffmpeg(
        self,
        mock_dims: MagicMock,
        mock_dur: MagicMock,
        mock_run: MagicMock,
        sample_tweet_screenshot: Path,
        sample_video_file: Path,
        tmp_path: Path,
    ) -> None:
        """Should call ffmpeg with correct arguments."""
        mock_dims.return_value = (1920, 1080)
        mock_dur.return_value = 30.0
        mock_run.return_value = MagicMock(returncode=0)

        output_path = str(tmp_path / "output.mp4")
        video_area = {"x": 40, "y": 500, "width": 1000, "height": 800}

        compose_with_ffmpeg(
            canvas_path=str(sample_tweet_screenshot),
            video_path=str(sample_video_file),
            output_path=output_path,
            video_area=video_area,
            background_color=(255, 255, 255),
        )

        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]

        assert cmd[0] == "ffmpeg"
        assert "-y" in cmd  # Overwrite
        assert "-i" in cmd  # Input flag
        assert "-filter_complex" in cmd
        assert output_path in cmd

    @patch("compose_video.subprocess.run")
    @patch("compose_video.get_video_duration")
    @patch("compose_video.get_video_dimensions")
    def test_uses_libx264(
        self,
        mock_dims: MagicMock,
        mock_dur: MagicMock,
        mock_run: MagicMock,
        sample_tweet_screenshot: Path,
        sample_video_file: Path,
        tmp_path: Path,
    ) -> None:
        """Should encode with H.264 codec."""
        mock_dims.return_value = (1920, 1080)
        mock_dur.return_value = 30.0
        mock_run.return_value = MagicMock(returncode=0)

        output_path = str(tmp_path / "output.mp4")
        video_area = {"x": 40, "y": 500, "width": 1000, "height": 800}

        compose_with_ffmpeg(
            canvas_path=str(sample_tweet_screenshot),
            video_path=str(sample_video_file),
            output_path=output_path,
            video_area=video_area,
            background_color=(0, 0, 0),
        )

        cmd = mock_run.call_args[0][0]
        assert "libx264" in cmd

    @patch("compose_video.subprocess.run")
    @patch("compose_video.get_video_duration")
    @patch("compose_video.get_video_dimensions")
    def test_respects_duration_limit(
        self,
        mock_dims: MagicMock,
        mock_dur: MagicMock,
        mock_run: MagicMock,
        sample_tweet_screenshot: Path,
        sample_video_file: Path,
        tmp_path: Path,
    ) -> None:
        """Should respect duration limit if specified."""
        mock_dims.return_value = (1920, 1080)
        mock_dur.return_value = 60.0  # Original is 60s
        mock_run.return_value = MagicMock(returncode=0)

        output_path = str(tmp_path / "output.mp4")
        video_area = {"x": 40, "y": 500, "width": 1000, "height": 800}

        compose_with_ffmpeg(
            canvas_path=str(sample_tweet_screenshot),
            video_path=str(sample_video_file),
            output_path=output_path,
            video_area=video_area,
            background_color=(0, 0, 0),
            duration=30.0,  # Limit to 30s
        )

        cmd = mock_run.call_args[0][0]
        # Should have -t flag with limited duration
        t_idx = cmd.index("-t")
        assert cmd[t_idx + 1] == "30.0"

    @patch("compose_video.subprocess.run")
    @patch("compose_video.get_video_duration")
    @patch("compose_video.get_video_dimensions")
    def test_raises_on_ffmpeg_failure(
        self,
        mock_dims: MagicMock,
        mock_dur: MagicMock,
        mock_run: MagicMock,
        sample_tweet_screenshot: Path,
        sample_video_file: Path,
        tmp_path: Path,
    ) -> None:
        """Should raise RuntimeError when FFmpeg fails."""
        mock_dims.return_value = (1920, 1080)
        mock_dur.return_value = 30.0
        mock_run.return_value = MagicMock(returncode=1, stderr="Encoding error")

        output_path = str(tmp_path / "output.mp4")
        video_area = {"x": 40, "y": 500, "width": 1000, "height": 800}

        with pytest.raises(RuntimeError, match="FFmpeg composition failed"):
            compose_with_ffmpeg(
                canvas_path=str(sample_tweet_screenshot),
                video_path=str(sample_video_file),
                output_path=output_path,
                video_area=video_area,
                background_color=(0, 0, 0),
            )

    @patch("compose_video.subprocess.run")
    @patch("compose_video.get_video_duration")
    @patch("compose_video.get_video_dimensions")
    def test_handles_vertical_video(
        self,
        mock_dims: MagicMock,
        mock_dur: MagicMock,
        mock_run: MagicMock,
        sample_tweet_screenshot: Path,
        sample_video_file: Path,
        tmp_path: Path,
    ) -> None:
        """Should handle vertical video (taller than wide)."""
        mock_dims.return_value = (1080, 1920)  # Vertical
        mock_dur.return_value = 30.0
        mock_run.return_value = MagicMock(returncode=0)

        output_path = str(tmp_path / "output.mp4")
        video_area = {"x": 40, "y": 500, "width": 1000, "height": 800}

        # Should not raise
        compose_with_ffmpeg(
            canvas_path=str(sample_tweet_screenshot),
            video_path=str(sample_video_file),
            output_path=output_path,
            video_area=video_area,
            background_color=(0, 0, 0),
        )

        mock_run.assert_called_once()


class TestComposeVideo:
    """Tests for compose_video main function."""

    @patch("compose_video.check_ffmpeg")
    def test_raises_if_no_ffmpeg(
        self,
        mock_check: MagicMock,
        sample_tweet_screenshot: Path,
        sample_video_file: Path,
        tmp_path: Path,
    ) -> None:
        """Should raise RuntimeError if FFmpeg not available."""
        mock_check.return_value = False

        with pytest.raises(RuntimeError, match="FFmpeg is required"):
            compose_video(
                screenshot_path=str(sample_tweet_screenshot),
                video_path=str(sample_video_file),
                output_path=str(tmp_path / "output.mp4"),
            )

    @patch("compose_video.check_ffmpeg")
    def test_raises_if_screenshot_missing(
        self, mock_check: MagicMock, sample_video_file: Path, tmp_path: Path
    ) -> None:
        """Should raise FileNotFoundError for missing screenshot."""
        mock_check.return_value = True

        with pytest.raises(FileNotFoundError, match="Screenshot not found"):
            compose_video(
                screenshot_path="/nonexistent/screenshot.png",
                video_path=str(sample_video_file),
                output_path=str(tmp_path / "output.mp4"),
            )

    @patch("compose_video.check_ffmpeg")
    def test_raises_if_video_missing(
        self, mock_check: MagicMock, sample_tweet_screenshot: Path, tmp_path: Path
    ) -> None:
        """Should raise FileNotFoundError for missing video."""
        mock_check.return_value = True

        with pytest.raises(FileNotFoundError, match="Video not found"):
            compose_video(
                screenshot_path=str(sample_tweet_screenshot),
                video_path="/nonexistent/video.mp4",
                output_path=str(tmp_path / "output.mp4"),
            )

    @patch("compose_video.compose_with_ffmpeg")
    @patch("compose_video.check_ffmpeg")
    def test_creates_output_directory(
        self,
        mock_check: MagicMock,
        mock_compose: MagicMock,
        sample_tweet_screenshot: Path,
        sample_video_file: Path,
        tmp_path: Path,
    ) -> None:
        """Should create output directory if it doesn't exist."""
        mock_check.return_value = True
        mock_compose.return_value = None

        output_dir = tmp_path / "new" / "nested" / "dir"
        output_path = output_dir / "output.mp4"

        compose_video(
            screenshot_path=str(sample_tweet_screenshot),
            video_path=str(sample_video_file),
            output_path=str(output_path),
        )

        assert output_dir.exists()


class TestTypedDicts:
    """Tests for TypedDict definitions."""

    def test_video_area_keys(self) -> None:
        """VideoArea should have x, y, width, height."""
        from compose_video import VideoArea

        # TypedDict is just for type hints, we test by creating an instance
        area: VideoArea = {"x": 0, "y": 0, "width": 100, "height": 100}
        assert area["x"] == 0
        assert area["y"] == 0
        assert area["width"] == 100
        assert area["height"] == 100

    def test_screenshot_bounds_keys(self) -> None:
        """ScreenshotBounds should have x, y, width, height."""
        from compose_video import ScreenshotBounds

        bounds: ScreenshotBounds = {"x": 10, "y": 20, "width": 550, "height": 400}
        assert bounds["x"] == 10
        assert bounds["y"] == 20
        assert bounds["width"] == 550
        assert bounds["height"] == 400

    def test_metadata_keys(self) -> None:
        """Metadata should have theme, background_color, screenshot_bounds, video_area."""
        from compose_video import Metadata, ScreenshotBounds, VideoArea

        screenshot_bounds: ScreenshotBounds = {
            "x": 0,
            "y": 0,
            "width": 100,
            "height": 100,
        }
        video_area: VideoArea = {"x": 0, "y": 100, "width": 100, "height": 200}

        metadata: Metadata = {
            "theme": "light",
            "background_color": (255, 255, 255),
            "screenshot_bounds": screenshot_bounds,
            "video_area": video_area,
        }

        assert metadata["theme"] == "light"
        assert metadata["background_color"] == (255, 255, 255)
