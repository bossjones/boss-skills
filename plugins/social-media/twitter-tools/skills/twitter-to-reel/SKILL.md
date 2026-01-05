---
name: twitter-to-reel
description: Convert Twitter/X posts into Instagram Reels format. Screenshots tweets, crops to show username/caption/media, creates a 9:16 vertical canvas with matching background color, and overlays downloaded video content. Works alongside twitter-media-downloader skill. Use when user wants to repurpose Twitter content for Instagram, TikTok, or other vertical video platforms.
---

# Twitter to Reel Converter

Convert Twitter/X posts into Instagram Reels format (9:16 vertical video).

## Dependencies

Python dependencies are installed automatically via PEP 723 inline metadata when using `uv run`.

Playwright and FFmpeg must be installed separately:

```bash
# Install Playwright globally via uv tool
uv tool install playwright

# Install Chromium browser for Playwright
playwright install chromium

# FFmpeg - Ubuntu/Debian
apt-get install ffmpeg

# FFmpeg - macOS
brew install ffmpeg
```

> **Note**: Using `uv tool install playwright` makes the `playwright` CLI available globally, which is required for installing browser binaries.

## Quick Start

Create a reel from a tweet URL (video auto-downloaded):

```bash
uv run scripts/create_reel.py "https://x.com/user/status/123" -o output.mp4
```

Or provide a video file explicitly:

```bash
uv run scripts/create_reel.py "https://x.com/user/status/123" video.mp4 -o output.mp4
```

## Workflow

1. **Download** (auto): If no video provided, downloads from tweet using twitter-media-downloader
2. **Screenshot**: Captures the tweet using a headless browser
3. **Detect Theme**: Identifies light/dark mode for background matching
4. **Canvas**: Creates 1080x1920 vertical canvas with matching background
5. **Compose**: Places tweet at top, overlays video in media area
6. **Export**: Outputs Instagram Reels-ready MP4

## Scripts

### create_reel.py (Main Script)

Full pipeline from tweet URL to finished reel:

```bash
uv run scripts/create_reel.py "TWEET_URL" [VIDEO_FILE] [options]
```

Options:
| Option | Description |
|--------|-------------|
| `-o, --output` | Output file path (default: reel_output.mp4) |
| `--theme` | Force theme: `light`, `dark`, or `auto` (default: auto) |
| `--position` | Tweet position: `top`, `center`, `bottom` (default: top) |
| `--padding` | Padding around tweet in pixels (default: 40) |
| `--no-cleanup` | Keep intermediate files |
| `--cookies` | Path to cookies.txt for auth |
| `--browser` | Browser to extract cookies from (recommended: firefox) |
| `--no-auto-download` | Disable automatic video download (require explicit video path) |
| `--debug` | Enable verbose debug output for troubleshooting |

> **Note**: Using `--browser firefox` is recommended as it automatically extracts cookies from your browser session. This applies to both tweet screenshots and video downloads.

### screenshot_tweet.py (Standalone)

Screenshot a tweet without video overlay:

```bash
uv run scripts/screenshot_tweet.py "TWEET_URL" -o screenshot.png
```

Options:
| Option | Description |
|--------|-------------|
| `-o, --output` | Output file path |
| `--theme` | Force `light` or `dark` theme |
| `--width` | Browser viewport width (default: 550) |
| `--full` | Capture full tweet thread |
| `--cookies` | Cookies file for protected tweets |

### compose_video.py (Standalone)

Compose video onto an existing screenshot:

```bash
uv run scripts/compose_video.py screenshot.png video.mp4 -o reel.mp4
```

## Examples

### Auto-Download (Recommended)

Simply provide the tweet URL - video is downloaded automatically:

```bash
uv run scripts/create_reel.py "https://x.com/NASA/status/123456" -o nasa_reel.mp4
```

With authentication for protected tweets:
```bash
uv run scripts/create_reel.py "https://x.com/user/status/123" --browser firefox -o reel.mp4
```

### Manual Download (Advanced)

If you want more control, download separately first:

```bash
# First download the video
uv run python ../twitter-media-downloader/scripts/download.py "https://x.com/user/status/123" -o ./downloads

# Then create the reel
uv run scripts/create_reel.py "https://x.com/user/status/123" ./downloads/*.mp4 -o reel.mp4
```

Or provide a video file directly:
```bash
uv run scripts/create_reel.py "https://x.com/NASA/status/123456" my_video.mp4 -o reel.mp4
```

### Customization

Dark theme with bottom positioning:
```bash
uv run scripts/create_reel.py "https://x.com/user/status/123" \
  --theme dark --position bottom -o my_reel.mp4
```

### Screenshot Only (No Video)

```bash
uv run scripts/screenshot_tweet.py "https://x.com/user/status/123" -o tweet.png
```

## Output Specifications

- **Resolution**: 1080x1920 (Instagram Reels standard)
- **Aspect Ratio**: 9:16 vertical
- **Format**: MP4 (H.264 video, AAC audio)
- **Background**: Matches tweet theme (white/black)

## Troubleshooting

- **Tweet not loading**: Use `--browser firefox` (recommended) or `--cookies` for protected accounts
- **Wrong colors**: Force theme with `--theme light` or `--theme dark`
- **Video too long**: Trim video before processing or use `--duration`
- **Playwright errors**: Run `uv tool install playwright && playwright install chromium`
- **Debug mode**: Use `--debug` flag for verbose output to diagnose issues
