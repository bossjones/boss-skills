# Cleanup Semantics

How `scripts/git_worktree_clean.py` decides what to remove, what it never
touches, and how it measures reclaimed disk. This is the detail behind the
short summary in `SKILL.md` — read it before running `--all` or `--force`, or
when a cleanup result is surprising.

## Classification: protected / merged / unmerged

Every worktree the script finds is sorted into exactly one of three buckets.
The order matters — protection wins over merge status.

1. **protected** — the worktree's branch is one of the protected names
   (`main`, `master`, `develop`, `staging`, `production`). These are never
   removed regardless of merge state. The main worktree (the first entry from
   `git worktree list --porcelain`) is also skipped outright before
   classification even runs.
2. **merged** — the branch is an ancestor of the main branch, i.e.
   `git merge-base --is-ancestor <branch> <base>` succeeds. The work has
   already landed, so the worktree is safe to remove.
3. **unmerged** — anything else: a branch with commits not yet in the main
   branch, *or* a detached-HEAD worktree (no branch name at all). Detached
   worktrees are treated as unmerged because the script can't prove their work
   is safe.

The "main branch" used as the merge base is resolved from
`origin/HEAD` (its short name), falling back to `main` when that ref is absent.

### What gets removed

| Bucket    | Default run        | With `--all`                  |
| --------- | ------------------ | ----------------------------- |
| protected | kept               | kept (always)                 |
| merged    | removed            | removed                       |
| unmerged  | kept and reported  | removed (force-deletes branch)|

After any non-dry run, the script calls `git worktree prune` to clear stale
administrative references left behind by removals or by worktrees deleted
out-of-band.

## What each flag does

- **`--dry-run`** — Preview only. Classifies everything and prints the report
  ("Would remove …", "Potential space savings …") but runs no `git worktree
  remove`, no branch deletion, and no prune. Make a habit of running this
  first; it's the cheapest way to confirm the script sees what you expect.
- **`--all`** — Widens removal to include the unmerged bucket. Merged
  worktrees still get a safe `git branch -d`; unmerged ones get a
  force-delete (`git branch -D`) because git would otherwise refuse to drop an
  unmerged branch. This is where unreviewed work can be lost — see failure
  modes below.
- **`--force`** — Passes `--force` to `git worktree remove`, skipping git's
  guard against removing a worktree with uncommitted or untracked changes.
  Independent of `--all`: `--all` decides *which* worktrees are eligible,
  `--force` decides whether a *dirty* one can still be removed.

Branch deletion choice is driven by merge status, not the flags directly: a
merged worktree always uses `-d` (git's own safety net), an unmerged worktree
removed under `--all` uses `-D`.

## Safety rules

- The main worktree is never a removal candidate.
- Protected branches are never removed, even with `--all --force`.
- Removal goes through `git worktree remove` (and `git branch -d/-D`), never a
  raw `rm -rf` — so git's own integrity checks and administrative bookkeeping
  stay in the loop, and `git worktree prune` tidies the rest.
- A merged branch is deleted with `-d`, so even if classification were wrong
  git would refuse the delete rather than discard unmerged commits.

## Disk accounting

The reclaimed-space figure is an honest on-disk measurement of each removed
worktree, computed by walking the directory tree with two deliberate skips:

- **Symlinks are skipped.** A shared `node_modules` (or any other symlinked
  dependency tree) points at storage you are not actually reclaiming by
  removing the worktree, so counting it would overstate savings.
- **`.git` metadata is skipped.** Any path with `.git` in its components is
  excluded so linked-worktree git plumbing doesn't inflate the total.

Files that can't be `stat`'d are skipped rather than aborting the walk. The
total is the sum of regular-file sizes under those rules, formatted as
B/KB/MB/GB. In `--dry-run` the same measurement is taken and reported as
"potential" savings without anything being removed.

## Failure modes

- **Running `--force` (or any real run) without `--dry-run` first.** Without a
  preview you are trusting the script's classification blind. Dry-run once,
  read the "Would remove" and "Kept (unmerged)" lists, then run for real.
- **Losing unmerged work with `--all`.** `--all` force-deletes unmerged
  branches (`git branch -D`). If a worktree held commits or local-only work you
  still wanted, they're gone. Prefer reviewing unmerged worktrees individually
  with [`/git-worktree-remove`](../git-worktree-remove/SKILL.md) and reserve
  `--all` for batches you've already triaged.
- **Detached-HEAD worktrees swept up by `--all`.** A detached worktree has no
  branch name and is classified unmerged, so `--all` will remove it. If you
  parked a build or experiment at a detached commit, name a branch first or
  remove it deliberately.
- **Dirty worktrees and the `--force` guard.** Without `--force`, git refuses
  to remove a worktree with uncommitted or untracked changes — that refusal is
  a feature. Reach for `--force` only after confirming there's nothing in those
  changes you need.
- **Stale locks or references blocking a remove.** A worktree left locked, or
  whose directory was deleted out of band, can make `git worktree remove`
  fail. The trailing `git worktree prune` clears orphaned administrative
  entries; for a stuck lock, inspect with
  [`/worktree-doctor`](../worktree-doctor/SKILL.md) and unlock or prune before
  retrying.
- **Expecting database branches to disappear.** This script only removes
  worktrees and their git branches. A branchable database provisioned for the
  work is untouched — see the database-cleanup pointer in `SKILL.md`.
