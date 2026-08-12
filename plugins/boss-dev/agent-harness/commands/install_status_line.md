---
description: Install the agent-harness status line into this project's .claude/settings.local.json (backed up, reversible).
argument-hint: "[--check|--uninstall|--restore]"
---

# Install Status Line

## Purpose

Wire the agent-harness status line (default `status_line_v10.py` — auth badge + context bar +
cost) into the **current project's** `.claude/settings.local.json`. That file is gitignored and the
highest-precedence settings file, so the status line is scoped to this project and never committed.
The write is backed up and fully reversible.

## Consent gate

This command writes a settings file, so it only proceeds once you have opted in:

1. Read `CLAUDE_PLUGIN_OPTION_ENABLE_STATUS_LINE`.
2. If it is unset or `false`, **stop** and tell the user to enable it via `/plugin` → Configure →
   "Enable the agent-harness status line" (or, for scripted use, re-run passing `--yes`). Do not
   write anything.
3. If it is `true`, continue.

## Workflow

1. Resolve the variant from `CLAUDE_PLUGIN_OPTION_STATUS_LINE_VARIANT` (default `status_line_v10.py`).
2. Parse `$ARGUMENTS` for an optional action flag: `--check`, `--uninstall`, or `--restore`
   (no flag = install).
3. Run the installer script with `uv run`, passing the variant and any action flag:

   ```bash
   uv run "${CLAUDE_PLUGIN_ROOT}/scripts/install_status_line.py" --variant <variant> [action]
   ```

   - Install writes the `statusLine` block into `./.claude/settings.local.json`, backing up any
     existing file first.
   - `--check` is a read-only dry run that prints the plan kind and exits non-zero on a foreign
     statusLine.
   - `--uninstall` removes only our block.
   - `--restore` reverts the target to its pre-install state.
   - Add `--force` to replace/remove a third-party statusLine.
   - To install globally instead, pass `--settings ~/.claude/settings.json`.

4. Report the outcome (see Report).

## Report

- The action taken (install / check / uninstall / restore) and the plan kind
  (`install` / `current` / `replace-ours` / `foreign`).
- The target settings file path.
- The backup directory path (under `~/.claude/backups/agent-harness-status-line/`).
- The exact revert command:

  ```bash
  uv run "${CLAUDE_PLUGIN_ROOT}/scripts/install_status_line.py" --restore --yes
  ```

## Example usage

```text
/agent-harness:install_status_line
/agent-harness:install_status_line --check
/agent-harness:install_status_line --uninstall
/agent-harness:install_status_line --restore
```
