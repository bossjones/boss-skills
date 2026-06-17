# Go worktree setup

After `git_worktree.py` creates the worktree:

## 1. Download dependencies

```bash
cd .claude/worktrees/<repo>-<name>
go mod download
```

The Go module cache (`$GOPATH/pkg/mod`) is shared, so downloads are reused
across worktrees.

## 2. Environment files

`git_worktree.py` copied `.worktreeinclude`-matched gitignored files and ran
`direnv allow` if an `.envrc` was copied. Never print `.env`/`.envrc`.

## 3. Background verification

```bash
mkdir -p .worktree-logs
go build ./... > .worktree-logs/build.log 2>&1 &
go test ./... > .worktree-logs/tests.log 2>&1 &
```

`/git-worktree-status` parses these logs for pass/fail.
