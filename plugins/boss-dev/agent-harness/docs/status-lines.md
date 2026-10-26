# Status Lines Reference

The `status_lines/` directory ships one status-line script, `status_line_v10.py` (PEP 723).
Unlike commands and skills, the status line is **not auto-wired** — you opt in by pointing your
`statusLine` setting at it, or by running
[`/agent-harness:install_status_line`](./commands.md#install_status_line).

## Table of Contents

- [What ships](#what-ships)
- [Wiring it up](#wiring-it-up)
- [Auth label (subscription vs API)](#auth-label-subscription-vs-api)
- [Installing for a project (`.claude/settings.local.json`)](#installing-for-a-project-claudesettingslocaljson)
- [Dependencies](#dependencies)

## What ships

| Script | Shows | Source |
| --- | --- | --- |
| `status_line_v10.py` | Leading `[auth:subscription]`/`[auth:api]`/`[auth:pending]` auth label, context-window usage bar (%), **and** running session cost in USD | [`status_lines/status_line_v10.py`](../status_lines/status_line_v10.py) |

The cost is computed from the transcript using public Anthropic list pricing, and the auth label
is inferred from the payload (see below), so you can keep an eye on context, cost, and auth mode
at a glance.

> Earlier releases shipped nine more variants (`status_line.py`, `status_line_v2.py` …
> `status_line_v9.py`). Several of them read per-session prompt data that was written by the
> lifecycle hooks this plugin no longer ships, so they were removed along with the hooks.
> `install_status_line` recognizes an old variant in your settings and replaces it with v10.

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

Claude Code pipes session JSON to the script on stdin; the script prints the status line to
stdout.

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

### What `--restore` reverts to

`latest` names the **restore target**, and only a pre-install backup ever advances it. `--uninstall`
still writes its own backup (the post-install file stays recoverable by hand under the same
`<target-slug>/` directory) but does not become the restore target — so `install → uninstall →
restore` lands on the original settings payload rather than re-adding the status-line block.

When the pre-image is "the file did not exist", `--restore` deletes the target. It does so **only
while that file still holds nothing but our own `statusLine` block**. If you have since added other
settings, replaced the `statusLine` with a third-party one, or the file no longer parses, restore
refuses with exit 1 and leaves the file untouched:

```console
$ uv run plugins/boss-dev/agent-harness/scripts/install_status_line.py --restore --yes
Refusing to delete /path/.claude/settings.local.json: it now holds settings added since install: permissions.
Run --uninstall instead to remove only our statusLine block.
```

Use `--uninstall` in that case: it surgically removes our block and keeps everything you added.

To install somewhere else, pass `--settings PATH`: `~/.claude/settings.json` for a manual **global**
install (applies to every project), or the committed `.claude/settings.json` for a **team-shared**
one.

## Dependencies

- **`uv`** — runs the script (PEP 723).
- **`python-dotenv`** — declared in the script's inline metadata; resolved automatically by `uv`.
