# Contributing to boss-skills

`boss-skills` is a Claude Code **plugin marketplace**. The most common contribution is adding a new
plugin (a bundle of skills, slash commands, subagents, hooks, or an LSP/MCP integration). This guide
walks the full path from scaffold to a validated, documented, releasable plugin.

For repo setup (uv, Python, `make` targets) see [`development.md`](development.md). For the deeper,
agent-facing rules this guide summarizes, see [`.claude/rules/plugin-structure.md`](.claude/rules/plugin-structure.md)
and [`.claude/rules/skill-development.md`](.claude/rules/skill-development.md).

## 1. Pick a category

Plugins live under `plugins/<category>/<plugin-name>/`. The categories currently on disk are:

| Category | For |
|----------|-----|
| `boss-dev` | Developer-experience tooling and agent harnessing |
| `boss-homelab` | Homelab / infrastructure utilities |
| `social-media` | Social-media content tooling |

You can introduce a new category — the scaffold command will register it for you.

## 2. Scaffold the plugin

### Option A — `/create-plugin` (recommended)

Run the slash command (defined in [`.claude/commands/create-plugin.md`](.claude/commands/create-plugin.md)):

```text
/create-plugin <category>/<plugin-name>
```

`<plugin-name>` must be kebab-case (`^[a-z0-9]+(-[a-z0-9]+)*$`) and unique across the whole
marketplace. The command creates the directory structure, writes `plugin.json` + `README.md` +
placeholder components, registers the plugin in `.claude-plugin/marketplace.json`, and runs the
validator — prompting you for description, keywords, and initial version (default `0.1.0`).

### Option B — copy the template

```bash
cp -r templates/plugin-template/ plugins/<category>/<plugin-name>/
```

Then edit `plugin.json`, `README.md`, and the component dirs by hand, and register it (step 4).

## 3. Add components

A plugin directory can contain any of:

| Component | Location | Invoked as |
|-----------|----------|------------|
| Skill | `skills/<name>/SKILL.md` | Loaded by Claude when relevant, or `/<name>` |
| Command | `commands/<name>.md` | `/<plugin>:<name>` |
| Agent | `agents/<name>.md` | Dispatched via the Agent/Task tool |
| Hook | `hooks/hooks.json` | Lifecycle events |
| LSP / MCP | `.lsp.json` / `.mcp.json` | Editor / tool integrations |

The validator **rejects empty** `commands/`, `agents/`, `skills/`, and `hooks/` dirs — populate them
or delete the ones you don't use. `monitors/`, `scripts/`, and `bin/` are not validated.

Writing a skill? See [`.claude/rules/skill-development.md`](.claude/rules/skill-development.md) and
use concrete trigger patterns. **Critical parser bug (GitHub #12781):** never put `` ` ``-prefixed
bang patterns inside fenced code blocks in `SKILL.md` — use `$ command` notation instead.

## 4. `plugin.json` and marketplace registration

`plugin.json` is validated with `additionalProperties: false`. Allowed fields only: `name`,
`version`, `description`, `author`, `homepage`, `repository`, `license`, `keywords`, and
component-path overrides. Adding anything else (e.g. `category`, `tags`) fails validation.

The matching `.claude-plugin/marketplace.json` entry **must agree** with `plugin.json` on
`description`, `version`, `keywords`, and `author` (mismatches are flagged as conflicts). The
marketplace entry may carry extra fields like `category` and `source`.

External (third-party) plugins are referenced remotely via a `git-subdir` source pinned to a
`ref` + `sha` instead of a local path — see [`github-pr-review`](docs/plugins/github-pr-review.md)
for the pattern.

## 5. Validate

```bash
make verify-structure     # or: ./scripts/verify-structure.py --strict
make lint                 # ruff + basedpyright
make eval                 # plugin-eval static scores for every skill (never fails)
```

`make eval-ci` is the quality gate CI runs (fails if any skill scores below the threshold).

## 6. Version and commit

Plugin updates only reach users when the version is bumped, so **`plugin.json.version` and the
`marketplace.json` entry's `version` must stay in lockstep**. Don't bump by hand — run the
[`version-bump-reviewer`](.claude/skills/version-bump-reviewer/SKILL.md) skill (also auto-triggered
by a hook when you edit a plugin component). It classifies the change (major/minor/patch), bumps both
artifacts, and writes a conventional-commit message a CHANGELOG generator can parse.

## 7. Document it

Bring the docs in sync (this is what makes a plugin discoverable):

- Add a reference page `docs/plugins/<name>.md` (mirror an existing one, e.g.
  [`python-dev.md`](docs/plugins/python-dev.md)).
- Add a row to **both** plugin tables: the root [`README.md`](README.md) and
  [`docs/plugins/README.md`](docs/plugins/README.md).
- Optionally add a hands-on walkthrough under `docs/tutorials/<name>/` (see the
  [tutorials guide](docs/tutorials/README.md)).
- Run `make markdown-lint` and `make link-check` on your docs.

## See also

- [Documentation index](docs/README.md) · [Development setup](development.md) ·
  [Publishing a release](publishing.md)
- Deeper rules: [`.claude/rules/`](.claude/rules/)
