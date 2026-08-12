# Hooks Reference

The plugin enables **20 lifecycle events** on install through
[`hooks/hooks.json`](../hooks/hooks.json). Every enabled event includes the universal logger and
may also run a separate behavior hook. Hooks are PEP 723 scripts run through `uv`; the
[`uv-guard.sh`](../hooks/uv-guard.sh) wrapper silently skips a hook when `uv` is unavailable.

## Table of Contents

- [Execution model](#execution-model)
- [Enabled events](#enabled-events)
- [Intentionally deferred events](#intentionally-deferred-events)
- [Storage and path resolution](#storage-and-path-resolution)
- [JSONL records and redaction](#jsonl-records-and-redaction)
- [Retention](#retention)
- [Configuration](#configuration)
- [Legacy artifacts and diagnosis](#legacy-artifacts-and-diagnosis)

## Execution model

Each enabled event invokes `log_event.py --event-type <Event>` through `uv-guard.sh`. The logger
reads the event payload from stdin, appends one JSONL record, and exits `0` even if parsing, disk
I/O, or retention fails. It is intentionally fail-open: observability must never block Claude.

Behavior hooks run independently of that logger. The `PreToolUse` guard can still reject dangerous
commands; other behavior hooks such as TTS, notifications, Snyk scanning, and Python formatting
retain their own documented behavior. Do not add per-hook audit writers: `log_event.py` is the
single event logger.

## Enabled events

Every row captures the full hook stdin payload after redaction and has a fail-open logger exit code
of `0`. The final column identifies the additional behavior hook, if any.

| Event | Audit record | Additional behavior |
| --- | --- | --- |
| `SessionStart` | `SessionStart.jsonl` | Project context / TTS and optional advisory Snyk scan |
| `SessionEnd` | `SessionEnd.jsonl`; starts retention | Session cleanup |
| `Setup` | `Setup.jsonl` | Dependency and project checks for setup runs |
| `UserPromptSubmit` | `UserPromptSubmit.jsonl` | Stores prompt/session state; optional LLM agent naming |
| `PreToolUse` | `PreToolUse.jsonl` | Dangerous-command and `.env` guard |
| `PermissionRequest` | `PermissionRequest.jsonl` | Permission-request handling |
| `PostToolUse` | `PostToolUse.jsonl` | Post-tool behavior plus ruff formatting for edited Python |
| `PostToolUseFailure` | `PostToolUseFailure.jsonl` | Tool-failure handling |
| `SubagentStart` | `SubagentStart.jsonl` | Optional TTS announcement |
| `SubagentStop` | `SubagentStop.jsonl` | Completion summary and optional TTS |
| `Stop` | `Stop.jsonl` | Transcript/TTS and tmux completion notification |
| `StopFailure` | `StopFailure.jsonl` | tmux failure notification |
| `PreCompact` | `PreCompact.jsonl` | Optional transcript backup |
| `Notification` | `Notification.jsonl` | TTS and filtered tmux notifications |
| `PostCompact` | `PostCompact.jsonl` | Log only |
| `UserPromptExpansion` | `UserPromptExpansion.jsonl` | Log only |
| `PermissionDenied` | `PermissionDenied.jsonl` | Log only |
| `PostToolBatch` | `PostToolBatch.jsonl` | Log only |
| `TaskCreated` | `TaskCreated.jsonl` | Log only |
| `TaskCompleted` | `TaskCompleted.jsonl` | Log only |

The behavior hooks can have their own effect or exit behavior; the `PreToolUse` safety guard is the
intentional blocking example. The universal logger itself never changes a Claude decision.

## Intentionally deferred events

`MessageDisplay` is **not enabled**. It is intentionally deferred pending a measured
`log_event.py` cold-start p95 against its 10-second event budget. It fires for every assistant
message, so enabling it without that measurement would add the highest-volume logging path.

These nine events are also deliberately deferred. They are documented here so a future change can
revisit a reasoned decision rather than treating their absence as an omission.

| Event | Rationale |
| --- | --- |
| `FileChanged`, `CwdChanged` | High-frequency and low signal for the baseline audit trail. |
| `InstructionsLoaded`, `ConfigChange` | Configuration-churn noise; reconsider only when debugging skill loading. |
| `Elicitation`, `ElicitationResult` | MCP-specific; there is no current consumer. |
| `WorktreeCreate`, `WorktreeRemove` | Worktree skills already maintain `.worktree-logs/`; duplicating that working mechanism adds noise. |
| `TeammateIdle` | Specific to agent teams and not exercised by this repository. |

## Storage and path resolution

Runtime artifacts are grouped under one project-local root:

```text
<project>/.{plugin-repo}/
├── logs/<session_id>/<Event>.jsonl
├── data/sessions/<session_id>.json
└── cache/
```

The default root is named for the marketplace repository that ships this plugin, lowercased and
slugged — not for the project being worked in. A plugin installed from the `boss-skills`
marketplace writes `.boss-skills/` in **every** project and worktree it runs in, which gives one
name to ignore, inspect, and document. The root resolution order is:

1. `CLAUDE_HARNESS_DIR`
2. Plugin option `HARNESS_DIR` (`CLAUDE_PLUGIN_OPTION_HARNESS_DIR`, then bare `HARNESS_DIR`)
3. The derived `.{plugin-repo}` root
4. `.agent-harness` only when no marketplace manifest is found above the plugin

The namespace is resolved from the plugin's own location on disk: the nearest ancestor directory
holding `.claude-plugin/marketplace.json`. That works identically for a development checkout and an
installed copy under `~/.claude/plugins/marketplaces/`, and needs no environment variable — status
lines and standalone skill scripts do not reliably receive `CLAUDE_PLUGIN_ROOT`.

Resolution walks a handful of ancestors and is cached per process, so it is safe on the
status-line hot path: measured at **0.087 ms** for the first resolve, **0.048 ms** per uncached
walk, and ~30 ns once cached (macOS, local SSD). Status lines re-run on every assistant message,
so if that walk ever becomes expensive, set `HARNESS_DIR` to skip it entirely.

Relative configured roots are resolved against the project directory. The legacy
`CLAUDE_HOOKS_LOG_DIR` override changes **only** the `logs/` subtree; `data/` and `cache/` remain
under the resolved harness root. Status lines use the project directory in their stdin workspace
payload so changing directories during a session does not move their session-state lookup.

## JSONL records and redaction

The logger creates one append-only file per event and session. Each line is one JSON object and is
written under a file lock so concurrent hooks do not interleave records.

```json
{
  "schema_version": 1,
  "timestamp": 1783554999498,
  "ts_iso": "2026-07-26T17:51:39.498Z",
  "source_app": "agent-harness",
  "hook_event_type": "PostToolUse",
  "session_id": "722628f2-53da-4eca-bb73-6e2cd615354d",
  "tool_name": "Bash",
  "payload": { "…": "redacted hook stdin" }
}
```

`timestamp` is Unix milliseconds and `ts_iso` is UTC. In addition to the payload, recognized fields
such as `session_id`, `cwd`, `permission_mode`, `tool_name`, `tool_use_id`, error details, task
details, command name, and agent ID are promoted when present. `schema_version: 1` makes future
record-layout changes explicit.

Before writing, the logger recursively replaces values with `[REDACTED]` for sensitive key names
(`AUTHORIZATION`, `PASSWORD`, `SECRET`, `TOKEN`, and names ending in `_TOKEN`, `_KEY`, `_SECRET`,
or `_PASSWORD`) and token-shaped values including `sk-`, GitHub token, Slack token, and masked-token
prefixes. Redaction is best-effort protection, not permission to put secrets in prompts or commands.

## Retention

At `SessionEnd`, the logger prunes runtime output with defaults of **7 days** and **100 MB**:

- session `logs/` directories and regenerable `cache/` entries older than the configured age are
  removed;
- if remaining logs and cache exceed the combined cap, the oldest entries are removed first;
- live `data/sessions/<id>.json` is not pruned by age while its corresponding log directory exists;
  it is removed only after that log directory is absent.

## Configuration

Configure these in `/plugin` → **Configure** or by environment variable. Plugin options resolve as
`CLAUDE_PLUGIN_OPTION_<KEY>` first, then a bare `<KEY>` environment variable.

| Option | Type | Default | Effect |
| --- | --- | --- | --- |
| `HARNESS_DIR` | string | _(empty)_ | Optional project-relative or absolute root. Empty uses `.{plugin-repo}`. |
| `HOOKS_LOG_RETENTION_DAYS` | number | `7` | Maximum age for log directories and cache entries. |
| `HOOKS_LOG_RETENTION_MAX_MB` | number | `100` | Combined log/cache cap; oldest entries are evicted first. |
| `ENABLE_TTS` | boolean | `true` | Enable spoken notifications and completion announcements. |
| `ENGINEER_NAME` | string | _(empty)_ | Optional name used in some spoken messages. |
| `tmux_notifications` | boolean | `false` | Enable tmux-aware desktop notifications. |
| `ENABLE_SNYK_AGENT_SCAN` | boolean | `false` | Enable advisory SessionStart scanning of `SKILL.md` files. |

See the [getting-started guide](./getting-started.md) for TTS and tmux prerequisites.

## Legacy artifacts and diagnosis

There is **no automatic migration** from the former cwd-relative `logs/` and `.claude/data/`
locations. They may belong to an older install, and moving them automatically could mix projects or
sessions. The read-only `harness-doctor` skill reports these as stale artifacts, alongside the
resolved root and storage sizes; review its report before deleting old files.

```text
uv run "${CLAUDE_SKILL_DIR}/scripts/harness_doctor.py" --repo-root /path/to/project
```
