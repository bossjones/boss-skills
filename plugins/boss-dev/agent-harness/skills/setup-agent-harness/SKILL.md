---
name: setup-agent-harness
description: Make a repo "agent-harness ready" by safely updating .gitignore and .claude/settings.local.json. Use when setting up or onboarding a repo to the agent-harness plugin, ensuring .gitignore covers the plugin's hook artifacts (logs/, .claude/data/) and optionally configuring the statusLine and an outputStyle in the per-user settings.local.json. Every file is backed up before any change.
disable-model-invocation: true
allowed-tools:
  - Bash(uv run:*)
  - AskUserQuestion
argument-hint: "[--apply | --dry-run]"
effort: low
---

# Setup agent-harness

Prepares a repository to use the agent-harness plugin without risking committed
hook output or hand-edited JSON. It does two things, each preceded by a
timestamped backup:

1. Adds a managed block to `.gitignore` covering the runtime artifacts the
   plugin's hooks write (`logs/`, `.claude/data/`, `*.log`, plus the backups
   this skill creates). Only patterns not already present are added — the update
   is additive and idempotent.
2. Merges `$schema`, an optional `statusLine`, an optional `outputStyle`, and the
   `enabledPlugins` entry into `.claude/settings.local.json` — the **per-user,
   git-ignored** settings file, so nothing is forced on the team.

The deterministic work lives in `scripts/setup_harness.py` (stdlib-only PEP 723).
This skill owns all user interaction and never lets the script decide policy on a
conflicting `statusLine` / `outputStyle`.

## Workflow

### 1. Detect current state (read-only)

```text
$ uv run "${CLAUDE_SKILL_DIR}/scripts/setup_harness.py" detect
```

This prints a JSON report: which managed `.gitignore` patterns are missing,
whether `settings.local.json` exists and already has `$schema` / `statusLine` /
`outputStyle`, whether the plugin is enabled, and environment readiness
(`uv`, `python3`, `gh` auth).

### 2. Summarize findings

If `settings_error` is non-null, `settings.local.json` is unreadable (invalid
JSON): the `has_*` / `output_style` / `plugin_enabled` fields are reported as
`null`. Surface the error, tell the user to fix or remove the file, and stop —
`apply` would refuse to overwrite it anyway. Do not prompt for settings changes.

Otherwise, tell the user, in plain language: the missing `.gitignore` patterns,
the current `statusLine` / `outputStyle` (if any), whether `agent-harness@boss-skills`
is enabled, and any environment warnings (these are advisory — they never block).

### 3. Collect decisions with AskUserQuestion

Ask only for what `detect` shows is undecided:

- **statusLine** — if unset, ask Set the harness status line / Skip. If already
  set, ask Keep existing / Overwrite (never overwrite silently).
- **outputStyle** — offer the available styles plus Skip:
  `bullet-points, genui, html-structured, markdown-focused, table-based,
  tts-summary, ultra-concise, yaml-structured`. If one is already set, ask Keep /
  pick a new one / Skip.
- **enable plugin** — if `plugin_enabled` is false, offer to enable
  `agent-harness@boss-skills`.

The `.gitignore` update is always safe to apply (additive), so include
`--gitignore` whenever any pattern is missing.

### 4. Preview the diff with `--dry-run`

Always preview before writing. Run the same `apply` command you intend to run,
plus `--dry-run`: nothing is written, and each touched file's result carries a
`diff` field — a git-style unified diff of exactly what would change in
`.gitignore` and `.claude/settings.local.json`. Show those diffs to the user
(rendered in a `diff`-highlighted fenced code block) and confirm before applying.

```text
# preview without writing — emits a unified `diff` per changed file
$ uv run "${CLAUDE_SKILL_DIR}/scripts/setup_harness.py" apply --gitignore --status-line set --output-style yaml-structured --enable-plugin --dry-run
```

When `dry_run` is true and `changed` is true, read `gitignore.diff` and
`settings.diff` from the JSON and present them. A `changed: false` result means
that file is already in the desired state (no diff).

### 5. Apply the chosen flags

Map the answers to flags and run `apply` (same command, drop `--dry-run`). Use
`--status-line set` only if the user chose to set/overwrite; pass
`--output-style <name>` only for a concrete choice (otherwise `skip`); include
`--enable-plugin` only if requested.

```text
$ uv run "${CLAUDE_SKILL_DIR}/scripts/setup_harness.py" apply --gitignore --status-line set --output-style yaml-structured --enable-plugin
```

### 6. Report

Relay the `apply` summary: what changed in `.gitignore` and
`settings.local.json`, the backup file paths created (`<file>.backup.<timestamp>`),
and confirm the written `settings.local.json` re-parsed successfully.

## Notes

- `--dry-run` writes nothing and returns a unified `diff` per changed file, so you
  can show the user exactly what `apply` would do before running it for real.
- Nothing is written without a backup first; `.gitignore` changes are additive
  and idempotent (re-running produces no diff and no new backup).
- The target is `.claude/settings.local.json` only — this skill never touches the
  team-shared `.claude/settings.json`.
- If `settings.local.json` contains invalid JSON, `apply` aborts and leaves the
  file untouched rather than overwriting it — fix the file and re-run.
- The status line resolves to the plugin's
  `${CLAUDE_PLUGIN_ROOT}/status_lines/status_line_v10.py` at runtime.
- All command examples are deliberately prefixed with a dollar sign and space —
  the skill parser executes exclamation-backtick patterns even inside fenced code
  blocks (see `.claude/rules/skill-development.md`).
