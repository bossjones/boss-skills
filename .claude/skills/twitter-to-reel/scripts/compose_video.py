#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "pillow>=10.0.0",
#     "numpy>=1.24.0",
# ]
# ///
"""
Compose video onto a tweet screenshot for Instagram Reels format.

Takes a tweet screenshot and overlays a video to create a 9:16 vertical video.
"""

import argparse
import contextlib
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image  # pyright: ignore[reportMissingImports]

from .utils import (
    REEL_HEIGHT,
    REEL_WIDTH,
    THEME_COLORS,
    check_ffmpeg,
    detect_theme,
    get_video_dimensions,
    get_video_duration,
    rgb_to_hex,
)


def create_reel_canvas(
    screenshot_path: str,
    theme: str = "auto",
    position: str = "top",
    padding: int = 40,
) -> tuple[Image.Image, dict]:
    """
    Create a 1080x1920 canvas with the tweet screenshot positioned.

    Returns:
        Tuple of (canvas image, metadata dict with video_area info)
    """
    # Load screenshot
    screenshot = Image.open(screenshot_path).convert("RGBA")
    orig_width, orig_height = screenshot.size

    # Detect or use specified theme
    if theme == "auto":
        theme = detect_theme(screenshot_path)

    bg_color = THEME_COLORS[theme]["background"]

    # Calculate scaling to fit width with padding
    max_width = REEL_WIDTH - (padding * 2)
    scale = max_width / orig_width
    new_width = int(orig_width * scale)
    new_height = int(orig_height * scale)

    # Resize screenshot
    screenshot = screenshot.resize((new_width, new_height), Image.Resampling.LANCZOS)

    # Create canvas
    canvas = Image.new("RGB", (REEL_WIDTH, REEL_HEIGHT), bg_color)

    # Calculate position
    x_offset = (REEL_WIDTH - new_width) // 2

    if position == "top":
        y_offset = padding
    elif position == "center":
        y_offset = (REEL_HEIGHT - new_height) // 2
    elif position == "bottom":
        y_offset = REEL_HEIGHT - new_height - padding
    else:
        y_offset = padding

    # Paste screenshot onto canvas
    canvas.paste(
        screenshot, (x_offset, y_offset), screenshot if screenshot.mode == "RGBA" else None
    )

    # Calculate video overlay area
    # We'll place the video below the tweet if at top, or find media area
    if position == "top":
        video_y = y_offset + new_height + padding
        video_height = REEL_HEIGHT - video_y - padding
    else:
        # Place video above the tweet
        video_y = padding
        video_height = y_offset - (padding * 2)

    video_area = {
        "x": padding,
        "y": video_y,
        "width": REEL_WIDTH - (padding * 2),
        "height": max(video_height, 400),  # Minimum height
    }

    metadata = {
        "theme": theme,
        "background_color": bg_color,
        "screenshot_bounds": {
            "x": x_offset,
            "y": y_offset,
            "width": new_width,
            "height": new_height,
        },
        "video_area": video_area,
    }

    return canvas, metadata


def compose_with_ffmpeg(
    canvas_path: str,
    video_path: str,
    output_path: str,
    video_area: dict,
    background_color: tuple[int, int, int],
    duration: float | None = None,
) -> str:
    """
    Use FFmpeg to compose the final video.

    Places the video within the specified area, maintaining aspect ratio.
    """
    # Get video dimensions
    vid_width, vid_height = get_video_dimensions(video_path)
    vid_duration = get_video_duration(video_path)

    if duration:
        vid_duration = min(vid_duration, duration)

    # Calculate video scaling to fit in area while maintaining aspect ratio
    area_width = video_area["width"]
    area_height = video_area["height"]

    vid_aspect = vid_width / vid_height
    area_aspect = area_width / area_height

    if vid_aspect > area_aspect:
        # Video is wider - fit to width
        scale_width = area_width
        scale_height = int(area_width / vid_aspect)
    else:
        # Video is taller - fit to height
        scale_height = area_height
        scale_width = int(area_height * vid_aspect)

    # Ensure even dimensions for video encoding
    scale_width = scale_width - (scale_width % 2)
    scale_height = scale_height - (scale_height % 2)

    # Calculate position to center video in area
    vid_x = video_area["x"] + (area_width - scale_width) // 2
    vid_y = video_area["y"] + (area_height - scale_height) // 2

    # Build FFmpeg command
    bg_hex = rgb_to_hex(background_color)

    # Complex filter for compositing
    filter_complex = (
        # Scale video
        f"[1:v]scale={scale_width}:{scale_height}:force_original_aspect_ratio=decrease,"
        f"pad={scale_width}:{scale_height}:(ow-iw)/2:(oh-ih)/2:color={bg_hex}[scaled];"
        # Loop background image for video duration
        f"[0:v]loop=loop=-1:size=1:start=0,trim=duration={vid_duration},fps=30[bg];"
        # Overlay video on background
        f"[bg][scaled]overlay={vid_x}:{vid_y}:shortest=1[out]"
    )

    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        canvas_path,  # Background image
        "-i",
        video_path,  # Video
        "-filter_complex",
        filter_complex,
        "-map",
        "[out]",
        "-map",
        "1:a?",  # Audio from video (if exists)
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-pix_fmt",
        "yuv420p",
        "-t",
        str(vid_duration),
        "-movflags",
        "+faststart",
        output_path,
    ]

    print("Composing video with FFmpeg...")
    print(f"  Video size: {scale_width}x{scale_height}")
    print(f"  Position: ({vid_x}, {vid_y})")
    print(f"  Duration: {vid_duration:.2f}s")

    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"FFmpeg error: {result.stderr}", file=sys.stderr)
        raise RuntimeError("FFmpeg composition failed")

    return output_path


def compose_video(
    screenshot_path: str,
    video_path: str,
    output_path: str,
    theme: str = "auto",
    position: str = "top",
    padding: int = 40,
    duration: float | None = None,
    keep_temp: bool = False,
) -> str:
    """
    Main function to compose a reel from screenshot and video.
    """
    if not check_ffmpeg():
        raise RuntimeError("FFmpeg is required but not found. Please install FFmpeg.")

    # Validate inputs
    if not Path(screenshot_path).exists():
        raise FileNotFoundError(f"Screenshot not found: {screenshot_path}")
    if not Path(video_path).exists():
        raise FileNotFoundError(f"Video not found: {video_path}")

    # Create canvas
    print(f"Creating {REEL_WIDTH}x{REEL_HEIGHT} canvas...")
    canvas, metadata = create_reel_canvas(
        screenshot_path=screenshot_path,
        theme=theme,
        position=position,
        padding=padding,
    )

    print(f"Theme: {metadata['theme']}")

    # Save canvas to temp file
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        canvas_path = f.name
        canvas.save(canvas_path, "PNG")

    try:
        # Compose with FFmpeg
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        compose_with_ffmpeg(
            canvas_path=canvas_path,
            video_path=video_path,
            output_path=str(output_file),
            video_area=metadata["video_area"],
            background_color=metadata["background_color"],
            duration=duration,
        )

        print(f"Output saved: {output_path}")
        return str(output_file)

    finally:
        # Clean up temp files
        if not keep_temp:
            with contextlib.suppress(OSError):
                Path(canvas_path).unlink()


def main():
    parser = argparse.ArgumentParser(
        description="Compose video onto tweet screenshot for Instagram Reels",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("screenshot", help="Path to tweet screenshot image")

    parser.add_argument("video", help="Path to video file")

    parser.add_argument(
        "-o",
        "--output",
        default="reel_output.mp4",
        help="Output file path (default: reel_output.mp4)",
    )

    parser.add_argument(
        "--theme",
        choices=["light", "dark", "auto"],
        default="auto",
        help="Background theme (default: auto-detect)",
    )

    parser.add_argument(
        "--position",
        choices=["top", "center", "bottom"],
        default="top",
        help="Tweet position on canvas (default: top)",
    )

    parser.add_argument(
        "--padding", type=int, default=40, help="Padding around elements in pixels (default: 40)"
    )

    parser.add_argument("--duration", type=float, help="Maximum output duration in seconds")

    parser.add_argument("--keep-temp", action="store_true", help="Keep temporary files")

    args = parser.parse_args()

    try:
        compose_video(
            screenshot_path=args.screenshot,
            video_path=args.video,
            output_path=args.output,
            theme=args.theme,
            position=args.position,
            padding=args.padding,
            duration=args.duration,
            keep_temp=args.keep_temp,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
