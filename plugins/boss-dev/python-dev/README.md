# python-dev

Python development tooling for Claude Code: debug GitHub Actions CI failures end-to-end and ship
changes via conventional-commit PRs.

## Installation

```bash
/plugin install python-dev@boss-skills
```

## Components

### Commands

- **`/python-dev:debug-ci`** — Diagnose a failed GitHub Actions run, fix the issues locally (ruff, ty,
  deptry, pre-commit, pytest, mkdocs), validate, commit, push, and poll until the new run passes. Up to
  3 outer retry cycles.
- **`/python-dev:commit-push-pr`** — Stage modified files (skipping secrets), write a conventional
  commit, push to the remote, and open or update a GitHub PR via `gh`.

## Project Assumptions

These commands assume the target repo is a Python project that uses:

- **`uv`** — package manager (`uv lock`, `uv run`, `uv add`)
- **`ruff`** — linter and formatter (`uv run ruff check`, `uv run ruff format`)
- **`ty`** — type checker (`uv run ty check`)
- **`deptry`** — dependency analyzer (`uv run deptry src`)
- **`pre-commit`** — git hooks (`uv run pre-commit run --all-files`)
- **`mkdocs`** — documentation builder
- Make targets `make test` and `make docs-test` mirroring CI jobs

## External Requirements

- `git` on PATH
- `gh` CLI authenticated (`gh auth login`)
- `uv` on PATH

## Status

Initial release — two commands shipped. See the `boss-skills` marketplace entry under `plugins/boss-dev/python-dev/`.
