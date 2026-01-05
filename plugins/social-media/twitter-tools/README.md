# twitter-tools

Twitter/X social media tools for downloading media and converting tweets to Instagram Reels format.

## Installation

```bash
/plugin install twitter-tools@boss-skills
```

## Skills

### twitter-media-downloader

Download images and videos from X/Twitter using gallery-dl.

**Supported content:**

- Single tweets
- User timelines and media galleries
- User likes (requires auth)
- Bookmarks (requires auth)
- Lists

**Usage:**

```bash
# Download from a user profile
uv run python scripts/download.py "https://x.com/NASA" --output ./downloads

# Download single tweet media
uv run python scripts/download.py "https://x.com/user/status/123"

# Download only videos
uv run python scripts/download.py "https://x.com/username" --videos-only --limit 50

# Download bookmarks with browser auth
uv run python scripts/download.py "https://x.com/i/bookmarks" --browser firefox

# JSON output for programmatic use
uv run python scripts/download.py "https://x.com/user/status/123" --json --videos-only
```

**Options:**

| Option | Description |
|--------|-------------|
| `--output DIR` | Output directory (default: ./downloads) |
| `--cookies FILE` | Path to cookies.txt file |
| `--browser NAME` | Extract cookies from browser (firefox, chrome, etc.) |
| `--videos-only` | Download only videos |
| `--images-only` | Download only images |
| `--limit N` | Limit number of items |
| `--json` | Output structured JSON with file paths |

---

### twitter-to-reel

Convert Twitter/X posts into Instagram Reels format (9:16 vertical video).

**Features:**

- Auto-downloads video from tweet if not provided
- Screenshots tweet with headless browser
- Auto-detects light/dark theme
- Creates 1080x1920 vertical canvas
- Composes final MP4 ready for Instagram

**Usage:**

```bash
# Auto-download and create reel (recommended)
uv run python scripts/create_reel.py "https://x.com/user/status/123" -o reel.mp4

# With browser authentication
uv run python scripts/create_reel.py "https://x.com/user/status/123" --browser firefox -o reel.mp4

# With explicit video file
uv run python scripts/create_reel.py "https://x.com/user/status/123" video.mp4 -o reel.mp4

# Dark theme, bottom positioning
uv run python scripts/create_reel.py "https://x.com/user/status/123" \
  --theme dark --position bottom -o reel.mp4
```

**Options:**

| Option | Description |
|--------|-------------|
| `-o, --output` | Output file path (default: reel_output.mp4) |
| `--theme` | Force theme: `light`, `dark`, or `auto` |
| `--position` | Tweet position: `top`, `center`, `bottom` |
| `--padding` | Padding around tweet in pixels |
| `--cookies` | Path to cookies.txt for auth |
| `--browser` | Browser to extract cookies from |
| `--no-auto-download` | Require explicit video path |

## Dependencies

**Required:**

- Python 3.11+
- gallery-dl
- playwright + chromium
- pillow, numpy
- FFmpeg

**Optional:**

- yt-dlp (recommended for video downloads)

**Install:**

```bash
pip install gallery-dl yt-dlp playwright pillow numpy
playwright install chromium

# macOS
brew install ffmpeg

# Ubuntu/Debian
apt-get install ffmpeg
```

## Authentication

For protected content (likes, bookmarks, private accounts), use browser cookie extraction:

```bash
# Recommended: extract from Firefox
--browser firefox

# Or provide cookies file
--cookies /path/to/cookies.txt
```

## Output

**Media downloads:** `{output_dir}/twitter_{username}_{tweet_id}_{num}.{ext}`

**Reels:** 1080x1920 MP4 (H.264 video, AAC audio)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Rate limiting | Add `--sleep 2` for delays between requests |
| Login required | Use `--browser firefox` or `--cookies` |
| Missing videos | Install yt-dlp: `pip install yt-dlp` |
| Playwright errors | Run `playwright install chromium` |
| Wrong theme colors | Force with `--theme light` or `--theme dark` |
