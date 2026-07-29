# Plan: Hooks Improved — session-scoped JSONL logging, universal logger, expanded event coverage

> **How to execute this spec:** `/agent-harness:build specs/hooks-improved.md`
>
> Work the **Step by Step Tasks** in order, committing at each numbered step. Start with step 1
> — it re-derives the authoritative hook-event list from live docs, and every later step depends
> on its output rather than on the tables in this document. See
> **Assume Nothing — Verify These First** for why.
>
> Supersedes [`specs/hooks-update-with-team.md`](hooks-update-with-team.md), which codified the
> flat `logs/<event>.json` scheme this spec replaces.

---

## Context

Why this change is happening.

The `agent-harness` plugin ships 15 lifecycle hook scripts wired to 14 events via
[`hooks/hooks.json`](../plugins/boss-dev/agent-harness/hooks/hooks.json). Event coverage is good —
better than the reference implementation we're borrowing from. The *logging mechanics* are not.

Concrete, measured problems in this repo today:

| Problem | Evidence |
| --- | --- |
| Logs land in whatever directory Claude happened to be launched from | `Path.cwd() / "logs"` in `post_tool_use.py:17`, bare `Path("logs")` in `session_start.py:27`, `os.path.join(os.getcwd(), "logs")` in `stop.py:169` — **three different idioms, none using `$CLAUDE_PROJECT_DIR`** |
| Whole-file JSON array rewrite on every single event → O(n²) | `post_tool_use.py:22-36` reads the entire array, appends one item, re-serializes. `logs/` is **4.9 MB**; `logs/post_tool_use.json` grew **1.7 MB → 2.2 MB during a single planning session**. (Those bytes were written by the globally-enabled `agent-harness@aif-skills` v0.5.0, which carries byte-identical logic — see the testing-implication note below) |
| `session_id` is captured then thrown away | `subagent_stop.py:215` — `_ = input_data.get("session_id", "")`. All sessions interleave into one flat file |
| Two hooks race on the same file | `stop.py:207` and `subagent_stop.py:257` both write `logs/chat.json`. [Hooks run in **parallel**](https://code.claude.com/docs/en/hooks-guide), so this is a genuine race, not just last-writer-wins |
| No shared path helper | 15 hooks + 4 status lines + `utils/llm/task_summarizer.py:38` each construct their own path |
| Logs written *inside the installed plugin* | `snyk_agent_scan.py:59` → `<plugin>/logs/snyk-scan-cache/`; `validators/*.py` → `<plugin>/hooks/validators/*.log` |
| **Runtime state has the same bug, in a second location** | `user_prompt_submit.py:58` — `Path(".claude/data/sessions")`, cwd-relative. 25 stale session JSONs plus `tts_queue/tts.lock` currently sit in `.claude/`, a directory Claude Code owns. Nothing prunes them |
| No retention, no redaction, no bound | Full Bash commands and file contents land verbatim, forever |

The reference implementation at
`/Users/malcolm/dev/adobe-ai-factory-summit/pinata/.claude/hooks` solves the mechanics with one
`log_event.py` doing **append-only JSONL** into
`$CLAUDE_PROJECT_DIR/<log-dir>/{session_id}/{Event}.jsonl`, plus a 4-line `uv-guard.sh` so hooks
silently no-op when `uv` is absent.

**Correction to the premise that motivated this work:** pinata's `.pinata/logs` is only the
*hardcoded fallback*. Its `.claude/settings.json:4` sets `CLAUDE_HOOKS_LOG_DIR=.logs`, so the real
runtime path is `.logs/{session_id}/`. The default is duplicated in both `log_event.py:89` and
`utils/constants.py:16` — a drift hazard this port must not reproduce.

**Intended outcome:** one writer, one path helper, one place to change; **every** plugin-generated
artifact — logs, runtime state, and caches — under a single repo-named dot-directory; per-session
append-only JSONL; expanded event coverage; and enough tests that the old pattern cannot silently
return.

---

## Objective

When this plan is complete:

1. Every hook event is logged by exactly **one** script — `hooks/log_event.py` — as append-only
   JSONL at `$CLAUDE_PROJECT_DIR/.{repo-slug}/logs/{session_id}/{HookEventName}.jsonl`.
2. Path resolution lives in exactly **one** module with a documented precedence chain, and it
   resolves **all three** artifact classes: `logs/`, `data/`, `cache/`.
3. **Nothing** the plugin generates is written outside that root — not to `logs/`, not to
   `.claude/data/`, not into the installed plugin directory.
4. The 15 behavior hooks contain **zero** path construction of their own.
5. Seven additional hook events are registered; nine more are documented as deliberately deferred.
6. Retention, secret redaction, and lock-guarded appends are in place.
7. A `harness-doctor` skill and `make doctor` report environment readiness, absorbing three
   duplicated `check_env()` implementations.
8. Nothing under the new root is ever committed.
9. Docs, tests, and the plugin version are all consistent with the above.

---

## Problem Statement

Hook logs are unusable as an observability surface and actively harmful as a performance
characteristic:

- **Unusable:** you cannot answer "what did session X do?" because all sessions share one file.
  You cannot `tail -f` because the writer rewrites the whole file. You cannot find the logs
  reliably because their location depends on the shell's cwd at launch.
- **Harmful:** every `PostToolUse` event deserializes and re-serializes a 2.2 MB JSON array. This
  cost is paid on *every tool call*, grows monotonically, and is never reclaimed.
- **Unsafe:** unbounded plaintext capture of every Bash command and file payload, with no
  retention and no redaction.
- **Unmaintainable:** 20+ independent copies of the path logic guarantee drift. It has already
  drifted three ways.

---

## Solution Approach

Port pinata's architecture, fix its known gaps, and keep our superior event coverage.

**Adopt from pinata:**

- One universal `log_event.py` registered per event.
- Append-only JSONL, one file per event type, per session.
- `$CLAUDE_PROJECT_DIR`-anchored paths with an env override.
- `uv-guard.sh` runtime wrapper.
- Always `exit 0`; disk errors must never block Claude.
- An end-to-end test suite that pipes real payloads through every registered hook.

**Fix pinata's gaps (it has none of these):**

- Single source of truth for the default path — no duplicated constant.
- Retention/pruning.
- Secret redaction.
- Lock-guarded appends for concurrent subagents sharing a `session_id`.
- Per-session `chat.json` separation so Stop and SubagentStop cannot race.

**Keep from agent-harness:**

- All 14 currently-wired events.
- The `CLAUDE_PLUGIN_OPTION_<KEY>` config resolver in
  [`hooks/utils/config.py`](../plugins/boss-dev/agent-harness/hooks/utils/config.py).
- PEP 723 + `shutil.which` house conventions per
  [`.claude/rules/python-scripts.md`](../.claude/rules/python-scripts.md).

### The path resolution contract

`hooks/utils/harness_paths.py` resolves **one root**, then derives every artifact path from it.
This is deliberately not a logs-only helper — logs, runtime state, and caches all share the root
so there is exactly one directory to gitignore, inspect, and delete.

```
resolve_harness_root():
  1. $CLAUDE_HARNESS_DIR                    → used verbatim, relative to project dir
  2. CLAUDE_PLUGIN_OPTION_HARNESS_DIR       → via utils/config.py resolver
  3. derived: .{slug(basename($CLAUDE_PROJECT_DIR))}
  4. fallback: .agent-harness               → when project dir is unresolvable

Derived from the root:
  logs_root()   → <root>/logs
  data_dir()    → <root>/data
  cache_dir()   → <root>/cache
  session_log_dir(sid) → <root>/logs/<sid>
```

**Back-compat override.** `$CLAUDE_HOOKS_LOG_DIR` (pinata's variable) stays supported and, when
set, overrides **only** the logs subtree — `data/` and `cache/` still come from the root. Document
this narrow scope; it is the one place the two variables can disagree, and a reader who assumes it
moves everything will be wrong.

Resulting in:

```
boss-skills  →  .boss-skills/logs/<session_id>/PostToolUse.jsonl
                .boss-skills/data/sessions/<session_id>.json
pinata       →  .pinata/logs/<session_id>/PostToolUse.jsonl
```

`slug()` must lowercase, replace any non-`[a-z0-9]` run with a single `-`, strip leading/trailing
`-` and `.`, and fall back to `agent-harness` if the result is empty. This matters: a repo named
`My Repo (v2)` must not produce a broken path, and a repo already named `.foo` must not produce
`..foo`.

`$CLAUDE_PROJECT_DIR` is resolved as `os.environ.get("CLAUDE_PROJECT_DIR")` falling back to
`os.getcwd()`. Per the [hooks reference](https://code.claude.com/docs/en/hooks), a hook's cwd is
set to the `cwd` field from its stdin payload and is **not** guaranteed to be the project root —
never rely on it.

#### Status lines resolve the project dir differently — by design

`resolve_harness_root()` must accept an **optional explicit `project_dir` argument** that, when
supplied, wins over every env branch. Hooks omit it; status lines always pass it. Reason: a status
line is a separate process, and the
[statusLine docs](https://code.claude.com/docs/en/statusline) document only `COLUMNS` and `LINES`
as environment variables Claude Code sets for it — **`CLAUDE_PROJECT_DIR` is not documented as
available there.** What *is* guaranteed is the stdin payload:

```json
{
  "cwd": "/current/working/directory",
  "session_id": "abc123...",
  "workspace": {
    "current_dir": "/current/working/directory",
    "project_dir": "/original/project/directory",
    "added_dirs": []
  }
}
```

The docs define `workspace.project_dir` as *"Directory where Claude Code was launched, which may
differ from `cwd` if the working directory changes during a session."* That last clause is the
whole point: **after any `cd`, `os.getcwd()` is actively wrong**, and today's status lines use a
bare relative `Path(f".claude/data/sessions/{session_id}.json")`, so they already read the wrong
directory in that case. Read `workspace.project_dir` from stdin and pass it in. Do not add an env
var the docs don't promise.

Note `cwd` and `workspace.current_dir` are documented as carrying the same value, with
`current_dir` preferred. Neither is the project root — use `project_dir`.

#### How the status line script itself is referenced

Separate question from *where it reads state*: **which copy of the script runs.** Three options,
and the right one differs by repo.

##### The two-repo workflow (context, not a defect)

`boss-skills` is the public personal testbed; `aif-skills` is the Adobe-internal downstream that
receives selectively migrated items. They are *expected* to be out of sync. Which copy is
installed globally differs by machine: on the author's personal machine **boss-skills** is the
global install; on this (work) machine it is **aif-skills**.

Measured here:

```
globally enabled:  agent-harness@aif-skills          → v0.5.0
this repo:         plugins/boss-dev/agent-harness    → v0.28.0
boss-skills marketplace installed here:               NO
```

Plus **six** `agent-harness` directories under `~/.claude/plugins/`, four in transient
`marketplaces/temp_<timestamp>/` dirs.

##### ⚠️ Testing implication — read this before trying to verify anything

**On a machine where boss-skills is not the global install, editing
`plugins/boss-dev/agent-harness/hooks/*.py` does not change which hooks fire.** Claude Code loads
plugin hooks from the *enabled* plugin — here `agent-harness@aif-skills` v0.5.0, which carries the
identical `Path.cwd() / "logs"` bug. The 4.9 MB `logs/` directory in this repo was written by that
v0.5.0 copy, not by the local checkout. (`.claude/hooks/hooks.json` is a symlink kept for
symmetry; Claude Code does not auto-load hooks from `.claude/hooks/`, only from a plugin's own
`hooks/hooks.json` and from `settings.json`.)

Before the live verification section, the build agent **must** establish which copy is live and
say so:

```bash
grep -n 'agent-harness' ~/.claude/settings.json          # which one is enabled
ls -d ~/.claude/plugins/marketplaces/*/                   # what is installed
```

If the local checkout is not the enabled plugin, either install/enable it locally, or run the
verification on a machine where boss-skills *is* the global install. Otherwise every live check in
this spec silently tests v0.5.0 and passes for the wrong reason — which is worse than not running
them.

##### Backport portability — a hard constraint

Because this code migrates boss-skills → aif-skills as a copy, **no plugin file may contain the
literal string `boss-skills`.** The dot-dir is *derived at runtime* from
`basename($CLAUDE_PROJECT_DIR)`, so the same bytes produce `.boss-skills/` in one repo,
`.aif-skills/` in another, and `.pinata/` in a consumer repo. Add a test asserting
`grep -rn 'boss-skills' plugins/boss-dev/agent-harness/ --include='*.py'` returns **zero** hits
outside tests and docs. That single constraint is what keeps the backport a clean `cp`.

Corollary for rollout: this change lands in boss-skills first, so anything still on the aif-skills
lineage keeps writing `.claude/data/` and flat `logs/` until it is backported. That is the normal
staged rollout, not a bug — but it is why the old `.gitignore` entries stay and why nothing
auto-migrates.

| Option | Use where | Why |
| --- | --- | --- |
| **Symlink + `$CLAUDE_PROJECT_DIR/.claude/status_lines/...`** | **boss-skills itself** | Already exists and works. `.claude/status_lines/` and `.claude/hooks/` are symlink farms with **relative, intra-repo** targets (`../../plugins/boss-dev/agent-harness/...`), so they always run the code you are editing. `.claude/settings.example.json:81` already uses this form |
| **`${CLAUDE_PLUGIN_ROOT}/status_lines/...`** | **consumer repos** | What `setup_harness.py:67` already writes. Install-location independent — *if* it expands (see the open verification item) |
| **Hardcoded `~/.claude/plugins/marketplaces/<mkt>/...`** | **nowhere by hand** | Six candidates on this machine, four transient. Worse: in boss-skills it resolves to the **v0.5.0** aif-skills copy, so a v0.29.0 hook would write `.boss-skills/data/sessions/` while a v0.5.0 status line reads `.claude/data/sessions/` — the status line silently renders nothing and nobody notices |

**Do not symlink into consumer repos.** The farm works in boss-skills only because its targets are
relative and inside the same repo. A consumer repo's symlink would have to point at an absolute
`~/.claude/plugins/...` path — committed, it breaks every teammate; gitignored, it breaks on fresh
clone. If `${CLAUDE_PLUGIN_ROOT}` turns out not to expand, the fallback is for
`setup_harness.py` to **resolve the real plugin root at install time and write the concrete
absolute path itself** — it knows the answer then, and the human never has to guess.

`make doctor` must report the **enabled** plugin id, its resolved root, and its version, and warn
when the plugin providing the status line differs from the one providing the hooks. Given the
two-repo workflow and six on-disk copies, "which agent-harness am I actually running?" is a
question the doctor should answer without the user going digging.

### Directory layout produced

```
$CLAUDE_PROJECT_DIR/
└── .boss-skills/                      # gitignored, repo-named, plugin-owned
    ├── logs/                          # append-only event record — safe to delete anytime
    │   └── <session_id>/
    │       ├── SessionStart.jsonl
    │       ├── UserPromptSubmit.jsonl
    │       ├── PreToolUse.jsonl
    │       ├── PostToolUse.jsonl
    │       ├── Stop.jsonl
    │       ├── chat.json              # Stop transcript export (one writer)
    │       ├── agents/
    │       │   └── <agent_id>/
    │       │       └── chat.json      # SubagentStop export — no longer races Stop
    │       └── transcript_backups/
    │           └── <session>_pre_compact_<trigger>_<ts>.jsonl
    ├── data/                          # live runtime state — was .claude/data/
    │   ├── sessions/
    │   │   └── <session_id>.json      # written by user_prompt_submit.py,
    │   │                              # read by status_line_v2/v3/v4 + /update_status_line
    │   └── tts_queue/
    │       └── tts.lock
    └── cache/                         # regenerable — safe to delete anytime
        └── snyk/<hash>.json           # moved out of the installed plugin dir
```

The three subtrees have genuinely different lifecycles, which is why they are siblings rather than
one bucket: `logs/` is append-only history, `data/` is live state a running session reads back,
`cache/` is regenerable. Retention (step 4) prunes `logs/` and `cache/`. **It must not prune
`data/sessions/` on age alone** — a resumed session will read its own state file back, so
`data/` is pruned only for sessions with no corresponding `logs/` directory.

### Record schema

```json
{
  "schema_version": 1,
  "timestamp": 1783554999498,
  "ts_iso": "2026-07-26T17:51:39.498Z",
  "source_app": "boss-skills",
  "session_id": "722628f2-53da-4eca-bb73-6e2cd615354d",
  "hook_event_type": "PostToolUse",
  "cwd": "/Users/malcolm/dev/bossjones/boss-skills",
  "permission_mode": "default",
  "tool_name": "Bash",
  "tool_use_id": "toolu_01...",
  "payload": { "...full verbatim stdin, post-redaction..." }
}
```

`schema_version` is new relative to pinata and exists so a future layout change is detectable
rather than silently ambiguous.

---

## Assume Nothing — Verify These First

The event table below was assembled by a research subagent whose report carried an internally
inconsistent date. **Treat it as a starting hypothesis, not ground truth.** Before writing
`hooks.json`, re-derive the authoritative list:

1. Fetch [https://code.claude.com/docs/en/hooks](https://code.claude.com/docs/en/hooks) and
   [https://code.claude.com/docs/en/hooks-guide](https://code.claude.com/docs/en/hooks-guide).
2. Cross-check against the vendored copies at
   [`ai_docs/claude_code_hooks_docs.md`](../ai_docs/claude_code_hooks_docs.md) and
   [`ai_docs/claude_code_hooks_getting_started.md`](../ai_docs/claude_code_hooks_getting_started.md)
   — note these are a **snapshot** and may lag the live docs.
3. Run `/hooks` in an interactive session to see what the installed Claude Code build actually
   registers, and `claude --debug-file /tmp/cc.log` to see what actually fires.
4. If an event in the "add" list below does not exist in the current build, **drop it and say so
   in the PR description** rather than registering a dead event.

Specifically verify, because the plan depends on each:

- **Do hooks in the same matcher group run in parallel or in sequence?** The guide states
  parallel. If so, pinata's "log_event first for Stop" ordering is cosmetic and provides no
  guarantee — and the existing `chat.json` collision is a true race. Our per-session/per-agent
  split fixes it either way, but the reasoning in the docs we write must be correct.
- **`StopFailure`** is wired in our `hooks.json:75` but appears in **no** vendored doc. Confirm it
  exists before preserving it.
- **Default timeouts.** Reported as 600s for `command`, 30s for `UserPromptSubmit`, 10s for
  `MessageDisplay`. `MessageDisplay` firing on every assistant message under a 10s budget is the
  single riskiest addition in this plan — confirm the budget and measure `log_event.py` cold-start
  under `uv run` before enabling it.
- **`CLAUDE_PLUGIN_DATA`.** Reported as a writable plugin-persistent data dir. If real, note in
  docs why we deliberately chose a project-local dir instead (inspectability, per-repo isolation,
  one gitignore line).
- **Does `${CLAUDE_PLUGIN_ROOT}` expand inside a `statusLine` command?** The
  [statusLine docs](https://code.claude.com/docs/en/statusline) do **not** document any variable
  expansion, yet this repo already depends on it — `setup_harness.py:67` writes
  `uv run "${CLAUDE_PLUGIN_ROOT}/status_lines/status_line_v10.py"` and `README.md:368` documents
  the same. Meanwhile `.claude/settings.example.json:81` uses `$CLAUDE_PROJECT_DIR` for the same
  purpose. These cannot both be the right answer. Verify which (if either) expands; if neither
  does, the currently-shipped `STATUS_LINE` constant is silently broken and that is a separate bug
  worth reporting. **Do not resolve it by hardcoding an absolute marketplace path** — the install
  path differs per marketplace, so a literal
  `~/.claude/plugins/marketplaces/<name>/plugins/agent-harness/...` breaks for anyone whose
  marketplace or category directory differs from yours.

Reference links to keep at hand:
[hooks reference](https://code.claude.com/docs/en/hooks) ·
[hooks guide](https://code.claude.com/docs/en/hooks-guide) ·
[plugin reference](https://code.claude.com/docs/en/plugin-reference) ·
[settings](https://code.claude.com/docs/en/settings) ·
[PEP 723](https://peps.python.org/pep-0723/) ·
[uv scripts](https://docs.astral.sh/uv/guides/scripts/) ·
[JSON Lines](https://jsonlines.org/)

---

## Event Coverage

### Currently wired (14) — all preserved

`SessionStart` · `SessionEnd` · `Setup` · `UserPromptSubmit` · `PreToolUse` · `PermissionRequest` ·
`PostToolUse` · `PostToolUseFailure` · `SubagentStart` · `SubagentStop` · `Stop` · `StopFailure` ·
`PreCompact` · `Notification`

### To add (7) — log-only, no behavior

| Event | Why it earns its place |
| --- | --- |
| `PostCompact` | We log `PreCompact` but not the result. Asymmetric and unhelpful for debugging context loss |
| `UserPromptExpansion` | This repo is a *skills* repo. Seeing what a skill command expanded to is directly on-mission |
| `PermissionDenied` | We log `PermissionRequest` but not denials — the more interesting half |
| `PostToolBatch` | Parallel tool batches are invisible in per-tool logs |
| `TaskCreated` / `TaskCompleted` | Background task lifecycle is currently unobservable |
| `MessageDisplay` | Completes the turn record. **Highest-volume addition — see the 10s timeout caveat above.** Land it last, behind its own commit, so it can be reverted independently |

### Deliberately deferred (9) — document with rationale, do not wire

| Event | Reason |
| --- | --- |
| `FileChanged`, `CwdChanged` | High-frequency, low signal for a logging baseline |
| `InstructionsLoaded`, `ConfigChange` | Config-churn noise; revisit if debugging skill loading |
| `Elicitation`, `ElicitationResult` | MCP-specific; no current consumer |
| `WorktreeCreate`, `WorktreeRemove` | The worktree skills already maintain `.worktree-logs/` — a separate, working mechanism. Do not duplicate |
| `TeammateIdle` | Agent-teams-specific; not exercised in this repo |

Record all nine in `docs/hooks.md` with these reasons, so the next person doesn't re-litigate.

---

## Relevant Files

### New files

- `plugins/boss-dev/agent-harness/hooks/utils/harness_paths.py` — the 4-branch precedence chain,
  `slug()`, `resolve_harness_root()`, `logs_root()`, `data_dir()`, `cache_dir()`,
  `session_log_dir()`. **Pure and side-effect-free except for `mkdir`** so it is trivially
  unit-testable. Named `harness_paths`, not `log_paths`, because it owns state and cache paths
  too — a logs-only name is how this drifts back apart.
- `plugins/boss-dev/agent-harness/hooks/utils/log_writer.py` — `build_record()`,
  `redact_payload()`, `append_jsonl()` (single `write()` under `fcntl.flock`).
- `plugins/boss-dev/agent-harness/hooks/utils/log_retention.py` — `prune_sessions(max_age_days, max_total_mb)`.
- `plugins/boss-dev/agent-harness/hooks/utils/preflight.py` — shared `check_env()` in the house
  `{"ok": bool, "hint": str | None}` shape.
- `plugins/boss-dev/agent-harness/hooks/log_event.py` — the universal logger CLI
  (`--event-type <Name>`). Model on
  `/Users/malcolm/dev/adobe-ai-factory-summit/pinata/.claude/hooks/log_event.py`, but importing
  the shared helpers instead of re-implementing the env lookup.
- `plugins/boss-dev/agent-harness/hooks/uv-guard.sh` — 4-line POSIX guard.
- `plugins/boss-dev/agent-harness/skills/harness-doctor/SKILL.md` + `scripts/harness_doctor.py` +
  `scripts/tests/test_harness_doctor.py`.
- `plugins/boss-dev/agent-harness/hooks/tests/test_harness_paths.py`, `test_log_event.py`,
  `test_redaction.py`, `test_retention.py`, `test_hooks_e2e.py`, `test_hooks_json_contract.py`,
  `test_state_relocation.py`.

### Files to modify

- [`hooks/hooks.json`](../plugins/boss-dev/agent-harness/hooks/hooks.json) — full rewrite: add
  `log_event.py` per event, route everything through `uv-guard.sh`, add the 7 new events.
- **All 15 hook scripts** — strip log-path construction. Representative:
  `post_tool_use.py:17-36` (the whole body becomes a no-op or the file is deleted),
  `stop.py:168-171,206-209`, `subagent_stop.py:27-33,219-221,256-257`,
  `session_start.py:26-29`, `pre_compact.py:26-29,56-63`, `user_prompt_submit.py:24-27`,
  `session_end.py:25-28,56-74,107-108`, `notification.py:98-102`, `pre_tool_use.py:207-210`,
  `permission_request.py:210,259-264`, `post_tool_use_failure.py:50-53`,
  `subagent_start.py:26-30,99-101`, `setup.py:28-30,199-206`, `snyk_agent_scan.py:59-63`.
- `hooks/setup.py:259-262` — the `if v` filter silently drops *missing* tools. Fix so absent
  prerequisites are actually reported.
- `hooks/utils/llm/task_summarizer.py:38-42` — third writer of `subagent_debug.log`; route
  through the shared helper.
- `hooks/validators/{ruff,ty}_validator.py`, `validate_{new_file,file_contains}.py` — sidecar
  `.log` files currently written **inside the installed plugin**; relocate under the log root.
- `status_lines/status_line{,_v2,_v3,_v4}.py:25-29` — four more copies of `Path("logs")`; **and**
  `status_line_v2.py:61`, `status_line_v3.py:60`, `status_line_v4.py:60` —
  `Path(f".claude/data/sessions/{session_id}.json")`. See the unverified-env caveat above.
- `hooks/user_prompt_submit.py:58` — `Path(".claude/data/sessions")`, the **only writer** of
  session state. → `harness_paths.data_dir() / "sessions"`.
- `hooks/utils/tts/tts_queue.py:28-37` — `Path(".claude") / "data" / "tts_queue" / "tts.lock"`.
  → `harness_paths.data_dir() / "tts_queue"`. Note this is a **lock**; if the path moves while a
  stale lock exists in the old location, two writers could briefly both hold "the" lock. Harmless
  here (TTS serialization only) but state it in the commit message rather than leaving it implicit.
- `hooks/tests/test_tts_queue.py:3` — docstring asserts the lock is at `.claude/data/tts_queue/`
  relative to CWD. Update the docstring, not just the assertion.
- `commands/update_status_line.md:2,20,30` — a **user-facing slash command** whose `description`
  frontmatter and body both name `.claude/data/sessions/{session_id}.json`. This is a documented
  contract; update all three references and mention the move in the changelog.
- `docs/commands.md:327` and `docs/status-lines.md:54` — same path in prose.
- [`hooks/tests/conftest.py:28-36`](../plugins/boss-dev/agent-harness/hooks/tests/conftest.py) — the
  `in_tmp_cwd` fixture **encodes the old cwd-relative contract in its docstring**. Replace with a
  `project_dir` fixture that sets `CLAUDE_PROJECT_DIR`.
- `hooks/tests/test_filesystem_hooks.py:34,44-70` — hard-coded `Path("logs")` assertions.
- `skills/setup-agent-harness/scripts/setup_harness.py:43-56` (`GITIGNORE_PATTERNS` — currently
  lists both `logs/` **and** `.claude/data/` at `:52`; both are replaced by the single derived
  root) and `:326` (`check_env` → delegate to `utils/preflight.py`), plus
  `skills/setup-agent-harness/scripts/tests/test_setup_harness.py:19-21,23,36-37,52-57,62,86-93,106-114,134-144`
  (`:23`, `:57`, `:113` assert on `.claude/data/` specifically).
- `skills/setup-agent-harness/SKILL.md:3,19` — the `description` frontmatter and body both
  enumerate `logs/`, `.claude/data/` as the artifacts the skill gitignores. The description is
  what the model matches on for triggering, so edit it deliberately rather than mechanically.
- `skills/pyrefly-typing/scripts/pyrefly_setup.py:303` and
  `skills/setup-second-brain/scripts/setup_second_brain.py:320` — the other two duplicated
  `check_env()` copies; delegate.
- [`Makefile:313-315`](../Makefile) — the `logs` target (`tail -f logs/*.json`) breaks under
  per-session dirs. Add a `doctor` target.
- `.gitignore` — add the derived `.boss-skills/` root. **Keep** the existing `logs/` (`:273`),
  `.claude/data/` (`:259`) and `**/.claude/data/` (`:261`) entries: they now cover *stale* output
  from before the migration, which must stay ignored rather than suddenly appearing as untracked.
  Add a comment saying so, or the next reader deletes them as dead.
- Docs: `plugins/boss-dev/agent-harness/docs/hooks.md`, `docs/getting-started.md`,
  `plugins/boss-dev/agent-harness/README.md`, root `README.md`, `docs/plugins/agent-harness.md`,
  `docs/tutorials/agent-harness/README.md`, `CLAUDE.md`.
- `.claude-plugin/plugin.json` + `.claude-plugin/marketplace.json` — version bump.
- `specs/hooks-update-with-team.md` — mark **superseded**; it codified the flat `logs/<event>.json`
  scheme this plan replaces (`:186,199,208,230,321,353,371,378`).

### Files to read for context (do not modify)

- `/Users/malcolm/dev/adobe-ai-factory-summit/pinata/.claude/hooks/log_event.py` — the model.
- `/Users/malcolm/dev/adobe-ai-factory-summit/pinata/.claude/hooks/uv-guard.sh` — copy nearly verbatim.
- `/Users/malcolm/dev/adobe-ai-factory-summit/pinata/.claude/hooks/test_hooks.sh` — the e2e suite
  to port from bash to pytest.
- `/Users/malcolm/dev/adobe-ai-factory-summit/pinata/docs/platform/hooks-guide.md` — the doc
  structure worth emulating.
- [`.claude/rules/audit-protocol.md`](../.claude/rules/audit-protocol.md) — **binding** on how the
  `config-reviewer` invocation in Phase 3 must be worded.

### Known pre-existing bugs — observe, do not fix here

Report these in the PR description; each deserves its own change:

- `session_start.py` builds `additionalContext` (`:158-166`) but only under `--load-context`, and
  `hooks.json:124` invokes it **flagless** — so the feature has never run.
- `permission_request.py:271` supports `--auto-allow`; `hooks.json:155` passes only `--log-only`.
- `session_end.py:85` supports `--cleanup`; `hooks.json:144` passes no flags.
- `stop.py:214` has `announce_completion()`; `hooks.json:61` passes `--chat` but not `--notify`.
- `.gitignore:247` ignores `dont_stop.log`, which nothing in the repo writes.

---

## Implementation Phases

### Phase 1: Foundation

Shared helpers + tests, with no hook rewired. The repo keeps working throughout; `logs/` is still
being written by the old code. Everything in this phase is new files only.

### Phase 2: Core Implementation

`log_event.py`, the `hooks.json` rewrite, and stripping logging from all 15 behavior hooks. This
is the hard cutover — at the end of this phase nothing writes to `logs/` any more.

### Phase 3: Integration & Polish

Doctor skill, `check_env()` consolidation, retention wiring, Makefile, gitignore, docs, version
bump, audits.

---

## Step by Step Tasks

Execute in order, top to bottom. Commit at each numbered step so any step can be reverted alone.

### 1. Verify the event list against live docs

- Fetch [hooks](https://code.claude.com/docs/en/hooks) and
  [hooks-guide](https://code.claude.com/docs/en/hooks-guide); diff against
  [`ai_docs/claude_code_hooks_docs.md`](../ai_docs/claude_code_hooks_docs.md).
- Confirm or drop each of the 7 proposed additions. Confirm `StopFailure` is real.
- Confirm parallel-vs-sequential hook execution and the per-event timeout defaults.
- Write the confirmed list into a scratch note; every later step reads from it, not from this spec.

### 2. Write `hooks/utils/harness_paths.py` — test first

- Write `tests/test_harness_paths.py` **before** the module. Cover all four precedence branches,
  and `slug()` against: `boss-skills`, `My Repo (v2)`, `.dotted`, `UPPER`, `---`, `""`, unicode.
- Assert branch 3 derives from `$CLAUDE_PROJECT_DIR`'s basename and **never** from `os.getcwd()`
  when the env var is set.
- Assert all three derived accessors (`logs_root`, `data_dir`, `cache_dir`) share one root, and
  that `$CLAUDE_HOOKS_LOG_DIR` moves **only** `logs_root()` while `data_dir()` and `cache_dir()`
  stay anchored to the root. That divergence is the one subtle part of the contract — pin it.
- Then implement. PEP 723 header, `from __future__ import annotations`, full type annotations,
  `pathlib.Path` — per [`CLAUDE.md`](../CLAUDE.md) and
  [`.claude/rules/python-scripts.md`](../.claude/rules/python-scripts.md).
- The default `.agent-harness` string must appear **exactly once in the entire codebase**. Add a
  test asserting that (`grep -c` across `plugins/`), because this is the specific drift the
  reference implementation suffers from.

### 3. Write `hooks/utils/log_writer.py` — test first

- `tests/test_log_event.py`: record schema, `schema_version`, promoted-field extraction, JSONL
  round-trip (write 3 records → read 3 lines → each parses).
- `tests/test_redaction.py`: key-name patterns (`*_TOKEN`, `*_KEY`, `*_SECRET`, `*_PASSWORD`,
  `AUTHORIZATION`), value prefixes (`sk-`, `ghp_`, `xoxb-`, `Bearer `), and — critically — a
  **negative** test that ordinary content is untouched. Redaction that eats real data is worse
  than none.
- Lock test: two threads/processes appending 200 lines each to one file → exactly 400 lines, every
  one parsing as valid JSON.
- Then implement. `fcntl` import must be guarded (`try: import fcntl / except ImportError:`) so
  the module still loads on non-POSIX.
- Promoted fields: extend pinata's `PROMOTED_FIELDS` list with fields for the newly-added events
  (`error_type`, `error_message`, `task_id`, `task_status`, `command_name`,
  `classifier_decision`, `tools_used`, `prompt_id`, …) — take the field names from the doc fetch
  in step 1, not from this spec.

### 4. Write `hooks/utils/log_retention.py` — test first

- `tests/test_retention.py`: age-based pruning with `os.utime`-backdated dirs; size-cap eviction
  oldest-first; a guard that it **never** deletes outside the resolved root (construct a
  symlink pointing out of the tree and assert it is not followed).
- **Prune `logs/` and `cache/` by age. Do NOT prune `data/sessions/` by age.** A long-lived or
  resumed session reads its own state file back; deleting it because it is 8 days old silently
  breaks the status line. Prune a `data/sessions/<id>.json` only when `logs/<id>/` no longer
  exists — i.e. let the logs retention decide, and have state follow it. Add an explicit test:
  backdate a session state file, run the prune, assert it **survives** while its log dir exists.
- Defaults: 7 days, 100 MB. Configurable via `CLAUDE_PLUGIN_OPTION_HOOKS_LOG_RETENTION_DAYS` and
  `..._MAX_MB` through the existing
  [`utils/config.py`](../plugins/boss-dev/agent-harness/hooks/utils/config.py) resolver.

### 5. Write `hooks/uv-guard.sh`

```sh
#!/bin/sh
# Silent guard: skip the hook entirely if uv is not installed.
command -v uv >/dev/null 2>&1 || exit 0
exec uv "$@"
```

- `chmod +x`. Add a test asserting the file is executable and exits 0 with `PATH=""`.

### 6. Write `hooks/log_event.py`

- `--event-type <Name>`, reads stdin, composes the helpers from steps 2–4, **always `sys.exit(0)`**,
  wraps all disk I/O in a bare `except Exception: pass`.
- Malformed stdin → exit 0 silently. A logger that can block Claude is a bug.
- Add `--prune` so `SessionEnd` can trigger retention in the same invocation.

### 7. Rewrite `hooks/hooks.json`

- Every command becomes:
  `sh "${CLAUDE_PLUGIN_ROOT}"/hooks/uv-guard.sh run "${CLAUDE_PLUGIN_ROOT}"/hooks/<script>`
- Add `log_event.py --event-type <Name>` to all 14 existing events + the events confirmed in
  step 1. Hold `MessageDisplay` back for its own commit (step 8).
- `SessionEnd` gets `log_event.py --event-type SessionEnd --prune`.
- Preserve all existing matchers verbatim, including
  `Notification` → `permission_prompt|idle_prompt|elicitation_dialog` (`:46`) and
  `PostToolUse` → `Edit|MultiEdit|Write` (`:26`).
- Write `tests/test_hooks_json_contract.py`: every referenced script exists; every script is
  executable; every script has a valid PEP 723 header; every event name is in the verified list;
  every script under `hooks/` is either registered or in an explicit allowlist (`validators/`,
  `utils/`, `uv-guard.sh`).

### 8. Add `MessageDisplay` — separate commit

- Measure `log_event.py` cold-start under `uv run` first. If p95 approaches the confirmed
  `MessageDisplay` timeout, **do not wire it** — record the measurement and the decision in
  `docs/hooks.md` instead. Report the number either way.

### 9. Relocate every generated path — logs, state, and cache

Not just hooks: this step also covers status lines and validators, which have the same bug.

**Logs:**

- Remove every `log_dir` / `log_path` construction and every read-append-rewrite block.
- `post_tool_use.py` becomes empty of purpose → **delete it** and remove its `hooks.json` entry
  (`log_event.py` covers it). Same audit for `post_tool_use_failure.py`, `subagent_start.py`,
  `session_start.py` (flagless, so currently log-only), `setup.py`'s log write.
- Keep genuine behavior: `pre_tool_use.py`'s dangerous-`rm` guard, `tmux_notify.py`,
  `ruff_autoformat.py`, `notification.py`'s TTS, `snyk_agent_scan.py`'s scan,
  `user_prompt_submit.py`'s agent-naming.
- **Fix the `chat.json` race:** `stop.py` → `<session>/chat.json`; `subagent_stop.py` →
  `<session>/agents/<agent_id>/chat.json`.
- `pre_compact.py` → `<session>/transcript_backups/`.
- `validators/*.py` and `utils/llm/task_summarizer.py:38` → shared helper.
- `status_lines/status_line{,_v2,_v3,_v4}.py:25-29` → `harness_paths.logs_root()`.

**State — `.claude/data/` → `<root>/data/`:**

- `user_prompt_submit.py:58` → `harness_paths.data_dir() / "sessions"`. This is the only writer.
- `status_line_v2.py:61`, `status_line_v3.py:60`, `status_line_v4.py:60` → same helper, but they
  **must pass the project dir in explicitly** rather than letting the helper read the environment.
  See "Status lines resolve the project dir differently" below — this is settled, not open.
- `utils/tts/tts_queue.py:28-37` → `harness_paths.data_dir() / "tts_queue"`.
- `commands/update_status_line.md:2,20,30` → update the frontmatter `description` and both body
  references. This is a user-facing contract.

**Cache:**

- `snyk_agent_scan.py:59-63` → `harness_paths.cache_dir() / "snyk"` instead of the installed
  plugin directory.

**Migration of existing artifacts — decide and state it explicitly:**

The recommended behavior is **no automatic migration, no automatic deletion**. There are 25 stale
session JSONs and a `tts.lock` in `.claude/data/` in this repo; they are gitignored, harmless, and
belong to sessions that have ended. Silently moving or deleting a developer's files is worse than
leaving them. Instead: `make doctor` reports "stale `.claude/data/` found (N files) — safe to
delete" and the changelog says the same. If the build agent concludes a migration is genuinely
needed, it must be opt-in behind an explicit flag, never automatic on session start.

Write `tests/test_state_relocation.py`: assert `user_prompt_submit.py` writes under
`harness_paths.data_dir()` and that **no** `.claude/data/` directory is created in a tmp project.

### 10. Rework the test fixtures

- Replace `conftest.py`'s `in_tmp_cwd` with a `project_dir` fixture that `monkeypatch.setenv`s
  `CLAUDE_PROJECT_DIR` to a tmp dir (still `chdir`ing, to catch accidental cwd reliance).
- **Update its docstring** — `conftest.py:7` and `:32` both document the old
  "`./logs` and `./.claude/data`" contract. That docstring is how the next reader learns the
  wrong thing; it is as load-bearing as the code.
- Fix `test_filesystem_hooks.py:34,44-70` and `test_tts_queue.py:3`.

### 11. Write the end-to-end suite `tests/test_hooks_e2e.py`

- Port `/Users/malcolm/dev/adobe-ai-factory-summit/pinata/.claude/hooks/test_hooks.sh` to pytest.
- Parametrize over every registered event; build a realistic payload per event from the schemas
  fetched in step 1; invoke via `subprocess` with `sys.executable` (permitted for CLI-semantics
  tests per [`CLAUDE.md`](../CLAUDE.md)); assert exit code and that
  `<log-root>/<session>/<Event>.jsonl` exists and its last line parses.
- Include `pre_tool_use.py`'s blocking cases: dangerous `rm` → **exit 2**, safe command → exit 0.
- *(Not mandated, one line if you want it: after the full sweep, `assert not (project_dir / "logs").exists()` — the cheapest possible guard that the hard cutover holds.)*

### 12. Build `hooks/utils/preflight.py` + the `harness-doctor` skill

- `check_env()` in the house shape, checking: `uv`, `python3`, `git`, `gh` (+ `gh auth status`,
  15s timeout), `ruff`, `tmux`. Advisory only — never blocks.
- `skills/harness-doctor/` per [`.claude/rules/plugin-structure.md`](../.claude/rules/plugin-structure.md):
  `SKILL.md` with concrete trigger patterns, `scripts/harness_doctor.py`, `scripts/tests/`.
  Also report the **resolved root**, its size broken down by `logs/` / `data/` / `cache/`, and any
  **stale pre-migration artifacts** (`logs/`, `.claude/data/`) with a "safe to delete" note. Those
  are the questions people will actually have. The doctor **reports**; it never deletes.
- Per [`CLAUDE.md`](../CLAUDE.md), a skill needs an `eval/` suite: run the
  [`scaffold-skill-eval`](../plugins/boss-experimental/boss-experimental/skills/scaffold-skill-eval/SKILL.md)
  skill. Note `claude-config-validation` Check #22 asserts `{skill_path}/eval/` exists.
- **Never** use `` ! ``-backtick patterns in `SKILL.md` — see the parser bug
  ([GitHub #12781](https://github.com/anthropics/claude-code/issues/12781)) noted in `CLAUDE.md`.
  Use `$ command` notation.

### 13. Consolidate the three duplicated `check_env()` implementations

- `setup_harness.py:326`, `pyrefly_setup.py:303`, `setup_second_brain.py:320` → delegate to
  `utils/preflight.py`.
- These live in skills that may be used standalone — if a hard import across the plugin tree is
  fragile, keep a thin local shim and say so in a comment. Do not break
  `test_setup_harness.py`.
- Fix `hooks/setup.py:259-262`'s `if v` filter.

### 14. Update gitignore, setup skill, and Makefile

- `.gitignore`: add `.boss-skills/`. Keep the existing `logs/`, `.claude/data/` and
  `**/.claude/data/` entries with a comment marking them as pre-migration leftovers.
- `setup_harness.py:43-56` `GITIGNORE_PATTERNS`: replace **both** `logs/` and `.claude/data/`
  (`:52`) with the single **derived** dot-dir. The setup skill knows the repo name at install
  time, so it can write the concrete name into the managed block. Because the managed block is
  delimited by `MANAGED_BLOCK_START`/`END` (`:43-44`), an existing consumer repo's block is
  rewritten in place on re-run — verify that path, don't assume it.
- Update `skills/setup-agent-harness/scripts/tests/test_setup_harness.py` (`:23`, `:57`, `:113`
  assert on `.claude/data/`) and `SKILL.md:3,19`.
- `Makefile`: rewrite `logs` (`:313-315`) to tail the newest session dir; add
  `logs-session SESSION=<id>`; add `doctor`. Register both in `.PHONY` (`:23`).
- Do **not** delete the developer's existing `logs/` directory. Print a one-line note from
  `make doctor` if a stale one is found.

### 15. Sync the `.claude/hooks` symlink farm

- `.claude/hooks/` symlinks into the plugin. New files (`uv-guard.sh`, `log_event.py`,
  `utils/log_*.py`, `utils/preflight.py`) need links; deleted files need theirs removed.
- Use the existing `make symlink-plugins` target rather than hand-linking, and verify with
  `make verify-structure`.

### 16. Documentation pass — subagents

Run these in parallel where independent. Invoke each with the file paths and the changed
behavior; for `config-reviewer`, follow
[`.claude/rules/audit-protocol.md`](../.claude/rules/audit-protocol.md) **exactly** — path only, no
context, no hints about what changed.

- `documentation-generation:documentation-generation-tutorial-engineer` →
  `docs/tutorials/agent-harness/README.md` and
  `plugins/boss-dev/agent-harness/docs/getting-started.md`.
- `documentation-generation:reference-builder` →
  `plugins/boss-dev/agent-harness/docs/hooks.md`: the event × payload × exit-code matrix, the
  path-precedence chain, the record schema, and the 9 deferred events **with their rationale**.
- `claude-md-management:claude-md-improver` → `CLAUDE.md` currently has **zero** occurrences of
  "hook" despite 15 shipping. Add a hook-logging section so future agents don't reinvent the old
  pattern.
- `config-reviewer` → invoke with exactly `plugins/boss-dev/agent-harness/hooks` and nothing else.

Also fix by hand (stale, contradicts reality today):

- `plugins/boss-dev/agent-harness/README.md:26,30,192-194,227,344-356,378-379` — says 13 hooks and
  "not active on install / manual wiring". Both false; they are wired via `hooks/hooks.json`.
- Root `README.md:30` — says version **0.14.0**; actual is **0.28.0**. `:56` — says 13 hooks,
  manual wiring.
- `docs/plugins/agent-harness.md:26,214-215` — same stale claims.
- `specs/hooks-update-with-team.md` — add a superseded banner pointing at this spec.

### 17. Version bump and release hygiene

- Run the [`version-bump-reviewer`](../.claude/skills/version-bump-reviewer/SKILL.md) skill. Expected
  **minor** → `0.29.0`: new features (7 events, doctor skill) plus a behavior change (log
  location) in a pre-1.0 plugin.
- It must bump **both** `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json:5` **and** the
  matching entry in `.claude-plugin/marketplace.json:39-43` — they are currently in parity at
  0.28.0 and must stay that way.
- If `HOOKS_LOG_RETENTION_DAYS` / `HOOKS_LOG_DIR` should be user-tunable from the plugin UI, add
  them to `plugin.json`'s `userConfig` alongside the existing `ENABLE_TTS`, `ENGINEER_NAME`,
  `ENABLE_SNYK_AGENT_SCAN` keys.

### 18. Final validation

- Run everything in **Validation Commands** below.
- Then do the live smoke test in **Verification** below. Tests passing is not the same as hooks
  working — the wiring only executes inside a real Claude Code session.

---

## Testing Strategy

Test-first throughout, per
`superpowers:test-driven-development` and `CLAUDE.md`. Tests live in
`plugins/boss-dev/agent-harness/hooks/tests/`.

**Layer 1 — unit (pure logic).** `harness_paths` precedence × 4 branches, `slug()` edge cases,
root-vs-logs override divergence, state/cache path derivation,
`build_record()` schema, redaction (positive **and** negative), retention pruning, lock-guarded
concurrent append. Loaded via the existing
[`hook_loader.py`](../plugins/boss-dev/agent-harness/hooks/tests/hook_loader.py) `importlib` pattern.

**Layer 2 — end-to-end (CLI semantics).** Real payload → `subprocess` → assert exit code and that
the `.jsonl` materialized. This is what catches a wrong flag or a bad matcher; unit tests
structurally cannot. Explicitly permitted by `CLAUDE.md`'s subprocess exception.

**Layer 3 — contract (config ↔ filesystem).** Parse `hooks.json`; assert every referenced script
exists, is executable, has valid PEP 723 metadata; every event name is valid; no orphan scripts.

**Edge cases that must have a named test:**

- `CLAUDE_PROJECT_DIR` unset → falls back to `os.getcwd()`, does not crash.
- `session_id` missing from payload → `"unknown"`, does not crash.
- Log dir unwritable (`chmod 000`) → hook still exits **0**.
- Malformed / empty / non-JSON stdin → exits **0**.
- Two subagents, one `session_id`, concurrent appends → no interleaved lines.
- Repo basename that slugs to empty → falls back to `agent-harness`.
- Same code, three different `$CLAUDE_PROJECT_DIR` values (`/x/boss-skills`, `/x/aif-skills`,
  `/x/pinata`) → `.boss-skills/`, `.aif-skills/`, `.pinata/`. Pins backport portability: the
  plugin must never hardcode its home repo's name.
- Retention with a symlink escaping the root → not followed, nothing outside is deleted.
- `$CLAUDE_HOOKS_LOG_DIR` set → `logs_root()` moves, `data_dir()` and `cache_dir()` do **not**.
- Explicit `project_dir=` argument set **and** `CLAUDE_PROJECT_DIR` set to something different →
  the explicit argument wins. This is the status-line path; if the precedence inverts, status
  lines read the wrong directory only in sessions where a `cd` happened, which is exactly the
  kind of bug that survives to production.
- Status line given a payload where `workspace.project_dir` differs from `cwd` → reads state from
  `project_dir`, not `cwd`.
- A backdated `data/sessions/<id>.json` whose `logs/<id>/` still exists → **survives** pruning.
- `user_prompt_submit.py` writes state → **no** `.claude/data/` directory is created.
- `pre_tool_use.py` still exits **2** on dangerous `rm` (the one intentional block must survive
  the refactor).

---

## Acceptance Criteria

1. `.{repo-slug}/logs/{session_id}/{Event}.jsonl` is created for every registered event during a
   real session; every line parses as JSON and carries `schema_version: 1`.
2. No file under `plugins/boss-dev/agent-harness/` (excluding tests) constructs a log, state, or
   cache path itself — **zero** grep hits for `Path("logs")`, `Path.cwd() / "logs"`,
   `getcwd(), "logs"`, or `.claude/data`.
3. The default root string appears exactly **once** in the codebase.
4. No new `logs/` **or** `.claude/data/` directory is created anywhere when the e2e suite runs.
5. Session state written by `user_prompt_submit.py` is read back correctly by
   `status_line_v2/v3/v4` and by `/update_status_line` from the new location.
6. Retention prunes `logs/` and `cache/` by age, and **never** deletes a `data/sessions/` file
   whose `logs/<id>/` directory still exists.
7. All 14 existing events remain wired; the events confirmed in step 1 are added; the 9 deferred
   are documented with rationale.
8. `make lint`, `make test`, `make test-agent-harness`, `make verify-structure`,
   `make markdown-lint` all pass with **zero** warnings — `CLAUDE.md` requires zero.
9. `make doctor` reports `uv`, `python3`, `git`, `gh`, `ruff`, `tmux`, the resolved root and its
   size, and any stale pre-migration `logs/` or `.claude/data/` it finds.
10. Hooks silently no-op with `PATH` stripped of `uv` — no error output.
11. `git status --porcelain` shows nothing under the new root; `git check-ignore -v` confirms the
    ignore rule.
12. `plugin.json` and `marketplace.json` versions are bumped and identical.
13. Every stale doc claim listed in step 16 is corrected, including the three `.claude/data/`
    references in `commands/update_status_line.md`.
14. `pre_tool_use.py` still exits 2 on a dangerous `rm`.

---

## Validation Commands

```bash
# Full gate — CLAUDE.md requires zero warnings
make lint
make test
make test-agent-harness
make verify-structure
make markdown-lint
make link-check

# Focused hook suites
uv run pytest -s plugins/boss-dev/agent-harness/hooks/tests/
uv run pytest -s plugins/boss-dev/agent-harness/skills/harness-doctor/scripts/tests/
uv run pytest -s plugins/boss-dev/agent-harness/skills/setup-agent-harness/scripts/tests/

# Acceptance #2 — nothing builds its own log/state/cache path (must print nothing)
grep -rn 'Path("logs")\|Path.cwd() / "logs"\|getcwd(), "logs"\|\.claude/data' \
  plugins/boss-dev/agent-harness/ --include='*.py' \
  | grep -v '/tests/'

# Acceptance #2 (docs/commands) — no stale .claude/data references left behind
grep -rn '\.claude/data' plugins/boss-dev/agent-harness/ --include='*.md' | grep -v CHANGELOG \
  | grep -v -E 'harness-doctor/SKILL\.md|setup-agent-harness/SKILL\.md|docs/hooks\.md|docs/getting-started\.md'

# Acceptance #3 — the default appears exactly once (must print 1)
grep -rn "'\.agent-harness'\|\"\.agent-harness\"" plugins/ --include='*.py' | wc -l

# Backport portability — plugin code must never hardcode this repo's name (must print nothing)
# setup_harness.py's `_plugin_id()` fallback (`or "boss-skills"`) is intentional: it's the
# last-resort marketplace name when neither the marketplaces/ path segment nor
# CLAUDE_PLUGIN_MARKETPLACE is set, matching this repo's own settings.local.json entry. Excluded
# by content, not by file, so any *other* hardcode in that file still fails the check.
grep -rn 'boss-skills' plugins/boss-dev/agent-harness/ --include='*.py' | grep -v '/tests/' \
  | grep -v 'or "boss-skills"'

# Acceptance #10 — uv-guard silently no-ops
echo '{}' | env PATH=/nonexistent /bin/sh \
  plugins/boss-dev/agent-harness/hooks/uv-guard.sh run \
  plugins/boss-dev/agent-harness/hooks/log_event.py --event-type Stop
echo "exit=$?   # must be 0, with no output above"

# Acceptance #11 — nothing is committable
git status --porcelain | grep -E '^\?\?.*\.boss-skills' && echo "FAIL: not ignored" || echo "OK"
git check-ignore -v .boss-skills/logs/

# Acceptance #12 — version parity (the two values must match)
jq -r .version plugins/boss-dev/agent-harness/.claude-plugin/plugin.json
jq -r '.plugins[] | select(.name=="agent-harness") | .version' .claude-plugin/marketplace.json

# hooks.json is valid JSON and every script resolves
jq -e . plugins/boss-dev/agent-harness/hooks/hooks.json > /dev/null && echo "valid JSON"
```

---

## Verification (live, end-to-end)

Passing tests do not prove the hooks are wired. The wiring only executes inside a real session, so
finish with this:

### Precondition: confirm you are testing the right copy

Do this before every run of the steps below.

```bash
grep -n 'agent-harness' ~/.claude/settings.json     # which plugin id is enabled
ls -d ~/.claude/plugins/marketplaces/*/              # what is installed
```

The enabled `agent-harness` must be **this repo's** checkout. If it is `agent-harness@aif-skills`
(or any other lineage), stop: every check below would pass against v0.5.0 and tell you nothing.
Install/enable the local plugin, or run this section on a machine where boss-skills is the global
install. **Record which copy you verified against in the PR description.**

### Steps

1. **Run a real session with debug output:**

   ```bash
   claude --debug-file /tmp/cc-hooks.log
   ```

   In another terminal: `tail -f /tmp/cc-hooks.log | grep -i hook`
2. **Inside that session:** run `/hooks` to confirm every event is registered from the plugin;
   issue a prompt, let it call a tool, then stop.
3. **Confirm the artifacts:**

   ```bash
   ls -R .boss-skills/logs/
   # every file must be valid JSONL:
   for f in .boss-skills/logs/*/*.jsonl; do
     jq -e . "$f" > /dev/null || echo "INVALID: $f"
   done
   jq -r '.hook_event_type' .boss-skills/logs/*/*.jsonl | sort | uniq -c
   ```

4. **Confirm the cutover:** no new `logs/` directory appeared, no new `.claude/data/` files were
   written, and the pre-existing ones have no files modified after the session started.

   ```bash
   # nothing under the old locations may be newer than the session start marker
   touch /tmp/session-start-marker   # run this BEFORE starting the session
   find logs .claude/data -newer /tmp/session-start-marker 2>/dev/null
   # ↑ must print nothing
   ls .boss-skills/data/sessions/    # ↑ the new location must have today's session
   ```

5. **Confirm state round-trips:** with the status line active, run `/update_status_line` to set a
   key, then confirm it appears in `.boss-skills/data/sessions/<session_id>.json` **and** renders
   in the status line. This is the one path that spans three processes (hook writes, command
   mutates, status line reads) and is the most likely thing to silently half-work.
6. **Confirm redaction:** run a Bash command containing a fake token
   (`echo "export FAKE_TOKEN=sk-abc123"`), then
   `grep -r 'sk-abc123' .boss-skills/` → **must return nothing** (search the whole root, not just
   `logs/` — the session state file records prompts too).
7. **Confirm the race fix:** run a session that spawns a subagent; assert `<session>/chat.json`
   and `<session>/agents/<id>/chat.json` both exist and differ.
8. **Confirm retention:** backdate a session dir with `touch -t`, start a session, exit, and
   verify the log dir was pruned — and that a `data/sessions/` file belonging to a session whose
   logs still exist was **not**.
9. **Run the doctor:** `make doctor`. It should report the resolved root, its size, and any stale
   pre-migration `logs/` or `.claude/data/`.

If any step fails, use `superpowers:systematic-debugging` — `/debug` inside the
session and `--debug-file` show which hook matched, its exit code, and its full stderr.

---

## Notes

- **No new dependencies.** Everything is stdlib (`json`, `os`, `time`, `fcntl`, `pathlib`,
  `shutil`, `argparse`). Keep `dependencies = []` in the PEP 723 headers of the new modules —
  `log_event.py` runs on **every event** and must stay cold-start cheap.
- **Pin `requires-python`.** The existing hooks disagree (`>=3.13` in `post_tool_use.py:3`, other
  values elsewhere) and pinata is inconsistent too (`>=3.8` vs `>=3.11`). Pick one — `>=3.11`
  unless something needs newer — and apply it to every new file.
- **Import bootstrap.** Hooks reach `utils/` via
  `sys.path.insert(0, str(Path(__file__).parent))` (see `notification.py:26`). Reuse that exact
  pattern; do not invent a package layout. Note `hook_loader.py` deliberately adds/removes the
  hooks dir per-load to avoid leaking a top-level `utils` package that would shadow other suites —
  don't break that.
- **The one non-negotiable:** `log_event.py` must **never** block Claude. Every failure path exits
  0. A logger that can hang a session is worse than no logger.
- **Status lines run hot.** Per the
  [statusLine docs](https://code.claude.com/docs/en/statusline): they re-run on every assistant
  message, on `/compact`, on permission-mode and vim-mode changes, and on any `refreshInterval`
  timer; updates are debounced at 300ms and **an in-flight script is cancelled** if a new update
  arrives. Reading one small session JSON is fine. Do not let `harness_paths` do anything
  expensive (directory walks, size computation, `mkdir` of the whole tree) on the status-line
  path — keep `mkdir` in the writers, not the resolvers.
- **Deferred by decision, not oversight:** per-record size truncation (a giant `tool_response`
  producing a multi-megabyte JSONL line) was considered and not included. The retention size cap
  bounds total growth but not a single pathological line. Revisit if it bites.
- **Scope boundary:** the worktree skills' `.worktree-logs/` is a separate, working mechanism.
  Do not absorb it.
