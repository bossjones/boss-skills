# Target-repo Stop hook setup

## What it does

Per Pyrefly's [agentic-loop post](https://pyrefly.org/blog/pyrefly-agentic-loop/), a `Stop` hook
nudges the agent to fix newly-introduced errors before ending its turn. The exact entry
`pyrefly_setup.py`'s `build_stop_hook_entry()` generates:

```json
{
  "hooks": [
    {
      "type": "command",
      "command": "cd \"$CLAUDE_PROJECT_DIR\" && uv run pyrefly check --baseline pyrefly-baseline.json >&2 || exit 2",
      "timeout": 30
    }
  ]
}
```

See [../examples/example-stop-hook.json](../examples/example-stop-hook.json) for a copy-pasteable
copy of this same entry, already wrapped in the full `.claude/settings.json` shape.

Unlike the task-runner targets (which pass `--summarize-errors` for a readable rollup), the hook
command omits it deliberately — its output only matters when it's non-empty (stderr on failure),
and the raw per-error output is more useful there than a summary table.

This gets appended to the `"Stop"` array in the **target repo's own**
`.claude/settings.json` — additively, alongside whatever `Stop` entries already exist there.
`merge_stop_hook()` dedupes by exact `command` string, so re-running `apply --with-stop-hook` is
idempotent.

## This is *not* the same mechanism as this plugin's own hooks

`agent-harness`'s own `hooks/hooks.json` wires **this repo's** lifecycle hooks statically, at
plugin-install time, via `${CLAUDE_PLUGIN_ROOT}`-relative script paths — see
`plugins/boss-dev/agent-harness/hooks/hooks.json` and `docs/hooks.md`. That mechanism is completely
separate from what this skill does.

`pyrefly-typing` instead **generates a hook entry at runtime** into a *different*, arbitrary target
repo's `.claude/settings.json`. There is no `${CLAUDE_PLUGIN_ROOT}` involved — the hook's `command`
is a plain shell command (`cd "$CLAUDE_PROJECT_DIR" && uv run pyrefly check ...`) that only assumes
`uv` and a `pyrefly-baseline.json` exist in that target repo.

**Do not** add a `pyrefly`-related entry to `plugins/boss-dev/agent-harness/hooks/hooks.json` — that
would only make sense if `boss-skills` itself became a Pyrefly target, which it isn't (it has no
`[tool.pyrefly]` and doesn't need one).

## Opt-in, and how to disable

The hook is only merged when `apply` is run with `--with-stop-hook`. To remove it later, delete the
matching entry from the target repo's `.claude/settings.json` `hooks.Stop` array (or drop the whole
`"hooks"` key if nothing else uses it).

## Alternative: pre-commit

For repos that already use `pre-commit` instead of (or alongside) Claude Code hooks,
`facebook/pyrefly-pre-commit` offers a `.pre-commit-hooks.yaml` entry:

```yaml
- id: pyrefly-check
  name: pyrefly check
  entry: pyrefly check
  language: python
  types_or: [python, pyi]
  pass_filenames: false
  require_serial: true
  stages: [pre-commit, pre-merge-commit, pre-push, manual]
```

`language: python` with a pinned `pyrefly` version builds an isolated venv rather than shelling to a
system binary; `pass_filenames: false` means it always runs `pyrefly check` project-wide. This is a
second, independent automation option — mention it to the user as an alternative, but don't wire it
up automatically; the Stop hook is this skill's default automation path.
