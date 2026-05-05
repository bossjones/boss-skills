---
argument-hint: <category>/<plugin-name>
description: Scaffold a new plugin under plugins/<category>/<plugin-name>/, register it in marketplace.json, and validate.
allowed-tools: Read, Write, Edit, Bash, AskUserQuestion
---

# Create Plugin

You are scaffolding a new Claude Code plugin in this repository. The end state: a complete plugin directory under `plugins/<category>/<plugin-name>/` with all standard component dirs initialized, registered in `.claude-plugin/marketplace.json`, and passing `./scripts/verify-structure.py --strict`.

## Input

The argument arrives via `$ARGUMENTS` and must be of the form `<category>/<plugin-name>`, for example: `aif-monitoring/distributed-tracing`.

If `$ARGUMENTS` is empty or missing, stop and tell the user the expected format.

## Step 1: Parse and validate the argument

- Split `$ARGUMENTS` on `/`. Reject unless it produces exactly two non-empty parts (`<category>` and `<plugin-name>`).
- Validate each part against the kebab-case regex `^[a-z0-9]+(-[a-z0-9]+)*$`. Reject otherwise with a message naming the offending part. Examples that should be rejected: `AIF-Monitoring/foo` (uppercase), `foo/bar baz` (space), `foo--bar/baz` (double hyphen), `/foo` (empty category), `foo/` (empty plugin-name).

Bind the parts to `<category>` and `<plugin-name>` and use them throughout the rest of the steps.

## Step 2: Detect collisions

Refuse to overwrite an existing plugin.

- Read `.claude-plugin/marketplace.json` and reject if any entry in `plugins[]` has `name == <plugin-name>` (plugin names must be unique within the marketplace).
- Run `[ -e plugins/<category>/<plugin-name> ] && echo EXISTS || echo NEW`. If it prints `EXISTS`, reject with a clear message and stop.

## Step 3: Detect new vs existing category

Read `.claude/rules/plugin-structure.md` and look for a bullet line containing `` `<category>/` `` under the `## Plugin Categories` section.

- If found: `is_new_category = false`. Skip the category-related question and Step 6.
- If not found: `is_new_category = true`. You'll register the new category in Step 6.

## Step 4: Gather metadata via AskUserQuestion

Use a single `AskUserQuestion` call with these questions. For free-form fields the user picks the "Other" option and types their value.

1. **Description** — "What does this plugin do? (1-2 sentences, will appear in plugin.json and marketplace.json)" — provide options like "Other (write your own)" plus 1-2 generic example descriptions. Effectively this is a free-text field.
2. **Keywords** — "What are 3-8 comma-separated keywords for discovery?" — same pattern, free-text via Other.
3. **Version** — "Initial version?" — options: `0.1.0 (Recommended)`, `0.0.1`, `1.0.0`, plus Other.
4. **(Only if `is_new_category` is true)** — "One-line description of the new category `<category>/`? (will be added to .claude/rules/plugin-structure.md)" — free-text via Other.

Author info is hardcoded from the existing plugins:

```text
name:  Malcolm Jones
email: bossjones@theblacktonystark.com
```

And the homepage is `https://github.com/bossjones/boss-skills`. Do not prompt for these.

## Step 5: Register the new category (only if needed)

If `is_new_category` is true, use the `Edit` tool to insert a new bullet under the `## Plugin Categories` section of `.claude/rules/plugin-structure.md`. Match the existing bullet format exactly:

```text
- `<category>/` - <user-supplied description>
```

Insert after the last existing bullet in that section. Do not change formatting of existing bullets.

## Step 6: Create the directory structure

Single Bash call:

```bash
mkdir -p plugins/<category>/<plugin-name>/{.claude-plugin,commands,agents,skills/example,hooks,scripts,monitors,bin}
```

This creates all 8 directories at once (`.claude-plugin/` plus the 7 component dirs the user requested, with `skills/example/` as the placeholder skill subdir).

## Step 7: Write `plugin.json`

Write `plugins/<category>/<plugin-name>/.claude-plugin/plugin.json` with exactly these fields and no others:

```json
{
  "name": "<plugin-name>",
  "version": "<version>",
  "description": "<description>",
  "author": {
    "name": "Malcolm Jones",
    "email": "bossjones@theblacktonystark.com"
  },
  "keywords": ["<kw1>", "<kw2>", "..."],
  "homepage": "https://github.com/bossjones/boss-skills"
}
```

**Important:** the local validator (`scripts/verify-structure.py`) uses `additionalProperties: false` on the plugin manifest schema. Do NOT add `category`, `tags`, `userConfig`, `dependencies`, `repository`, `license`, or any other field — those will fail validation. The allowed fields are: `name`, `version`, `description`, `author`, `homepage`, `keywords`, plus the component-path overrides (`commands`, `agents`, `hooks`, `mcpServers`) which we don't need here.

## Step 8: Write `README.md`

Write `plugins/<category>/<plugin-name>/README.md`:

```markdown
# <plugin-name>

<description>

## Installation

This plugin is part of the boss-skills marketplace. Enable it via Claude Code's plugin manager.

## Components

- **Commands** — see `commands/`
- **Agents** — see `agents/`
- **Skills** — see `skills/`
- **Hooks** — see `hooks/hooks.json`
- **Monitors** — see `monitors/monitors.json`
- **Scripts** — see `scripts/`
- **Binaries** — see `bin/`

## Status

Initial scaffold. Replace placeholder examples in each component directory with real components, or remove component directories you don't plan to use (the validator rejects empty `commands/`, `agents/`, `skills/`, and `hooks/`).
```

`README.md` is required at the plugin root — `verify-structure.py` flags its absence as an error.

## Step 9: Write placeholder component files

The validator hard-rejects empty `commands/`, `agents/`, `skills/`, and `hooks/` dirs, so each must contain at least one valid file. `monitors/`, `scripts/`, and `bin/` are not validated — `.gitkeep` is fine.

### `commands/example.md`

```markdown
---
description: Example command — replace with a real one
---

# Example Command

Replace this body with your command instructions. Delete this file once you have real commands, or delete the `commands/` directory if this plugin won't have any.
```

### `agents/example.md`

```markdown
---
description: Example agent — replace with a real one
capabilities:
  - Replace with what this agent does
---

# Example Agent

Replace this body with your agent's system prompt. Delete this file once you have real agents, or delete the `agents/` directory if this plugin won't have any.
```

The local validator requires both `description` and `capabilities` for agent frontmatter. Keep both.

### `skills/example/SKILL.md`

```markdown
---
name: example
description: Example skill Use this skill when the user asks to [trigger pattern] (replace with real triggers)
---

# Example Skill

Replace this body with your skill instructions. Delete this directory once you have real skills, or delete the `skills/` directory if this plugin won't have any.
```

### `hooks/hooks.json`

```json
{
  "hooks": {}
}
```

An empty `hooks` object is valid — it skips the validator's event-type check entirely.

### `monitors/monitors.json`

```json
{
  "monitors": []
}
```

### `scripts/.gitkeep`

Empty file (zero bytes).

### `bin/.gitkeep`

Empty file (zero bytes).

## Step 10: Append to `marketplace.json`

Read `.claude-plugin/marketplace.json`, append a new entry to the `plugins` array, and write it back. The new entry MUST use the same field values as `plugin.json` for `description`, `version`, `keywords`, and `author` — otherwise the validator emits "Conflict in '<field>'" warnings (which `--strict` treats as errors).

Entry shape (match the field order shown for consistency with existing entries):

```json
{
  "name": "<plugin-name>",
  "source": "./plugins/<category>/<plugin-name>",
  "description": "<description>",
  "version": "<version>",
  "category": "<category>",
  "keywords": ["<kw1>", "<kw2>", "..."],
  "author": {
    "name": "Malcolm Jones",
    "email": "bossjones@theblacktonystark.com"
  }
}
```

When writing the file back, preserve 2-space indentation and a trailing newline to match the existing style.

## Step 11: Run the validator

```bash
./scripts/verify-structure.py --strict
```

Capture stdout/stderr and the exit code.

- If exit code is `0`: report success and proceed to Step 12.
- If non-zero: print the validator's output and stop. Do NOT attempt to silently auto-fix. Tell the user what failed and offer to investigate. Common issues:
  - **"Conflict in '<field>'"** — `plugin.json` and `marketplace.json` disagree on `description`, `version`, `keywords`, or `author`. Re-check Step 10.
  - **"Missing required field 'capabilities'"** — `agents/example.md` is missing `capabilities`. Re-check Step 9.
  - **"plugin.json: Additional properties are not allowed"** — extra field in `plugin.json`. Re-check Step 7.

## Step 12: Print the final summary

```text
✓ Plugin scaffolded

  Path:        plugins/<category>/<plugin-name>/
  Registered:  .claude-plugin/marketplace.json
  Validation:  ✓ verify-structure.py --strict passed

  Next steps:
  - Replace example.md / SKILL.md placeholders with real components
  - OR delete component dirs you don't plan to use (validator requires non-empty
    commands/, agents/, skills/, hooks/)
  - Bump version in BOTH plugin.json and the marketplace.json entry when ready
    to release (they must stay in sync)
```

## Important Constraints (Reference)

- **Plugin name uniqueness**: enforced across the entire marketplace, not just per category.
- **Allowed `plugin.json` fields**: `name` (required), plus `version`, `description`, `author`, `homepage`, `repository`, `license`, `keywords`, and component-path overrides. Adding any other field fails the validator.
- **Marketplace entry can include extra fields** (`category`, `tags`, `source`, `strict`) — those are NOT allowed in `plugin.json`.
- **Field consistency**: `description`, `version`, `keywords`, `author` must be identical between `plugin.json` and the marketplace entry.
- **Required at plugin root**: `.claude-plugin/plugin.json` and `README.md`.
- **Validator-rejected empty dirs**: `commands/`, `agents/`, `skills/`, `hooks/` — each must contain at least one valid file.
- **Validator-ignored dirs**: `monitors/`, `scripts/`, `bin/` — `.gitkeep` is fine.

## Example Invocation

```text
/create-plugin aif-monitoring/distributed-tracing
```

Produces `plugins/aif-monitoring/distributed-tracing/` with all 8 dirs (`.claude-plugin/` + 7 component dirs), registers it in `marketplace.json`, adds the new `aif-monitoring/` category to `.claude/rules/plugin-structure.md` (since it didn't exist), and runs the validator.
