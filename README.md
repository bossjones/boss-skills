# boss-skills

Personal Claude Code plugin marketplace for social media automation and content creation tools.

## Installation

Add this marketplace to Claude Code:

```bash
/plugin marketplace add bossjones/boss-skills
```

Then install individual plugins:

```bash
/plugin install twitter-tools@boss-skills
```

## Available Plugins

### social-media/twitter-tools

Twitter/X social media tools for downloading media and converting tweets to Instagram Reels format.

```bash
/plugin install twitter-tools@boss-skills
```

**Skills included:**

| Skill | Description |
|-------|-------------|
| `twitter-media-downloader` | Download images and videos from X/Twitter using gallery-dl |
| `twitter-to-reel` | Convert tweets to Instagram Reels format (9:16 vertical video) |

**Features:**
- Download media from tweets, user profiles, timelines, likes, and bookmarks
- Support for protected content via browser cookie extraction
- Automatic video download and reel composition in a single command
- Theme auto-detection (light/dark) for seamless background matching
- JSON output mode for programmatic integration

See [`plugins/social-media/twitter-tools/README.md`](plugins/social-media/twitter-tools/README.md) for details.

## Quick Start Examples

### Download Twitter Media

```bash
# Download all media from a user
uv run python scripts/download.py "https://x.com/NASA" --output ./downloads

# Download only videos from a tweet
uv run python scripts/download.py "https://x.com/user/status/123" --videos-only

# Download with authentication
uv run python scripts/download.py "https://x.com/i/bookmarks" --browser firefox
```

### Create Instagram Reels from Tweets

```bash
# Auto-download video and create reel (recommended)
uv run python scripts/create_reel.py "https://x.com/user/status/123" -o reel.mp4

# With authentication for protected tweets
uv run python scripts/create_reel.py "https://x.com/user/status/123" --browser firefox -o reel.mp4

# With explicit video file
uv run python scripts/create_reel.py "https://x.com/user/status/123" video.mp4 -o reel.mp4
```

## Development

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- FFmpeg (for video processing)

### Commands

```bash
# Install dependencies
make install

# Run linting (ruff + basedpyright)
make lint

# Run tests
make test

# Run all checks
make
```

### Project Structure

```text
boss-skills/
├── plugins/
│   └── social-media/
│       └── twitter-tools/
│           ├── .claude-plugin/
│           │   └── plugin.json
│           ├── skills/
│           │   ├── twitter-media-downloader/
│           │   │   ├── SKILL.md
│           │   │   └── scripts/
│           │   └── twitter-to-reel/
│           │       ├── SKILL.md
│           │       └── scripts/
│           └── README.md
├── devtools/
├── scripts/
└── tests/
```

## Dependencies

The twitter-tools plugin requires:

- **gallery-dl** - Media download engine
- **yt-dlp** - Video download support (optional but recommended)
- **playwright** - Browser automation for screenshots
- **pillow** - Image processing
- **FFmpeg** - Video composition

Install with:

```bash
pip install gallery-dl yt-dlp playwright pillow numpy
playwright install chromium
brew install ffmpeg  # macOS
```

## License

MIT
