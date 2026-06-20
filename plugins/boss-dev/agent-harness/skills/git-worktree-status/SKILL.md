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

Report the background verification jobs launched by
[`/git-worktree`](../git-worktree/SKILL.md), without blocking. A Python script
detects the worktree, reads `.worktree-logs/*.log`, and classifies each job
using language-neutral markers (works for pytest, vitest, tsc, basedpyright,
cargo, go). It is read-only — it never starts, stops, or re-runs a check.

## Steps

Run from inside any worktree directory:

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/git_worktree_status.py"
```

`scripts/git_worktree_status.py` takes **no arguments**. Run it from inside a
worktree; everything it needs comes from git and the log files. It:

- confirms the working directory is a worktree by inspecting git's common
  directory, and exits non-zero without a report if run from the main repo,
  outside git, or where git is unavailable;
- reads three known logs at the worktree top level —
  `.worktree-logs/typecheck.log`, `.worktree-logs/tests.log`, and
  `.worktree-logs/build.log` — each independently, with a missing log treated
  as `NOT_RUN` rather than an error;
- classifies each log from its captured text (not exit codes), reporting
  `PASS`, `FAIL`, `RUNNING`, or `NOT_RUN`, and returns immediately so a job
  still writing its log simply shows as `RUNNING`.

The logs themselves are produced by the background jobs that `git-worktree`
launches during worktree setup; this skill only reads them. See
[references/status-semantics.md](references/status-semantics.md) for the exact
markers behind each status and how to interpret failures.

## Status meanings

| Status    | Meaning                                                      |
| --------- | ------------------------------------------------------------ |
| `PASS`    | Log shows zero failures/errors or an explicit success marker |
| `FAIL`    | Log shows failures, errors, a traceback, or a panic          |
| `RUNNING` | Log exists but has no terminal marker yet                    |
| `NOT_RUN` | No log file (the job was never started or logs were cleared) |

Numeric counts win first: a log reporting `0 failed` is a `PASS` even though it
contains the word "failed". For the precise per-status markers and the
failure-mode rundown (not a worktree, missing log, truncated log, where to look
on `FAIL`), see [references/status-semantics.md](references/status-semantics.md).

## Reference Files

- [references/status-semantics.md](references/status-semantics.md) — precise
  `PASS`/`FAIL`/`RUNNING`/`NOT_RUN` definitions, the language-neutral markers,
  which logs are read, why the report is non-blocking, and failure modes.

Re-running a check is **not** this skill's job — the commands that write these
logs are owned by the `git-worktree` setup guides so the launch detail lives in
one place. To re-launch a check, clear the relevant log and start it from the
guide for your stack:

- Python: [../git-worktree/references/setup-python.md](../git-worktree/references/setup-python.md)
- Node.js: [../git-worktree/references/setup-node.md](../git-worktree/references/setup-node.md)
- Rust: [../git-worktree/references/setup-rust.md](../git-worktree/references/setup-rust.md)
- Go: [../git-worktree/references/setup-go.md](../git-worktree/references/setup-go.md)

## Related skills

This skill is the status reader in the **worktree lifecycle suite**.
[`/git-worktree`](../git-worktree/SKILL.md) creates a worktree and launches the
background checks; the rest of the suite manages those worktrees:

- [`/git-worktree`](../git-worktree/SKILL.md) — create a worktree and launch the verification jobs
- [`/git-worktree-status`](SKILL.md) — read those jobs' status (this skill)
- [`/git-worktree-clean`](../git-worktree-clean/SKILL.md) — clean up worktree artifacts
- [`/git-worktree-remove`](../git-worktree-remove/SKILL.md) — remove a worktree
- [`/worktree-doctor`](../worktree-doctor/SKILL.md) — diagnose worktree health

## Usage

```
/git-worktree-status
```

No arguments. Run from inside a worktree directory.
