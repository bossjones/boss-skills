# Plan: Port the `meta-docs` plugin to `boss-skills` for Claude Code, Copilot CLI, and Codex

## Task Description

Port the `meta-docs` plugin from `Adobe-AIFoundations/aif-skills` into `boss-skills`, combining
two upstream pull requests into one change:

- `Adobe-AIFoundations/aif-skills#117` added the plugin: the `unslop`, `humanize-skills`, and
  `interrogate` skills, the `docs-anti-slop-reviewer` subagent, Claude and Codex manifests, a Codex
  marketplace entry, plugin docs, and tutorials.
- `Adobe-AIFoundations/aif-skills#118` removed `"agents": "./agents/"` from both manifests, because
  Claude Code rejects a directory string in `agents`. It also added a validator rule that catches
  the mistake.

The plugin layout matches upstream. The port also has to install on all three runtimes that
`boss-skills` targets: Claude Code, GitHub Copilot CLI, and Codex.

- **Task Type**: `feature`
- **Complexity**: `medium`

## Runtime Matrix

| Runtime | Marketplace file | Plugin manifest | Components loaded |
|---|---|---|---|
| Claude Code | `.claude-plugin/marketplace.json` | `.claude-plugin/plugin.json` | Skills and subagent |
| GitHub Copilot CLI | `.claude-plugin/marketplace.json` | `.claude-plugin/plugin.json` | Skills and subagent |
| Codex | `.agents/plugins/marketplace.json` (new) | `.codex-plugin/plugin.json` | Skills |

Copilot CLI reads the Claude marketplace and manifest directly, so it needs no extra manifest.
Codex needs its own manifest and marketplace. `meta-docs` is the first `boss-skills` plugin to
ship them.

## Layout

```text
.agents/plugins/marketplace.json            # new Codex marketplace (meta-docs only)
.claude-plugin/marketplace.json             # + meta-docs entry (category: meta)
.claude/agents/docs-anti-slop-reviewer.md   # symlink (scripts/symlink_plugins.py)
.claude/skills/{humanize-skills,interrogate,unslop}  # symlinks (scripts/symlink_plugins.py)
plugins/meta/meta-docs/
├── .claude-plugin/plugin.json
├── .codex-plugin/plugin.json
├── LICENSE.md                              # MIT + CC BY 4.0 attribution
├── README.md
├── agents/docs-anti-slop-reviewer.md
└── skills/{humanize-skills,interrogate,unslop}/
docs/plugins/meta-docs.md
docs/tutorials/meta-docs/{README,deslop-and-humanize-docs,interrogate-docs-and-plans}.md
```

## Deviations from Upstream

1. **Category directory**: The plugin lives at `plugins/meta/meta-docs/` because `boss-skills`
   requires `plugins/<category>/<plugin>/`, and `meta/` is a documented category.
2. **Authorship and install commands**: The manifests, README, and docs point at
   `bossjones/boss-skills` and `meta-docs@boss-skills`. `LICENSE.md` records the port from
   `aif-skills`.
3. **Agent frontmatter**: `docs-anti-slop-reviewer` adds a `capabilities` list, which
   `scripts/verify-structure.py` requires for plugin agents.
4. **Tutorial authoring**: `boss-skills` has no `/docs-tutorial` skill, so the docs only describe
   delegating to the external `documentation-generation:tutorial-engineer` and
   `code-documentation:tutorial-engineer` subagents. The README also explains how the plugin relates
   to the existing `agent-harness` `stop-slop` skill.
5. **Validation**: `boss-skills` has no `validate_cross_runtime.py`, so this PR adds the upstream
   rule from `Adobe-AIFoundations/aif-skills#118` to `scripts/verify-structure.py`:
   - An `agents` manifest entry must be a `.md` file. Directory strings fail.
   - When `.codex-plugin/plugin.json` exists, its `name`, `version`, and `description` must match
     the Claude manifest. It must also pass the same component-path checks.
   - Every local entry in `.agents/plugins/marketplace.json` must resolve to a plugin directory
     that has a `.codex-plugin/plugin.json` with a matching `name`.
6. **Repo-level skill mirrors**: Upstream also commits `.github/skills/` and `.agents/skills/`
   symlinks. `boss-skills` mirrors only into `.claude/` (`scripts/symlink_plugins.py`), and Copilot
   CLI already reads `.claude/skills/`. Adding the other two mirrors would require extending the
   sync script for every plugin, which is out of scope for this PR.
7. **Codespell**: `pyproject.toml` skips the vendored multilingual
   `humanize-skills/references/` snapshot so `make lint` does not rewrite quoted text.

## Validation Commands

```bash
make verify-structure
uv run pytest -q tests/test_verify_structure.py
make symlink-plugins-check
make lint
make test
make markdown-lint
make link-check
make eval-ci
claude plugin validate plugins/meta/meta-docs
```

Install smoke tests run against throwaway config homes so they leave real installs untouched:

```bash
export COPILOT_HOME="$(mktemp -d)" CODEX_HOME="$(mktemp -d)"
copilot plugin marketplace add "$PWD"
copilot plugin install meta-docs@boss-skills   # "Installed 3 skills"
codex plugin marketplace add "$PWD"
codex plugin add meta-docs@boss-skills         # caches all three SKILL.md files
```

## Acceptance Criteria

- `meta-docs` installs from `boss-skills` in Claude Code, Copilot CLI, and Codex.
- Neither manifest declares `"agents": "./agents/"`. `make verify-structure` rejects that form.
- The Claude manifest, Codex manifest, and Claude marketplace entry all report version `0.1.0`.
- Docs, tutorials, and the root README list the plugin, and the link checker passes.
