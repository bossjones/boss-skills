# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Personal Claude Code skills repository. Contains Claude Code skills (`.claude/skills/`), slash commands (`.claude/commands/`), and development tools.

## Commands

```bash
# Install dependencies
make install

# Run linting (ruff + basedpyright) - auto-fixes formatting and imports
make lint

# Run tests
make test

# Run single test with output
uv run pytest -s path/to/test.py

# Run all checks (install, lint, test)
make

# Type checking with ty
make check

# Lint markdown files
make markdown-lint

# Check links in markdown
make link-check
```

## Architecture

### Claude Code Skills (`/.claude/skills/`)

Skills are self-contained features with:
- `SKILL.md` - Main definition (name, description, instructions)
- `scripts/` - Python scripts using PEP 723 inline metadata

Current skills:
- **twitter-media-downloader**: Downloads media from X/Twitter using gallery-dl
- **twitter-to-reel**: Converts tweets to Instagram Reels format (9:16 vertical)
- **doc-generator**: Generates markdown docs from Python codebases

### Slash Commands (`/.claude/commands/`)

- `convert-to-agent.md`: Convert slash command to sub-agent
- `convert-to-slash.md`: Convert sub-agent to slash command

### Development Tools (`/devtools/`)

- `lint.py` (`make lint`): codespell + `ruff check --fix` + `ruff format` on `devtools/`, `scripts/`, `plugins/`; `basedpyright` on `devtools/`, `scripts/` (plus select agent-harness scripts). Does NOT cover `tests/` or `.claude/` (ruff excludes `.claude/`).

## Code Standards

### Python

- Python 3.11-3.13, full type annotations required
- Use `from __future__ import annotations` in typed files
- Use `pathlib.Path` over `os.path`
- Use absolute imports only (no relative imports like `from .module`)
- Use `@override` decorator when overriding base class methods
- Use modern syntax: `str | None` not `Optional[str]`, `list[str]` not `List[str]`
- Import `Callable`, `Coroutine` from `collections.abc`, use `typing_extensions` for `@override`

### PEP 723 Scripts

Standalone scripts use inline metadata:
```python
#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.13"
# dependencies = ["rich>=13.0.0"]
# ///
```

### Linting

- Formatter: ruff format (120 char line length; config in `pyproject.toml`)
- Linter: ruff check — rule set in `pyproject.toml` `[tool.ruff.lint]` (E/W, F, UP, B, SIM, I, S, RUF, TRY, C4, C90, A, YTT, T10, PGH)
- Type checker: basedpyright (recommended mode)

Zero linter warnings/errors required before task completion.

## Skill Development

### SKILL.md Requirements

1. YAML frontmatter with `name` and `description`
2. Concrete trigger patterns (not vague like "when needed")
3. Step-by-step instructions
4. Example commands

### Critical Parser Bug (GitHub #12781)

The skill parser executes backtick patterns inside fenced code blocks. Never use `!`backtick patterns in SKILL.md - use `$ command` notation instead.

### Eval reports

PluginEval reports live under `docs/evals/<plugin>/<skill>.md` (repo-internal skills:
`docs/evals/<skill>.md`) — **not** inside the skill directory. An eval report is generated
process/meta output, not content an agent needs to do the job, so a skill folder stays limited
to `SKILL.md` + `references/` + `scripts/`. The [`/skill-evals`](.claude/skills/skill-evals/SKILL.md)
skill / `make eval-skill` writes there; see [`docs/evals/README.md`](docs/evals/README.md) for the
index. These files are regenerated output — overwrite freely.

### Skill workspace directories

`skill-creator`'s Description Optimization loop (and similar tooling) writes scratch output —
eval fixtures, `trigger-eval.json`, benchmark results — to a sibling `<skill-name>-workspace/`
directory. `scripts/verify-structure.py` treats any `*-workspace` directory name as non-skill
scratch (like the existing `logs` exclusion), so it's valid either under `skills/` next to the
skill it belongs to, or at the plugin root.

## Second Brain (obsidian-wiki)

[`obsidian-wiki`](https://github.com/ar9av/obsidian-wiki) is a globally-installed uv tool that maintains an Obsidian markdown "digital brain" (Karpathy's LLM-Wiki pattern: distill knowledge once into interconnected notes).

- **One-command bootstrap**: run the `setup-second-brain` skill (agent-harness plugin). It detects what's present, previews every change, then installs obsidian-wiki, runs setup against the vault, and optionally installs/configures QMD. The steps below are what it automates.
- **Install** (never pip; it's a global CLI, not a repo dependency, so do NOT add it to `pyproject.toml`/`uv sync`):

  ```bash
  uv tool install "obsidian-wiki[graph,ast]"   # graph = export/analysis, ast = code parsing
  uv tool upgrade obsidian-wiki                  # later upgrades
  ```

- **Setup** (one-time, machine-level): `obsidian-wiki setup --vault ~/Documents/obsidian/personal.vault` writes `~/.obsidian-wiki/config` and symlinks its skills into `~/.claude/skills/` (and other agents' skill dirs). Verify with `obsidian-wiki info` / `obsidian-wiki list`.
- **Vault path**: default `~/Documents/obsidian/personal.vault` (documented in `.env.sample` as `OBSIDIAN_VAULT_PATH`). The authoritative path lives in `~/.obsidian-wiki/config`, not the env var.
- **Skills** (invoked automatically once installed): ingest sources (`wiki-ingest`, `wiki-update`, `wiki-research`), query (`wiki-query`, `wiki-status`), maintain (`wiki-lint`, `cross-linker`, `wiki-dedup`, `tag-taxonomy`), capture (`wiki-capture`), export (`wiki-export`, `graph-colorize`), and mine agent history (`claude-history-ingest`, `codex-history-ingest`, etc.). Manage multiple vaults with `wiki-switch`.
- **QMD semantic search** (optional): [`@tobilu/qmd`](https://github.com/tobi/qmd) upgrades `wiki-query`/`wiki-ingest` from Grep to on-device semantic search. Requires **Node ≥ 22**; install with `npm install -g @tobilu/qmd`. Configure via `QMD_TRANSPORT` (`cli` or `mcp`), `QMD_WIKI_COLLECTION`, `QMD_PAPERS_COLLECTION`, `QMD_CLI_SEARCH_MODE` (see `plugins/boss-dev/agent-harness/docs/getting-started.md`); the wiki skills read these from `~/.obsidian-wiki/config` and silently fall back to Grep when unset. Index with `qmd collection add <vault> --name wiki && qmd embed`.

## Testing

- Place tests in `tests/` directory as `test_*.py`
- Simple inline tests can go below `## Tests` comment in source files
- Run with `uv run pytest -s` to see output
- No trivial tests for obvious functionality
- PEP 723 scripts are tested by loading them with `importlib.util.spec_from_file_location` (the `if __name__ == "__main__"` guard makes import side-effect-free)
  - Exception: a stdlib-only PEP 723 script whose tests assert CLI exit codes, argparse flag behavior, or end-to-end severity counts may be invoked via subprocess (`sys.executable`), since `importlib` loading cannot exercise CLI semantics

## Agent skills

### Issue tracker

Issues live in GitHub Issues for `bossjones/boss-skills`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default five-label vocabulary (needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix). See `docs/agents/triage-labels.md`.

### Domain docs

Single-context — one `CONTEXT.md` + `docs/adr/` at the repo root. See `docs/agents/domain.md`.
