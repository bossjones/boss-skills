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
- [Configuring agent personalization and residual storage](#configuring-agent-personalization-and-residual-storage)
- [Dependency & prerequisite matrix](#dependency--prerequisite-matrix)
- [Second brain (obsidian-wiki) environment](#second-brain-obsidian-wiki-environment)
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

The plugin's commands, agents, and output styles work the moment it installs. Skills and
the status line run small Python scripts via [`uv`](https://docs.astral.sh/uv/), so install `uv` to use
the full feature set. `gh` (the GitHub CLI) is required for the PR- and CI-oriented features.

| Tool | Required for | Install |
| --- | --- | --- |
| [Claude Code](https://claude.ai/code) | Everything | Anthropic CLI / desktop / IDE |
| [`uv`](https://docs.astral.sh/uv/) | Skills and the status line (any `uv run` script) | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
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

This auto-discovers and activates the plugin's **commands**, **agents**, **skills**, and **output
styles**. The status line is opt-in — see [status-lines.md](./status-lines.md).

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

## Configuring agent personalization and residual storage

Run `/plugin` → select **agent-harness** → **Configure** to set `ENGINEER_NAME` (used by
[`work-completion-summary`](./agents.md#work-completion-summary)) and `ENABLE_STATUS_LINE`.

`agent-harness` no longer ships lifecycle hooks or writes runtime logs. Residual `.boss-skills/`
directories, repo-root `logs/`, and `.claude/data/` artifacts from earlier versions are not
migrated or deleted automatically—run the read-only `harness-doctor` skill to inspect them.

## Dependency & prerequisite matrix

Most features work with just `uv` + `gh`. This table maps each feature group to exactly what it
needs so you only install what you'll use.

| Feature | Needs | Notes |
| --- | --- | --- |
| Commands `prime`, `question`, `all_tools` | Nothing beyond Claude Code | Read-only / demo |
| Commands `plan`, `build`, `plan_w_team` | Claude Code | Planning and implementation workflows |
| Commands `commit-push-pr`, `fix-gh-pr-comments`, `debug-ci`, `autobuild` | `gh` (authenticated), `git` | Run `gh auth login` first |
| Command `validate-unicode-hygiene` | `uv` | Runs the repo-root unicode validator |
| Skills — worktree suite (`git-worktree*`, `worktree-doctor`) | `git` 2.5.0+ | No network needed |
| Skills — `fetch-diff`, `fetch-unresolved-comments`, `pr-review`, `add-review-comment` | `uv`, `gh` (or `GH_TOKEN`) | PEP 723 deps auto-resolved |
| Skill — `release-notes-generator` | `git`, `gh` | Reads commits + PR metadata |
| Skills — `stop-slop`, `unicode-hygiene` | Nothing (uv for the unicode scanner) | Prose hygiene / supply-chain scan |
| Skills — `setup-agent-harness`, `setup-second-brain`, `harness-doctor` | `uv` (stdlib-only scripts); `node` ≥ 22 + `npm` for the optional QMD step | `setup-second-brain` installs obsidian-wiki; QMD degrades to Grep without Node — see [Second brain environment](#second-brain-obsidian-wiki-environment) |
| Agent — `work-completion-summary` | ElevenLabs MCP server; `ENGINEER_NAME` plugin user-config (optional) | Configure MCP separately; set name via `/plugin` → Configure |
| Agents — `meta-agent`, `llm-ai-agents-and-eng-research` | Firecrawl MCP server | Configure MCP separately |
| Status line | `uv`, `python-dotenv` (auto), `statusLine` setting | Opt-in; not auto-wired |

## Second brain (obsidian-wiki) environment

The [`setup-second-brain`](./skills.md#setup-second-brain) skill installs
[`obsidian-wiki`](https://github.com/ar9av/obsidian-wiki) as a global uv tool
(`uv tool install "obsidian-wiki[graph,ast]"`); the vault path is persisted in
`~/.obsidian-wiki/config` when you run `obsidian-wiki setup`. See the "Second Brain
(obsidian-wiki)" section in the repo-root [`CLAUDE.md`](../../../../CLAUDE.md) for full setup steps.

| Variable | Description | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `OBSIDIAN_VAULT_PATH` | Path to the Obsidian vault used as the knowledge base | Optional | `~/Documents/obsidian/personal.vault` | Documented default only; the real path lives in `~/.obsidian-wiki/config`. `~` is not auto-expanded — call `expanduser` if read in code |
| `OBSIDIAN_RAW_DIR` | Staging directory for unprocessed captures | Optional | `_raw` | Relative to the vault root |

### QMD semantic search (optional)

[`@tobilu/qmd`](https://github.com/tobi/qmd) is an optional on-device search engine that upgrades
`wiki-query`/`wiki-ingest` from Grep to semantic matching. Requires **Node ≥ 22**
(`npm install -g @tobilu/qmd`). The wiki skills read these from `~/.obsidian-wiki/config` and fall
back to Grep silently when they are unset. The `setup-second-brain` skill writes them.

| Variable | Description | Required | Default | Accepted values |
| --- | --- | --- | --- | --- |
| `QMD_TRANSPORT` | How the wiki skills call QMD | Optional | `cli` | `cli`, `mcp` (`mcp` adds a `qmd` server to `~/.claude/settings.json`) |
| `QMD_WIKI_COLLECTION` | QMD collection queried by `wiki-query` | Optional | _(unset → Grep)_ | Any collection name, e.g. `wiki` |
| `QMD_PAPERS_COLLECTION` | QMD collection of source docs queried by `wiki-ingest` | Optional | _(unset → Grep)_ | Any collection name, e.g. `papers` |
| `QMD_CLI_SEARCH_MODE` | CLI search quality/speed tradeoff | Optional | `quality` | `quality` (rerank), `balanced` (no rerank), `fast` (vector-only) |
| `QMD_CLI` | Override the `qmd` binary name/path | Optional | `qmd` | Any executable |

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `/agent-harness:*` commands don't appear | Re-run `/plugin install agent-harness@boss-skills`; check `/plugin` shows it enabled. |
| A skill errors with "uv: command not found" | Install `uv` (see Step 1) and restart Claude Code. |
| PR/CI commands fail immediately | Run `gh auth login`; commands hard-stop if `gh auth status` fails. |
| Completion-summary agent is silent | Configure its ElevenLabs MCP server. |

## Where to go next

| Doc | What's inside |
| --- | --- |
| [commands.md](./commands.md) | All 16 slash commands with args, when-to-use, and examples |
| [agents.md](./agents.md) | The 6 subagents and how the builder/validator team works |
| [skills.md](./skills.md) | The 21 model- and explicitly-invoked skills |
| [output-styles.md](./output-styles.md) | The 7 response output styles |
| [status-lines.md](./status-lines.md) | The v10 status line and how to wire it up |
| [workflows.md](./workflows.md) | End-to-end recipes that chain the pieces together |
