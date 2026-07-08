---
name: cmux-team
description: Spawn, orient, and drive a multi-agent terminal team in cmux from natural language. Use when a prompt asks you to boot a team of agents (lead + workers) as a cmux workspace, stand up a "full-stack team" / "agent fleet", orchestrate several terminal agents on one feature, or attach to and drive a team that was just spawned. Roles, models, app, and completion sentinel come from a team-config JSON.
argument-hint: "[team-name] [feature description...]"
allowed-tools: Bash
---

# cmux-team

## Purpose

Boot and orchestrate a **team of terminal agents** inside cmux. One team = one cmux
workspace = one feature. A **lead** agent (left half of the window) drives its **workers**
(a grid on the right); you drive only the lead. Everything specific — roles, per-role
models, launcher, role prompts, the app path, and the completion sentinel — is data in a
**team-config JSON**, not code, so the same machinery works for any team shape.

This skill builds on the `agent-harness:cmux` driver skill (the verb-level cmux control
loop, credential injection, and notification-wait). Read that skill for the primitives;
this one is the team layer on top.

## Prerequisites

Same as `agent-harness:cmux` (macOS + cmux installed, `cmux hooks setup`,
`automation.socketControlMode: allowAll` for an orchestrator outside cmux). Agents launch
authenticated via `--env-file .env` — assume the keys are set; never read their values.

## Team config

`spawn_team.py` resolves a config in this order:

1. `--config <path>`
2. `./.cmux/team.json` (project-local)
3. the bundled `assets/team-config.example.json` (a generic 5-role full-stack team)

Copy the example to `./.cmux/team.json` and fill in real model IDs to customize. The config
declares `cwd`, `env_file`, `completion_sentinel`, `app_path`, `stack`, `orchestrator`
models, and a `roles[]` array. **The first role is the lead** (left half); the rest fill a
balanced grid on the right. Each role has `name`, `model`, `launcher` (default `pi`),
`prompt` (relative paths resolve against `assets/roles/`), and a one-line `kickoff` (with
`__FEATURE__` / `__APP_PATH__` / `__STACK__` / `__SENTINEL__` substituted at spawn time).

## Two ways to spawn

### A. Scripted fast path (recommended)

Boot the whole team in one `cmux workspace create --layout` call and hand command to an
orchestrator, already oriented:

```bash
# preview the plan without touching cmux
uv run "${CLAUDE_PLUGIN_ROOT}"/skills/cmux-team/scripts/spawn_team.py cc <feature-slug> --dry-run

# actually spawn (cc = Claude Code orchestrator; pi = pi orchestrator)
uv run "${CLAUDE_PLUGIN_ROOT}"/skills/cmux-team/scripts/spawn_team.py cc <feature-slug> --config ./.cmux/team.json
```

The script reuses the open cmux window (creating one only if none exists), generates the
layout from the config, colors/labels the workspace, writes `.team/<feature>.spawn.json`,
then `exec`s the orchestrator with `/cmux-did-spawn` so it takes over already oriented.

### B. Drive cmux yourself

If you're orchestrating in natural language without the script, use the cmux verbs directly
(`new-window` only if none open, `workspace create --env-file .env --json`, `new-split`,
`rename-tab`, `workspace-action`, `set-status`, `send` + `send-key enter`, `read-screen`).
See the `agent-harness:cmux` skill for the control loop and the `/cmux-spawn-team` command
for a step-by-step recipe.

## Orient onto an existing team (`/cmux-did-spawn`)

After a scripted spawn, orient by the **stable window UUID** in the spawn file — never cache
positional `surface:N` refs (they renumber). Locate the team's workspace by **name** (the
window may be shared with other teams), then map each role to its current surface ref by
layout name:

```bash
F=$(jq -r .feature "$SPAWN_FILE"); WIN=$(jq -r .window "$SPAWN_FILE")
WSNAME=$(jq -r '.workspace_name // .feature' "$SPAWN_FILE")
WS=$(cmux workspace list --window "$WIN" --json \
     | jq -r --arg n "$WSNAME" '.workspaces[] | select(.custom_title==$n) | .ref' | head -1)
cmux list-pane-surfaces --workspace "$WS"      # names: lead / plan / build-be / build-fe / test
```

Talk to the **lead only** — it dispatches its own workers. Read the lead once to confirm the
team booted (workers should reply `ready: <role>`), then hand it the feature.

## The completion contract

Every worker ends a finished task by printing one line: `<SENTINEL>: <role> | <summary>`
(default sentinel `TASK-DONE`). The lead **waits on cmux notification events** (matching on
`workspace_id`, since `surface_id` is often null) rather than busy-polling, then does a
single `read-screen` to capture the summary. See `agent-harness:cmux` →
**Wait for agents via notification events**.

## Best practices

1. **One team = one workspace = one feature.** Teams share a window as sibling workspaces.
2. **Anchor to the window UUID**, rediscover surface refs at the moment of use.
3. **Drive the lead, not the workers** — the lead owns dispatch and integration.
4. **Push over poll** — wait on `cmux events`, don't loop `read-screen` + `sleep`.
5. **Close scoped** — tear down the team's workspace as a unit; never loop-close the tree.

## Report Format

Report the team name, window UUID, workspace ref, and a per-role table (role · surface ·
model). Then state whether the workers reported ready and what the lead is doing. Never echo
secret values.
