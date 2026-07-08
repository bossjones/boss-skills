---
description: Boot a multi-agent team as a new workspace in the cmux window (reuse the open window; only create one if none exists) — a lead on the left half, workers in a grid on the right, each launched with its role and model from the team config. Drive cmux yourself in natural language, or use the scripted fast path.
argument-hint: "[team-name] [feature description...] [--config PATH]"
---

# Spawn Team

## Purpose

You are an orchestrator running in a terminal (not inside cmux). Boot a fresh team as
**a new workspace in the cmux window** and, if given a feature, hand it to the team's lead.
**One team = one workspace = one feature**, and teams **share a window** — reuse the window
that's already open and only create a new one if cmux has none. Roles, models, role prompts,
the app, and the completion sentinel all come from the **team config** (see the
`agent-harness:boss-cmux-team` skill) — there is nothing app-specific hardcoded here.

## Variables

TEAM: $1 # short slug for the team; default "team" if omitted
FEATURE: $2 # everything after the slug — optional feature to ship now
CONFIG: --config value # optional team-config path (default: ./.cmux/team.json or bundled example)

## Fast path (recommended)

The scripted spawner boots every pane in one call and hands command to an orchestrator,
already oriented via `/cmux-did-spawn`:

```bash
# preview without touching cmux
uv run "${CLAUDE_PLUGIN_ROOT}"/skills/boss-cmux-team/scripts/spawn_team.py cc "$TEAM" --dry-run

# spawn for real (cc = Claude Code orchestrator, pi = pi orchestrator)
uv run "${CLAUDE_PLUGIN_ROOT}"/skills/boss-cmux-team/scripts/spawn_team.py cc "$TEAM" --config ./.cmux/team.json
```

## Instructions (driving cmux yourself)

If you prefer to orchestrate by hand instead of the script:

- **Learn the verbs first.** Run `cmux --help` (and consult the `agent-harness:boss-cmux` skill).
  The whole boot is just these verbs: `new-window`, `workspace create`, `new-split <dir>`,
  `rename-tab`, `workspace-action`, `set-status`, `send`, `send-key`, `read-screen`,
  `workspace close`.
- You are **outside** cmux; the socket is in `allowAll` mode, so your `cmux` calls drive it
  directly. Confirm with `cmux identify --json` before starting.
- **If cmux isn't running, start it — don't stop.** A refused socket just means the app
  isn't up yet. Run `open -a cmux`, wait for the socket, then carry on.
- **`send` types, `send-key enter` submits.** To stop a pane, `close-surface` it.
- **Capture refs as you create them.** `workspace create --json` returns `workspace_ref` +
  the lead's `surface_ref`; each `new-split --json` returns the new `surface_ref`. Thread
  these through — never guess refs.
- Launch each agent by typing its launch line **into its pane** (via `cmux send` +
  `send-key enter`), not from your own shell. Read each role's model and prompt from the
  team config; read each role prompt from the `boss-cmux-team` skill's `assets/roles/`.
- **Reuse the open window; one team = one workspace.** Only run `new-window` when cmux has
  no window at all. Multiple teams coexist as sibling workspaces in one window.
- The **lead** drives the workers; you drive only the lead. Keep every agent observable —
  read panes, don't assume.

## Workflow

1. **Preflight (auto-launch cmux if needed).** Set `TEAM` (default `team`) and `FEATURE`
   from the arguments. Ensure the cmux socket is reachable — and if it isn't, **launch cmux
   yourself** and wait, rather than stopping:

   ```bash
   if ! cmux identify --json >/dev/null 2>&1; then
     open -a cmux
     for i in $(seq 1 30); do
       cmux identify --json >/dev/null 2>&1 && break
       sleep 0.5
     done
   fi
   cmux identify --json >/dev/null 2>&1 || { echo "cmux failed to start — aborting."; exit 1; }
   ```

2. **Spawn.** Prefer the fast path above. Otherwise: find the window (reuse if one's open,
   else `new-window`), `workspace create --window <win> --name "$TEAM" --cwd "$PWD"
   --env-file ./.env --focus true --json`, split the workers per the config's role list,
   `rename-tab` / `set-status` for identity, then launch each role's line into its pane.
3. **Hand off the feature (if given).** Send `$FEATURE` to the lead as one single-line
   `send` + `send-key enter`, then `read-screen` the lead to confirm it's coordinating.
4. Now follow the `Report` section.

## Report

```
## Team "[TEAM]" — booted as a workspace in window [WIN]

**Window**: [WIN] ([reused existing | new])   ·   **Workspace**: [WS]   ·   **Layout**: lead (left half) + workers (grid)

| Role | Surface | Model |
|------|---------|-------|
| lead | [LEAD] | [model] |
| … | … | … |

**Spawn file**: .team/[TEAM].spawn.json
```
