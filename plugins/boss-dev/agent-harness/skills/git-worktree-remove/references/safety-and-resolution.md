# Safety and target resolution

Load this when you need the exact rules behind how `git_worktree_remove.py`
chooses which worktree to delete, which safety guards fire before deletion, and
how the branch cleanup is decided. The body of `SKILL.md` is the quick path;
this file is the detail behind it.

## Target resolution

The script reads `git worktree list --porcelain` and resolves the single
positional argument against every worktree record. A record carries its `path`,
the short `branch` name (with `refs/heads/` stripped), the `HEAD` sha, and a
`detached` flag.

Resolution tries these forms and returns the **first** match:

| You pass                          | Matches against            | Example                  |
| --------------------------------- | -------------------------- | ------------------------ |
| Full path                         | `path` exactly             | `/repo/../boss-skills-auth` |
| Directory basename                | `Path(path).name`          | `boss-skills-auth`       |
| Exact branch name                 | `branch`                   | `worktree-auth`          |
| Bare name                         | derived `worktree-<name>`  | `auth` → `worktree-auth` |

The bare-name form is the convenience case: passing `auth` resolves to the
worktree whose branch is `worktree-auth`, matching the naming convention that
`/git-worktree` creates. If nothing matches, the script prints
`No worktree matches '<target>'` and exits non-zero without touching anything.

Resolution is a pure function over the parsed records, so an ambiguous or
misspelled target fails loudly rather than guessing.

## Safety-check matrix

All three guards run **before** the worktree is removed. The first one that
trips stops the run; nothing is deleted.

| Condition                         | Outcome                                                       | Override        |
| --------------------------------- | ------------------------------------------------------------ | --------------- |
| Branch is protected               | **BLOCK** — exit non-zero, no removal                        | none (by design)|
| Worktree has uncommitted changes  | **WARN + STOP** — prompts you to commit or force             | `--force`       |
| Branch not merged into main       | **WARN + CONTINUE** — "changes may be lost", then proceeds   | n/a (advisory)  |

### Protected-branch block

The protected set is `main`, `master`, `develop`, `staging`, and `production`.
If the resolved worktree sits on any of these, the script prints
`BLOCKED: '<branch>' is a protected branch.` and exits. There is intentionally
no flag to override this — protected branches are not throwaway feature
worktrees, and removing one is almost always a mistake.

### Uncommitted-change guard

The script runs `git status --porcelain` inside the target worktree. If it
reports anything, removal stops with a warning telling you to commit or re-run
with `--force`. This is the guard most worth respecting: `--force` is passed
through to `git worktree remove --force`, which discards the dirty tree.

### Merge-status check

The script resolves the repo's base branch from `origin/HEAD` (falling back to
`main`) and asks `git merge-base --is-ancestor <branch> <base>`. If the branch
is **not** an ancestor of base, it prints a "NOT merged… changes may be lost"
warning but does **not** stop — it proceeds and force-deletes the local branch.
The merge result also selects the branch-deletion flag (below).

## Branch-cleanup semantics

After the worktree is removed, the branch is cleaned up in two places unless you
opt out.

- **Local branch.** Deleted with `git branch -d` when the branch is merged into
  base, or `git branch -D` (force) when it is not. The merge check from above
  picks the flag, so an unmerged branch is still removed — the earlier warning
  is your signal to abort first if that is wrong.
- **Remote branch.** If `git ls-remote --heads origin <branch>` shows the branch
  exists on `origin`, the script runs `git push origin --delete <branch>`. If
  the remote branch is already gone, this step is silently skipped.
- **Reference pruning.** A final `git worktree prune` clears the stale
  `.git/worktrees/` bookkeeping the removal left behind.

### Opt-outs

| Flag            | Keeps                                                          |
| --------------- | ------------------------------------------------------------- |
| `--keep-branch` | The local branch (the remote is still deleted unless `--keep-remote`) |
| `--keep-remote` | The remote branch on `origin`                                 |

The two opt-outs are independent: `--keep-branch` guards only the local-branch
deletion, and `--keep-remote` guards only the remote-branch deletion. Use
`--keep-branch` when removing the working directory but still wanting the local
branch around — e.g. to re-check it out elsewhere. Use `--keep-remote` when a
teammate or an open PR still depends on the pushed branch (pass both to keep the
branch entirely).

## Failure modes

These expand on the "Common mistakes" list in `SKILL.md`.

- **Removing the worktree you are standing in.** `git worktree remove` refuses
  to delete the current worktree. Run the skill from another worktree (usually
  the primary checkout) and pass the feature worktree as the target.
- **Protected-branch refusal.** If you get `BLOCKED: '<branch>' is a protected
  branch`, you targeted a worktree on `main`/`develop`/etc. There is no
  override — double-check the target name; you almost certainly meant a feature
  worktree.
- **Lost uncommitted work with `--force`.** `--force` skips the dirty-tree guard
  *and* hard-removes the worktree. Anything uncommitted in that directory is
  gone. Prefer committing or stashing first; reserve `--force` for worktrees you
  are certain are disposable.
- **Remote already deleted.** If `origin/<branch>` was deleted earlier (merged
  PR auto-delete, manual cleanup), the remote-deletion step is skipped rather
  than erroring. The local branch and worktree still clean up normally.
- **No match.** A typo'd or non-existent target exits non-zero with
  `No worktree matches '<target>'` and changes nothing — safe to re-run with the
  corrected name.

## Related cleanup

If the work used a branchable database, the database branch is **not** touched
by this skill — delete it separately. The provider commands and the
"branch the DB or not" decision live in the create-side skill's reference:
[`../git-worktree/references/database-branching.md`](../git-worktree/references/database-branching.md).
