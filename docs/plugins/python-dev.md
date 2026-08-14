# python-dev

> `boss-dev` · v1.0.0 · [plugin source](../../plugins/boss-dev/python-dev/)

Python development tooling for Claude Code: debug GitHub Actions CI failures end-to-end and
ship changes via conventional-commit pull requests. The plugin ships two slash commands and
assumes a `uv`-based Python project.

## Installation

```bash
/plugin marketplace add bossjones/boss-skills   # once
/plugin install python-dev@boss-skills
```

## Commands

Slash commands are namespaced `/python-dev:<command>`.

| Command | Allowed tools | Description |
|---------|---------------|-------------|
| `/python-dev:debug-ci` | Bash, Read, Edit, Write, Glob, Grep, Agent | Diagnose a failed GitHub Actions run, fix the issues locally, validate, commit, push, and poll until the new run passes. Up to 3 outer retry cycles. |
| `/python-dev:commit-push-pr` | Bash, Read, Glob, Grep | Stage modified files (skipping secrets), write a conventional commit, push to the remote, and open or update a GitHub PR via `gh`. |

## Project assumptions

These commands assume the target repository is a Python project that uses:

| Tool | Role | Typical invocation |
|------|------|--------------------|
| `uv` | Package manager | `uv lock`, `uv run`, `uv add` |
| `ruff` | Linter and formatter | `uv run ruff check`, `uv run ruff format` |
| `ty` | Type checker | `uv run ty check` |
| `deptry` | Dependency analyzer | `uv run deptry src` |
| `pre-commit` | Git hooks | `uv run pre-commit run --all-files` |
| `mkdocs` | Documentation builder | `make docs-test` |

It also expects `make test` and `make docs-test` targets that mirror the CI jobs.

## External requirements

- `git` on `PATH`
- `gh` CLI authenticated — run `gh auth login` first
- `uv` on `PATH`

## Usage examples

### Debug a failed CI run

```text
/python-dev:debug-ci
```

The command pulls the most recent failed GitHub Actions run, identifies which jobs failed
(ruff, ty, deptry, pre-commit, pytest, or mkdocs), reproduces and fixes them locally,
commits and pushes the fix, then polls the new run. It retries up to three times before
handing back control.

### Ship the current changes as a PR

```text
/python-dev:commit-push-pr
```

Stages the modified files (skipping anything that looks like a secret), writes a
[Conventional Commits](https://www.conventionalcommits.org/) message, pushes the branch,
and opens — or updates — a GitHub pull request with `gh`.

### Chain both: fix CI, then open the PR

```text
/python-dev:debug-ci
/python-dev:commit-push-pr
```

Use `debug-ci` to get the branch green, then `commit-push-pr` to package any remaining
work into a reviewable PR.

## See also

- Plugin source: [`plugins/boss-dev/python-dev/`](../../plugins/boss-dev/python-dev/)
- Plugin README: [`plugins/boss-dev/python-dev/README.md`](../../plugins/boss-dev/python-dev/README.md)
