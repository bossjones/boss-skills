# cmux Tutorial

A hands-on, progressive walkthrough of the two cmux skills in `agent-harness`:
[`boss-cmux`](../skills/boss-cmux/SKILL.md) (drive one terminal surface at a time) and
[`boss-cmux-team`](../skills/boss-cmux-team/SKILL.md) (spawn and orchestrate a whole fleet of
terminal agents on top of it). Read this top to bottom the first time — each section
builds on commands from the one before it. After that, use it as a lookup.

**What you'll learn:** how cmux's window → workspace → pane → surface hierarchy works,
how to drive a single agent in a pane through the type → submit → read → close loop,
how to wait on an agent's turn without busy-polling, and how to boot a config-driven
multi-agent team and hand it a feature.

**Prerequisites:** macOS 14+ (Sonoma or later) with cmux installed. Everything here is
`Bash` — no Claude Code session is strictly required to follow along, but the last two
sections assume you're driving from inside one (or from `pi`/`claude` running in a plain
terminal).

**Time estimate:** 20–30 minutes to read and try the single-surface loop; add another
15 for the team-spawn walkthrough if you follow along on a real machine.

## Table of Contents

1. [What cmux is and prerequisites](#1-what-cmux-is-and-prerequisites)
2. [The mental model: window → workspace → pane → surface](#2-the-mental-model-window--workspace--pane--surface)
3. [Discovering verbs with `--help`](#3-discovering-verbs-with---help)
4. [The control loop](#4-the-control-loop)
5. [Waiting on agents the right way](#5-waiting-on-agents-the-right-way)
6. [Launching agents in panes](#6-launching-agents-in-panes)
7. [Scaling to a team (`boss-cmux-team`)](#7-scaling-to-a-team-boss-cmux-team)
8. [Spawning a team](#8-spawning-a-team)
9. [Cleanup and next steps](#9-cleanup-and-next-steps)

---

## 1. What cmux is and prerequisites

[cmux](https://cmux.com) is a native **macOS** terminal, built on
[Ghostty](https://ghostty.org), distributed as a Homebrew cask. What makes it
interesting for agent work is that every window, workspace, pane, and surface is a
real, addressable object — scriptable over a CLI backed by a Unix socket. An
orchestrator (a script, or another agent) can open a pane, type into it, read what
came back, and close it, exactly the way a person would drive a terminal by hand.

### Install

```bash
$ brew tap manaflow-ai/cmux
$ brew install --cask cmux
```

Requires macOS 14+ (Sonoma). This tutorial is validated against cmux `0.64.17`.

### Put the CLI on `PATH` (optional)

The cmux app ships its own CLI binary inside the app bundle. If you want `cmux` to work
from any terminal (not just inside the app), symlink it:

```bash
$ sudo ln -sf "/Applications/cmux.app/Contents/Resources/bin/cmux" /usr/local/bin/cmux
```

### Notification hooks

Later sections rely on cmux pushing a "turn finished" notification for each agent. Wire
that up once:

```bash
$ cmux hooks setup            # wires pi, codex, opencode, gemini, … to emit on turn-stop
```

or install one agent at a time:

```bash
$ cmux hooks pi install
$ cmux hooks codex install
```

Claude Code emits these notifications out of the box when launched inside cmux — no
hook entry needed for it.

### Socket control from outside cmux

If you want to drive cmux's socket from an orchestrator running in a *plain* terminal
(not itself inside cmux — this is exactly what `boss-cmux-team`'s spawner does), the socket
needs to allow it. Set `automation.socketControlMode` to `allowAll` (or `password`) in
`~/.config/cmux/cmux.json`. The socket itself lives at `~/.local/state/cmux/cmux.sock`
(override with the `CMUX_SOCKET_PATH` env var).

`cmux docs settings` prints the full config schema and file paths. Before you hand-edit
`~/.config/cmux/cmux.json`, copy it to a timestamped `.bak` beside it so you can revert.
After editing, reload without restarting the app:

```bash
$ cmux docs settings
$ cp ~/.config/cmux/cmux.json ~/.config/cmux/cmux.json.bak-$(date +%s)
# ... edit cmux.json ...
$ cmux reload-config
```

`cmux reload-config` reloads **both** `cmux.json` and Ghostty's
`~/.config/ghostty/config` in place. Keep the split straight: app behavior (sidebar,
notifications, automation, workspace colors, cmux shortcuts) lives in `cmux.json`;
terminal rendering (font, cursor, theme, scrollback, `background-opacity`,
`background-blur`) belongs in the Ghostty config.

> **What you should see:** after `cmux reload-config`, any open panes keep running —
> there's no app restart, no dropped sessions.

### Deeper vendor skill set (optional)

The `agent-harness:boss-cmux` skill is everything you need to *drive* cmux. For the fuller
published skill set (browser automation, settings, diagnostics, a markdown viewer, and
more), install the vendor skills globally:

```bash
$ npx skills add manaflow-ai/cmux -g -y
```

Namespacing keeps them distinct — this tutorial's skill installs as
`agent-harness:boss-cmux`, so there's no collision even if you install the vendor `cmux`
skill too.

---

## 2. The mental model: window → workspace → pane → surface

Everything in cmux nests in one tree. Learn the four boxes and the verbs mostly follow:

| Level | What it is |
| --- | --- |
| **Window** | A top-level OS window. |
| **Workspace** | A sidebar entry ("tab") inside a window. |
| **Pane** | A split region within a workspace. |
| **Surface** | A tab within a pane — a terminal *or* a browser. |

So: one window can hold several workspaces; one workspace can be split into several
panes; one pane can hold several surface tabs. When you launch an agent in a pane,
you're really launching it into one surface.

Before you act on anything, look at the current state:

```bash
$ cmux tree --all
$ cmux workspace list
$ cmux list-pane-surfaces
```

`tree --all` gives you the whole nested picture in one shot; the other two are
narrower views scoped to workspaces and pane→surface mappings respectively.

> **Note on command spelling:** some verbs come in two forms — a namespaced
> `cmux workspace <verb>` (e.g. `workspace create`, `workspace list`) and flat aliases
> (`new-workspace`, `list-workspaces`, `select-workspace`, `close-workspace`). Both
> work. When in doubt, `--help` is authoritative over either form.

---

## 3. Discovering verbs with `--help`

cmux evolves. Before doing anything, run:

```bash
$ cmux --help
```

Then drill into any subcommand you intend to use:

```bash
$ cmux workspace --help
$ cmux send --help
```

**Trust `--help` over memory — never guess a flag.** Every command in this tutorial
came from reading `--help` output and the skill's reference files, not from assumption.
If a flag you expect isn't there, `--help` is where you'll find out before you break
something.

---

## 4. The control loop

This is the core loop you'll use for almost everything: create a workspace, type into
it, submit, read the result, tear it down.

### Create a workspace and inject credentials

```bash
$ cmux workspace create --name <name> --cwd <dir> --env-file .env --json
```

Capture **both** refs from the JSON output in one call — `workspace_ref` and the
initial `surface_ref`. Never guess a positional ref; always thread through what
`--json` gave you.

A few things worth knowing about this command:

- `--env-file` loads that file's environment variables into every surface in the
  workspace, so an agent launched in a pane (`claude`, `pi`, `codex`, `gemini`) comes
  up already authenticated — no manual `export` needed. Default it to `.env` (the
  repo's `.env`) unless told otherwise; that's the canonical source for
  `OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, etc.
- Pair it with `--layout <compact-json>` to boot a whole multi-pane team declaratively
  in one call (each pane's `command` auto-launches its agent) — this is exactly what
  `boss-cmux-team`'s spawner does in [section 8](#8-spawning-a-team).
- **Don't inject over a working login.** If an agent is already authenticated (e.g.
  Claude Code), don't push a placeholder key over it via `--env-file`; scope credential
  injection to the agents that actually need it.
- **Assume the keys are already set up, and never read their values.** Point
  `--env-file` at `.env` and move on — don't `cat .env`, `echo $OPENROUTER_API_KEY`, or
  `read-screen` a surface to capture a key. Only if an agent actually fails to
  authenticate should you validate, and do it *safely*:

  ```bash
  $ cmux workspace env --workspace <ref> --mask
  ```

  That shows a var is present without revealing it; `[ -n "$VAR" ]` confirms it's
  non-empty. Report the masked/presence result, never the secret itself.

### The loop itself

```bash
$ cmux send --surface <ref> "<text>"        # type text into a surface
$ cmux send-key --surface <ref> enter       # submit it (press a key)
$ cmux read-screen --surface <ref>          # read what's on screen — your eyes
$ cmux close-surface --surface <ref>        # end a surface cleanly
```

**`send` types; `send-key enter` submits — they are separate steps.** A prompt isn't
sent until you press enter, and there's no combined "type and submit" verb. Give the
agent a beat before you `read-screen` its reply. Add `--scrollback` to `read-screen`
when you need history, not just the current viewport:

```bash
$ cmux read-screen --surface <ref> --scrollback --lines 40
```

> **What you should see:** after `send` + `send-key enter`, the pane's prompt line
> clears and the agent starts producing output. If `read-screen` still shows your typed
> text sitting in the input box, the `send-key enter` didn't land — retry it before
> assuming the agent is just slow.

### Refs are positional and renumber

`surface:N` / `workspace:N` shift as things open and close elsewhere in cmux — they are
**not** stable identifiers over time. Re-read the tree right before you act on a ref you
captured a while ago. For anything long-lived (a team you'll come back to across
multiple turns), anchor to a **stable window UUID** instead of a positional ref, and
request UUID output explicitly:

```bash
$ cmux --json --id-format uuids identify
$ cmux --json --id-format both identify
```

`--id-format both` gives you the UUID *and* the current short ref together, which is
the pattern [section 8](#8-spawning-a-team) uses to re-locate a team after time has
passed.

---

## 5. Waiting on agents the right way

Once you've sent an agent a task, you need to know when it's done — without burning
tool calls in a `read-screen` + `sleep` loop. cmux has a push channel for exactly this.

**`cmux events` is the wait channel — not `cmux wait-for`.** `cmux wait-for <name>` is
an unrelated *named-token rendezvous* — a manual semaphore you signal yourself. It has
no idea when an agent finishes a turn. The signal you actually want is the
`notification` event category, which requires the hooks from
[section 1](#1-what-cmux-is-and-prerequisites) to be installed (`cmux hooks setup`).
Without them, an agent stays silent and you're back to polling.

### What fires

One event per completed turn, verified working for pi, Codex, and Claude Code:

```json
{ "name": "notification.requested", "category": "notification",
  "workspace_id": "120FC732-…", "surface_id": null, "seq": 1512 }
```

Match on **`workspace_id`** — for hook-emitted notifications, `surface_id` is usually
`null`, but `workspace_id` is always set. The title/body are **redacted** in the event
itself (you get the signal, not the text), so once it fires, `read-screen` that
workspace's surface to see the actual reply. Filter to `--name notification.requested`
— a sibling `notification.clear_requested` fires when a surface gains focus, and is
just noise you should ignore.

### Blocking on one agent's turn

Capture the target workspace's UUID first:

```bash
$ cmux list-workspaces --json --id-format both
```

Then, start the listener **before** you send the prompt (so you can't miss the event),
and stream to a file rather than piping directly:

```bash
WS=<agent-workspace-uuid>
$ cmux events --name notification.requested --no-heartbeat --no-ack > /tmp/cmux.ev &
EV=$!
$ cmux send --surface <ref> "<task>"; cmux send-key --surface <ref> enter
until grep -q "\"workspace_id\":\"$WS\"" /tmp/cmux.ev; do sleep 1; done
kill $EV
$ cmux read-screen --surface <ref> --scrollback --lines 40   # now read the reply
```

**Pitfall:** a `cmux events | jq … &` pipeline in a one-liner can stall on stdout
buffering. Stream to a file and poll the file (as above), or pass `jq --unbuffered` if
you must pipe directly.

For a durable cursor across reconnects (so you don't miss events across a restart of
your listener), use:

```bash
$ cmux events --cursor-file <path> --reconnect
```

---

## 6. Launching agents in panes

You now have the full single-surface loop: create, send, wait, read, close. Here's how
to launch the three agent types this tutorial cares about, so they run unattended
inside a pane rather than stalling on an approval prompt meant for a human.

### pi

`pi` is an interactive TUI agent — launch it inside a pane the same way you'd type any
other command:

```bash
$ pi --model <model> "<task>"
```

Launch it via `cmux send` + `send-key enter` **inside a pane** — not from your own
non-interactive/batch shell.

### Codex — run it unattended

Start Codex unattended so it doesn't stall on approval prompts (it's running inside
cmux, driven by an orchestrator, not a human at the keyboard). Pass the flag at
**launch time** — don't edit Codex's global config:

```bash
# yolo: full access, no sandbox — use only because the run is orchestrated/observed
$ codex --dangerously-bypass-approvals-and-sandbox "<task>"

# auto: sandboxed, automatic execution inside a workspace-write sandbox
$ codex --full-auto "<task>"
```

Default to yolo for hands-off fleet runs; reach for `--full-auto` when you want the
sandbox. Both are per-launch flags — they never change the user's global Codex setup.

**Always launch Codex with the `gpt-5.5` model unless a prompt specifies otherwise:**

```bash
$ codex -m gpt-5.5 --dangerously-bypass-approvals-and-sandbox "<task>"
```

If a prompt names a different Codex model or effort, use that instead — `gpt-5.5` is
just the default.

### Claude Code — use bypass mode

Plain `claude` launches in **ask-for-permission mode**: it will *decline* to run Bash
or make edits and instead print instructions, then end its turn. For a hands-off fleet
agent, bypass permissions at launch the same way you yolo Codex:

```bash
$ claude --dangerously-skip-permissions "<task>"
```

The composer then shows `⏵⏵ bypass permissions on` and executes shell/edits without
prompting. This is a per-launch flag — it doesn't change global Claude settings.

> **Caveat, verified in testing:** a notification still fires on turn-completion
> **even when Claude refused to do the work**. If you only watch events, you can
> mistake a "declined, nothing happened" turn for success. Always `read-screen` (or
> check the actual artifacts) after the event fires — don't trust the event alone.

---

## 7. Scaling to a team (`boss-cmux-team`)

Everything so far drives one surface. `boss-cmux-team` composes that same primitive loop
into a whole fleet: **one team = one cmux workspace = one feature.** A **lead** agent
runs in the left half of the window; its **workers** fill a balanced grid on the right.
You drive only the lead — it dispatches its own workers using exactly the `send` /
`send-key enter` / `read-screen` loop from sections 4–6.

The important design choice: roles, per-role models, the launcher, role prompts, the
app path, and the completion sentinel are all **data in a team-config JSON**, not code.
The same spawner works for any team shape.

### Config resolution order

`spawn_team.py` (the script that boots a team) resolves a config in this order:

1. `--config <path>` — explicit override
2. `./.cmux/team.json` — project-local
3. the bundled `assets/team-config.example.json` — a generic 5-role full-stack team

Copy the example to `./.cmux/team.json` and fill in real model IDs to customize:

```bash
$ cp "${CLAUDE_PLUGIN_ROOT}"/skills/boss-cmux-team/assets/team-config.example.json ./.cmux/team.json
```

### What's in the config

The bundled example declares `cwd`, `env_file`, `completion_sentinel`, `app_path`,
`stack`, `orchestrator` models (one entry for a Claude Code lead, one for a `pi` lead),
and a `roles[]` array. **The first role in `roles[]` is the lead**; the rest fill the
grid. Each role has:

| Field | Meaning |
| --- | --- |
| `name` | Role name — becomes the pane's surface name and the `.team/` roster key. |
| `model` | Model ID for that role. Placeholder in the bundled example (`<your-lead-model>`, `<your-builder-model>`, …) — fill in real IDs in your own `./.cmux/team.json`. |
| `launcher` | The agent binary to launch (default `pi`). |
| `prompt` | Role prompt file; relative paths resolve against the skill's `assets/roles/`. |
| `kickoff` | One-line launch message, with `__FEATURE__` / `__APP_PATH__` / `__STACK__` / `__SENTINEL__` substituted at spawn time. |

The bundled example ships a generic full-stack shape — `lead`, `plan`, `build-be`,
`build-fe`, `test` — with placeholder models and the default sentinel `TASK-DONE`.
Nothing here hardcodes a specific app or model provider; that's the whole point of
pushing the specifics into config.

---

## 8. Spawning a team

### The scripted fast path (recommended)

Boot the whole team in one `cmux workspace create --layout` call and hand command to an
orchestrator that's already oriented. Always preview first — `--dry-run` prints the
resolved config, the generated layout, and the cmux commands it *would* run, then exits
0 without touching cmux (CI-safe):

```bash
$ uv run "${CLAUDE_PLUGIN_ROOT}"/skills/boss-cmux-team/scripts/spawn_team.py cc <feature-slug> --dry-run
```

> **What you should see:** the resolved config path, the role list, the completion
> sentinel, a JSON layout tree (lead on the left, workers arranged in a balanced grid
> on the right), and the exact `cmux workspace create …` command it would run — with no
> network or socket activity.

Once the plan looks right, spawn for real, pointing at your own config:

```bash
$ uv run "${CLAUDE_PLUGIN_ROOT}"/skills/boss-cmux-team/scripts/spawn_team.py cc <feature-slug> --config ./.cmux/team.json
```

`cc` launches a Claude Code orchestrator; use `pi` instead for a `pi` orchestrator. The
full CLI:

```text
spawn_team.py <cc|pi> <feature-slug> [--config PATH] [--cwd DIR] [--orch-pi-model MODEL] [--dry-run]
```

Under the hood, the script reuses the currently open cmux window (creating one only if
none exists), generates the `--layout` from your config, colors and labels the
workspace, writes `.team/<feature-slug>.spawn.json`, then execs the chosen orchestrator
already pointed at `/agent-harness:cmux-did-spawn` — so it takes command already
oriented, with no manual hand-off step.

### Three slash commands

- **`/agent-harness:cmux-spawn-team [team-name] [feature description...] [--config PATH]`**
  — boots a fresh team as a new workspace in the cmux window (reusing the open window;
  only creating one if none exists). This is the command-level entry point over the
  scripted fast path above; it can also drive cmux by hand if you'd rather orchestrate
  in natural language than run the script.

- **`/agent-harness:cmux-did-spawn <spawn-file path>`** — orients an orchestrator onto
  a team that was *just* spawned. It reads the spawn file, locates the team's
  workspace by the **stable window UUID** plus the workspace **name** (a window can be
  shared by several teams as sibling workspaces), rediscovers each role's current
  surface ref, and confirms the workers reported ready before handing control back to
  you:

  ```bash
  F=$(jq -r .feature "$SPAWN_FILE"); WIN=$(jq -r .window "$SPAWN_FILE")
  WSNAME=$(jq -r '.workspace_name // .feature' "$SPAWN_FILE")
  WS=$(cmux workspace list --window "$WIN" --json \
       | jq -r --arg n "$WSNAME" '.workspaces[] | select(.custom_title==$n) | .ref' | head -1)
  cmux list-pane-surfaces --workspace "$WS"      # names: lead / plan / build-be / build-fe / test
  ```

  Talk to the **lead only** — it dispatches its own workers. Read it once to confirm
  the team booted (workers should each reply `ready: <role>`), then hand it the
  feature.

- **`/agent-harness:cmux-fresh`** — unrelated to spawning; covered in
  [section 9](#9-cleanup-and-next-steps).

### The completion contract

Every worker ends a finished task by printing exactly one line:

```text
<SENTINEL>: <role> | <summary>
```

with the default sentinel `TASK-DONE`. The lead **waits on cmux notification events**
(matching on `workspace_id`, the same technique from [section 5](#5-waiting-on-agents-the-right-way),
since `surface_id` is often `null`) rather than busy-polling — then does a single
`read-screen` to capture the summary. This is the same push-over-poll discipline from
section 5, just applied by the lead to each of its own workers instead of by you to a
single surface.

> **What you should see:** once you hand the lead a feature, `read-screen`ing the lead
> shows it dispatching work to `plan`, then to `build-be` / `build-fe`, then to `test`
> — each transition gated on a notification event, not a fixed sleep.

---

## 9. Cleanup and next steps

### Reset cmux to a blank slate

cmux replays its window/workspace/pane tree from a saved session file on launch. If
that gets stale or cluttered:

```text
/agent-harness:cmux-fresh
```

This **quits cmux first** (so the session file it rewrites on quit reflects the clear),
**backs up** each session file to a timestamped `.bak-<epoch>` copy before touching
anything, then empties the top-level `windows` array in
`session-com.cmuxterm.app.json` and its `-previous` sibling. It only ever touches those
two files. The next launch opens fresh, blank windows; to restore the old layout, move
a `.bak-*` file back over the original.

### Where to go next

- [`../skills/boss-cmux/SKILL.md`](../skills/boss-cmux/SKILL.md) — the full driver skill this
  tutorial is based on, including the best-practices list and report format.
- [`../skills/boss-cmux-team/SKILL.md`](../skills/boss-cmux-team/SKILL.md) — the full team skill,
  including how to drive cmux by hand instead of the scripted fast path.
- Deep-dive references for the topology-routing verbs beyond the control loop
  (`move-surface`, `reorder-surface`, `split-off`, `surface-health`, and more):
  [`../skills/boss-cmux/references/handles-and-identify.md`](../skills/boss-cmux/references/handles-and-identify.md),
  [`../skills/boss-cmux/references/windows-workspaces.md`](../skills/boss-cmux/references/windows-workspaces.md),
  [`../skills/boss-cmux/references/panes-surfaces.md`](../skills/boss-cmux/references/panes-surfaces.md),
  [`../skills/boss-cmux/references/trigger-flash-and-health.md`](../skills/boss-cmux/references/trigger-flash-and-health.md).
- [`./skills.md#cmux-orchestration`](./skills.md#cmux-orchestration) and
  [`./commands.md#cmux-orchestration`](./commands.md#cmux-orchestration) — the
  reference-style entries for both skills and all three commands, if you want the
  condensed version instead of this walkthrough.
- [`../../../../specs/cmux.md`](../../../../specs/cmux.md) — the design spec: why the
  team feature is entirely config-driven, and what it was ported and generalized from.
