# Agents Reference

Six subagent definitions under `agents/`, auto-discovered on `/plugin install` and namespaced as
`agent-harness:<name>`. Subagents are specialized assistants the primary agent delegates to — some
are triggered proactively, others are deployed by the `plan_w_team` workflow.

## Table of Contents

- [At a glance](#at-a-glance)
- [General-purpose agents](#general-purpose-agents)
  - [`meta-agent`](#meta-agent)
  - [`llm-ai-agents-and-eng-research`](#llm-ai-agents-and-eng-research)
  - [`work-completion-summary`](#work-completion-summary)
  - [`hello-world-agent`](#hello-world-agent)
- [The team (used by `plan_w_team`)](#the-team-used-by-plan_w_team)
  - [`team/builder`](#teambuilder)
  - [`team/validator`](#teamvalidator)
- [Important caveat: plugin-shipped agent hooks](#important-caveat-plugin-shipped-agent-hooks)

## At a glance

| Agent | Model | Triggers | When to use | External deps |
| --- | --- | --- | --- | --- |
| [`meta-agent`](#meta-agent) | opus | "create a new sub-agent" | Generate a complete agent config file | Firecrawl MCP |
| [`llm-ai-agents-and-eng-research`](#llm-ai-agents-and-eng-research) | default | AI/LLM news requests | Gather latest LLM/agent/eng developments | Firecrawl MCP, web |
| [`work-completion-summary`](#work-completion-summary) | default | "tts" / work finished | Spoken summary when a task completes | ElevenLabs MCP |
| [`hello-world-agent`](#hello-world-agent) | default | "hi claude" | Reference/template example | WebSearch |
| [`team/builder`](#teambuilder) | opus | deployed by `plan_w_team` | Execute ONE engineering task | — |
| [`team/validator`](#teamvalidator) | opus | deployed by `plan_w_team` | Read-only check of ONE task | — |

---

## General-purpose agents

### `meta-agent`

> Generate a new, complete Claude Code sub-agent configuration file from a description.

- **Model:** opus · **Tools:** `Write`, `WebFetch`, `firecrawl_scrape`, `firecrawl_search`,
  `MultiEdit` · **Color:** cyan
- **When to use:** Proactively when you ask to create a new sub-agent — "make me an agent that…".
- **What it does:** Acts as an expert agent architect. Scrapes the current Claude Code sub-agent and
  tools documentation, analyzes your prompt, devises a `kebab-case` name and color, infers the
  minimal tool set, writes a focused system prompt, and emits a ready-to-use agent markdown file.
- **External deps:** Firecrawl MCP server (for docs scraping) must be configured separately.
- **Source:** [`agents/meta-agent.md`](../agents/meta-agent.md)

### `llm-ai-agents-and-eng-research`

> AI research specialist that gathers the latest LLM, AI-agent, and engineering developments.

- **Model:** default · **Tools:** `Bash`, `firecrawl_search`, `firecrawl_scrape`, `WebFetch`
- **When to use:** Staying current with AI/ML — finding recent news, tools, and actionable insights.
- **What it does:** Establishes the current date (via `date`), discards anything older than one
  week, searches recent developments across major LLM labs, and synthesizes findings into organized
  categories (major developments, models, agents, engineering, tools, takeaways).
- **External deps:** Firecrawl MCP + web access.
- **Source:** [`agents/llm-ai-agents-and-eng-research.md`](../agents/llm-ai-agents-and-eng-research.md)

### `work-completion-summary`

> Announce a concise spoken (TTS) summary when work finishes, and suggest next steps.

- **Model:** default · **Tools:** `Bash`, `ElevenLabs text_to_speech`, `ElevenLabs play_audio` ·
  **Color:** green
- **When to use:** When a task completes and you want a 1–2 sentence audio recap; also on "tts",
  "tts summary", or "audio summary".
- **What it does:** Converts the result you describe into a very short spoken message, synthesizes
  audio, and plays it. It has **no prior conversation context**, so the prompting agent must tell it
  exactly what to say. Addresses the user by the `ENGINEER_NAME` plugin user-config value (or
  `ENGINEER_NAME` env var as fallback).
- **External deps:** ElevenLabs MCP server configured separately.
- **Source:** [`agents/work-completion-summary.md`](../agents/work-completion-summary.md)

### `hello-world-agent`

> Minimal greeting agent — a template/reference example.

- **Tools:** `WebSearch` · **Color:** green
- **When to use:** As a starting template for your own agents, or proactively on "hi claude" / "hi
  cc".
- **What it does:** Greets the user, asks how it can help, and shares a random tech-news tidbit. Its
  value is as the simplest possible agent definition to copy.
- **Source:** [`agents/hello-world-agent.md`](../agents/hello-world-agent.md)

---

## The team (used by `plan_w_team`)

These two back the [`/agent-harness:plan_w_team`](./commands.md#plan_w_team) orchestration workflow.
The planning command acts as team lead and deploys them as `agent-harness:team:builder` and
`agent-harness:team:validator` against tasks in the shared task list. See
[workflows.md](./workflows.md#team-orchestration-plan_w_team) for the full loop.

### `team/builder`

> Generic engineering agent that executes ONE task at a time.

- **Model:** opus · **Color:** cyan
- **When to use:** When work needs doing — writing code, creating files, implementing a feature —
  scoped to a single task.
- **What it does:** Reads its assigned task via `TaskGet`, does the work (write/modify code, run
  commands), and marks the task `completed` via `TaskUpdate`. It executes only — it does not plan,
  coordinate, or spawn other agents, and it works around blockers rather than stopping.
- **Source:** [`agents/team/builder.md`](../agents/team/builder.md)

### `team/validator`

> Read-only validation agent that checks whether a task met its acceptance criteria.

- **Model:** opus · **Color:** yellow · **Disallowed tools:** `Write`, `Edit`, `NotebookEdit`
- **When to use:** After a builder finishes, to independently verify the work — it cannot modify
  anything.
- **What it does:** Reads the task and acceptance criteria via `TaskGet`, inspects files, runs
  read-only validation (tests, type checks, lint), and reports pass/fail with findings via
  `TaskUpdate`.
- **Source:** [`agents/team/validator.md`](../agents/team/validator.md)

---

## Important caveat: plugin-shipped agent hooks

`team/builder` declares inline `PostToolUse` hooks (ruff + `ty` validators), and some agents declare
`mcpServers`/`hooks` frontmatter. **Claude Code ignores `hooks` and `mcpServers` frontmatter on
plugin-shipped agents for security.** So:

- `team/builder`'s inline lint/type-check hooks take effect only when that file is used **outside**
  the plugin (e.g. copied into a project's `.claude/agents/`). Inside the plugin, rely on the
  plugin-level [hooks](./hooks.md) instead.
- MCP-dependent agents (`meta-agent`, `llm-ai-agents-and-eng-research`, `work-completion-summary`)
  need their MCP servers (Firecrawl, ElevenLabs) configured in your own settings — the agent
  frontmatter alone won't register them.
</content>
