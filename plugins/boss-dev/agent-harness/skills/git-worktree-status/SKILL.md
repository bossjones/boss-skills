---
name: git-worktree-status
description: Report the status of background verification jobs (tests, type check, build) in a git worktree. Use when you want a non-blocking PASS/FAIL/RUNNING/NOT_RUN summary of the checks launched by the git-worktree skill, run from inside a worktree directory.
effort: low
allowed-tools:
  - Bash(uv run:*)
  - Bash(git rev-parse:*)
disable-model-invocation: true
---

# Git Worktree Status

Report background verification jobs launched by [`/git-worktree`](../git-worktree/SKILL.md),
without blocking. A Python script detects the worktree, reads
`.worktree-logs/*.log`, and classifies each job using language-neutral markers
(works for pytest, vitest, tsc, basedpyright, cargo, go).

**Part of the Worktree Lifecycle Suite:** [`/git-worktree`](../git-worktree/SKILL.md) | [`/git-worktree-remove`](../git-worktree-remove/SKILL.md) | [`/git-worktree-clean`](../git-worktree-clean/SKILL.md)

## Steps

Run from inside any worktree directory:

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/git_worktree_status.py"
```

The script:

- confirms the working directory is a worktree (errors out if run from the main
  repo or outside git);
- reads `.worktree-logs/typecheck.log`, `tests.log`, and `build.log`;
- reports each as `PASS`, `FAIL`, `RUNNING`, or `NOT_RUN`.

## Status meanings

| Status    | Meaning                                                      |
| --------- | ------------------------------------------------------------ |
| `PASS`    | Log shows zero failures/errors or an explicit success marker |
| `FAIL`    | Log shows failures, errors, a traceback, or a panic          |
| `RUNNING` | Log exists but has no terminal marker yet                    |
| `NOT_RUN` | No log file (the job was never started or logs were cleared) |

## Re-running checks

The language-specific commands that write these logs live in the `git-worktree`
references, not here. To re-run them, clear the logs and relaunch from the
matching reference for your stack:

- Python: [../git-worktree/references/setup-python.md](../git-worktree/references/setup-python.md)
- Node.js: [../git-worktree/references/setup-node.md](../git-worktree/references/setup-node.md)
- Rust: [../git-worktree/references/setup-rust.md](../git-worktree/references/setup-rust.md)
- Go: [../git-worktree/references/setup-go.md](../git-worktree/references/setup-go.md)

## Usage

```
/git-worktree-status
```

No arguments. Run from inside a worktree directory.
