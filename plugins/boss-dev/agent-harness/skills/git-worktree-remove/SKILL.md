---
name: git-worktree-remove
description: Safely remove a single git worktree with branch cleanup and safety checks. Use when you are done with one feature worktree and want to delete it plus its local and remote branches, with protected-branch, uncommitted-change, and merge-status checks first.
argument-hint: "<name_or_path> [--force] [--keep-branch] [--keep-remote]"
effort: low
allowed-tools:
  - Bash(uv run:*)
  - Bash(git worktree:*)
  - Bash(git rev-parse:*)
  - Bash(git merge-base:*)
  - Bash(git status:*)
  - Bash(git branch:*)
  - Bash(git ls-remote:*)
  - Bash(git push:*)
disable-model-invocation: true
---

# Git Worktree Remove

Safely remove a single git worktree with branch cleanup and safety checks. A
Python script resolves the target, runs the safety checks, removes the
worktree, deletes the branch (local and remote), and prunes references.

**Part of the Worktree Lifecycle Suite:** [`/git-worktree`](../git-worktree/SKILL.md) | [`/git-worktree-status`](../git-worktree-status/SKILL.md) | [`/git-worktree-clean`](../git-worktree-clean/SKILL.md)

## Steps

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/git_worktree_remove.py" <name_or_path> [--force] [--keep-branch] [--keep-remote]
```

The target may be a bare name (`auth`), a directory basename
(`boss-skills-auth`), a branch (`worktree-auth`), or a full path. The script:

- **blocks** removal on a protected branch (`main master develop staging production`);
- **warns** and stops if the worktree has uncommitted changes (override with `--force`);
- checks merge status and deletes the local branch with `-d` (merged) or `-D` (unmerged);
- deletes the remote branch if it exists (unless `--keep-remote`);
- prunes stale references.

## Flags

| Flag            | Effect                                          |
| --------------- | ----------------------------------------------- |
| `--force`       | Skip the uncommitted-changes guard              |
| `--keep-branch` | Remove the worktree but keep the local branch   |
| `--keep-remote` | Do not delete the remote branch                 |

## Database branch cleanup

If the work used a branchable database, delete its branch too — see
[../git-worktree/references/database-branching.md](../git-worktree/references/database-branching.md).
Removal never touches the database automatically.

## Common mistakes

- **Removing a worktree for `main`/`develop`** — blocked by the protected-branch check.
- **Deleting an unmerged branch without checking** — the script warns; confirm before forcing.
- **Using `rm -rf` instead of this skill** — leaves stale references in `.git/worktrees/`.

## Usage

```
/git-worktree-remove auth
/git-worktree-remove worktree-fix-login --force
/git-worktree-remove boss-skills-experiment --keep-branch
```

Target: $ARGUMENTS
