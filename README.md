# boss-skills

Personal Claude Code plugin marketplace spanning developer-experience tooling, homelab
infrastructure, and social-media content creation.

## Installation

Add this marketplace to Claude Code:

```bash
/plugin marketplace add bossjones/boss-skills
```

Then install individual plugins:

```bash
/plugin install agent-harness@boss-skills
/plugin install basedpyright-lsp@boss-skills
/plugin install twitter-tools@boss-skills
```

## Available Plugins

Full per-plugin documentation — components, install commands, and usage examples — lives in
[`docs/plugins/`](docs/plugins/README.md).

| Plugin | Category | Version | Description | Docs |
|--------|----------|---------|-------------|------|
| [agent-harness](#boss-devagent-harness) | `boss-dev` | 0.4.1 | Subagents, commands, hooks, and skills for agentic dev workflows | [↗](docs/plugins/agent-harness.md) |
| [basedpyright-lsp](#boss-devbasedpyright-lsp) | `boss-dev` | 0.1.1 | Wire basedpyright into Claude Code for real-time Python diagnostics | [↗](docs/plugins/basedpyright-lsp.md) |
| python-dev | `boss-dev` | 0.1.1 | Debug GitHub Actions CI and ship conventional-commit PRs | [↗](docs/plugins/python-dev.md) |
| [twitter-tools](#social-mediatwitter-tools) | `social-media` | 0.1.1 | Download X/Twitter media and convert tweets to Reels | [↗](docs/plugins/twitter-tools.md) |
| proxmox-infra | `boss-homelab` | 0.1.1 | Manage Proxmox VE homelab infrastructure and IaC | [↗](docs/plugins/proxmox-infra.md) |

### boss-dev/agent-harness

Agent harness tooling for Claude Code: subagents, commands, hooks, skills, and scripts that build
and operate agentic dev workflows. It bundles a GitHub PR-review workflow, a git-worktree
lifecycle, and a release-notes generator, plus planning/priming/shipping commands and a roster of
subagents.

```bash
/plugin install agent-harness@boss-skills
```

**Components:**

| Component | Count | Active on install? |
|-----------|-------|--------------------|
| Skills | 9 | Yes |
| Commands | 12 | Yes |
| Agents | 6 | Yes |
| Output styles | 8 | Yes |
| Hooks | 13 | Manual wiring |
| Status lines | 10 | Manual wiring |

The planning and shipping commands chain into a single isolated feature loop:

```mermaid
flowchart LR
    plan["/plan"] --> wt["git-worktree"]
    wt --> ab["/autobuild"]
    ab --> verify{"lint + test"}
    verify -- red --> ab
    verify -- green --> cpp["/commit-push-pr"]
    cpp --> fix["/fix-gh-pr-comments"]
    fix --> pr(["PR shipped"])
```

```text
/agent-harness:prime
/agent-harness:plan add a --json flag to the download script
/agent-harness:autobuild specs/add-json-flag.md   # run inside a git worktree
```

See [`plugins/boss-dev/agent-harness/README.md`](plugins/boss-dev/agent-harness/README.md) or the
[expanded docs](docs/plugins/agent-harness.md) for the full component reference.

### boss-dev/basedpyright-lsp

LSP plugin that wires [basedpyright](https://docs.basedpyright.com/) into Claude Code — real-time
Python diagnostics, hover docs, go-to-definition, and find-references for `.py`/`.pyi`/`.pyw` files.
basedpyright is a strict superset of pyright that re-adds semantic tokens, inlay hints, and baseline
files, and ships as a single binary.

```bash
uv tool install basedpyright          # prerequisite: language server on PATH
/plugin install basedpyright-lsp@boss-skills
```

**Capabilities:**

| Capability | Description |
|------------|-------------|
| Real-time diagnostics | Type errors surface as you edit, in the `/plugin` Errors tab |
| Hover / definition / references | Inferred types, docstrings, and symbol navigation |
| Semantic tokens & inlay hints | Richer highlighting and inline type annotations |
| Baseline files | Suppress pre-existing findings so only new issues surface |

Configure strictness per-project via `pyrightconfig.json` or `[tool.basedpyright]` in
`pyproject.toml`. See
[`plugins/boss-dev/basedpyright-lsp/README.md`](plugins/boss-dev/basedpyright-lsp/README.md) or the
[expanded docs](docs/plugins/basedpyright-lsp.md) for prerequisites and troubleshooting.

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

### Skill Quality

Skills are quality-gated with [`plugin-eval`](https://github.com/wshobson/agents/tree/main/plugins/plugin-eval),
pulled on demand from upstream via `uvx` (nothing is vendored or submoduled, so
you always get the latest version).

```bash
# Report static scores for every skill (never fails)
make eval

# Quality gate used by CI: fail if any skill < EVAL_THRESHOLD
make eval-ci

# Override the floor ad hoc
make eval-ci EVAL_THRESHOLD=70

# Deep-dive one skill at standard depth (LLM judge; uses Claude Code Max)
make eval-skill SKILL=plugins/social-media/twitter-tools/skills/twitter-to-reel
```

`make eval-ci` runs in CI at static (`quick`) depth — deterministic, no API key
required. `EVAL_THRESHOLD` (in the `Makefile`) is a regression floor set to
`min(baseline scores) - 5`; bump it as skills improve.

For interactive use, install the Claude Code plugin from the already-registered
marketplace (these are user-typed slash commands, not repo scripts):

```text
/plugin install plugin-eval@claude-code-workflows
/plugin marketplace update claude-code-workflows   # pull the latest on demand
```

Enable autoUpdate on the `claude-code-workflows` marketplace if you want plugin
updates without the manual `marketplace update`. This gives you `/eval`,
`/certify`, and `/compare` while iterating on skills.

**Escape hatch:** if upstream `plugin-eval` changes ever make the gate flaky,
pin a known-good revision without editing code:

```bash
PLUGIN_EVAL_SOURCE='git+https://github.com/wshobson/agents.git@<sha>#subdirectory=plugins/plugin-eval' make eval-ci
```

### Project Structure

```text
boss-skills/
├── plugins/
│   ├── boss-dev/
│   │   ├── agent-harness/      # subagents, commands, hooks, skills, status lines
│   │   ├── basedpyright-lsp/   # Python LSP integration (.lsp.json)
│   │   └── python-dev/         # CI debugging + conventional-commit PR commands
│   ├── boss-homelab/
│   │   └── proxmox-infra/      # Proxmox VE infrastructure skill
│   └── social-media/
│       └── twitter-tools/      # media download + tweet-to-Reel skills
├── docs/
│   └── plugins/                # expanded per-plugin documentation
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
