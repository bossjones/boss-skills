---
name: harness-doctor
description: Inspect agent-harness environment readiness and runtime storage without changing files. Use when asked to diagnose agent-harness, check hook prerequisites, find harness logs or data, learn which plugin repository names the harness root, inspect stale logs, .claude/data, or a legacy repository-named harness directory, or run a harness health check.
disable-model-invocation: true
allowed-tools:
  - Bash(uv run:*)
argument-hint: "[repo-root]"
effort: low
---

# Harness doctor

Use this read-only diagnostic before changing an agent-harness installation or
when hook output is missing. It reports advisory tool readiness, the resolved
harness root with the plugin namespace that names it, sizes for its `logs`,
`data`, and `cache` directories, enabled plugin identities when settings expose
them, and stale pre-migration artifacts. It never deletes, moves, or edits
files.

## Triggers

Use this skill for concrete requests such as:

- "run the agent-harness doctor"
- "why are my agent-harness logs missing?"
- "check whether my hook environment is ready"
- "is old logs/ or .claude/data/ safe to remove?"
- "why is there a dot-directory named after this repo?"
- "which agent-harness plugin is enabled?"

## Run the report

Run from the repository to inspect, or pass an explicit repository path:

```text
$ uv run "${CLAUDE_SKILL_DIR}/scripts/harness_doctor.py"
$ uv run "${CLAUDE_SKILL_DIR}/scripts/harness_doctor.py" --repo-root /path/to/repo
```

Read the JSON report and summarize its advisory hints. `harness_root.namespace`
is the plugin's marketplace repository, and `harness_root.namespace_source` is
the directory that supplied it — the same name is used in every repository the
plugin runs in. A stale `logs/`, `.claude/data/`, or `legacy_project_root`
result means the directory predates the current layout; report each as safe to
delete only after the user has reviewed it. Do not delete anything as part of
this skill.

## Follow-up

- Missing `uv`, `python3`, `git`, `gh`, `ruff`, or `tmux` is advisory. Explain
  the affected capability and its reported hint.
- If GitHub CLI is installed but unauthenticated, suggest `$ gh auth login`.
- If the resolved root is unexpected, inspect `CLAUDE_HARNESS_DIR` and
  `CLAUDE_PLUGIN_OPTION_HARNESS_DIR`; `CLAUDE_HOOKS_LOG_DIR` only overrides
  the logs subtree. A `namespace_source` of `null` means no marketplace
  manifest was found above the plugin, so the root falls back to
  `.agent-harness`.
- Use `/setup-agent-harness` only when the user wants to update repository
  settings or the managed `.gitignore` block.
