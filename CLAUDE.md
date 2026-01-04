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

- `lint.py`: Runs codespell, ruff check/format, basedpyright on `devtools/` and `.claude/skills/`

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

- Formatter: ruff format (100 char line length)
- Linter: ruff check (E, F, UP, B, SIM, I rules)
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

## Testing

- Place tests in `tests/` directory as `test_*.py`
- Simple inline tests can go below `## Tests` comment in source files
- Run with `uv run pytest -s` to see output
- No trivial tests for obvious functionality
