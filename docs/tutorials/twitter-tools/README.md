# Tutorial: From tweet to Instagram Reel

`twitter-tools` ships two skills — `twitter-media-downloader` (grab media from X/Twitter) and
`twitter-to-reel` (turn a tweet into a 9:16 vertical Reel). This walkthrough downloads media from a
tweet and then composes a Reel from it.

**Time:** ~10 minutes · **Level:** beginner · **Reference:** [twitter-tools.md](../../plugins/twitter-tools.md)

## Prerequisites

| You need | Install |
|----------|---------|
| The plugin | `/plugin install twitter-tools@boss-skills` |
| Media tooling | `pip install gallery-dl yt-dlp playwright pillow numpy` then `playwright install chromium` |
| FFmpeg | `brew install ffmpeg` (macOS) / `apt-get install ffmpeg` (Debian/Ubuntu) |

The skills run their scripts with `uv run`, so Python deps resolve on demand — but the system tools
above (gallery-dl, FFmpeg, chromium) must be present.

## Step 1 — Download media from a tweet

Ask Claude in natural language (the `twitter-media-downloader` skill activates and runs `gallery-dl`):

```text
Download the media from https://x.com/NASA/status/1234567890123456789
```

Or run the skill's script directly:

```bash
uv run python scripts/download.py "https://x.com/NASA/status/1234567890123456789"
```

Media lands as `{output_dir}/twitter_{username}_{tweet_id}_{num}.{ext}` (default `./downloads`). For
profiles, likes, or bookmarks, point at that URL instead; protected content needs auth (Step 3).

## Step 2 — Compose a Reel

Turn a tweet into a 1080×1920 MP4. The `twitter-to-reel` skill screenshots the tweet, builds a 9:16
canvas with a theme-matched background, and overlays the video — auto-downloading it if needed:

```text
Make an Instagram Reel from https://x.com/user/status/123 and save it to reel.mp4
```

Or directly:

```bash
# Auto-download the video and compose the reel (recommended)
uv run python scripts/create_reel.py "https://x.com/user/status/123" -o reel.mp4

# Force dark theme + bottom positioning
uv run python scripts/create_reel.py "https://x.com/user/status/123" \
  --theme dark --position bottom -o reel.mp4
```

## Step 3 — Protected content (optional)

Likes, bookmarks, and private accounts need session cookies. Extract them from a logged-in browser:

```bash
uv run python scripts/download.py "https://x.com/i/bookmarks" --browser firefox
```

`--browser` (firefox/chrome/…) or `--cookies cookies.txt` works on both scripts.

## What you get

- **Downloads:** original-quality images/videos named by username + tweet id.
- **Reel:** a 1080×1920 H.264/AAC MP4 ready to upload.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Rate limiting | Add `--sleep 2` to space out requests |
| Login required | `--browser firefox` or `--cookies` |
| Missing videos | Install `yt-dlp` |
| Playwright errors | `playwright install chromium` |
| Wrong theme colors | Force `--theme light` / `--theme dark` |

## Next steps

- Reference (all options): [`docs/plugins/twitter-tools.md`](../../plugins/twitter-tools.md)
- Plugin README: [`plugins/social-media/twitter-tools/README.md`](../../../plugins/social-media/twitter-tools/README.md)
- Back to all [tutorials](../README.md)
