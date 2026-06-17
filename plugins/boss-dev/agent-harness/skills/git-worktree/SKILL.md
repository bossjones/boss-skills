---
name: git-worktree
description: Create an isolated git worktree under .claude/worktrees/<repo>-<name>/ for feature development without switching branches. Use when starting a new feature, fix, or experiment that needs its own working directory — handles repo-prefixed naming, base-ref selection, .worktreeinclude file copying, and language-specific setup pointers.
argument-hint: "<name> [--from <base>]"
effort: medium
allowed-tools:
  - Bash(uv run:*)
  - Bash(git worktree:*)
  - Bash(git rev-parse:*)
  - Bash(direnv allow:*)
disable-model-invocation: true
---

# Git Worktree Setup

Create an isolated git worktree under `.claude/worktrees/<repo>-<name>/` on
branch `worktree-<name>`, aligned with Claude Code's native worktree
convention. A deterministic Python script owns naming, base-ref selection, and
the `.worktreeinclude` copy step; this skill picks the language-specific setup.

**Requires:** Git 2.5.0+ and `uv`.

**Companion commands:** [`/git-worktree-status`](../git-worktree-status/SKILL.md) | [`/git-worktree-remove`](../git-worktree-remove/SKILL.md) | [`/git-worktree-clean`](../git-worktree-clean/SKILL.md)

## Steps

### 1. Create the worktree

Run the script from anywhere inside the repo:

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/git_worktree.py" <name> [--from <base>]
```

The script:

- derives `<repo>` from the `origin` URL (falls back to the toplevel dir name)
  and builds the path `.claude/worktrees/<repo>-<name>/` with no double prefix;
- creates branch `worktree-<name>` from the base ref (default `origin/HEAD`,
  else `HEAD`; override with `--from <base>` for the `head` behavior);
- ensures `.claude/worktrees/` is in `.gitignore` (appends + reports if absent);
- copies every `.worktreeinclude`-matched, gitignored file into the worktree
  (the step a plain `git worktree add` skips) and runs `direnv allow` if an
  `.envrc` was copied;
- prints the path, branch, copied files, the detected project type, and the
  matching `references/setup-<lang>.md` to follow next.

Never `cat`, print, or log `.env` / `.envrc` — they hold secrets. The script
copies them byte-for-byte and reports when a protected `.envrc` copy was
declined (see [references/worktreeinclude.md](references/worktreeinclude.md)).

### 2. Set up the language environment

Read the reference the script names for the detected project type and follow it:

- Python / `uv` (first-class): [references/setup-python.md](references/setup-python.md)
- Node.js: [references/setup-node.md](references/setup-node.md)
- Rust: [references/setup-rust.md](references/setup-rust.md)
- Go: [references/setup-go.md](references/setup-go.md)
- Unknown stack: [references/setup-generic.md](references/setup-generic.md)

Each reference covers isolated dependency install and background verification
into `.worktree-logs/`, which [`/git-worktree-status`](../git-worktree-status/SKILL.md) reads.

### 3. Optional follow-ups

- Schema or data-model work on a branchable database: see
  [references/database-branching.md](references/database-branching.md).
- Missing env files in the worktree: add patterns to `.worktreeinclude` (see
  [references/worktreeinclude.md](references/worktreeinclude.md)) and re-run, or
  run the `worktree-doctor` skill to suggest a starter `.worktreeinclude`.

## Running unattended (headless agents)

Two interactive gates must be cleared when an autonomous agent drives a worktree
(they are independent):

1. **Workspace trust** — `claude -p --worktree <name> "<task>"` skips the trust
   check entirely. Interactively, accept trust once at the repo root (saved
   per-directory); later `--worktree` calls reuse it.
2. **Permission prompts** — set a looser mode at startup, e.g. from inside the
   new worktree: `claude -p --permission-mode acceptEdits "<task>"`. Use
   `bypassPermissions` only in an isolated container/VM.

Because `.claude/worktrees` is exempt from protected paths, creation and copy
run cleanly even in `default` mode — except the `.envrc` copy, which is a
protected file (silent only under `auto`/`bypassPermissions`).

## Common mistakes

- **Expecting `.worktreeinclude` to work with a manual `git worktree add`** —
  it does not; that is why this skill's script copies the files.
- **Reading `.env` / `.envrc`** — never do this; copy only.
- **Installing full dependencies when isolation is not needed** — the language
  references note when reuse (e.g. a `node_modules` symlink) is appropriate.

## Usage

```
/git-worktree auth
/git-worktree fix/session-bug
/git-worktree refactor/db-layer --from main
```

Name: $ARGUMENTS
