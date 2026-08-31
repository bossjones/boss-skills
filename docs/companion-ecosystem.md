# Companion marketplaces & plugins

What surrounds this repo on a working machine: the marketplaces registered alongside the
`boss-skills` marketplace, the third-party plugins its workflows lean on, and where the live state
actually lives so this page can be re-verified instead of trusted.

Snapshot taken **2026-08-31** from `~/.claude/plugins/known_marketplaces.json` and
`~/.claude/plugins/installed_plugins.json` (note: the latter nests entries under a top-level
`plugins` key). Versions drift by design — auto-update moves official-marketplace plugins on
release — so treat version columns as "at snapshot time" and re-derive with the commands at the
bottom.

## This repo's own catalog

`boss-skills` is itself a marketplace (`.claude-plugin/marketplace.json`) shipping:
`agent-harness`, `basedpyright-lsp`, `github-pr-review`, `python-dev`, `twitter-tools`,
`proxmox-infra`, `boss-experimental`. Per-plugin reference pages live in
[plugins/](plugins/README.md); the [root README](../README.md) carries the catalog and install
commands.

## Plugins this repo pins for itself

The project `.claude/settings.json` `enabledPlugins` roster is the authoritative "works with this
repo" list — these load for anyone who trusts a clone:

| Plugin | Marketplace | Why it's pinned |
|--------|-------------|-----------------|
| `agent-harness@boss-skills` | boss-skills | This repo's own harness: hooks (event logging, version-bump + skill-edit review), commands (`/plan`, `/build`, `/fix-gh-pr-comments`, …), core skills |
| `superpowers@claude-plugins-official` | official | Process discipline: brainstorming, TDD, systematic debugging, verification-before-completion |
| `code-review@claude-plugins-official` | official | PR review command (`code-review:code-review`) |
| `skill-creator@claude-plugins-official` | official | Skill authoring + description optimization loops |
| `claude-code-setup@claude-plugins-official` | official | Automation recommender |
| `frontend-design@claude-plugins-official` | official | UI design guidance for prototypes |
| `context7@claude-plugins-official` | official | Live library docs (MCP) |
| `code-simplifier@claude-plugins-official` | official | Post-hoc simplification agent |
| `playwright@claude-plugins-official` | official | Browser automation for skill testing |
| `claude-md-management@claude-plugins-official` | official | CLAUDE.md audits (`claude-md-improver`) |
| `code-documentation@claude-code-workflows` | wshobson/agents | Docs-from-code agents |
| `documentation-generation@claude-code-workflows` | wshobson/agents | Doc generators incl. `/doc-generate`, mermaid |
| `c4-architecture@claude-code-workflows` | wshobson/agents | C4 architecture documentation agents |
| `documentation-standards@claude-code-workflows` | wshobson/agents | HADS token-lean doc format |
| `obsidian@obsidian-skills` | kepano/obsidian-skills | Obsidian markdown/canvas/bases conventions for the second-brain workflow |

Two cautions carried over from `wshobson/agents`: its `plugin-eval` is the engine behind
`make eval-ci` / [`eval-skills.md`](eval-skills.md) (consumed vendored at `scripts/plugin_eval/`,
not as a plugin), and this repo's eval work patched its judge — see `PLUGIN_EVAL_SOURCE` in
`.env.sample` before assuming upstream behavior.

## User-scope complements (not pinned, relied on)

Installed at user scope on this machine and referenced by this repo's docs or workflows:

| Plugin | Marketplace / source | Role |
|--------|----------------------|------|
| `mattpocock-skills@claude-plugins-official` | official | The 25 engineering/productivity skills this repo used to vendor — **see [external-skills.md](external-skills.md)**; never re-vendor into `.claude/skills/` |
| `claude-mem@thedotmack` | thedotmack/claude-mem | Cross-session memory, `/learn-codebase`, timeline |
| `superpowers@superpowers-marketplace` | obra/superpowers-marketplace | Duplicate install of superpowers (same version as the official one; either may serve) |
| `superpowers-developing-for-claude-code@superpowers-marketplace` | obra | Plugin/skill authoring guidance |
| `plugin-dev@claude-plugins-official` + `plugin-dev@lunar-claude` | official / basher83 | Plugin scaffolding + the `skill-reviewer` agent this repo's edit-review hook dispatches — **the hook depends on plugin-dev being installed** |
| `engineering-skills@claude-code-skills` | alirezarezvani | Adversarial-reviewer and role personas |
| `python-master@claude-plugin-marketplace`, `python-development@claude-code-workflows` | JosiahSiegel / wshobson | Python depth (asyncio, typing, packaging) |
| `llm-application-dev@claude-code-workflows` | wshobson | RAG/agent/prompt patterns |
| `example-skills@anthropic-agent-skills` | anthropics/skills | Anthropic's reference skills (docx/pptx/pdf/xlsx, mcp-builder, artifacts) |
| `telegram@claude-plugins-official`, `frontend-slides`, `langsmith-tracing`, `agent-sdk-dev` | various | Channel, slides, tracing, SDK-app scaffolding |

Project-scope extras seen in other checkouts (`bash-master`, `docker-master`,
`git-workflow`/`hookify`/`meta-claude`/`python-tools@lunar-claude`,
`observability-monitoring@claude-code-workflows`) are per-project choices, not requirements of
this repo.

## Registered marketplaces (Claude Code, user level)

| Marketplace | Source | Provides |
|-------------|--------|----------|
| `claude-plugins-official` | anthropics/claude-plugins-official | Auto-registered; auto-updates; most pinned plugins above + `mattpocock-skills` |
| `boss-skills` | bossjones/boss-skills | This repo |
| `claude-code-workflows` | wshobson/agents | Docs/architecture/python/LLM plugin suites + plugin-eval upstream |
| `superpowers-marketplace` | obra/superpowers-marketplace | superpowers + authoring companion |
| `lunar-claude` | basher83/lunar-claude | plugin-dev, git-workflow, hookify, meta-claude |
| `claude-plugin-marketplace` | JosiahSiegel/claude-plugin-marketplace | bash/docker/python "master" packs |
| `claude-code-skills` | alirezarezvani/claude-skills | engineering-skills personas |
| `anthropic-agent-skills` | anthropics/skills | example-skills |
| `obsidian-skills` | kepano/obsidian-skills | obsidian plugin |
| `thedotmack` | thedotmack/claude-mem | claude-mem |
| `langsmith-claude-code-plugins` | langchain-ai | langsmith-tracing |
| `frontend-slides` | zarazhangrui/frontend-slides | frontend-slides |
| `ecc` | affaan-m/ECC | (registered, nothing installed at snapshot) |

## Copilot CLI side

Copilot bundles `copilot-plugins` and `awesome-copilot` as marketplaces but everything relevant
here was installed **direct** (`~/.copilot/config.json` `installedPlugins`): `superpowers`,
`skill-creator`, `code-review`, `frontend-design`, `context7`, `code-simplifier`,
`claude-md-management`, the four wshobson doc plugins, and `mattpocock-skills`
(direct installs are deprecated per Copilot's own warning — migration path in
[external-skills.md](external-skills.md)). Non-plugin skills also reach Copilot via
`~/.copilot/skills/` and `~/.agents/skills/` symlinks (obsidian-wiki, cmux).

## Re-deriving this page

```bash
claude plugin marketplace list
```

```bash
claude plugin list
```

```bash
python3 -c "import json;from pathlib import Path;d=json.loads((Path.home()/'.claude/plugins/installed_plugins.json').read_text());[print(k) for k in sorted(d['plugins'])]"
```

```bash
copilot plugin list
```
