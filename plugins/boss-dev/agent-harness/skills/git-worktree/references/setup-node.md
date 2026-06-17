# Node.js worktree setup

After `git_worktree.py` creates the worktree, install dependencies and launch
background checks.

## 1. Dependencies

Detect the package manager from the lockfile and install:

| Lockfile            | Command        |
| ------------------- | -------------- |
| `pnpm-lock.yaml`    | `pnpm install` |
| `yarn.lock`         | `yarn install` |
| `package-lock.json` | `npm install`  |

```bash
cd .claude/worktrees/<repo>-<name>
pnpm install   # or yarn / npm per the lockfile
```

### Optional: reuse `node_modules` (speed over isolation)

To avoid a full reinstall (~30s), symlink the main worktree's `node_modules`:

```bash
ln -s "$(git rev-parse --show-toplevel | xargs dirname | xargs dirname)/node_modules" node_modules
```

Use a fresh install (the `--isolated` escape hatch — no symlink) when changing
dependency versions, testing upgrades, or debugging `node_modules` issues.

## 2. Environment files

`git_worktree.py` copied `.worktreeinclude`-matched gitignored files and ran
`direnv allow` if an `.envrc` was copied. Never print `.env`/`.envrc`.

## 3. Background verification

```bash
mkdir -p .worktree-logs
npx tsc --noEmit > .worktree-logs/typecheck.log 2>&1 &
npx vitest run --reporter=json > .worktree-logs/tests.log 2>&1 &
```

`/git-worktree-status` parses these logs.
