# Copilot Instructions for boss-skills

## Commands

| Task | Command |
| --- | --- |
| Install dependencies | `make install` |
| Run the usual repository checks | `make` |
| Lint Python sources | `make lint` |
| Run all tests | `make test` |
| Run the CI test groups | `make ci` |
| Run one test file or test | `uv run pytest -s tests/test_verify_structure.py` or `uv run pytest -s tests/test_verify_structure.py::TestComponentDirectories::test_skills_empty` |
| Validate marketplace manifests and component layout | `make verify-structure` |
| Run the skill-quality CI gate | `make eval-ci` |
| Lint Markdown and SKILL.md files | `make markdown-lint` |
| Check Markdown links | `make link-check` |
| Build the distribution | `make build` |

`make lint` intentionally runs auto-fixing `codespell`, `ruff check`, and `ruff format`, then
`basedpyright` only on curated paths. It does not lint `tests/`, `.claude/`, or the vendored
`scripts/plugin_eval/` tree. CI runs the linter on Python 3.13 and 3.14, plus Unicode hygiene,
`make eval-ci`, and `make ci`.

## Architecture

- This is a Claude Code plugin marketplace. `.claude-plugin/marketplace.json` is the catalog; each
  local distributable plugin lives at `plugins/<category>/<plugin-name>/` with its own manifest,
  README, and optional skills, commands, agents, hooks, LSP, or MCP configuration.
- `plugins/` is the source of truth for distributed components. `scripts/symlink_plugins.py`
  mirrors plugin components into `.claude/` for local dogfooding, usually as relative symlinks.
  When a `.claude/` item is symlinked, edit its plugin source rather than the mirror.
- Root `scripts/` and `devtools/` provide repository-wide validation and maintenance tooling.
  Pytest collects both root tests and plugin tests; tests for standalone, hyphenated scripts load
  them with `importlib` so imports remain side-effect free.
- `.cursor/rules/` is the canonical shared agent-policy source. `make agent-rules` generates
  `CLAUDE.md` and `AGENTS.md` from those rules; change the Cursor rules instead of hand-editing
  generated files.

## Repository Conventions

- For a plugin, keep `.claude-plugin/plugin.json` and its marketplace entry aligned on version,
  description, keywords, and author. `plugin.json` rejects unrecognized fields. Every local
  plugin also needs a README; optional `skills/`, `commands/`, `agents/`, and `hooks/` directories
  must be omitted when unused rather than left empty.
- Skills require YAML frontmatter with `name` and `description`, concrete activation triggers, and
  actionable instructions. Never place an exclamation mark immediately followed by a backtick in a
  fenced `SKILL.md` code block; the parser can execute it. Use `$ command` notation in examples.
- Plugin-facing documentation changes require a per-plugin page under `docs/plugins/` and matching
  entries in both the root `README.md` and `docs/plugins/README.md`. Run Markdown linting and link
  checks for those changes.
- Feature-bearing plugin changes require a version bump that stays in lockstep between the plugin
  manifest and marketplace entry; use the repository's `version-bump-reviewer` workflow instead
  of changing those versions independently.
- Standalone Python scripts use PEP 723 `uv` metadata. Target Python 3.13+ and follow the
  repository's typed-script conventions: `from __future__ import annotations`, absolute imports,
  `pathlib.Path`, modern unions, and `typing_extensions.override` for overrides.
- When changing `agent-harness`, resolve runtime storage with
  `hooks/utils/harness_paths.py`. Do not add cwd-relative `logs/` or `.claude/data/` paths, and do
  not migrate legacy artifacts automatically.
