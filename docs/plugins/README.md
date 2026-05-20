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
| agent-harness | `boss-dev` | 0.2.0 | Subagents, commands, and skills for agentic dev workflows | [agent-harness.md](agent-harness.md) |
| python-dev | `boss-dev` | 0.1.0 | Debug GitHub Actions CI and ship conventional-commit PRs | [python-dev.md](python-dev.md) |
| twitter-tools | `social-media` | 0.1.0 | Download X/Twitter media and convert tweets to Reels | [twitter-tools.md](twitter-tools.md) |
| proxmox-infra | `boss-homelab` | 0.1.0 | Manage Proxmox VE homelab infrastructure and IaC | [proxmox-infra.md](proxmox-infra.md) |

> **Note:** `proxmox-infra` lives under `plugins/boss-homelab/proxmox/` but is not yet
> registered in `.claude-plugin/marketplace.json`. Until it is, the `@boss-skills` install
> shorthand will not resolve it — see [proxmox-infra.md](proxmox-infra.md) for the local
> install path.

## Source layout

```text
plugins/
├── boss-dev/
│   ├── agent-harness/   # 9 skills, 9 commands, 6 agents
│   └── python-dev/      # 2 commands
├── boss-homelab/
│   └── proxmox/         # 1 skill (proxmox-infra)
└── social-media/
    └── twitter-tools/   # 2 skills
```

Every plugin also keeps its own `README.md` next to its `plugin.json`. The pages in this
directory collect that information — components and usage examples — in one place.
