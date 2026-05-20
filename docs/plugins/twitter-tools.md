# twitter-tools

> `social-media` · v0.1.0 · [plugin source](../../plugins/social-media/twitter-tools/)

Twitter/X social media tools for downloading media and converting tweets into Instagram
Reels format. The plugin ships two skills: a [gallery-dl](https://github.com/mikf/gallery-dl)
media downloader and a video composer that produces 9:16 vertical content.

## Installation

```bash
/plugin marketplace add bossjones/boss-skills   # once
/plugin install twitter-tools@boss-skills
```

## Dependencies

The plugin's scripts run with `uv run`, but the underlying media tooling must be installed
separately:

```bash
pip install gallery-dl yt-dlp playwright pillow numpy
playwright install chromium

brew install ffmpeg          # macOS
# apt-get install ffmpeg     # Ubuntu/Debian
```

| Dependency | Role | Required |
|------------|------|----------|
| `gallery-dl` | Media download engine | Yes |
| `playwright` + chromium | Headless browser for tweet screenshots | Yes |
| `pillow`, `numpy` | Image processing and theme detection | Yes |
| FFmpeg | Video composition | Yes |
| `yt-dlp` | Video download support | Recommended |

## Skills

| Skill | Description |
|-------|-------------|
| `twitter-media-downloader` | Download images and videos from X/Twitter using gallery-dl. Supports single tweets, user timelines and galleries, likes, bookmarks, and lists. Handles cookie authentication for protected content. |
| `twitter-to-reel` | Convert a Twitter/X post into Instagram Reels format. Screenshots the tweet, crops to username/caption/media, builds a 9:16 vertical canvas with a matching background, and overlays the downloaded video. |

## Usage examples

### Download media from a single tweet

```bash
uv run python scripts/download.py "https://x.com/user/status/123"
```

### Download an entire user gallery

```bash
# All media from a profile, into a chosen directory
uv run python scripts/download.py "https://x.com/NASA" --output ./downloads

# Only videos, capped at 50 items
uv run python scripts/download.py "https://x.com/NASA" --videos-only --limit 50
```

### Download protected content with browser authentication

```bash
# Likes and bookmarks require auth — extract cookies from a browser
uv run python scripts/download.py "https://x.com/i/bookmarks" --browser firefox
```

### Convert a tweet into an Instagram Reel

```bash
# Auto-download the video and compose a 1080x1920 MP4 (recommended)
uv run python scripts/create_reel.py "https://x.com/user/status/123" -o reel.mp4

# Force dark theme and bottom positioning
uv run python scripts/create_reel.py "https://x.com/user/status/123" \
  --theme dark --position bottom -o reel.mp4
```

## Key options

### `twitter-media-downloader` (`scripts/download.py`)

| Option | Description |
|--------|-------------|
| `--output DIR` | Output directory (default: `./downloads`) |
| `--cookies FILE` | Path to a `cookies.txt` file |
| `--browser NAME` | Extract cookies from a browser (`firefox`, `chrome`, …) |
| `--videos-only` / `--images-only` | Restrict to one media type |
| `--limit N` | Limit the number of items |
| `--json` | Emit structured JSON with file paths |

### `twitter-to-reel` (`scripts/create_reel.py`)

| Option | Description |
|--------|-------------|
| `-o, --output` | Output file path (default: `reel_output.mp4`) |
| `--theme` | Force theme: `light`, `dark`, or `auto` |
| `--position` | Tweet position: `top`, `center`, or `bottom` |
| `--padding` | Padding around the tweet, in pixels |
| `--cookies` / `--browser` | Authentication for protected tweets |
| `--no-auto-download` | Require an explicit video path instead of auto-downloading |

## Authentication

Protected content (likes, bookmarks, private accounts) needs session cookies. Either
extract them from a logged-in browser with `--browser firefox`, or supply a
`cookies.txt` file with `--cookies /path/to/cookies.txt`.

## Output

- **Media downloads:** `{output_dir}/twitter_{username}_{tweet_id}_{num}.{ext}`
- **Reels:** 1080x1920 MP4 (H.264 video, AAC audio)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Rate limiting | Add `--sleep 2` to space out requests |
| Login required | Use `--browser firefox` or `--cookies` |
| Missing videos | Install `yt-dlp`: `pip install yt-dlp` |
| Playwright errors | Run `playwright install chromium` |
| Wrong theme colors | Force it with `--theme light` or `--theme dark` |

## See also

- Plugin source: [`plugins/social-media/twitter-tools/`](../../plugins/social-media/twitter-tools/)
- Plugin README: [`plugins/social-media/twitter-tools/README.md`](../../plugins/social-media/twitter-tools/README.md)
