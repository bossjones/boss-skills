# Status semantics

This reference defines exactly how `git-worktree-status` classifies each
verification job, which logs it reads, where those logs come from, and how to
interpret each result. The status script (`scripts/git_worktree_status.py`)
takes no arguments and is read-only — it inspects log files and prints a
report. It never starts, stops, or re-runs a check.

## What the report reads

The script looks for a `.worktree-logs/` directory at the **top level of the
current worktree** and reads three known log files, in this display order:

| Log file               | Reported as  |
| ---------------------- | ------------ |
| `.worktree-logs/typecheck.log` | `Type check` |
| `.worktree-logs/tests.log`     | `Tests`      |
| `.worktree-logs/build.log`     | `Build`      |

Each log is read independently. A log that does not exist is reported as
`NOT_RUN`; the script does not treat a missing log as an error. Only these
three filenames are inspected — other files written under `.worktree-logs/`
are ignored by the status report.

## Where the logs come from

The status skill is a **reader, not a writer**. The `.worktree-logs/*.log`
files are produced by the background verification jobs that the
[`git-worktree`](../../git-worktree/SKILL.md) skill launches when it sets up a
worktree. Each language stack redirects the stdout/stderr of its type checker,
test runner, and build into the matching log file so the work happens
off the critical path:

- the type checker (e.g. `basedpyright`, `tsc`) writes `typecheck.log`;
- the test runner (e.g. `pytest`, `vitest`, `cargo test`, `go test`) writes
  `tests.log`;
- the build (e.g. `cargo build`, `go build`, a bundler) writes `build.log`.

The exact commands and how they are backgrounded for each stack live in the
`git-worktree` setup guides (see [Re-running checks](#re-running-checks)),
not here. This skill only needs the resulting log files to exist.

## Why the report is non-blocking

The status report is a **snapshot**, not a wait. It reads whatever the log
files contain at the moment it runs and returns immediately, even while a job
is still writing to its log. This is deliberate: an agent can poll the status
between other steps without stalling on a long test run or build. A job that
is still in progress simply shows as `RUNNING` (see below); re-run the status
command later to see whether it has reached a terminal state.

## The four statuses

Classification is **language-neutral**: it keys off textual markers that show
up across pytest, vitest, `tsc`, `basedpyright`, `cargo`, and `go` rather than
any single tool's exact format. The script does not parse exit codes — only
the captured log text.

### `NOT_RUN`

The log file is absent, or present but empty/whitespace-only. The job was
never started, or the logs were cleared. This is the default reported status
for any of the three known logs that is missing.

### `PASS`

The log indicates the check finished cleanly. Two kinds of evidence count:

- **A zero failure/error count.** When the log carries an explicit count and
  it is zero — e.g. `0 failed`, `0 errors`, or a `numFailedTests` of `0` — the
  job is a pass. Numeric counts are checked first and win over everything else,
  so a non-zero count of failures is decisive in the other direction.
- **An explicit success marker** when no failure count is present — e.g.
  `passed`, `build succeeded`, `success`, `no issues`, or a trailing ` ok`.

### `FAIL`

The log shows the check did not succeed. This is signalled either by a
**non-zero failure/error count** (e.g. `3 failed`, `2 errors`,
`numFailedTests` greater than zero), or by a hard-failure marker such as a
Python traceback header, a `tsc`-style `error TS…`, a `panic:`, a `fatal:`,
`build failed`, or a bare `failed`. Because counts are evaluated first, a log
that reports `0 failed` is **not** misclassified as a failure even though the
word "failed" appears in it.

### `RUNNING`

The log file exists and has content, but contains no terminal marker — no
failure/error count, no hard-failure signal, and no success marker yet. This
is the expected state for a job that is mid-flight and still appending output.

## Failure modes and how to interpret them

**Not inside a worktree → error.** The script first asks git for the common
git directory and confirms it points at `…/​.git/worktrees/…`. If you are in
the main repository, outside any git repo, or git is unavailable, it prints a
message and exits non-zero **without** producing a status table. Re-run it from
inside a worktree directory (one created by `git-worktree`).

**Missing log → `NOT_RUN`.** A check whose log file does not exist is reported
`NOT_RUN`, not `FAIL`. If you expected a job to be running, the launch step in
the `git-worktree` setup probably did not start it (or the `.worktree-logs/`
directory was removed). Re-launch from the relevant setup guide.

**Truncated or partial log → `RUNNING`.** A job that has written some output
but not yet a terminal marker reads as `RUNNING`. If a status stays `RUNNING`
far longer than the underlying job should take, the writer may have died
without flushing a final marker — open the log directly to see the last lines.

**Interpreting `FAIL` — where to look.** `FAIL` means the captured log text
matched a failure signal. Open the specific log under `.worktree-logs/`
(`typecheck.log`, `tests.log`, or `build.log`) to read the actual diagnostics:
the failing test names, the type error and its `error TS…`/​`basedpyright`
location, or the build/​panic output. The status report tells you *which*
check failed; the log tells you *why*.

## Re-running checks

This skill does not re-run anything. To re-launch a check, clear or overwrite
the relevant log and start the job from the language setup guide that owns the
command for your stack. Those guides live in the sibling `git-worktree` skill
so the launch detail lives in exactly one place:

- Python: [`../../git-worktree/references/setup-python.md`](../../git-worktree/references/setup-python.md)
- Node.js: [`../../git-worktree/references/setup-node.md`](../../git-worktree/references/setup-node.md)
- Rust: [`../../git-worktree/references/setup-rust.md`](../../git-worktree/references/setup-rust.md)
- Go: [`../../git-worktree/references/setup-go.md`](../../git-worktree/references/setup-go.md)

After re-launching, run `/git-worktree-status` again to read the fresh logs.
