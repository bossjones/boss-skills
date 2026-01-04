---
name: twitter-to-reel
description: Convert Twitter/X posts into Instagram Reels format. Screenshots tweets, crops to show username/caption/media, creates a 9:16 vertical canvas with matching background color, and overlays downloaded video content. Works alongside twitter-media-downloader skill. Use when user wants to repurpose Twitter content for Instagram, TikTok, or other vertical video platforms.
---

# Twitter to Reel Converter

Convert Twitter/X posts into Instagram Reels format (9:16 vertical video).

## Dependencies

Install required packages before use:

```bash
pip install playwright pillow numpy
playwright install chromium
```

FFmpeg must also be available:
```bash
# Ubuntu/Debian
apt-get install ffmpeg

# macOS
brew install ffmpeg
```

## Quick Start

Create a reel from a tweet URL and video file:

```bash
uv run python scripts/create_reel.py "https://x.com/user/status/123" video.mp4 -o output.mp4
```

## Workflow

1. **Screenshot**: Captures the tweet using a headless browser
2. **Crop**: Extracts just the tweet content (username, text, media placeholder)
3. **Detect Theme**: Identifies light/dark mode for background matching
4. **Canvas**: Creates 1080x1920 vertical canvas with matching background
5. **Compose**: Places tweet at top, overlays video in media area
6. **Export**: Outputs Instagram Reels-ready MP4

## Scripts

### create_reel.py (Main Script)

Full pipeline from tweet URL to finished reel:

```bash
uv run python scripts/create_reel.py "TWEET_URL" VIDEO_FILE [options]
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

> **Note**: Using `--browser firefox` is recommended as it automatically extracts cookies from your browser session.

### screenshot_tweet.py (Standalone)

Screenshot a tweet without video overlay:

```bash
uv run python scripts/screenshot_tweet.py "TWEET_URL" -o screenshot.png
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
uv run python scripts/compose_video.py screenshot.png video.mp4 -o reel.mp4
```

## Examples

Basic reel creation:
```bash
uv run python scripts/create_reel.py "https://x.com/NASA/status/123456" nasa_video.mp4
```

Dark theme with bottom positioning:
```bash
uv run python scripts/create_reel.py "https://x.com/user/status/123" clip.mp4 \
  --theme dark --position bottom -o my_reel.mp4
```

Using with twitter-media-downloader:
```bash
# First download the video
uv run python ../twitter-media-downloader/scripts/download.py "https://x.com/user/status/123" -o ./downloads

# Then create the reel
uv run python scripts/create_reel.py "https://x.com/user/status/123" ./downloads/*.mp4 -o reel.mp4
```

Screenshot only (no video):
```bash
uv run python scripts/screenshot_tweet.py "https://x.com/user/status/123" -o tweet.png
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
- **Playwright errors**: Run `playwright install chromium`
