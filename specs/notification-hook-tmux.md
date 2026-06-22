# Spec: tmux-aware desktop notifications for `agent-harness`

## Context

The user runs Claude Code inside **tmux on macOS** (and has Linux homelab boxes). Claude Code's
built-in desktop notifications don't pass through tmux (it sends plain OSC sequences; tmux requires
DCS passthrough — a known open issue), so after plan-mode approval or a permission prompt there's no
reliable signal that the agent needs input, and no way to jump to the right tmux window.

The Claude Code hooks lifecycle fires several relevant events. As of the current docs
(https://code.claude.com/docs/en/hooks), the full event catalog groups as:

- **Once per session:** `SessionStart`, `SessionEnd`, `Setup`
- **Once per turn:** `UserPromptSubmit`, `Stop`, `StopFailure`
- **Per tool call:** `PreToolUse`, `PostToolUse`, `PostToolUseFailure`, `PostToolBatch`,
  `PermissionRequest`, `PermissionDenied`
- **Async / event-driven:** `Notification`, `SubagentStart`, `SubagentStop`, `TeammateIdle`,
  `PreCompact`/`PostCompact`, `InstructionsLoaded`, `ConfigChange`, `CwdChanged`, `FileChanged`,
  `MessageDisplay`, `WorktreeCreate`/`WorktreeRemove`, `Elicitation`/`ElicitationResult`,
  `TaskCreated`/`TaskCompleted`

Events of interest for this feature and why:

| Event | When | Decision control | Why we use it |
|---|---|---|---|
| `Notification` | Claude sends a notification (permission request, idle, MCP elicitation, etc.) | None (logging/observability only) | Signals "Claude is blocked on you" |
| `Stop` | Claude finishes responding normally | Can block or add context | Signals "turn complete" |
| `StopFailure` | Turn ends on an API error (`rate_limit`, `overloaded`, `server_error`, …) | **Output and exit code ignored** | Signals "turn failed — check it" |

Matcher notes that directly affect the wiring:
- `Notification` matcher = `notification_type`. Values: `permission_prompt`, `idle_prompt`,
  `auth_success`, `elicitation_dialog`, `elicitation_complete`, `elicitation_response`. Matchers
  support `|`-alternation (e.g. `permission_prompt|idle_prompt`).
- `Stop` matcher: none (always fires). Input carries `permission_mode` + `effort`.
- `StopFailure` matcher = `error_type`. Input carries `error_type` + `error_message`. **Output/exit
  code are ignored** — the hook's value is its side-effect (the notification).

A hook-based notifier sidesteps the OSC/tmux issue entirely: the hook script captures the tmux
context from `$TMUX` / `$TMUX_PANE`, fires a desktop notification, and (on macOS) attaches a click
action that runs `tmux switch-client`/`select-window` to jump to the exact `session:window` where
Claude is waiting.

The intended outcome: when you install the `boss-skills` marketplace, you can flip **one config
toggle** to turn tmux desktop notifications on/off. Default **off** so users without
tmux/terminal-notifier are unaffected.

## Objective

Add an opt-in, tmux-aware desktop-notification capability to the existing **`agent-harness`**
plugin, controlled by a per-plugin **`userConfig`** toggle surfaced at install/configure time,
wired into the plugin's `Notification`, `Stop`, and `StopFailure` hooks without regressing current
behavior.

## Problem Statement

There is currently no way to know — while working in another tmux window — that Claude has finished
a turn, is blocked waiting for input, or that a turn died on an API error. The built-in notification
path is broken under tmux. We need a notification that (a) is reliable under tmux, (b) is clickable
to jump to the right pane on macOS, (c) degrades gracefully on Linux and when optional tools are
missing, and (d) is **off by default** and toggleable through the documented plugin user-configuration
mechanism rather than manual settings edits.

## Solution Approach

- A **standalone Python hook script** `hooks/tmux_notify.py` (PEP 723, stdlib-only) in the
  `agent-harness` plugin handles all three notification events with a single `--event` flag.
- A **`userConfig`** block in `plugin.json` exposes a boolean enable toggle plus two optional knobs
  (terminal bundle id to focus, notification sound).
- The script is gated by `CLAUDE_PLUGIN_OPTION_TMUX_NOTIFICATIONS` — always runs but exits
  immediately (silent no-op) unless the toggle is on.
- The script is wired as **parallel** hook entries so the current Python TTS/logging hooks are
  untouched. The `Notification` entry uses a **filtered matcher** so it only fires when Claude is
  actually blocked on the user — not on `auth_success` or elicitation echo events.

### Design decisions (confirmed with the user)
| Decision | Choice |
|---|---|
| Plugin home | **`agent-harness`** (already owns the `Notification`/`Stop` hooks) |
| Script language | **Python (PEP 723)** — matches repo convention; run via `uv run --script` |
| Platforms | **macOS (`terminal-notifier`) + Linux fallback (`notify-send`)**, then terminal bell |
| Terminal focus | **Configurable bundle id, default `com.mitchellh.ghostty`** |

---

## v0.9.0 — Initial implementation (SHIPPED on branch `feature-implement-tmux-notify`)

This increment shipped and is committed. The sections below document what was built.

### Grounding facts at time of ship

- `plugin.json` at `0.9.0`, with the full `userConfig` block present. Marketplace mirrors `0.9.0`.
- `hooks.json` wires `Notification → notification.py --notify` and `Stop → stop.py --chat` as
  existing entries, plus the new `tmux_notify.py` entries as parallel hook objects. Also contains
  `SubagentStop`, `UserPromptSubmit`, `PreCompact`, `SessionStart`, `SessionEnd`, `PermissionRequest`,
  `PostToolUseFailure`, `SubagentStart`, `Setup`.
- Real `Notification` event JSON on stdin: `session_id`, `transcript_path`, `cwd`,
  `hook_event_name`, `message`, `notification_type`. `Stop` events: `session_id`, `transcript_path`,
  `cwd`, `hook_event_name`, `permission_mode`, `effort`.
- Per Claude Code docs: `userConfig` in `.claude-plugin/plugin.json`; each value exported as
  `CLAUDE_PLUGIN_OPTION_<KEY-UPPERCASED>` (booleans arrive as `"true"`/`"false"`), also substitutable
  as `${user_config.KEY}`.

### What shipped

**`plugin.json`** — added `userConfig`:
```json
"userConfig": {
  "tmux_notifications": { "type": "boolean", "default": false, ... },
  "tmux_notify_activate_bundle_id": { "type": "string", "default": "com.mitchellh.ghostty", ... },
  "tmux_notify_sound": { "type": "boolean", "default": false, ... }
}
```

**`hooks/tmux_notify.py`** — stdlib-only PEP 723 script. Toggle gate → read stdin JSON → build
title/subtitle/message → try `terminal-notifier` (macOS, with `-execute` click-to-jump) → try
`notify-send` (Linux) → terminal bell fallback. Always exits `0`.

**`hooks.json`** — parallel entry under `Notification` and `Stop`:
```json
{ "matcher": "", "hooks": [{ "type": "command",
  "command": "uv run \"${CLAUDE_PLUGIN_ROOT}\"/hooks/tmux_notify.py --event notification" }] }
{ "matcher": "", "hooks": [{ "type": "command",
  "command": "uv run \"${CLAUDE_PLUGIN_ROOT}\"/hooks/tmux_notify.py --event stop" }] }
```

---

## v0.10.0 — Refinements (SHIPPED, same branch)

Two gaps surfaced by reviewing the current hooks lifecycle docs:

1. **`Notification` matcher was too broad.** The `matcher: ""` fired on every notification type,
   including `auth_success` and `elicitation_complete`/`elicitation_response` echoes — noise, not
   "Claude needs you."
2. **`StopFailure` was unwired.** API-error turns (`rate_limit`, `overloaded`, `server_error`, …)
   fire `StopFailure` instead of `Stop`. The v0.9.0 wiring covered `Stop` only, so a failed turn
   produced no notification.

### Changes in this increment

**`hooks.json` — narrow `Notification` tmux entry matcher:**
```json
"matcher": "permission_prompt|idle_prompt|elicitation_dialog"
```
Fires only when Claude is blocked on the user (permission / idle / MCP elicitation). The
`notification.py` TTS entry's matcher is unchanged.

**`hooks.json` — new `StopFailure` array:**
```json
"StopFailure": [
  { "matcher": "",
    "hooks": [{ "type": "command",
      "command": "uv run \"${CLAUDE_PLUGIN_ROOT}\"/hooks/tmux_notify.py --event stopfailure" }] }
]
```

**`tmux_notify.py` — `stopfailure` event support:**
- Added `"stopfailure"` to `--event` choices.
- New `build_text` branch:
  ```python
  if event == "stopfailure":
      etype = (payload.get("error_type") or "unknown").strip()
      emsg = (payload.get("error_message") or "").strip()
      detail = f"{etype}: {emsg}" if emsg else etype
      return ("Claude Code", "Turn failed", f"The turn ended on an API error ({detail}).")
  ```

Plugin bumped `0.9.0` → `0.10.0` (minor — new hook event wired).

---

## Relevant Files

- `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json` — `userConfig` block; version `0.10.0`.
- `plugins/boss-dev/agent-harness/hooks/hooks.json` — `Notification`/`Stop`/`StopFailure` tmux entries.
- `.claude-plugin/marketplace.json` — `agent-harness` entry at `0.10.0`.
- `plugins/boss-dev/agent-harness/hooks/tmux_notify.py` — the notification hook (stdlib-only, PEP 723).
- `plugins/boss-dev/agent-harness/README.md` — prerequisites, toggle, bundle-id examples.
- Existing patterns mirrored: `hooks/notification.py` and `hooks/stop.py` (stdin JSON parse,
  graceful `exit 0`, PEP 723 shebang).

---

## Testing Strategy

All edge cases must be **silent and non-fatal** (the script always exits 0):

| Case | Expected behavior |
|---|---|
| Toggle unset / `false` (default) | Immediate `exit 0`, no notification |
| `Notification` type `auth_success` | tmux notifier does not fire (matcher-filtered); TTS unaffected |
| `Notification` type `permission_prompt` / `idle_prompt` / `elicitation_dialog` | Banner fires |
| `Stop` (normal turn end) | "Response finished" banner |
| `StopFailure` (`overloaded`) | "Turn failed — The turn ended on an API error (overloaded: …)" banner |
| `StopFailure` with empty `error_message` | Shows just `error_type` |
| Not inside tmux (`$TMUX` empty) | Notification fires, no click-jump action |
| `terminal-notifier` missing (macOS) | Falls to `notify-send`, then terminal bell |
| Linux homelab | `notify-send`; tmux target shown in body |
| Neither notifier present | Terminal bell + one tty line |
| Malformed/empty stdin JSON | Falls back to generic message text |

Manual recipes (from repo root):
```bash
# 1. Toggle OFF (default) → nothing, exit 0
echo '{"hook_event_name":"Notification","message":"test","session_id":"t1"}' \
  | uv run plugins/boss-dev/agent-harness/hooks/tmux_notify.py --event notification; echo "exit=$?"

# 2. Toggle ON, Notification → banner + click-jump
CLAUDE_PLUGIN_OPTION_TMUX_NOTIFICATIONS=true \
CLAUDE_PLUGIN_OPTION_TMUX_NOTIFY_ACTIVATE_BUNDLE_ID=com.mitchellh.ghostty \
  uv run plugins/boss-dev/agent-harness/hooks/tmux_notify.py --event notification \
  <<<'{"message":"Claude needs your input","session_id":"t2"}'

# 3. Stop event
CLAUDE_PLUGIN_OPTION_TMUX_NOTIFICATIONS=true \
  uv run plugins/boss-dev/agent-harness/hooks/tmux_notify.py --event stop \
  <<<'{"hook_event_name":"Stop","session_id":"t3"}'

# 4. StopFailure, toggle ON
CLAUDE_PLUGIN_OPTION_TMUX_NOTIFICATIONS=true \
  uv run plugins/boss-dev/agent-harness/hooks/tmux_notify.py --event stopfailure \
  <<<'{"hook_event_name":"StopFailure","error_type":"overloaded","error_message":"server busy","session_id":"f1"}'

# 5. StopFailure, toggle OFF → nothing, exit 0
echo '{"error_type":"rate_limit"}' \
  | uv run plugins/boss-dev/agent-harness/hooks/tmux_notify.py --event stopfailure; echo "exit=$?"

# 6. Simulate "no tmux"
env -u TMUX CLAUDE_PLUGIN_OPTION_TMUX_NOTIFICATIONS=true \
  uv run plugins/boss-dev/agent-harness/hooks/tmux_notify.py --event notification <<<'{"message":"hi"}'
```

End-to-end: enable `tmux_notifications` in plugin config, run Claude in a tmux pane, trigger a
plan-mode approval (`Notification`) and let a turn finish (`Stop`); confirm a banner appears and
clicking it jumps to the pane. Trigger an API error (`StopFailure`) and confirm a "Turn failed"
banner. Verify existing TTS/logging still works (proves parallel wiring didn't regress
`notification.py`/`stop.py`). Confirm an `auth_success` notification (e.g. after `/login`) does
**not** pop a tmux banner.

## Acceptance Criteria (v0.10.0)

- `plugin.json` declares the three `userConfig` keys; `tmux_notifications` defaults to `false`.
- `plugin.json` and the `marketplace.json` `agent-harness` entry are both at `0.10.0`.
- `hooks/tmux_notify.py` exists, is executable, exits 0 in every path, and accepts
  `--event notification|stop|stopfailure`.
- `hooks.json` tmux `Notification` entry uses `matcher: "permission_prompt|idle_prompt|elicitation_dialog"`.
- `hooks.json` has a `StopFailure` array invoking `tmux_notify.py --event stopfailure`.
- Existing `notification.py`/`stop.py` entries are unchanged.
- With the toggle off/unset, the script produces no output and no notification.
- With the toggle on inside tmux on macOS, a clickable notification appears and clicking it switches
  to the correct `session:window`.
- `auth_success` notifications do not trigger the tmux banner.
- A `StopFailure` event triggers a "Turn failed" banner with error detail.
- Graceful degradation verified for: no tmux, no terminal-notifier (Linux / bell), malformed JSON.
- README documents prerequisites, the toggle, bundle-id examples, and the three event types.

## Validation Commands

```bash
uv run python -m py_compile plugins/boss-dev/agent-harness/hooks/tmux_notify.py
python -c "import json; json.load(open('plugins/boss-dev/agent-harness/hooks/hooks.json'))"
python -c "import json; json.load(open('plugins/boss-dev/agent-harness/.claude-plugin/plugin.json'))"
python -c "import json; json.load(open('.claude-plugin/marketplace.json'))"
make lint
make verify-structure
```

## Notes

- No new Python dependencies — the script uses only stdlib (`argparse`, `json`, `os`, `shutil`,
  `subprocess`, `sys`), so the PEP 723 block needs no `dependencies`.
- `StopFailure`'s "output/exit code ignored" semantics are fine: the script's value is the
  side-effect (the banner), and it already exits 0.
- Deliberately out of scope: `SubagentStop`/`SubagentStart` (frequent, already TTS-wired),
  `TeammateIdle`, raw `Elicitation`/`ElicitationResult` (`elicitation_dialog` Notification covers
  the "MCP wants input" banner), and all tool-level events. Keeping the list narrow avoids
  notification spam.
- Linux click-to-jump is not supported (`notify-send` action buttons need a running listener) — tmux
  target is shown in the body instead. Documented as a limitation.
