# Rust worktree setup

After `git_worktree.py` creates the worktree:

## 1. Build dependencies

```bash
cd .claude/worktrees/<repo>-<name>
cargo build
```

Cargo's registry cache is shared, so dependency downloads are reused across
worktrees. The `target/` directory is per-worktree; add it to
`.worktreeinclude` only if you deliberately want to copy build artifacts (you
usually do not — a fresh `cargo build` is cleaner).

## 2. Environment files

`git_worktree.py` copied `.worktreeinclude`-matched gitignored files and ran
`direnv allow` if an `.envrc` was copied. Never print `.env`/`.envrc`.

## 3. Background verification

```bash
mkdir -p .worktree-logs
cargo build > .worktree-logs/build.log 2>&1 &
cargo test > .worktree-logs/tests.log 2>&1 &
```

`/git-worktree-status` parses these logs for pass/fail.
