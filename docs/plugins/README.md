# Plugin Documentation

Reference documentation for the Claude Code plugins published by the `boss-skills`
marketplace. Each plugin bundles some combination of **skills**, **slash commands**, and
**subagents** that extend Claude Code.

For repo-level setup and the development workflow, see the [root README](../../README.md).

## What is a plugin?

`boss-skills` is a Claude Code *plugin marketplace* — a Git repository whose
`.claude-plugin/marketplace.json` lists installable plugins. A plugin is a directory under
`plugins/<category>/<name>/` containing a `.claude-plugin/plugin.json` manifest plus one or
more optional component directories:

| Component | Location | Invoked as | Purpose |
|-----------|----------|------------|---------|
| Skill | `skills/<name>/SKILL.md` | Loaded by Claude when relevant, or `/<name>` | Task-specific guidance plus bundled scripts |
| Command | `commands/<name>.md` | `/<plugin>:<name>` | User-typed slash command |
| Agent | `agents/<name>.md` | Dispatched via the `Agent`/`Task` tool | Autonomous subagent with its own context |
| Hook | `hooks/hooks.json` | Lifecycle events | Event-driven automation |
| LSP | `.lsp.json` | File-type editor events | Wire a language server for diagnostics and navigation |

A plugin doesn't have to live in this repo. Entries can also be **external** — referenced remotely
via a `git-subdir` source pinned to a `ref` + `sha` — so the marketplace can offer third-party
plugins without vendoring their code. [`github-pr-review`](github-pr-review.md) is the first such
entry; see its page for how pinning and the install fallback work.

## Installing plugins

Add the marketplace once, then install plugins by name:

```bash
# 1. Register the marketplace (once)
/plugin marketplace add bossjones/boss-skills

# 2. Install the plugins you want
/plugin install agent-harness@boss-skills
/plugin install python-dev@boss-skills
/plugin install twitter-tools@boss-skills
```

Browse and manage installed plugins with the `/plugin` menu. To pull the latest versions
after the marketplace changes:

```bash
/plugin marketplace update boss-skills
```

## Available plugins

| Plugin | Category | Version | Description | Docs |
|--------|----------|---------|-------------|------|
| agent-harness | `boss-dev` | 0.12.1 | Subagents, commands, and skills for agentic dev workflows | [agent-harness.md](agent-harness.md) |
| basedpyright-lsp | `boss-dev` | 0.1.1 | Wire basedpyright into Claude Code for real-time Python diagnostics | [basedpyright-lsp.md](basedpyright-lsp.md) |
| python-dev | `boss-dev` | 0.1.1 | Debug GitHub Actions CI and ship conventional-commit PRs | [python-dev.md](python-dev.md) |
| github-pr-review | `boss-dev` | 1.1.1 | Approval-gated GitHub PR reviews with inline code suggestions (external) | [github-pr-review.md](github-pr-review.md) |
| twitter-tools | `social-media` | 0.1.1 | Download X/Twitter media and convert tweets to Reels | [twitter-tools.md](twitter-tools.md) |
| proxmox-infra | `boss-homelab` | 0.1.1 | Manage Proxmox VE homelab infrastructure and IaC | [proxmox-infra.md](proxmox-infra.md) |

## Source layout

```text
plugins/
├── boss-dev/
│   ├── agent-harness/      # 9 skills, 12 commands, 6 agents, hooks + status lines
│   ├── basedpyright-lsp/   # LSP integration (.lsp.json)
│   └── python-dev/         # 2 commands
├── boss-homelab/
│   └── proxmox-infra/      # 1 skill (proxmox-infrastructure)
└── social-media/
    └── twitter-tools/      # 2 skills

# github-pr-review has no local directory — it's an external git-subdir entry
# (aidankinzett/claude-git-pr-skill, pinned v1.1.1) declared in marketplace.json
```

Every *local* plugin also keeps its own `README.md` next to its `plugin.json`. The pages in this
directory collect that information — components and usage examples — in one place. External plugins
(like [`github-pr-review`](github-pr-review.md)) have no local directory, so their page links to the
upstream source instead.

For hands-on, step-by-step walkthroughs of these plugins, see [`../tutorials/`](../tutorials/README.md).
