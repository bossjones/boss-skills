# Status Lines Reference

The `status_lines/` directory ships **ten** status-line scripts (PEP 723). Unlike commands, skills,
and hooks, status lines are **not auto-wired** — they're a library you opt into by pointing your
`statusLine` setting at one. The variants progress from a simple model/branch line to richer
context-window and cost readouts; pick the one that surfaces what you watch most.

## Table of Contents

- [What ships](#what-ships)
- [Wiring it up](#wiring-it-up)
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
| `status_line_v10.py` | Context-window usage bar (%) **and** running session cost in USD | [`status_lines/status_line_v10.py`](../status_lines/status_line_v10.py) |

`v10` is the current iteration of a progressively richer status line — it extends v6's context-window
bar with a running cost total computed from the transcript using public Anthropic list pricing, so you
can keep an eye on both at a glance.

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

## Custom fields via `update_status_line`

The [`/agent-harness:update_status_line`](./commands.md#update_status_line) command writes arbitrary
key/value pairs into a session's data file (`.claude/data/sessions/{session_id}.json`, under an
`extras` object). A status line that reads `extras` (such as `status_line_v4.py`) can then display
custom fields — project name, current status, ticket number — that you set on the fly:

```text
/agent-harness:update_status_line <session_id> status debugging
```

## Dependencies

- **`uv`** — runs the script (PEP 723).
- **`python-dotenv`** — declared in each script's inline metadata; resolved automatically by `uv`.
</content>
