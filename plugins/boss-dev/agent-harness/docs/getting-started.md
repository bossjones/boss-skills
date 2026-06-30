# Getting Started with Agent Harness

Go from zero to a working `agent-harness` install in about **5 minutes**. This guide covers the
prerequisites, installing the marketplace, installing the plugin, verifying it loaded, and running
your first command.

## Table of Contents

- [The 5-minute path](#the-5-minute-path)
- [Step 1 — Prerequisites](#step-1--prerequisites)
- [Step 2 — Add the marketplace](#step-2--add-the-marketplace)
- [Step 3 — Install the plugin](#step-3--install-the-plugin)
- [Step 4 — Verify it loaded](#step-4--verify-it-loaded)
- [Step 5 — Run your first command](#step-5--run-your-first-command)
- [Running autonomous commands (Plan mode + Opus)](#running-autonomous-commands-plan-mode--opus)
- [Configuring TTS and desktop notifications](#configuring-tts-and-desktop-notifications)
- [Dependency & prerequisite matrix](#dependency--prerequisite-matrix)
- [Troubleshooting](#troubleshooting)
- [Where to go next](#where-to-go-next)

## The 5-minute path

```text
1. Install uv + gh           (one-time, ~2 min)
2. /plugin marketplace add bossjones/boss-skills
3. /plugin install agent-harness@boss-skills
4. /help                     (confirm /agent-harness:* commands appear)
5. /agent-harness:prime      (load project context — your first command)
```

That is the whole happy path. Everything below explains each step and what each feature needs.

## Step 1 — Prerequisites

The plugin's commands, agents, and output styles work the moment it installs. Skills, hooks, and
status lines run small Python scripts via [`uv`](https://docs.astral.sh/uv/), so install `uv` to use
the full feature set. `gh` (the GitHub CLI) is required for the PR- and CI-oriented features.

| Tool | Required for | Install |
| --- | --- | --- |
| [Claude Code](https://claude.ai/code) | Everything | Anthropic CLI / desktop / IDE |
| [`uv`](https://docs.astral.sh/uv/) | Skills, hooks, status lines (any `uv run` script) | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Python 3.13+ | All bundled scripts (PEP 723) | Managed automatically by `uv` |
| `git` 2.5.0+ | Worktree skills | Preinstalled on most systems |
| [`gh`](https://cli.github.com/) (authenticated) | PR-review skills, `fix-gh-pr-comments`, `commit-push-pr`, `debug-ci` | `brew install gh && gh auth login` |

> `uv` resolves each script's dependencies on demand from inline PEP 723 metadata, so there is **no
> `pip install` step** — `aiohttp`, `pydantic`, `jsonschema`, and `python-dotenv` are fetched the
> first time a script that needs them runs.

See the full [dependency & prerequisite matrix](#dependency--prerequisite-matrix) for the optional
API keys and MCP servers that unlock individual features.

## Step 2 — Add the marketplace

In Claude Code, register this repository as a plugin marketplace (one-time):

```text
/plugin marketplace add bossjones/boss-skills
```

The marketplace identifier is **`boss-skills`** (defined in `.claude-plugin/marketplace.json`). You
can also point at a local checkout:

```text
/plugin marketplace add /path/to/boss-skills
```

## Step 3 — Install the plugin

```text
/plugin install agent-harness@boss-skills
```

This auto-discovers and activates the plugin's **commands**, **agents**, **skills**, **output
styles**, and **hooks**. (Hooks ship pre-wired via `hooks/hooks.json` — see
[hooks.md](./hooks.md).) Status lines ship as a library and are opt-in — see
[status-lines.md](./status-lines.md).

## Step 4 — Verify it loaded

Run `/help` and confirm the `/agent-harness:*` commands appear. You should see entries such as
`/agent-harness:prime`, `/agent-harness:plan`, and `/agent-harness:build`.

To list the installed plugin directly:

```text
/plugin
```

## Step 5 — Run your first command

A safe, read-only first command is `prime` — it scans the repo and summarizes the project so a fresh
session has context:

```text
/agent-harness:prime
```

Then try turning a request into a saved plan, and implementing it:

```text
/agent-harness:plan add a rate limiter to the public API
/agent-harness:build specs/add-a-rate-limiter-to-the-public-api.md
```

## Running autonomous commands (Plan mode + Opus)

> [!IMPORTANT]
> **Run the autonomous, code-changing commands with Plan mode and an Opus-level model.**
> Commands like [`fix-gh-pr-comments`](./commands.md#fix-gh-pr-comments),
> [`autobuild`](./commands.md#autobuild), [`debug-ci`](./commands.md#debug-ci), and
> [`plan_w_team`](./commands.md#plan_w_team) edit code and run multi-cycle agentic loops. Launch
> Claude in **plan mode** with a strong model so it proposes a plan first; then on the approval
> prompt choose **"Approve and start in auto mode"** to let it run hands-off.
>
> ```bash
> claude --model 'claude-opus-4-8[1m]' --permission-mode plan
> ```

Why this matters: these commands change files, push commits, and loop until done. Planning first
lets you review the approach before any edits, and **auto mode requires an Opus-level model**
(Opus 4.6+ or Sonnet 4.6 on the Anthropic API), so a weaker model can't run them hands-off anyway.
See the [auto mode docs][auto-mode] for the full requirements.

[auto-mode]: https://code.claude.com/docs/en/permission-modes#eliminate-prompts-with-auto-mode

**Copy-paste variants** — same flow, different models:

```bash
claude --model 'claude-opus-4-8[1m]' --permission-mode plan   # Opus 4.8, 1M context (max capability)
claude --model 'claude-opus-4-8'     --permission-mode plan    # Opus 4.8, standard context
claude --model opus                  --permission-mode plan    # always-latest Opus (alias)
claude --model sonnet                --permission-mode plan    # Sonnet 4.6 — cheaper, still auto-capable
```

`--model` accepts a pinned id like `'claude-opus-4-8[1m]'` or an alias (`opus`, `sonnet`). After the
plan is approved into auto mode, a background classifier reviews each action and still blocks risky
ones (production deploys, force-push, `curl | bash`), so you keep guardrails while skipping routine
prompts.

## Configuring TTS and desktop notifications

Several hooks and the [`work-completion-summary`](./agents.md#work-completion-summary) agent can
speak status updates aloud. The TTS backend is **offline `pyttsx3`** — it needs **no API key**. Two
plugin user-config options control it:

| Option | Type | Default | Effect |
| --- | --- | --- | --- |
| `ENABLE_TTS` | boolean | `true` | Speak completion/notification messages aloud. Set to a falsy value (`0`, `false`, `no`, or `off`) to silence **all** TTS (Stop, SubagentStop, Notification). |
| `ENGINEER_NAME` | string | _(empty)_ | Your name, used in ~30% of spoken messages. Leave blank to stay generic. |

Set them either through `/plugin` → **Configure** (which writes
`CLAUDE_PLUGIN_OPTION_ENABLE_TTS` / `CLAUDE_PLUGIN_OPTION_ENGINEER_NAME`) or as bare environment
variables of the same name. The shared resolver at
[`hooks/utils/config.py`](../hooks/utils/config.py) reads the `CLAUDE_PLUGIN_OPTION_<KEY>` value
first and falls back to the bare env var, so existing `.env` / `.envrc` setups keep working.

The plugin can also fire **clickable desktop notifications** that jump you back to the exact tmux
`session:window` when the agent needs input or finishes (via
[`tmux_notify.py`](../hooks/tmux_notify.py)). These are off by default and gated behind three more
user-config options:

| Option | Type | Default | Effect |
| --- | --- | --- | --- |
| `tmux_notifications` | boolean | `false` | Master switch for tmux desktop notifications. Requires `tmux` and `terminal-notifier` (macOS) or `notify-send` (Linux). |
| `tmux_notify_activate_bundle_id` | string | `com.mitchellh.ghostty` | macOS bundle id of your terminal so the notification raises it on click (e.g. `com.googlecode.iterm2`, `dev.warp.Warp`, `com.apple.Terminal`). Blank skips activation. |
| `tmux_notify_sound` | boolean | `false` | Play the default notification sound. Off keeps notifications silent. |

## Dependency & prerequisite matrix

Most features work with just `uv` + `gh`. This table maps each feature group to exactly what it
needs so you only install what you'll use.

| Feature | Needs | Notes |
| --- | --- | --- |
| Commands `prime`, `question`, `all_tools`, `sentient` | Nothing beyond Claude Code | Read-only / demo |
| Commands `plan`, `build`, `plan_w_team` | Claude Code (uv for `plan_w_team` validators) | `plan_w_team` runs Stop-hook validators via `uv` |
| Commands `commit-push-pr`, `fix-gh-pr-comments`, `debug-ci`, `autobuild` | `gh` (authenticated), `git` | Run `gh auth login` first |
| Command `validate-unicode-hygiene` | `uv` | Runs the repo-root unicode validator |
| Skills — worktree suite (`git-worktree*`, `worktree-doctor`) | `git` 2.5.0+ | No network needed |
| Skills — `fetch-diff`, `fetch-unresolved-comments`, `pr-review`, `add-review-comment` | `uv`, `gh` (or `GH_TOKEN`) | PEP 723 deps auto-resolved |
| Skill — `release-notes-generator` | `git`, `gh` | Reads commits + PR metadata |
| Skills — `stop-slop`, `unicode-hygiene` | Nothing (uv for the unicode scanner) | Prose hygiene / supply-chain scan |
| Hooks — logging / guards / auto-format | `uv`; `ruff` on `PATH` or `uvx` (format hook only) | Active on install via `hooks/hooks.json`; format hook runs only in projects with a ruff config |
| Hooks — LLM agent naming / summaries | `ANTHROPIC_API_KEY` **or** `OPENAI_API_KEY` (or local Ollama) | Optional; degrades gracefully if unset |
| Hooks / agents — TTS announcements | offline `pyttsx3` (no key), or `OPENAI_API_KEY`, or ElevenLabs | Optional; toggle with `ENABLE_TTS` via `/plugin` → Configure |
| Hooks — tmux desktop notifications | `tmux` + `terminal-notifier` (macOS) / `notify-send` (Linux) | Off by default; enable `tmux_notifications` |
| Agent — `work-completion-summary` | ElevenLabs MCP server; `ENGINEER_NAME` plugin user-config (optional) | Configure MCP separately; set name via `/plugin` → Configure |
| Agents — `meta-agent`, `llm-ai-agents-and-eng-research` | Firecrawl MCP server | Configure MCP separately |
| Status lines | `uv`, `python-dotenv` (auto), `statusLine` setting | Opt-in; not auto-wired |

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `/agent-harness:*` commands don't appear | Re-run `/plugin install agent-harness@boss-skills`; check `/plugin` shows it enabled. |
| A skill or hook errors with "uv: command not found" | Install `uv` (see Step 1) and restart Claude Code. |
| PR/CI commands fail immediately | Run `gh auth login`; commands hard-stop if `gh auth status` fails. |
| Python auto-format hook does nothing | By design it only runs when the project has a ruff config (`ruff.toml`, `.ruff.toml`, or `[tool.ruff]` in `pyproject.toml`) and `ruff`/`uvx` is available. Add a ruff config to opt in. |
| TTS still speaks after you wanted silence | Set `ENABLE_TTS` to `0`/`false`/`no`/`off` (via `/plugin` → Configure or env var). |
| LLM agent-naming / TTS silent | Optional — set `ANTHROPIC_API_KEY`/`OPENAI_API_KEY`, or rely on the offline `pyttsx3` backend. |

## Where to go next

| Doc | What's inside |
| --- | --- |
| [commands.md](./commands.md) | All 13 slash commands with args, when-to-use, and examples |
| [agents.md](./agents.md) | The 6 subagents and how the builder/validator team works |
| [skills.md](./skills.md) | The 12 model- and explicitly-invoked skills |
| [hooks.md](./hooks.md) | The 14 lifecycle hook events and how to enable/disable them |
| [output-styles.md](./output-styles.md) | The 8 response output styles |
| [status-lines.md](./status-lines.md) | The 10 status-line variants and how to wire one up |
| [workflows.md](./workflows.md) | End-to-end recipes that chain the pieces together |

</content>
</invoke>
