# Tutorial: Get a red CI run green, then ship the fix

`python-dev` debugs failed GitHub Actions runs end-to-end and ships changes as conventional-commit
PRs. This walkthrough takes a failing CI run, fixes it locally, and opens a pull request.

**Time:** ~10 minutes · **Level:** intermediate · **Reference:** [python-dev.md](../../plugins/python-dev.md)

## Prerequisites

| You need | Notes |
|----------|-------|
| The plugin | `/plugin install python-dev@boss-skills` |
| `git` + `gh` CLI authenticated | `gh auth status` (run `gh auth login` first) |
| A `uv`-based Python project | with `ruff`, `ty`, `deptry`, `pre-commit`, `mkdocs`, and `make test` / `make docs-test` targets mirroring CI |

## Step 1 — Debug the failed CI run

From the repo whose latest CI run failed:

```text
/python-dev:debug-ci
```

The command pulls the most recent failed GitHub Actions run, identifies which jobs failed (ruff, ty,
deptry, pre-commit, pytest, or mkdocs), reproduces and fixes them locally, commits and pushes the
fix, then polls the new run — retrying up to three times before handing back control.

## Step 2 — Ship the changes as a PR

Once the branch is green (or to package any remaining local work):

```text
/python-dev:commit-push-pr
```

Stages the modified files (skipping anything that looks like a secret), writes a
[Conventional Commits](https://www.conventionalcommits.org/) message, pushes the branch, and opens —
or updates — a GitHub PR with `gh`.

## Step 3 — Respond to review comments

After reviewers leave unresolved comments, fetch them, apply fixes, push, and reply per thread:

```text
/python-dev:fix-gh-pr-comments
```

It evaluates each unresolved thread, applies the fixes locally, validates, pushes, replies, and polls
for new comments — up to three outer cycles.

## The full chain

```text
/python-dev:debug-ci            # get the branch green
/python-dev:commit-push-pr      # open/update the PR
/python-dev:fix-gh-pr-comments  # address review feedback
```

## What you get

A failing CI run diagnosed and fixed at its root cause, packaged into a conventional-commit PR, with
review feedback handled — without leaving Claude Code.

## Next steps

- Reference: [`docs/plugins/python-dev.md`](../../plugins/python-dev.md)
- Plugin README: [`plugins/boss-dev/python-dev/README.md`](../../../plugins/boss-dev/python-dev/README.md)
- Back to all [tutorials](../README.md)
