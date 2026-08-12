# Status Lines Reference

The `status_lines/` directory ships **ten** status-line scripts (PEP 723). Unlike commands, skills,
and hooks, status lines are **not auto-wired** — they're a library you opt into by pointing your
`statusLine` setting at one. The variants progress from a simple model/branch line to richer
context-window and cost readouts; pick the one that surfaces what you watch most.

## Table of Contents

- [What ships](#what-ships)
- [Wiring it up](#wiring-it-up)
- [Auth label (subscription vs API)](#auth-label-subscription-vs-api)
- [Installing for a project (`.claude/settings.local.json`)](#installing-for-a-project-claudesettingslocaljson)
- [Custom fields via `update_status_line`](#custom-fields-via-update_status_line)
- [Dependencies](#dependencies)

## What ships

| Script | Shows | Source |
| --- | --- | --- |
| `status_line.py` | Model, current directory, git branch + uncommitted-change count, and project version | [`status_lines/status_line.py`](../status_lines/status_line.py) |
| `status_line_v2.py` | Model plus the session's most recent prompt, color-coded by prompt type | [`status_lines/status_line_v2.py`](../status_lines/status_line_v2.py) |
| `status_line_v3.py` | Agent name, model, and the latest prompt with a type-based icon | [`status_lines/status_line_v3.py`](../status_lines/status_line_v3.py) |
| `status_line_v4.py` | Like v3 plus any `extras` key/value pairs from the session data file | [`status_lines/status_line_v4.py`](../status_lines/status_line_v4.py) |
| `status_line_v5.py` | Cost tracking — session cost (USD), lines added/removed, and duration | [`status_lines/status_line_v5.py`](../status_lines/status_line_v5.py) |
| `status_line_v6.py` | Context-window usage — progress bar, percent used, tokens left, session id | [`status_lines/status_line_v6.py`](../status_lines/status_line_v6.py) |
| `status_line_v7.py` | Session duration timer — elapsed time and start time | [`status_lines/status_line_v7.py`](../status_lines/status_line_v7.py) |
| `status_line_v8.py` | Token usage with cache stats — input/output tokens and cache create/read | [`status_lines/status_line_v8.py`](../status_lines/status_line_v8.py) |
| `status_line_v9.py` | Minimal powerline style — model, branch, cwd, context % with powerline separators | [`status_lines/status_line_v9.py`](../status_lines/status_line_v9.py) |
| `status_line_v10.py` | Leading `[auth:subscription]`/`[auth:api]`/`[auth:pending]` auth label, context-window usage bar (%), **and** running session cost in USD | [`status_lines/status_line_v10.py`](../status_lines/status_line_v10.py) |

`v10` is the current iteration of a progressively richer status line — it extends v6's context-window
bar with a running cost total computed from the transcript using public Anthropic list pricing, and
prepends a subscription-vs-API auth label (see below), so you can keep an eye on all three at a glance.

## Wiring it up

Point your Claude Code `statusLine` setting at one of the scripts. In your settings (e.g.
`.claude/settings.json`):

```json
{
  "statusLine": {
    "type": "command",
    "command": "uv run \"${CLAUDE_PLUGIN_ROOT}\"/status_lines/status_line_v10.py"
  }
}
```

Swap `status_line_v10.py` for any variant in the table above. Claude Code pipes session JSON to the
script on stdin; the script prints the status line to stdout.

> **`${CLAUDE_PLUGIN_ROOT}` only expands for plugin-owned entries.** A `statusLine` block you place
> in a project's `.claude/settings.local.json` (or any user settings file) has no owning plugin, so
> `${CLAUDE_PLUGIN_ROOT}` expands to the empty string through the shell and the command breaks. In a
> user/project settings file, use a **fully resolved absolute path**, or let the installer below
> write one for you.

## Auth label (subscription vs API)

`status_line_v10.py` prepends a label inferred from the `rate_limits` object Claude Code includes in
the status-line payload:

| `rate_limits` present | assistant `usage` seen in transcript | label |
| --- | --- | --- |
| yes | — | `[auth:subscription]` |
| no | yes | `[auth:api]` |
| no | no | `[auth:pending]` |

Claude Code emits `rate_limits` only for subscription (Pro/Max) sessions, and only once at least one
rate-limit window exists — so it is absent both on API-key sessions and on a subscription session
before its first response. The transcript's assistant `usage` entries disambiguate: absence *after* a
response has landed is a genuine API key (`[auth:api]`); absence *before* any response means the
transcript has not yet distinguished API from subscription, an explicit pending state
(`[auth:pending]`).

> **This is an inference, not a reported fact.** The payload exposes no auth-source field; the label
> keys off the mere *presence* of `rate_limits`, the narrowest possible coupling to an undocumented
> shape. Do not treat `[auth:subscription]` as authoritative for billing — `subscription` covers
> both Pro and Max, it is a hint, and the adjacent cost figure is list-price arithmetic from the
> transcript (meaningful on an API key, notional on a subscription).

## Installing for a project (`.claude/settings.local.json`)

Rather than hand-editing settings, let [`scripts/install_status_line.py`](../scripts/install_status_line.py)
(wrapped by [`/agent-harness:install_status_line`](./commands.md#install_status_line)) wire it up. By
default it targets the current project's `.claude/settings.local.json` — gitignored, highest
precedence, never committed — writing a fully-resolved absolute path (no `${CLAUDE_PLUGIN_ROOT}`):

```bash
# Install into ./.claude/settings.local.json (backs up any existing file first)
uv run plugins/boss-dev/agent-harness/scripts/install_status_line.py

# Read-only dry run: prints the plan (install / current / replace-ours / foreign)
uv run plugins/boss-dev/agent-harness/scripts/install_status_line.py --check

# Remove only our block
uv run plugins/boss-dev/agent-harness/scripts/install_status_line.py --uninstall

# Revert the target to its exact pre-install state
uv run plugins/boss-dev/agent-harness/scripts/install_status_line.py --restore --yes
```

Every mutation is preceded by a timestamped backup under
`~/.claude/backups/agent-harness-status-line/<target-slug>/` (outside the repo, so nothing lands in a
git diff), with a `manifest.json` and a per-target `latest` pointer. A pre-existing third-party
`statusLine` is never clobbered without `--force`, and a settings file that cannot be parsed is never
overwritten.

To install somewhere else, pass `--settings PATH`: `~/.claude/settings.json` for a manual **global**
install (applies to every project), or the committed `.claude/settings.json` for a **team-shared**
one. Pick the variant with `--variant status_line_v9.py`.

## Custom fields via `update_status_line`

The [`/agent-harness:update_status_line`](./commands.md#update_status_line) command writes arbitrary
key/value pairs into a session's data file
(`.{repo-slug}/data/sessions/{session_id}.json`, under an `extras` object). A status line that reads
`extras` (such as `status_line_v4.py`) can then display custom fields — project name, current
status, ticket number — that you set on the fly. The root is derived from the project directory, so
the data remains associated with the project even if a session changes its working directory:

```text
/agent-harness:update_status_line <session_id> status debugging
```

## Dependencies

- **`uv`** — runs the script (PEP 723).
- **`python-dotenv`** — declared in each script's inline metadata; resolved automatically by `uv`.
</content>
