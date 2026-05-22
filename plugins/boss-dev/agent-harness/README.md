# agent-harness

Agent harness tooling for Claude Code: subagents, commands, hooks, skills, and scripts that build
and operate agentic dev workflows.

## Installation

```bash
/plugin install agent-harness@boss-skills
```

## Components

### Skills

Nine skills under `skills/<skill-name>/SKILL.md`.

**PR review workflow** (adapted from the [mlflow](https://github.com/mlflow/mlflow)
skills, Apache-2.0):

- **fetch-diff** — fetch a GitHub PR diff with old/new line numbers and
  auto-generated-file masking, optionally filtered to file globs.
- **fetch-unresolved-comments** — fetch only the unresolved PR review threads
  via the GitHub GraphQL API, grouped by file.
- **pr-review** — review a PR and emit a schema-validated local review payload
  (inline comments plus an approve-or-comment decision).
- **add-review-comment** — post a single inline review comment to a PR line or
  line range via the GitHub API.

**Git worktree lifecycle** (adapted from
[claude-code-ultimate-guide](https://github.com/FlorianBruniaux/claude-code-ultimate-guide),
MIT):

- **git-worktree** — create an isolated worktree for feature development with
  branch naming, dependency symlinking, and background verification.
- **git-worktree-status** — report background type-check, test, and build
  status for a worktree.
- **git-worktree-remove** — safely remove one worktree with branch cleanup and
  safety checks.
- **git-worktree-clean** — batch-clean stale and merged worktrees with a disk
  usage report.

**Release notes** (adapted from claude-code-ultimate-guide, MIT):

- **release-notes-generator** — generate release notes in three formats
  (CHANGELOG, PR body, Slack) from git commits.

The `fetch-diff`, `fetch-unresolved-comments`, and `pr-review` skills carry
standalone PEP 723 scripts under `scripts/`, invoked with
`uv run "${CLAUDE_SKILL_DIR}/scripts/<script>.py"` — `uv` resolves their
dependencies on demand, so the skills work after `/plugin install` with no
extra setup.

### Commands

Nine slash commands under `commands/*.md`, auto-discovered on `/plugin install`
and namespaced as `/agent-harness:<name>`.

| Command | Arguments | Purpose |
| --- | --- | --- |
| `build` | `[path-to-plan]` | Read a plan file and implement it. |
| `plan` | `[user prompt]` | Produce a concise engineering plan and save it to the specs directory. |
| `plan_w_team` | `[user prompt] [orchestration prompt]` | Produce a team-orchestrated plan with task dependencies and builder/validator assignments (model: opus). |
| `prime` | — | Load context for a new session by scanning the codebase, README, and docs. |
| `question` | `[question]` | Answer questions about project structure and docs without writing code. |
| `cook` | — | Fan out a fixed batch of seven parallel sub-agent tasks to exercise parallel execution. |
| `update_status_line` | `<session_id> <key> <value>` | Upsert a key/value pair into a session's status-line data file. |
| `all_tools` | — | List every available tool as TypeScript-style signatures with purposes. |
| `sentient` | — | Demo command that triggers the `rm -rf` guard in `pre_tool_use.py`. |

### Agents

Six subagent definitions under `agents/`, auto-discovered on `/plugin install`
and namespaced as `agent-harness:<name>`.

| Agent | Model | Purpose |
| --- | --- | --- |
| `meta-agent` | opus | Generate a complete sub-agent configuration file from a description. |
| `llm-ai-agents-and-eng-research` | default | Research the latest LLM, AI-agent, and engineering developments. |
| `work-completion-summary` | default | Announce concise audio (TTS) summaries when work finishes. |
| `hello-world-agent` | default | Minimal greeting agent — a template/reference example. |
| `team/builder` | opus | Execute a single engineering task: write code, create files, implement features. |
| `team/validator` | opus | Read-only check that a task met its acceptance criteria. |

`team/builder` and `team/validator` back the `/agent-harness:plan_w_team`
orchestration workflow. `meta-agent`, `llm-ai-agents-and-eng-research`, and
`work-completion-summary` reference external MCP tools (firecrawl, ElevenLabs)
that must be configured separately. Note that Claude Code ignores
`hooks`/`mcpServers` frontmatter on plugin-shipped agents for security, so
`team/builder`'s inline lint and type-check hooks take effect only when that
agent file is used outside the plugin.

### Hooks

`hooks/` ships a **library** of lifecycle hook scripts (PEP 723, run via `uv`).
They are **not active on install** — Claude Code only registers plugin hooks
declared in `hooks/hooks.json` (or an inline `hooks` key in `plugin.json`), and
neither exists yet. To enable a hook, add an entry that points at the script
with `${CLAUDE_PLUGIN_ROOT}`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|Write|Edit",
        "hooks": [
          { "type": "command", "command": "\"${CLAUDE_PLUGIN_ROOT}\"/hooks/pre_tool_use.py" }
        ]
      }
    ]
  }
}
```

Lifecycle hook scripts:

| Script | Event | Purpose |
| --- | --- | --- |
| `session_start.py` | SessionStart | Log start; optionally inject git/project context or announce via TTS. |
| `setup.py` | Setup | Check dependencies, detect project type, install packages for CI/`--init` runs. |
| `user_prompt_submit.py` | UserPromptSubmit | Log prompts, manage session metadata, optionally name the agent via an LLM. |
| `pre_tool_use.py` | PreToolUse | Block dangerous `rm -rf` and `.env` access; log tool calls. |
| `permission_request.py` | PermissionRequest | Auto-allow read-only operations; log permission requests. |
| `post_tool_use.py` | PostToolUse | Log successful tool executions. |
| `post_tool_use_failure.py` | PostToolUseFailure | Log tool failures with error detail. |
| `notification.py` | Notification | Log notifications; optionally announce via TTS. |
| `subagent_start.py` | SubagentStart | Log subagent spawns; optional TTS announcement. |
| `subagent_stop.py` | SubagentStop | Log subagent completion; summarize and announce via TTS. |
| `pre_compact.py` | PreCompact | Log compaction; optionally back up the transcript. |
| `stop.py` | Stop | Log session stop; optional transcript export and TTS completion message. |
| `session_end.py` | SessionEnd | Log session end; optionally clean up stale temp files. |

Supporting modules:

- `hooks/validators/` — PostToolUse and Stop validators: `ruff_validator.py` and
  `ty_validator.py` lint and type-check Python after writes; `validate_new_file.py`
  and `validate_file_contains.py` assert a file was created or contains expected
  content.
- `hooks/utils/llm/` — pluggable LLM backends (`oai.py`, `anth.py`, `ollama.py`)
  and `task_summarizer.py` for generating completion messages.
- `hooks/utils/tts/` — text-to-speech backends (`pyttsx3_tts.py`, `openai_tts.py`,
  `elevenlabs_tts.py`) and `tts_queue.py`, a file-lock queue that serializes
  overlapping announcements.

Hook runs write structured JSON to `logs/` for auditing and debugging.

### Output Styles

Eight output styles under `output-styles/*.md`, auto-discovered on
`/plugin install` and selectable with `/output-style`.

| Style | Description |
| --- | --- |
| `markdown-focused` | Full markdown toolbox — headers, tables, blockquotes, task lists. |
| `bullet-points` | Hierarchical bullet lists, broad to specific. |
| `table-based` | Markdown tables for comparisons, steps, and analysis. |
| `ultra-concise` | Minimal words, fragments over sentences, code-first. |
| `yaml-structured` | Machine-readable YAML with hierarchical key/value blocks. |
| `html-structured` | Semantic HTML5 with data attributes for programmatic use. |
| `genui` | Generative UI — writes a styled, self-contained HTML page to `/tmp/` and opens it. |
| `tts-summary` | Announces task completion as audio (experimental). |

### Status Lines

`status_lines/` ships nine status-line scripts (PEP 723, `python-dotenv`) —
progressively richer takes on the Claude Code status line. They are a library,
not auto-wired: point your `statusLine` setting at one to use it.

| Script | Shows |
| --- | --- |
| `status_line.py` | Model, directory, git branch, version. |
| `status_line_v2.py` | Adds the last user prompt. |
| `status_line_v3.py` | Adds agent name and the last three prompts (fading). |
| `status_line_v4.py` | Adds custom key/value pairs (see `update_status_line`). |
| `status_line_v5.py` | Session cost, lines added/removed, duration. |
| `status_line_v6.py` | Context-window usage bar and tokens remaining. |
| `status_line_v7.py` | Elapsed session time and start time. |
| `status_line_v8.py` | Input/output token counts and cache stats. |
| `status_line_v9.py` | Minimal powerline layout (model, branch, path, context %). |

## Status

Plugin version **v0.2.0**. Skills, commands, agents, and output styles are
auto-discovered and active on `/plugin install`. The hook scripts and status
lines ship as a library and require manual wiring — a `hooks/hooks.json` entry
for hooks, a `statusLine` setting for status lines — before they take effect.
