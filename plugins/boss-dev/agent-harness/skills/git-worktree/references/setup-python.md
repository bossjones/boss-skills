# Python / uv worktree setup (first-class)

After `git_worktree.py` creates the worktree, set up an isolated Python
environment. This is the default path for this repo.

## 1. Isolated dependencies

```bash
cd .claude/worktrees/<repo>-<name>
uv sync --all-extras
```

`uv sync` builds a fresh `.venv` in the worktree — no symlinking, full
isolation. This is fast because uv's global cache is reused across worktrees.

## 2. Environment files

`git_worktree.py` already copied any `.worktreeinclude`-matched, gitignored
files (`.env`, `.envrc`, …) into the worktree and ran `direnv allow` if an
`.envrc` was copied. If direnv was missing or the copy was declined, allow it
manually from inside the worktree:

```bash
direnv allow .
```

Never print or cat `.env` / `.envrc` — they hold secrets.

## 3. Background verification (non-blocking)

Launch checks into `.worktree-logs/` so `/git-worktree-status` can report on
them without blocking:

```bash
mkdir -p .worktree-logs
uv run pytest -q > .worktree-logs/tests.log 2>&1 &
uv run basedpyright > .worktree-logs/typecheck.log 2>&1 &
```

If the project uses `ty` instead of basedpyright:

```bash
uv run ty check > .worktree-logs/typecheck.log 2>&1 &
```

`/git-worktree-status` parses these logs for `PASS`/`FAIL`/`RUNNING`/`NOT_RUN`.
