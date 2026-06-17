# Generic worktree setup (unknown project type)

No recognized project marker (`pyproject.toml`, `package.json`, `Cargo.toml`,
`go.mod`) was found. Make no dependency-manager assumptions.

## 1. Environment files

`git_worktree.py` already copied any `.worktreeinclude`-matched gitignored
files into the worktree and ran `direnv allow` if an `.envrc` was copied. If
the project relies on env files not yet listed, add them to `.worktreeinclude`
(see [worktreeinclude.md](worktreeinclude.md)) and re-run, or copy them
manually. Never print `.env`/`.envrc`.

## 2. Dependencies

Run whatever the project's own docs prescribe (`make install`, a setup script,
etc.). There is no auto-detected command for an unknown stack.

## 3. Background verification (optional)

If the project has a test or build command, run it into `.worktree-logs/` so
`/git-worktree-status` can report on it:

```bash
mkdir -p .worktree-logs
<your-test-command> > .worktree-logs/tests.log 2>&1 &
```
