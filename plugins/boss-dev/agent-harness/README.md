# agent-harness

Agent harness tooling for Claude Code: subagents, commands, hooks, skills, and scripts that build
and operate agentic dev workflows.

## Installation

```bash
/plugin install agent-harness@boss-skills
```

## Components

### Skills

Nine skills under `skills/<skill-name>/SKILL.md`.

**PR review workflow** (adapted from the [mlflow](https://github.com/mlflow/mlflow)
skills, Apache-2.0):

- **fetch-diff** — fetch a GitHub PR diff with old/new line numbers and
  auto-generated-file masking, optionally filtered to file globs.
- **fetch-unresolved-comments** — fetch only the unresolved PR review threads
  via the GitHub GraphQL API, grouped by file.
- **pr-review** — review a PR and emit a schema-validated local review payload
  (inline comments plus an approve-or-comment decision).
- **add-review-comment** — post a single inline review comment to a PR line or
  line range via the GitHub API.

**Git worktree lifecycle** (adapted from
[claude-code-ultimate-guide](https://github.com/FlorianBruniaux/claude-code-ultimate-guide),
MIT):

- **git-worktree** — create an isolated worktree for feature development with
  branch naming, dependency symlinking, and background verification.
- **git-worktree-status** — report background type-check, test, and build
  status for a worktree.
- **git-worktree-remove** — safely remove one worktree with branch cleanup and
  safety checks.
- **git-worktree-clean** — batch-clean stale and merged worktrees with a disk
  usage report.

**Release notes** (adapted from claude-code-ultimate-guide, MIT):

- **release-notes-generator** — generate release notes in three formats
  (CHANGELOG, PR body, Slack) from git commits.

The `fetch-diff`, `fetch-unresolved-comments`, and `pr-review` skills carry
standalone PEP 723 scripts under `scripts/`, invoked with
`uv run "${CLAUDE_SKILL_DIR}/scripts/<script>.py"` — `uv` resolves their
dependencies on demand, so the skills work after `/plugin install` with no
extra setup.

### Commands

_Coming soon._ Slash commands will live in `commands/*.md`.

### Agents

_Coming soon._ Subagent definitions will live in `agents/*.md`.

### Hooks

_Coming soon._ Hook configuration will live in `hooks/hooks.json`.

### Scripts and Tools

_Coming soon._ Helper scripts will live under `scripts/`; tooling under `tools/`.

## Status

Skills shipped (v0.2.0); other components are still scaffolding. See the boss-skills
marketplace entry under `plugins/boss-dev/agent-harness/` to track progress.
