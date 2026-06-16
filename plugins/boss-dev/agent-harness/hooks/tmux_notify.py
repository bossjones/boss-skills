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
