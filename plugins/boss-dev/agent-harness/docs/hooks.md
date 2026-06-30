# Hooks Reference

The `hooks/` directory ships **14** lifecycle hook scripts (PEP 723, run via `uv`) **wired live**
through [`hooks/hooks.json`](../hooks/hooks.json). On `/plugin install` they are **active** — Claude
Code registers every event declared in that file (14 lifecycle events in total). This page lists each
event, what its script does, the supporting modules, the TTS/notification config, and how to turn
hooks on or off.

## Table of Contents

- [Are hooks active?](#are-hooks-active)
- [Lifecycle hooks](#lifecycle-hooks)
- [The Python auto-format hook](#the-python-auto-format-hook)
- [TTS and desktop notifications](#tts-and-desktop-notifications)
- [Supporting modules](#supporting-modules)
- [Enabling & disabling hooks](#enabling--disabling-hooks)
- [Logs](#logs)
- [Dependencies](#dependencies)

## Are hooks active?

**Yes — on install.** `hooks/hooks.json` wires all of the events below. Each entry invokes a script
with `uv run "${CLAUDE_PLUGIN_ROOT}"/hooks/<script>.py`. Most scripts default to logging and become
louder (TTS, context injection, LLM naming, desktop notifications) only when their optional flags and
credentials are present, so they're safe to leave on.

## Lifecycle hooks

| Event | Script | Matcher | Purpose |
| --- | --- | --- | --- |
| `PreToolUse` | [`pre_tool_use.py`](../hooks/pre_tool_use.py) | all | Block dangerous `rm -rf` and `.env` access; log tool calls. |
| `PostToolUse` | [`post_tool_use.py`](../hooks/post_tool_use.py) | all | Log successful tool executions. |
| `PostToolUse` | inline `jq` + `ruff` | `Edit\|MultiEdit\|Write` | Auto-lint and format edited Python files (see below). |
| `Notification` | [`notification.py`](../hooks/notification.py) | all | Log notifications; announce via TTS (`--notify`). |
| `Notification` | [`tmux_notify.py`](../hooks/tmux_notify.py) | `permission_prompt\|idle_prompt\|elicitation_dialog` | Fire a clickable desktop notification when the agent needs input. |
| `Stop` | [`stop.py`](../hooks/stop.py) | all | Log session stop; transcript export + TTS (`--chat`). |
| `Stop` | [`tmux_notify.py`](../hooks/tmux_notify.py) | all | Desktop notification when the agent finishes a turn. |
| `StopFailure` | [`tmux_notify.py`](../hooks/tmux_notify.py) | all | Desktop notification when a turn ends in failure. |
| `SubagentStop` | [`subagent_stop.py`](../hooks/subagent_stop.py) | all | Log subagent completion; summarize + announce via TTS (`--notify`). |
| `UserPromptSubmit` | [`user_prompt_submit.py`](../hooks/user_prompt_submit.py) | — | Log prompts (`--log-only`), store last prompt (`--store-last-prompt`), name the agent via an LLM (`--name-agent`). |
| `PreCompact` | [`pre_compact.py`](../hooks/pre_compact.py) | all | Log compaction; optionally back up the transcript. |
| `SessionStart` | [`session_start.py`](../hooks/session_start.py) | all | Log start; optionally inject git/project context or announce via TTS. |
| `SessionEnd` | [`session_end.py`](../hooks/session_end.py) | all | Log session end; optionally clean up stale temp files. |
| `PermissionRequest` | [`permission_request.py`](../hooks/permission_request.py) | all | Log permission requests (`--log-only`); auto-allow read-only operations. |
| `PostToolUseFailure` | [`post_tool_use_failure.py`](../hooks/post_tool_use_failure.py) | all | Log tool failures with error detail. |
| `SubagentStart` | [`subagent_start.py`](../hooks/subagent_start.py) | all | Log subagent spawns; optional TTS announcement. |
| `Setup` | [`setup.py`](../hooks/setup.py) | all | Check dependencies, detect project type, install packages for CI / `--init` runs. |

> Want to see a hook in action? Run [`/agent-harness:sentient`](./commands.md#sentient) — it
> attempts three `rm -rf` variants and the `PreToolUse` guard blocks each one.

## The Python auto-format hook

The second `PostToolUse` entry matches `Edit|MultiEdit|Write` and formats Python on the fly. It does
**not** call a plugin script — it's an inline shell pipeline:

```bash
jq -r '.tool_input.file_path' | while read file_path; do
  if [[ "$file_path" =~ \.py$ ]]; then
    uv run ruff check --fix "$file_path" && uv run ruff format "$file_path"
  fi
done
```

It reads the edited file path from the tool input via `jq`, and only acts on `.py` files. This is
why `jq` is a prerequisite (see [getting-started.md](./getting-started.md#step-1--prerequisites)).

## TTS and desktop notifications

The `Stop`, `SubagentStop`, and `Notification` scripts can **speak** their messages aloud. The TTS
backend is **offline `pyttsx3`** — it needs **no API key**. Two plugin user-config options control
the spoken output:

| Option | Type | Default | Effect |
| --- | --- | --- | --- |
| `ENABLE_TTS` | boolean | `true` | Speak completion/notification messages aloud. Set to a falsy value (`0`, `false`, `no`, or `off`) to silence **all** TTS (Stop, SubagentStop, Notification). |
| `ENGINEER_NAME` | string | _(empty)_ | Your name, used in ~30% of spoken messages. Leave blank to stay generic. |

These resolve through the shared helper [`hooks/utils/config.py`](../hooks/utils/config.py): it reads
the plugin user-config value `CLAUDE_PLUGIN_OPTION_<KEY>` first and falls back to a bare environment
variable of the same name, so `CLAUDE_PLUGIN_OPTION_ENABLE_TTS` and a plain `ENABLE_TTS` env var both
work (likewise for `ENGINEER_NAME`).

Separately, [`tmux_notify.py`](../hooks/tmux_notify.py) fires **clickable desktop notifications** that
jump you back to the exact tmux `session:window`. It's off by default and gated behind three more
user-config options:

| Option | Type | Default | Effect |
| --- | --- | --- | --- |
| `tmux_notifications` | boolean | `false` | Master switch. Requires `tmux` and `terminal-notifier` (macOS) or `notify-send` (Linux). |
| `tmux_notify_activate_bundle_id` | string | `com.mitchellh.ghostty` | macOS bundle id of your terminal so the notification raises it on click. Blank skips activation. |
| `tmux_notify_sound` | boolean | `false` | Play the default notification sound. Off keeps notifications silent. |

Set any of these via `/plugin` → **Configure** or as bare environment variables.

## Supporting modules

These are libraries the hook scripts import — not wired as events themselves.

- **`hooks/utils/config.py`** — the shared config resolver described above
  (`CLAUDE_PLUGIN_OPTION_<KEY>` with bare-env fallback; `tts_enabled()` and `engineer_name()`).
- **`hooks/validators/`** — `ruff_validator.py` and `ty_validator.py` lint and type-check Python
  after writes; `validate_new_file.py` and `validate_file_contains.py` assert a file was created or
  contains expected content. The latter two back the
  [`plan_w_team`](./commands.md#plan_w_team) Stop-hook checks (they confirm the generated spec
  exists and contains the required sections).
- **`hooks/utils/llm/`** — pluggable LLM backends (`oai.py`, `anth.py`, `ollama.py`) and
  `task_summarizer.py`, used to name agents and write completion summaries. Selected by available
  credentials; absent credentials degrade gracefully to no-op.
- **`hooks/utils/tts/`** — text-to-speech backends (`pyttsx3_tts.py` local/offline, `openai_tts.py`,
  `elevenlabs_tts.py`) and `tts_queue.py`, a file-lock queue that serializes overlapping
  announcements.

## Enabling & disabling hooks

Hooks are controlled entirely by [`hooks/hooks.json`](../hooks/hooks.json).

**To disable a hook:** remove (or comment out by deleting) its event block from `hooks.json`, then
reload the plugin. For example, to stop the TTS-on-stop behavior, delete the `Stop` entry — or just
set `ENABLE_TTS` to a falsy value to keep the logging but silence the speech.

**To make a hook quieter rather than off:** drop its flag. The TTS/LLM behaviors are opt-in via
flags like `--notify`, `--chat`, and `--name-agent` — removing the flag keeps logging but silences
the extra behavior. Desktop notifications stay off until you set `tmux_notifications`.

**To add a hook of your own**, add an entry pointing at a script with `${CLAUDE_PLUGIN_ROOT}`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|Write|Edit",
        "hooks": [
          { "type": "command", "command": "uv run \"${CLAUDE_PLUGIN_ROOT}\"/hooks/pre_tool_use.py" }
        ]
      }
    ]
  }
}
```

An empty `"matcher": ""` (or omitting it) matches all tools; a regex like `"Edit|Write"` scopes the
hook to specific tools.

## Logs

Hook runs write structured JSON to a `logs/` directory for auditing and debugging — useful for
seeing exactly which tools ran, which were blocked, and why.

## Dependencies

- **`uv`** — runs every hook script (PEP 723; dependencies auto-resolved).
- **`jq`** — required by the Python auto-format `PostToolUse` hook.
- **Optional `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`** (or local Ollama) — enable LLM agent naming and
  summaries.
- **Optional TTS backend** — offline `pyttsx3` (no key), OpenAI, or ElevenLabs for spoken
  announcements; toggle with `ENABLE_TTS`.
- **Optional `tmux` + `terminal-notifier`/`notify-send`** — for the `tmux_notify.py` desktop
  notifications (enable `tmux_notifications`).
</content>
