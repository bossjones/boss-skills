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

**Part of the Worktree Lifecycle Suite:** [`/git-worktree`](../git-worktree/SKILL.md) | [`/git-worktree-status`](../git-worktree-status/SKILL.md) | [`/git-worktree-remove`](../git-worktree-remove/SKILL.md)

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
- **Forgetting database branch cleanup** — the worktree goes, the DB branch
  stays until you delete it.

## Usage

```
/git-worktree-clean --dry-run
/git-worktree-clean
/git-worktree-clean --all
```

Flags: $ARGUMENTS
