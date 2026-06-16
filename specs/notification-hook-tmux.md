# Spec: tmux-aware desktop notifications for `agent-harness` (with install-time on/off toggle)

## Context

The user runs Claude Code inside **tmux on macOS** (and has Linux homelab boxes). Claude Code's built-in desktop notifications don't pass through tmux (it sends plain OSC sequences; tmux requires DCS passthrough — a known open issue), so after plan-mode approval or a permission prompt there's no reliable signal that the agent needs input, and no way to jump to the right tmux window.

Claude Code fires two relevant lifecycle hooks:
- **`Notification`** — when Claude is waiting for input (after plan-mode approval, permission requests, etc.)
- **`Stop`** — when Claude finishes responding.

A hook-based notifier sidesteps the OSC/tmux issue entirely: the hook script captures the tmux context from `$TMUX` / `$TMUX_PANE`, fires a desktop notification, and (on macOS) attaches a click action that runs `tmux switch-client`/`select-window` to jump to the exact `session:window` where Claude is waiting.

The intended outcome: when you install the `boss-skills` marketplace, you can flip **one config toggle** to turn tmux desktop notifications on/off. Default **off** so users without tmux/terminal-notifier are unaffected.

## Objective

Add an opt-in, tmux-aware desktop-notification capability to the existing **`agent-harness`** plugin, controlled by a per-plugin **`userConfig`** toggle surfaced at install/configure time, wired into the plugin's existing `Notification` and `Stop` hooks without regressing current behavior.

## Problem Statement

There is currently no way to know — while working in another tmux window — that Claude has finished a turn or is blocked waiting for input. The built-in notification path is broken under tmux. We need a notification that (a) is reliable under tmux, (b) is clickable to jump to the right pane on macOS, (c) degrades gracefully on Linux and when optional tools are missing, and (d) is **off by default** and toggleable through the documented plugin user-configuration mechanism rather than manual settings edits.

## Solution Approach

- Add a **new standalone Python hook script** `hooks/tmux_notify.py` (PEP 723, matching the repo's existing hook convention) to the `agent-harness` plugin.
- Declare a **`userConfig`** block in the plugin's `plugin.json` with a boolean enable toggle plus two optional knobs (terminal bundle id to focus, notification sound). This is the first `userConfig` in the repo.
- Gate the script with the exported env var **`CLAUDE_PLUGIN_OPTION_TMUX_NOTIFICATIONS`** — the hook always runs but exits immediately (silent no-op) unless the toggle is on.
- Wire the script as **parallel** hook entries under the existing `Notification` and `Stop` arrays so the current Python TTS/logging hooks are untouched.
- Bump the plugin **minor** version in both `plugin.json` and `marketplace.json` (0.5.0 → 0.6.0).

### Design decisions (confirmed with the user)
| Decision | Choice |
|---|---|
| Plugin home | **`agent-harness`** (already owns the `Notification`/`Stop` hooks) |
| Script language | **Python (PEP 723)** — matches repo convention; run via `uv run --script` |
| Platforms | **macOS (`terminal-notifier`) + Linux fallback (`notify-send`)**, then terminal bell |
| Terminal focus | **Configurable bundle id, default `com.mitchellh.ghostty`** |

## Relevant Files

- `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json` — add `userConfig` block; bump `version` 0.5.0 → 0.6.0.
- `plugins/boss-dev/agent-harness/hooks/hooks.json` — append parallel hook objects to `Notification` and `Stop` arrays.
- `.claude-plugin/marketplace.json` — bump `agent-harness` entry `version` 0.5.0 → 0.6.0 (parity required by `version-bump-reviewer`).
- `plugins/boss-dev/agent-harness/README.md` — document prerequisites, toggle, and bundle-id examples.
- Existing patterns to mirror: `plugins/boss-dev/agent-harness/hooks/notification.py` and `hooks/stop.py` (stdin JSON parse, graceful `exit 0`, PEP 723 shebang `#!/usr/bin/env -S uv run --script`).

### New Files

- `plugins/boss-dev/agent-harness/hooks/tmux_notify.py` — the notification hook (full source below).

## Verified grounding facts

- `plugin.json` is at `0.5.0`, **no** `userConfig` field today. Marketplace mirrors `0.5.0`.
- `hooks.json` already wires `Notification → notification.py --notify` and `Stop → stop.py --chat`, and contains an inline **bash** PostToolUse hook — so non-trivial hook commands are an accepted convention.
- Real `Notification` event JSON on stdin: `session_id`, `transcript_path`, `cwd`, `hook_event_name`, `message`, `notification_type` (e.g. `"permission_prompt"`). `Stop` events: `session_id`, `transcript_path`, `cwd`, `hook_event_name`, `stop_hook_active`.
- Per Claude Code docs: `userConfig` lives in `.claude-plugin/plugin.json`; each value is exported to plugin subprocesses as `CLAUDE_PLUGIN_OPTION_<KEY-UPPERCASED>` (booleans arrive as the strings `"true"`/`"false"`), and is also substitutable in command strings as `${user_config.KEY}`. `${CLAUDE_PLUGIN_ROOT}` resolves to the plugin install dir.

## Why a separate script + env-var gate (not folding into `notification.py`)

- **Orthogonal concern.** tmux/terminal-notifier logic shares nothing with `notification.py`'s TTS/LLM utils. A separate file keeps the existing `tests/` suite valid and prevents the tmux path from regressing TTS/logging.
- **Fail-safe off-state.** The hook always runs (Claude Code has no conditional-hook mechanism); gating on `CLAUDE_PLUGIN_OPTION_TMUX_NOTIFICATIONS` inside the script means unset/false → immediate `exit 0`. This is also true for older Claude Code versions that ignore `userConfig` (env var unset → treated as off).
- **Testable in isolation.** `CLAUDE_PLUGIN_OPTION_TMUX_NOTIFICATIONS=true uv run tmux_notify.py --event notification < event.json` exercises it without Claude Code's substitution engine.

## Step by Step Tasks

IMPORTANT: Execute every step in order, top to bottom.

### 1. Add `userConfig` to `plugin.json` and bump version
- In `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json`, change `"version": "0.5.0"` → `"0.6.0"`.
- Add this top-level `userConfig` object (e.g. after `"keywords"`):

```json
  "userConfig": {
    "tmux_notifications": {
      "type": "boolean",
      "title": "tmux desktop notifications",
      "description": "Fire a clickable macOS/Linux desktop notification when the agent needs input or finishes, that jumps you to the exact tmux session:window. Requires tmux and terminal-notifier (macOS) or notify-send (Linux). Default off.",
      "default": false,
      "required": false
    },
    "tmux_notify_activate_bundle_id": {
      "type": "string",
      "title": "Terminal app bundle id (macOS)",
      "description": "macOS bundle identifier of your terminal so the notification raises it on click (e.g. com.mitchellh.ghostty, com.googlecode.iterm2, dev.warp.Warp, com.apple.Terminal). Leave blank to skip activation.",
      "default": "com.mitchellh.ghostty",
      "required": false
    },
    "tmux_notify_sound": {
      "type": "boolean",
      "title": "Play notification sound",
      "description": "Play the default notification sound (macOS terminal-notifier -sound default). Off keeps notifications silent.",
      "default": false,
      "required": false
    }
  }
```

Resulting env vars: `CLAUDE_PLUGIN_OPTION_TMUX_NOTIFICATIONS`, `CLAUDE_PLUGIN_OPTION_TMUX_NOTIFY_ACTIVATE_BUNDLE_ID`, `CLAUDE_PLUGIN_OPTION_TMUX_NOTIFY_SOUND`. None are secrets, so no `sensitive: true`.

### 2. Bump the marketplace entry
- In `.claude-plugin/marketplace.json`, set the `agent-harness` plugin entry `"version"` to `"0.6.0"` to keep parity with `plugin.json`.

### 3. Create `hooks/tmux_notify.py`
- Add the new file with the full source below. Keep the PEP 723 shebang and `chmod +x`.

```python
#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.13"
# ///
"""tmux-aware desktop notification hook for agent-harness.

Fires a clickable desktop notification (macOS terminal-notifier or Linux
notify-send) when Claude needs input (Notification) or finishes (Stop).
Clicking the macOS notification runs ``tmux switch-client`` to jump to the
exact session:window where Claude is waiting.

Invoked from hooks.json as::

    uv run "${CLAUDE_PLUGIN_ROOT}"/hooks/tmux_notify.py --event notification
    uv run "${CLAUDE_PLUGIN_ROOT}"/hooks/tmux_notify.py --event stop

Hook event JSON arrives on stdin. Gated by the user_config toggle
CLAUDE_PLUGIN_OPTION_TMUX_NOTIFICATIONS (default off). This script must never
fail the hook chain: it always exits 0 and swallows every error.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys

TRUTHY = {"true", "1", "yes", "on"}


def _flag(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).strip().lower() in TRUTHY


def enabled() -> bool:
    return _flag("CLAUDE_PLUGIN_OPTION_TMUX_NOTIFICATIONS")


def read_event() -> dict:
    try:
        return json.loads(sys.stdin.read() or "{}")
    except (json.JSONDecodeError, ValueError):
        return {}


def tmux_context() -> tuple[str, str] | None:
    """Return (socket, "session:window") for the current pane, or None.

    None means "not inside tmux / tmux unavailable" -> notify without a
    click-to-jump action.
    """
    tmux_env = os.environ.get("TMUX", "")
    if not tmux_env or not shutil.which("tmux"):
        return None
    socket = tmux_env.split(",", 1)[0]  # TMUX == "<socket>,<pid>,<session>"
    pane = os.environ.get("TMUX_PANE", "")
    cmd = ["tmux", "-S", socket, "display-message", "-p"]
    if pane:
        cmd += ["-t", pane]
    cmd += ["#{session_name}:#{window_index}"]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout.strip()
    except (subprocess.SubprocessError, OSError):
        return None
    return (socket, out) if out else None


def build_text(event: str, payload: dict) -> tuple[str, str, str]:
    """Return (title, subtitle, message) for the given event."""
    if event == "stop":
        return ("Claude Code", "Response finished", "Claude finished and is ready for your next instruction.")
    message = (payload.get("message") or "").strip() or "Claude needs your input."
    return ("Claude Code", "Waiting for you", message)


def notify_macos(title: str, subtitle: str, message: str, group: str, ctx: tuple[str, str] | None) -> bool:
    if not shutil.which("terminal-notifier"):
        return False
    args = ["terminal-notifier", "-title", title, "-subtitle", subtitle, "-message", message, "-group", group]
    if _flag("CLAUDE_PLUGIN_OPTION_TMUX_NOTIFY_SOUND"):
        args += ["-sound", "default"]
    bundle = os.environ.get("CLAUDE_PLUGIN_OPTION_TMUX_NOTIFY_ACTIVATE_BUNDLE_ID", "").strip()
    if bundle:
        args += ["-activate", bundle]
    if ctx:
        socket, target = ctx
        # Click action: jump to the exact tmux session:window via the same socket.
        execute = f"tmux -S '{socket}' switch-client -t '{target}' \\; select-window -t '{target}'"
        args += ["-execute", execute]
    try:
        subprocess.run(args, capture_output=True, timeout=10)
        return True
    except (subprocess.SubprocessError, OSError):
        return False


def notify_linux(title: str, subtitle: str, message: str, ctx: tuple[str, str] | None) -> bool:
    if not shutil.which("notify-send"):
        return False
    body = message
    if ctx:  # notify-send has no click-to-execute; surface the target as text.
        body = f"{message}\ntmux: {ctx[1]}"
    try:
        subprocess.run(["notify-send", f"{title} — {subtitle}", body], capture_output=True, timeout=10)
        return True
    except (subprocess.SubprocessError, OSError):
        return False


def notify_bell(subtitle: str, message: str) -> None:
    """Last resort: terminal bell + one line to the controlling tty."""
    try:
        with open("/dev/tty", "w") as tty:
            tty.write(f"\a{subtitle}: {message}\n")
    except OSError:
        pass


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", choices=["notification", "stop"], default="notification")
    args, _ = parser.parse_known_args()

    if not enabled():  # toggle gate: silent no-op unless opted in
        return

    payload = read_event()
    title, subtitle, message = build_text(args.event, payload)
    group = f"claude-code-{payload.get('session_id') or 'default'}"
    ctx = tmux_context()

    if notify_macos(title, subtitle, message, group, ctx):
        return
    if notify_linux(title, subtitle, message, ctx):
        return
    notify_bell(subtitle, message)


if __name__ == "__main__":
    try:
        main()
    except Exception:  # never fail the hook chain
        pass
    sys.exit(0)
```

### 4. Wire parallel hook entries in `hooks.json`
- Append a **second** hook object to the existing `Notification` array (leave the existing `notification.py --notify` object first):

```json
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "uv run \"${CLAUDE_PLUGIN_ROOT}\"/hooks/tmux_notify.py --event notification"
          }
        ]
      }
```

- Append a **second** hook object to the existing `Stop` array:

```json
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "uv run \"${CLAUDE_PLUGIN_ROOT}\"/hooks/tmux_notify.py --event stop"
          }
        ]
      }
```

### 5. Update the plugin README
- In `plugins/boss-dev/agent-harness/README.md`, document: prerequisites (`tmux`; `brew install terminal-notifier` on macOS, `notify-send`/`libnotify` on Linux), the three `userConfig` knobs, default-off behavior, and example bundle ids.

### 6. Validate
- Run repo structure/lint checks and the manual test recipes (see Testing Strategy and Validation Commands).

## Testing Strategy

All edge cases must be **silent and non-fatal** (the script always exits 0):

| Case | Expected behavior |
|---|---|
| Toggle unset / `false` (default) | Immediate `exit 0`, no notification — invisible to existing users |
| Older Claude Code ignoring `userConfig` | Env var unset → off → no-op |
| Not inside tmux (`$TMUX` empty) | Notification fires, no click-jump action |
| `tmux` not installed | Same graceful degradation as above |
| `terminal-notifier` missing (macOS) | Falls to `notify-send`, then `/dev/tty` bell |
| Linux homelab box | `notify-send`; tmux target shown in body (no click-to-jump) |
| Neither notifier present | Terminal bell + one line to tty; swallowed if no tty |
| Malformed/empty stdin JSON | Falls back to generic message text |
| Non-default tmux socket / multiple servers | `tmux -S "$socket"` (derived from `$TMUX`) targets the correct server for both query and click |
| Many `Stop` events | `-group claude-code-<session_id>` coalesces per session on macOS |

Manual recipes (run from repo root):

```bash
# 1. Toggle OFF (default) -> nothing, exit 0
echo '{"hook_event_name":"Notification","message":"test","session_id":"t1"}' \
  | uv run plugins/boss-dev/agent-harness/hooks/tmux_notify.py --event notification; echo "exit=$?"

# 2. Toggle ON, inside a tmux pane -> clickable macOS banner that jumps
CLAUDE_PLUGIN_OPTION_TMUX_NOTIFICATIONS=true \
CLAUDE_PLUGIN_OPTION_TMUX_NOTIFY_ACTIVATE_BUNDLE_ID=com.mitchellh.ghostty \
  uv run plugins/boss-dev/agent-harness/hooks/tmux_notify.py --event notification \
  <<<'{"message":"Claude needs your input","session_id":"t2"}'

# 3. Stop event variant
CLAUDE_PLUGIN_OPTION_TMUX_NOTIFICATIONS=true \
  uv run plugins/boss-dev/agent-harness/hooks/tmux_notify.py --event stop \
  <<<'{"hook_event_name":"Stop","session_id":"t3","stop_hook_active":true}'

# 4. Simulate "no tmux"
env -u TMUX CLAUDE_PLUGIN_OPTION_TMUX_NOTIFICATIONS=true \
  uv run plugins/boss-dev/agent-harness/hooks/tmux_notify.py --event notification <<<'{"message":"hi"}'
```

End-to-end: enable `tmux_notifications` in plugin config, run Claude in a tmux pane, trigger a plan-mode approval (`Notification`) and let a turn finish (`Stop`); confirm a banner appears and clicking it jumps to the pane. Verify existing TTS/logging still works (proves parallel wiring didn't regress `notification.py`/`stop.py`).

## Acceptance Criteria

- `plugin.json` declares the three `userConfig` keys; `tmux_notifications` defaults to `false`.
- `plugin.json` and the `marketplace.json` `agent-harness` entry are both at `0.6.0`.
- `hooks/tmux_notify.py` exists, is executable, and exits 0 in every path.
- `hooks.json` runs `tmux_notify.py` as a parallel entry under both `Notification` and `Stop`; existing `notification.py`/`stop.py` entries are unchanged.
- With the toggle off/unset, the script produces no output and no notification.
- With the toggle on inside tmux on macOS, a clickable notification appears and clicking it switches to the correct `session:window`.
- Graceful degradation verified for: no tmux, no terminal-notifier (Linux path / bell), malformed JSON.
- README documents prerequisites, the toggle, and bundle-id examples.

## Validation Commands

- `uv run python -m py_compile plugins/boss-dev/agent-harness/hooks/tmux_notify.py` — script compiles.
- `python -c "import json,sys; json.load(open('plugins/boss-dev/agent-harness/.claude-plugin/plugin.json'))"` — plugin.json is valid JSON.
- `python -c "import json; json.load(open('plugins/boss-dev/agent-harness/hooks/hooks.json'))"` — hooks.json is valid JSON.
- `python -c "import json; json.load(open('.claude-plugin/marketplace.json'))"` — marketplace.json is valid JSON.
- `make lint` — ruff/codespell (note: `tmux_notify.py` lives under `plugins/` which is linted).
- Manual recipes 1–4 above (toggle off = silent; toggle on = notifies).
- Run the repo's plugin-structure verification script if present (e.g. `./scripts/verify-structure.py`) to confirm plugin/marketplace parity.

## Notes

- No new Python dependencies — the script uses only stdlib (`argparse`, `json`, `os`, `shutil`, `subprocess`, `sys`), so the PEP 723 block needs no `dependencies`.
- The hook invocation uses `uv run "${CLAUDE_PLUGIN_ROOT}"/hooks/tmux_notify.py` (matching every other hook), so it does not depend on the executable bit.
- This is the first `userConfig` in the repo; the `version-bump-reviewer` skill treats a feature-bearing plugin file + new hook wiring as a **minor** bump, and requires `plugin.json`/`marketplace.json` version parity.
- Out of scope for v0.6.0: a bats/pytest harness for the bash-shaped behavior, and Linux click-to-jump (notify-send action buttons need a running listener). Documented as limitations.
