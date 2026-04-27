# Plan: Scaffold `boss-dev/agent-harness` Claude Plugin

## Task Description

Create the directory and file scaffolding for a new Claude Code plugin at `plugins/boss-dev/agent-harness/` inside `/Users/malcolm/dev/bossjones/boss-skills`. The user will fill in components (subagents, commands, hooks, skills, scripts, tools) themselves; this scaffolding turn ships only what passes `make verify-structure` on day one.

Component subdirectories (`agents/`, `commands/`, `skills/`, `hooks/`, `scripts/`, `tools/`) are **deferred** because the local validator (`scripts/verify-structure.py`) treats empty component dirs as hard errors (lines 506–510, 542–546, 570–574). They will be created later, each alongside its first real component.

The plugin is also registered in the repo's marketplace catalog, and the new `boss-dev/` category is added to the canonical category list in the plugin-structure rules.

## Objective

When this plan is complete:

- `plugins/boss-dev/agent-harness/` exists with a valid `plugin.json` and `README.md`.
- The plugin is registered in `.claude-plugin/marketplace.json` with metadata that exactly matches `plugin.json`.
- `.claude/rules/plugin-structure.md` lists `boss-dev/` as a canonical category.
- `make verify-structure` and `make verify-structure-strict` both exit 0.

## Problem Statement

The user wants a place to develop a cohesive set of agent-harness tooling for Claude Code (subagents, commands, hooks, skills, scripts, tools) and prefers to organize it as a single, distributable plugin under a `boss-dev/` category. None of this exists yet, and there is no `boss-dev` category in the repo's canonical rule list. Without scaffolding, every additional component would risk manifest drift or local-validator failures.

## Solution Approach

Mirror the **lean** layout used by `plugins/social-media/twitter-tools/`: ship only `.claude-plugin/plugin.json` and `README.md` on day one. Defer every component subdirectory until its first real entry exists. This avoids the local validator's "empty component dir is a hard error" rule and sidesteps the need for placeholder components that would become technical debt.

Register the plugin in `.claude-plugin/marketplace.json` with metadata verbatim-matching `plugin.json` so `verify-structure-strict` passes. Add `boss-dev/` to the canonical category list in `.claude/rules/plugin-structure.md` so future contributors see it as sanctioned.

User decisions captured (from clarifying questions):

1. Scaffolding shape: **Lean — manifest + README only.**
2. Category: **`plugins/boss-dev/agent-harness/` and update the rules file.**
3. Author email: **`bossjones@theblacktonystark.com`** (matches twitter-tools).

## Relevant Files

Files to read for reference (do not modify):

- `plugins/social-media/twitter-tools/.claude-plugin/plugin.json` — exact local convention for plugin manifest field set.
- `plugins/social-media/twitter-tools/README.md` — README style and section ordering to mirror.
- `scripts/verify-structure.py` — the local validator. Notable: `PLUGIN_MANIFEST_SCHEMA` at line 266 (`additionalProperties: false`); empty-dir checks at lines 506, 542, 570; marketplace/plugin field-conflict check at lines 802–847.
- `Makefile` — `verify-structure` (line 165), `verify-structure-strict` (line 170), `test-plugins` (line 127, takes `PLUGIN_DIR=...`).

Files modified:

- `.claude-plugin/marketplace.json` — appended new plugin entry to the `plugins` array.
- `.claude/rules/plugin-structure.md` — added `boss-dev/` to the **Plugin Categories** list.

### New Files

- `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json` — plugin manifest (only required + optional metadata; no empty component overrides).
- `plugins/boss-dev/agent-harness/README.md` — user-facing doc matching twitter-tools style with placeholders for the components the user will add later.
- `specs/scaffold-boss-dev-agent-harness-plugin.md` — this spec.

## Step by Step Tasks

IMPORTANT: Execute every step in order, top to bottom.

### 1. Create the plugin directory structure

- `mkdir -p plugins/boss-dev/agent-harness/.claude-plugin`
- Do NOT create `agents/`, `commands/`, `skills/`, `hooks/`, `scripts/`, or `tools/` subdirectories. They will be added later, each alongside its first real component.

### 2. Write `plugin.json`

- Path: `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json`
- Content:

```json
{
  "name": "agent-harness",
  "version": "0.1.0",
  "description": "Agent harness tooling for Claude Code: subagents, commands, hooks, skills, and scripts that build and operate agentic dev workflows.",
  "author": {
    "name": "Malcolm Jones",
    "email": "bossjones@theblacktonystark.com"
  },
  "keywords": [
    "agent",
    "harness",
    "subagent",
    "claude-code",
    "boss-dev",
    "dev-tools",
    "automation"
  ],
  "homepage": "https://github.com/bossjones/boss-skills"
}
```

- Field choices: kebab-case bare plugin name (no `boss-dev-` prefix — twitter-tools convention). No `category`, `tags`, `userConfig`, or `dependencies` (rejected by `additionalProperties: false`). No `repository`/`license` (twitter-tools omits both).

### 3. Write `README.md`

- Path: `plugins/boss-dev/agent-harness/README.md`
- Match twitter-tools section structure: H1 plugin name, brief description, install snippet, component sections marked `_Coming soon._` since none ship on day one, status note.

### 4. Register in `marketplace.json`

- Path: `.claude-plugin/marketplace.json`
- Append a new object to the `plugins` array (after the existing `twitter-tools` entry). The marketplace entry's `description`, `version`, and `keywords` MUST match `plugin.json` byte-for-byte to satisfy the strict-mode conflict check (`scripts/verify-structure.py` lines 802–847).

```json
{
  "name": "agent-harness",
  "source": "./plugins/boss-dev/agent-harness",
  "description": "Agent harness tooling for Claude Code: subagents, commands, hooks, skills, and scripts that build and operate agentic dev workflows.",
  "version": "0.1.0",
  "category": "boss-dev",
  "keywords": [
    "agent",
    "harness",
    "subagent",
    "claude-code",
    "boss-dev",
    "dev-tools",
    "automation"
  ],
  "author": {
    "name": "Malcolm Jones",
    "email": "bossjones@theblacktonystark.com"
  }
}
```

### 5. Update the canonical category list

- Path: `.claude/rules/plugin-structure.md`
- Append a new bullet under `## Plugin Categories`:

```markdown
- `boss-dev/` - Personal developer-experience tools and agent harnessing
```

- Do not reorder or rename existing categories.

### 6. Validate

- `make verify-structure` — must exit 0 with `agent-harness` listed.
- `make verify-structure-strict` — must exit 0 (no warnings).
- `python -m json.tool plugins/boss-dev/agent-harness/.claude-plugin/plugin.json > /dev/null`
- `python -m json.tool .claude-plugin/marketplace.json > /dev/null`
- `make test-plugins PLUGIN_DIR=./plugins/boss-dev/agent-harness` if `claude` CLI is on PATH.

## Testing Strategy

There is no runtime code to unit-test in this scaffold — validation IS the test. Four checks cover the relevant edge cases:

- **Manifest schema** — `make verify-structure` runs the JSON-Schema validator against `plugin.json`; catches typos in field names, version string format violations, and any field added that isn't in the allowed set.
- **Marketplace consistency** — `make verify-structure-strict` runs the field-conflict check between `plugin.json` and the marketplace entry; catches drift in `description`, `version`, `keywords`.
- **Component placement** — the validator's `check_component_placement` function rejects any component subdir (`commands/`, `agents/`, `skills/`, `hooks/`) accidentally placed inside `.claude-plugin/`. With the lean layout there are no such dirs at all, so this check is automatically clean.
- **Smoke load** — `make test-plugins` confirms Claude Code can parse and attach the plugin without crashing on launch.

If a future contributor adds an empty `agents/`, `commands/`, or `skills/` directory by hand, `make verify-structure` will catch it as a hard error on next run — no silent regression.

## Acceptance Criteria

- [ ] `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json` exists with the exact field set specified in Step 2 and passes JSON-Schema validation.
- [ ] `plugins/boss-dev/agent-harness/README.md` exists with the section structure specified in Step 3.
- [ ] No `agents/`, `commands/`, `skills/`, `hooks/`, `scripts/`, or `tools/` subdirectories exist in the new plugin (lean layout preserved).
- [ ] `.claude-plugin/marketplace.json` contains a new entry with `name: "agent-harness"`, `source: "./plugins/boss-dev/agent-harness"`, `category: "boss-dev"`, and metadata matching `plugin.json`.
- [ ] `.claude/rules/plugin-structure.md` lists `boss-dev/` in the **Plugin Categories** section.
- [ ] `make verify-structure` exits 0.
- [ ] `make verify-structure-strict` exits 0.
- [ ] No commit is created unless the user explicitly requests one.

## Validation Commands

Run from repo root:

- `make verify-structure` — validates plugin manifest, marketplace entry, and component placement. Must exit 0.
- `make verify-structure-strict` — same as above with warnings treated as errors; catches plugin/marketplace field drift. Must exit 0.
- `python -m json.tool plugins/boss-dev/agent-harness/.claude-plugin/plugin.json > /dev/null` — confirms manifest is valid JSON.
- `python -m json.tool .claude-plugin/marketplace.json > /dev/null` — confirms marketplace catalog is valid JSON.
- `make test-plugins PLUGIN_DIR=./plugins/boss-dev/agent-harness` — smoke-loads the plugin in Claude Code (skip if `claude` CLI is not on PATH).
- `git status` and `git diff --stat plugins/boss-dev/agent-harness .claude-plugin/marketplace.json .claude/rules/plugin-structure.md specs/` — sanity-check the change set before any commit.

## Notes

- **No new dependencies.** All scaffolding is markdown and JSON; no `uv add`.
- **Do not copy `templates/plugin-template/` wholesale** — it ships with hook scripts referencing `${CLAUDE_PLUGIN_ROOT}/scripts/example-hook.sh` that don't exist in the new plugin and would fail validation (`scripts/verify-structure.py` lines 668–676).
- **Do not add `userConfig` or `dependencies` to `plugin.json`** even though the official spec lists them — the local validator's `additionalProperties: false` rejects both. If a real `userConfig`/`dependencies` need arises later, that's a separate change to `scripts/verify-structure.py` and out of scope here.
- **Do not bump or tag a version.** Stay at `0.1.0` in both files; bump only when the first real component lands.
- **Do not push, open a PR, or commit** unless explicitly requested. Scaffolding only.
- **Future component additions** (per `.claude/rules/skill-development.md` and the validator):
  - Each agent file in `agents/*.md` requires `description` AND `capabilities` in frontmatter.
  - Each skill needs a `SKILL.md` with `name` + `description` frontmatter, no backtick-bang patterns inside fenced code blocks (parser bug #12781), and concrete trigger patterns.
  - `hooks/hooks.json` must have a top-level `"hooks"` key; command-type hook scripts referenced via `${CLAUDE_PLUGIN_ROOT}/...` must exist on disk and be executable.
- **CLAUDE.md project standards** apply to any Python that lands in `scripts/` later: PEP 723 inline metadata, Python 3.11–3.13, full type annotations, `from __future__ import annotations`, `pathlib.Path`, absolute imports, ruff format (100 char), basedpyright. Out of scope for this scaffolding turn.
