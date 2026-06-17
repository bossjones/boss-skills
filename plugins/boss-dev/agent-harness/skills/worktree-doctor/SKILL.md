---
name: worktree-doctor
description: Analyze a repo and suggest a .worktreeinclude so worktrees inherit env, secret, and local-config files. Use when setting up worktrees in a new repo, before the first /git-worktree, or when a worktree is missing its .env / local settings — scans gitignored files and proposes patterns.
argument-hint: "[--write]"
effort: low
allowed-tools:
  - Bash(uv run:*)
  - Bash(git rev-parse:*)
  - Bash(git ls-files:*)
---

# Worktree Doctor

Analyze a repository and suggest a `.worktreeinclude` so new worktrees inherit
the local files they need (env vars, secrets, local config). This matters
because a plain `git worktree add` — and the `git-worktree` skill that wraps it
— only copies files that are **both** gitignored and listed in
`.worktreeinclude`.

**Companion:** [`/git-worktree`](../git-worktree/SKILL.md) creates worktrees and performs the copy.

## When to use

- Setting up worktrees in a new repo, before the first `/git-worktree`.
- A worktree is missing its `.env` or local settings.
- You want to know whether `.claude/worktrees/` is gitignored.

## Steps

Print a suggestion (default — makes no changes):

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/worktree_doctor.py"
```

Opt in to writing the file (never overwrites an existing `.worktreeinclude`):

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/worktree_doctor.py" --write
```

The script:

- lists gitignored files and flags env/secret/local-config candidates (skipping
  vendored paths like `.venv` and `node_modules`);
- detects the project type(s) (`pyproject.toml`, `package.json`, `Cargo.toml`,
  `go.mod`);
- reports whether `.claude/worktrees/` is gitignored;
- prints a suggested `.worktreeinclude`.

Review the suggestion before adopting it — see
[references/worktreeinclude-patterns.md](references/worktreeinclude-patterns.md)
for what each pattern means and why vendored paths are excluded.

## Secrets

The doctor never reads file *contents* — only paths. `.env` / `.envrc` hold
secrets; never print or log them. `.envrc` is a Claude protected path (see the
[`/git-worktree`](../git-worktree/references/worktreeinclude.md) notes).

## Usage

```
/worktree-doctor
/worktree-doctor --write
```

Flags: $ARGUMENTS
