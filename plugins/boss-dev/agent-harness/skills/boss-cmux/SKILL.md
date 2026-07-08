---
name: boss-cmux
description: Drive cmux — the terminal multiplexer / agent-surface control CLI — from natural language. Use this whenever a prompt asks you to open, inspect, prompt, read, or tear down cmux windows, workspaces, panes, surfaces, or agent sessions. Prefix orchestration prompts with /boss-cmux.
argument-hint: "[what to do in cmux]"
allowed-tools: Bash
---

# boss-cmux

## Purpose

You are driving **cmux**, a CLI + socket for controlling terminal surfaces (and the
agents running inside them). Every window, workspace, pane, and surface is a real,
addressable object you can spawn, prompt, read, and close from the command line.

## Prerequisites

cmux is a native **macOS** terminal (built on Ghostty) distributed as a Homebrew cask.
The skill triggers anywhere, but only functions on a Mac with cmux installed.

- **Install:** `brew tap manaflow-ai/cmux && brew install --cask cmux` (macOS 14+
  Sonoma). Validated against cmux `0.64.17`.
- **CLI on PATH (optional):** so `cmux` works outside the app,
  `sudo ln -sf "/Applications/cmux.app/Contents/Resources/bin/cmux" /usr/local/bin/cmux`.
- **Notification hooks:** run `cmux hooks setup` once so `pi`/`codex`/`gemini` emit a
  turn-stop event you can wait on (see **Wait for agents via notification events**).
  Claude Code has no such hook — cmux instead bridges Claude's own model-initiated
  `PushNotification` tool call, which only fires if the model decides to call it (see
  the caveat under **Wait for agents via notification events**).
- **Socket control (orchestrator outside cmux):** set `automation.socketControlMode`
  to `allowAll` (or password) in `~/.config/cmux/cmux.json` so an orchestrator running
  in a plain terminal can drive the socket. The socket lives at
  `~/.local/state/cmux/cmux.sock` (`CMUX_SOCKET_PATH`). Enabling this is a genuine
  security surface (any local process can then drive the app) — confirm with the
  user before flipping it, the way you would for any other risky config change.
  - **Reload bootstrap problem:** if the app is currently `cmuxOnly` and you edit the
    file to `allowAll`, `cmux reload-config` (and every other socket command) still
    fails with `Failed to write to socket (Broken pipe, errno 32)` until the running
    app re-reads the file — but `reload-config` itself needs socket access, so the
    CLI can't bootstrap its own permission change. There's no signal-based or
    file-watch reload from outside; ask the user to reload manually inside the app
    (⌘⇧, / "reload configuration") or quit and reopen cmux, then retry.
- **Editing cmux settings safely:** `cmux docs settings` prints the schema/paths.
  Before editing `~/.config/cmux/cmux.json`, copy it to a timestamped `.bak` beside it
  so the user can revert; after editing, run `cmux reload-config` (reloads **both**
  `cmux.json` and Ghostty's `~/.config/ghostty/config` in place — no app restart).
  App behavior (sidebar, notifications, automation, workspace colors, cmux shortcuts)
  lives in `cmux.json`; terminal rendering (font, cursor, theme, scrollback,
  `background-opacity`, `background-blur`) belongs in the Ghostty config.

Only the repo-local skill is required to *drive* cmux. For the deeper published skill set
(browser automation, settings, diagnostics, markdown viewer, etc.) install the vendor
skills globally: `npx skills add manaflow-ai/cmux -g -y`.

> This skill installs as `agent-harness:boss-cmux`. If you also `npx skills add` the vendor
> `cmux` skill globally, the namespaces keep them distinct.

## Instructions

### Discover commands first (`--help`)

Before doing anything, run:

```bash
cmux --help
```

Then drill into any subcommand you intend to use:

```bash
cmux <command> --help     # e.g. cmux workspace --help, cmux send --help
```

cmux evolves; **trust `--help` over memory**. Never guess flags — confirm them.

### Understand the hierarchy

Everything nests in one tree. Learn the boxes and the verbs fall out:

- **Window** → a top-level OS window.
- **Workspace** → a sidebar entry ("tab") inside a window.
- **Pane** → a split region within a workspace.
- **Surface** → a tab within a pane (a terminal or a browser).

Use `cmux tree --all` (or `cmux workspace list` / `cmux list-pane-surfaces`) to see
the current state before you act.

### Create a workspace and inject credentials (`--env-file`)

Create a workspace and capture BOTH refs in one call. `--json` returns the
`workspace_ref` and the initial `surface_ref` — grab and thread them; never guess
positional refs.

```bash
cmux workspace create --name <name> --cwd <dir> --env-file .env --json
```

- **`cmux workspace create` supports `--env-file`, which loads that file's
  environment variables into every surface in the workspace** — so an agent
  launched in a pane (`claude`, `pi`, `codex`, `gemini`) comes up already
  authenticated, no manual `export` needed.
- **Default `--env-file` to `.env`** (the repo's `.env`) unless told otherwise:
  `--env-file .env`. That is the canonical source for `OPENROUTER_API_KEY`,
  `ANTHROPIC_API_KEY`, etc.
- Pair it with `--layout <compact-json>` to boot a whole multi-pane team
  declaratively in one call (each pane's `command` auto-launches its agent).
- **Don't inject over a working login.** If an agent is already authenticated
  (e.g. Claude Code), don't push a placeholder key over it via `--env-file`;
  scope credential injection to the agents that actually need it.
- **Assume the keys are already set up — and never read their values.** By
  default, just point `--env-file` at `.env` and proceed; do not `cat .env`,
  `echo $OPENROUTER_API_KEY`, or `read-screen` a surface to capture a key. **Only
  if an agent actually fails to authenticate** should you validate, and do it
  *safely*: `cmux workspace env --workspace <ref> --mask` shows that a var is
  present without revealing it, and `[ -n "$VAR" ]` confirms it is non-empty.
  Report the masked/presence result, never the secret itself.
- **Subscribe to events immediately, before sending any prompt.** The `--json` output
  gives you the workspace's `workspace_id` right away — start the `cmux events`
  listener for it in the background *now*, not when you're about to wait on an agent.
  Late subscription is how you miss a turn-done signal:

  ```bash
  WS=<workspace_id from --json>
  cmux events --name notification.requested --no-heartbeat --no-ack > /tmp/cmux-$WS.ev &
  ```

  See **Wait for agents via notification events** below for the full pattern —
  including why Claude Code needs a different completion signal than pi/codex/gemini.

### The control loop

You operate surfaces the way a person would, but over the CLI:

- `cmux send --surface <ref> "<text>"` — type text into a surface.
- `cmux send-key --surface <ref> enter` — submit it (press a key). **`send` types; `send-key` submits — they are separate steps.**
- `cmux read-screen --surface <ref>` — read what's on screen (add `--scrollback` for history). This is your eyes.
- `cmux close-surface --surface <ref>` — end a surface cleanly.

### Wait for agents via notification events (don't busy-poll) — pi/codex/gemini only

Instead of looping on `read-screen`, subscribe to cmux's push channel and block
until an agent finishes its turn. **This is deterministic for pi and codex** — read
the next section before relying on it for Claude Code.

**`cmux events` is the wait channel — not `cmux wait-for`.** `cmux wait-for <name>`
is an unrelated *named-token rendezvous* (a manual semaphore you signal yourself);
it does **not** know when an agent finishes. The agent-completion signal is the
`notification` event category.

**Prerequisite — install the notification hooks once:**

```bash
cmux hooks setup            # wires pi, codex, opencode, gemini, … to emit on turn-stop
# or per agent:  cmux hooks pi install   /   cmux hooks codex install
```

These agents get a hook that fires deterministically on every turn-stop. Without it,
an agent stays silent and you're back to polling — so install hooks before relying on
the wait. **Claude Code is different — see the next section**, it has no turn-stop
hook and is not covered by `cmux hooks setup`.

**What an agent emits when its turn ends** — one event per completed turn:

```json
{ "name": "notification.requested", "category": "notification",
  "workspace_id": "120FC732-…", "surface_id": null, "seq": 1512, … }
```

Match on **`workspace_id`** — for hook-emitted notifications `surface_id` is usually
`null`, but `workspace_id` is always set. The title/body are **redacted** in the
event (you get the signal, not the text), so once it fires, `read-screen` that
workspace's surface for the actual reply. Filter to `--name notification.requested`;
a sibling `notification.clear_requested` fires when a surface gains focus and is just
noise.

**Block until a specific agent finishes** (capture its `workspace_id` first via
`cmux list-workspaces --json --id-format both`) — you should already have this
listener running from **Create a workspace** above, started before the first prompt:

```bash
WS=<agent-workspace-uuid>
# Listener already started at workspace-creation time (see above). If not, start it now,
# BEFORE sending the prompt:
cmux events --name notification.requested --no-heartbeat --no-ack > /tmp/cmux.ev &
EV=$!
cmux send --surface <ref> "<task>"; cmux send-key --surface <ref> enter
# wait (bounded) for this workspace's turn-done event
until grep -q "\"workspace_id\":\"$WS\"" /tmp/cmux.ev; do sleep 1; done
kill $EV
cmux read-screen --surface <ref> --scrollback --lines 40   # now read the reply
```

Pitfall: a `cmux events | jq … &` pipeline in a one-liner can stall on stdout
buffering — stream to a **file** and poll the file (above), or pass
`jq --unbuffered`. For a durable cursor across reconnects use
`cmux events --cursor-file <path> --reconnect`.

### Claude Code: use a completion marker, not the notification event

Claude Code has **no deterministic turn-stop hook** like pi/codex/gemini, so
`cmux hooks setup` doesn't cover it. Instead, cmux bridges Claude's own
model-initiated `PushNotification` tool call through a `PostToolUse` hook into a cmux
notification — see [cmux's `agent-hooks.md`](https://github.com/manaflow-ai/cmux/blob/main/docs/agent-hooks.md).
That means a notification only appears if **both** are true: "Claude Code
integration" is enabled in cmux's app Settings, **and** the model itself decides to
call `PushNotification` during that turn. A scripted, task-oriented sub-agent that's
never told to proactively "notify the user" typically never calls it — so
`cmux events` shows heartbeats only, with no `notification.requested` ever arriving.
That's expected behavior, not a broken integration — don't spend time debugging hooks
setup for it.

**Default to a printed completion marker for Claude Code** — the same contract
`agent-harness:boss-cmux-team` already uses for its workers:

1. Tell the agent, in its prompt, to end with one distinctive line when truly done,
   e.g. `TASK-DONE: <summary>`.
2. Poll `read-screen` for that marker on a bounded loop (still fine to race it against
   the notification listener as a free early exit — just don't make the loop's exit
   condition depend on the notification alone):

   ```bash
   for i in $(seq 1 60); do
     cmux read-screen --surface <ref> --lines 5 | grep -q "TASK-DONE:" && break
     sleep 5
   done
   cmux read-screen --surface <ref> --scrollback --lines 40
   ```

3. If the marker never appears within the bound, treat it as "possibly slow, or the
   model never got to it," not "cmux is broken" — `read-screen` to see what's
   actually on screen before deciding.

Separately: a Claude Code notification, when it does fire, still doesn't mean the task
succeeded — see the caveat under **Launching Claude Code** below.

### Launching the pi agent

`pi` is an interactive TUI agent — launch it as `pi --model … "<task>"`.

- Launch it **inside a pane** (via `cmux send` + `send-key enter`), not from your
  own non-interactive/batch shell.

### Launching Codex — run it in yolo / auto mode

When launching **Codex** in a pane, start it unattended so it doesn't stall on
approval prompts (it's running inside cmux, driven by an orchestrator). Pass the
flag at launch — do **not** edit Codex's global config:

- **Yolo (full, no sandbox):** `codex --dangerously-bypass-approvals-and-sandbox "<task>"`
  — skips every approval prompt and the sandbox. Use only because the run is
  orchestrated/observed.
- **Auto (sandboxed):** `codex --full-auto "<task>"` — automatic execution inside a
  workspace-write sandbox; safer when full access isn't needed.

Default to yolo for hands-off fleet runs; reach for `--full-auto` when you want a
sandbox. These are per-launch flags, so they never change the user's global Codex setup.

**Always launch Codex with the `gpt-5.5` model unless a prompt specifies otherwise** —
pass `-m gpt-5.5` at launch, e.g. `codex -m gpt-5.5 --dangerously-bypass-approvals-and-sandbox "<task>"`.
If a prompt names a different Codex model/effort, use that instead; gpt-5.5 is just the default.

### Launching Claude Code — use cc bypass mode

Plain `claude` launches in **ask-for-permission mode**: it will *decline* to run
Bash/edits and instead print instructions, then end its turn. For a hands-off fleet
agent, launch it the same way you yolo Codex — bypass permissions at launch:

- **cc bypass:** `claude --dangerously-skip-permissions "<task>"` — Claude's
  equivalent of Codex yolo. The composer then shows `⏵⏵ bypass permissions on` and it
  executes shell/edits without prompting. (`--dangerously-skip-permissions` is a
  per-launch flag; it doesn't change global Claude settings.)

Caveat verified in testing: on the rare turn where a Claude Code notification *does*
fire, it fires on turn-completion **even when Claude refused to do the work** — so if
you only watch events, you can mistake a "declined, nothing happened" turn for success.
Always `read-screen` (or check the artifacts), don't trust the event alone. More
fundamentally, Claude Code's cmux notification is bridged from a model-initiated
`PushNotification` tool call, not a deterministic turn-stop hook, so most turns emit no
notification at all — default to the completion-marker pattern instead; see
**Claude Code: use a completion marker, not the notification event** above.

### Best practices

1. **`--help` before every unfamiliar verb.** Confirm the subcommand and flags exist.
2. **Look before you leap.** Inspect with `tree` / `list` / `read-screen` before sending or closing anything.
3. **Refs are positional and renumber.** `surface:N` / `workspace:N` shift as things open and close. Re-read the tree right before you act; for anything long-lived, anchor to a **stable window UUID**, not a positional ref.
4. **Type then submit.** A prompt isn't sent until you `send-key enter`. Give agents a beat before you `read-screen` their reply.
5. **Read back to verify.** After sending a command, `read-screen` to confirm it actually ran and got the result you expected — don't assume.
6. **Close scoped, never broad.** Close only surfaces you just created or explicitly identified. Never loop a close over the whole `tree` — you'll kill things you didn't mean to. `close`/`close-window` may no-op while a live agent occupies a pane; use `close-surface` per pane.
7. **One window per team.** Keep a unit of work to a single window so it stays monitorable and tearable as a unit.
8. **Never print secrets.** If a surface has credentials/keys loaded, read results back without echoing the secret values.
9. **Prefer push over poll for pi/codex/gemini; use a completion marker for Claude Code.** Subscribe to `cmux events --category notification` the instant the workspace is created (before the first prompt), matched on `workspace_id`. This is a deterministic turn-stop signal for pi/codex/gemini (install hooks first: `cmux hooks setup`) — but Claude Code has no such hook, so default to the printed-marker pattern for it instead of waiting on the event (see **Claude Code: use a completion marker, not the notification event**). `cmux wait-for` is a manual named-token semaphore, **not** an agent-finished signal, for either case.

## Workflows

### Drive a surface end-to-end

The default loop for any single-surface task: discover, inspect, act, verify, report.

1. `cmux --help` (and per-subcommand `--help`) to confirm the verbs.
2. Inspect current state (`tree --all` / `workspace list`).
3. Take the action (create / send + send-key / read).
4. Read back to verify the result.
5. Report concisely what happened, citing the surfaces/refs involved.

## Topology & routing

Beyond the send/read/close control loop, cmux has a full set of placement verbs for
deterministic multi-pane layouts — `move-surface`, `reorder-surface`, `split-off`,
`new-surface --type terminal|browser`, `focus-pane`/`focus-panel`, `surface-health`,
and `--id-format uuids|both` for stable UUID output. Surface identity is stable across
move/reorder/split-off. See the deep-dive references below.

Note: some verbs come in two forms — a namespaced `cmux workspace <verb>` (e.g. `workspace
create`, `workspace list`) used above, and flat aliases (`new-workspace`, `list-workspaces`,
`select-workspace`, `close-workspace`) used in the references. Both work; when in doubt,
confirm the exact spelling with `--help` (which is authoritative over either form here).

## Deep-Dive References

| Reference | When to Use |
|-----------|-------------|
| [references/handles-and-identify.md](references/handles-and-identify.md) | Handle syntax, self-identify, caller targeting, `--id-format` output shaping |
| [references/windows-workspaces.md](references/windows-workspaces.md) | Window/workspace lifecycle and reorder/move |
| [references/panes-surfaces.md](references/panes-surfaces.md) | Splits, surfaces, move/reorder, focus routing |
| [references/trigger-flash-and-health.md](references/trigger-flash-and-health.md) | Flash cue and surface health checks |

For team orchestration (spawn/orient/drive a multi-agent team), see the
`agent-harness:boss-cmux-team` skill.

## Report Format

Report concisely in plain English: what you did, the surfaces/refs involved, and
what `read-screen` confirmed. Cite refs (e.g. `workspace:2` / `surface:3`) and never
echo secret values.
