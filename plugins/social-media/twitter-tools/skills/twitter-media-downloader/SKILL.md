---
name: twitter-media-downloader
description: Download images and videos from X/Twitter using gallery-dl. Use when user wants to download media from Twitter/X URLs including tweets, user profiles, timelines, or likes. Supports single tweets, entire user media galleries, bookmarks, and lists. Handles authentication via cookies for accessing protected content.
---

# Twitter/X Media Downloader

Download images and videos from X/Twitter using gallery-dl.

## Quick Start

Run the download script with a Twitter/X URL:

```bash
uv run python scripts/download.py "https://x.com/username" --output ./downloads
```

## Supported URL Types

- **Single tweets**: `https://x.com/user/status/1234567890`
- **User timelines**: `https://x.com/username`
- **User media**: `https://x.com/username/media`
- **User likes**: `https://x.com/username/likes` (requires auth)
- **Bookmarks**: `https://x.com/i/bookmarks` (requires auth)
- **Lists**: `https://x.com/i/lists/1234567890`

## Authentication

For protected content (likes, bookmarks, private accounts), provide cookies:

```bash
uv run python scripts/download.py "URL" --cookies /path/to/cookies.txt
```

Or use browser cookies directly:

```bash
uv run python scripts/download.py "URL" --browser firefox
```

## Common Options

| Option | Description |
|--------|-------------|
| `--output DIR` | Output directory (default: ./downloads) |
| `--cookies FILE` | Path to cookies.txt file |
| `--browser NAME` | Extract cookies from browser (firefox, chrome, etc.) |
| `--videos-only` | Download only videos |
| `--images-only` | Download only images |
| `--limit N` | Limit number of items to download |
| `--retweets` | Include retweets when downloading user timeline |
| `--replies` | Include replies when downloading user timeline |

## Examples

Download all media from a user:
```bash
uv run python scripts/download.py "https://x.com/NASA" --output ./nasa_media
```

Download a single tweet's media:
```bash
uv run python scripts/download.py "https://x.com/user/status/1234567890"
```

Download only videos from a user (limit 50):
```bash
uv run python scripts/download.py "https://x.com/username" --videos-only --limit 50
```

Download bookmarks with Firefox cookies:
```bash
uv run python scripts/download.py "https://x.com/i/bookmarks" --browser firefox
```

## Output Structure

Files are saved with the following naming pattern:
```
{output_dir}/twitter_{username}_{tweet_id}_{num}.{ext}
```

## Troubleshooting

- **Rate limiting**: Add delays between requests with `--sleep 2`
- **Login required**: Use `--cookies` or `--browser` for authentication
- **Missing videos**: Ensure yt-dlp is installed for video downloads
