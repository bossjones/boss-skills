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

This is the **single-worktree remove** step of the worktree lifecycle suite —
see [Related skills](#related-skills) below.

## Steps

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/git_worktree_remove.py" <name_or_path> [--force] [--keep-branch] [--keep-remote]
```

**Input.** One positional `target` plus optional flags. The target may be a bare
name (`auth`), a directory basename (`boss-skills-auth`), a branch
(`worktree-auth`), or a full path; it is resolved against
`git worktree list --porcelain` and the first match wins. An unresolved target
exits non-zero (`No worktree matches '<target>'`) and changes nothing.

**Behavior and output.** Once a worktree resolves, the script:

- **blocks** removal on a protected branch (`main master develop staging production`) — exit non-zero, no override;
- **warns** and stops if the worktree has uncommitted changes (override with `--force`, which discards them);
- checks merge status (`merge-base --is-ancestor` against the base branch) and warns if unmerged, then deletes the local branch with `-d` (merged) or `-D` (unmerged);
- deletes the remote branch with `git push origin --delete` if it still exists (unless `--keep-remote`);
- runs `git worktree prune` to clear stale references.

It reports each step (worktree removed, local/remote branch deleted, references
pruned) to stderr via `rich`. The full resolution order, safety-check matrix,
and failure modes are in
[references/safety-and-resolution.md](references/safety-and-resolution.md).

## Flags

| Flag            | Effect                                          |
| --------------- | ----------------------------------------------- |
| `--force`       | Skip the uncommitted-changes guard              |
| `--keep-branch` | Remove the worktree but keep the local branch   |
| `--keep-remote` | Do not delete the remote branch                 |

## Database branch cleanup

If the work used a branchable database, delete its branch separately — this
skill never touches the database. Provider commands and the decision of whether
to branch at all live in
[../git-worktree/references/database-branching.md](../git-worktree/references/database-branching.md).

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

## Reference Files

- [references/safety-and-resolution.md](references/safety-and-resolution.md) —
  target-resolution order, the full safety-check matrix (protected / uncommitted
  / merge-status), branch-cleanup semantics, and failure modes.
- [../git-worktree/references/database-branching.md](../git-worktree/references/database-branching.md) —
  database branch cleanup (provider commands, when to branch). Shared with the
  create-side skill; this skill never deletes a database branch automatically.

## Related skills

The worktree lifecycle suite, in order of use:

- [`/git-worktree`](../git-worktree/SKILL.md) — **create** an isolated feature worktree (the starting point).
- [`/git-worktree-remove`](SKILL.md) — **this skill**; remove one worktree plus its branches.
- [`/git-worktree-clean`](../git-worktree-clean/SKILL.md) — bulk-remove merged/stale worktrees.
- [`/git-worktree-status`](../git-worktree-status/SKILL.md) — list worktrees and their state.
- [`worktree-doctor`](../worktree-doctor/SKILL.md) — diagnose and repair a broken worktree setup.
