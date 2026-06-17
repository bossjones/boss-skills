# `.worktreeinclude`

`.worktreeinclude` lists files that should follow a repo into each new
worktree. It lives at the repository root and uses **`.gitignore` glob syntax**
(`*`, `**`, anchoring, negation with `!`).

## The copy rule

Only files that are **both** matched by a `.worktreeinclude` pattern **and**
gitignored are copied. A file that matches a pattern but is tracked by git is
already present in the worktree, so it is skipped.

## Why this skill copies them itself

A plain `git worktree add` does **not** process `.worktreeinclude`. Only
Claude's native worktree creation (`claude --worktree`, `EnterWorktree`, and
`isolation: worktree` subagents) applies it. Because `git_worktree.py` calls
`git worktree add` directly, it replicates the copy step itself — that is the
central reason the script exists rather than deferring to native creation.

See the official docs: <https://code.claude.com/docs/en/worktrees>.

## Common entries

```gitignore
.env
.env.local
.env.development
.envrc
**/.claude/settings.local.json
```

## Secrets

`.env` and `.envrc` are copied byte-for-byte. Never `cat`, print, or log their
contents. `.envrc` is a Claude **protected path**: under `default`/`acceptEdits`
the copy may prompt or be declined (it is auto-approved only under `auto` or
`bypassPermissions`). The creation report calls out when a matched file was not
copied so the gap is visible rather than silent.

## Discovering candidates

Run the `worktree-doctor` skill to scan a repo's gitignored files and suggest a
starter `.worktreeinclude`.
