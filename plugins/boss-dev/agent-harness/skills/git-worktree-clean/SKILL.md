---
name: git-worktree-clean
description: Clean up stale git worktrees with merged-branch detection and a disk-usage report. Use when feature worktrees under .claude/worktrees/ have accumulated and you want to reclaim space — auto-removes merged worktrees and reviews unmerged ones.
argument-hint: "[--dry-run] [--all] [--force]"
effort: low
allowed-tools:
  - Bash(uv run:*)
  - Bash(git worktree:*)
  - Bash(git rev-parse:*)
  - Bash(git merge-base:*)
  - Bash(git branch:*)
disable-model-invocation: true
---

# Git Worktree Clean

Batch cleanup of stale git worktrees. A Python script lists worktrees,
classifies each as merged / unmerged / protected, removes the safe ones, and
reports reclaimed space. Disk accounting is language-neutral — it skips
symlinks (e.g. a shared `node_modules`) and `.git`, with no stack-specific
excludes.

## Script

`scripts/git_worktree_clean.py` is a standalone PEP 723 script (run via `uv`,
no install). It is the entire engine of this skill.

- **Inputs:** the optional flags `--dry-run`, `--all`, `--force` (see below).
  It reads the repo from the current working directory — no path argument.
- **Reads:** `git worktree list --porcelain`, the main branch from
  `origin/HEAD` (fallback `main`), and `git merge-base --is-ancestor` to test
  whether each branch has landed.
- **Writes (only on a real run):** removes eligible worktrees with
  `git worktree remove`, deletes their branches (`git branch -d`/`-D`), then
  `git worktree prune`.
- **Output:** a Rich report to stdout — removed worktrees with per-worktree
  size, kept-unmerged and kept-protected lists, and total space
  reclaimed/potential. Exit code `1` if run outside a git repository, else `0`.

For the full classification rules, flag semantics, disk-accounting details,
and failure modes, see
[references/cleanup-semantics.md](references/cleanup-semantics.md).

## Steps

Always preview first:

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/git_worktree_clean.py" --dry-run
```

Then execute:

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/git_worktree_clean.py" [--all] [--force]
```

The script:

- skips the main worktree and any worktree on a protected branch
  (`main master develop staging production`);
- removes worktrees whose branch is merged into the main branch and deletes the
  local branch (`git branch -d`);
- keeps unmerged worktrees unless `--all` is given (then `git branch -D`);
- prunes stale references with `git worktree prune`.

## Flags

| Flag        | Effect                                                       |
| ----------- | ------------------------------------------------------------ |
| `--dry-run` | Preview what would be cleaned; make no changes               |
| `--all`     | Also remove unmerged worktrees (force-deletes their branch)  |
| `--force`   | Skip git's dirty-state guard when removing a worktree        |

## Database branch cleanup

Worktree removal does not delete associated database branches. If the work used
a branchable database, follow the matching cleanup command in
[../git-worktree/references/database-branching.md](../git-worktree/references/database-branching.md).

## Common mistakes

- **Running `--force` without `--dry-run` first** — always preview.
- **Losing unmerged work with `--all`** — it force-deletes unmerged branches.
  Triage individually with `/git-worktree-remove` first.
- **Forgetting database branch cleanup** — the worktree goes, the DB branch
  stays until you delete it.

The full failure-mode list (detached-HEAD worktrees swept by `--all`, dirty
worktrees and the `--force` guard, stale locks) lives in
[references/cleanup-semantics.md](references/cleanup-semantics.md).

## Usage

```
/git-worktree-clean --dry-run
/git-worktree-clean
/git-worktree-clean --all
```

Flags: $ARGUMENTS

## Reference Files

- [references/cleanup-semantics.md](references/cleanup-semantics.md) —
  classification (protected/merged/unmerged), exact flag behavior, safety
  rules, disk accounting, and failure modes.
- [../git-worktree/references/database-branching.md](../git-worktree/references/database-branching.md) —
  database branch cleanup commands (shared with `git-worktree`; not duplicated
  here).

## Related skills

This skill is the cleanup stage of the **Worktree Lifecycle Suite**. A typical
flow runs left to right:

- [`/git-worktree`](../git-worktree/SKILL.md) — create an isolated worktree for
  a feature.
- **`/git-worktree-clean`** (this skill) — batch-remove merged worktrees and
  reclaim disk once work has landed.
- [`/git-worktree-remove`](../git-worktree-remove/SKILL.md) — remove a single
  worktree deliberately; use this to triage an unmerged one before reaching for
  `--all` here.
- [`/git-worktree-status`](../git-worktree-status/SKILL.md) — inspect current
  worktrees and their branch/merge state.
- [`/worktree-doctor`](../worktree-doctor/SKILL.md) — diagnose and repair stuck
  worktrees (stale locks, orphaned references) when a remove fails.
