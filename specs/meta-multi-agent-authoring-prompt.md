# Build `plugins/meta/multi-agent`: a Claude Code + Codex plugin for running a multi-agent team on a SQLite message board, driven through cmux

You are working in `~/dev/bossjones/boss-skills` (branch `feature-multi-agent-system`). Build a new plugin, **`multi-agent`**, under category **`meta`** (`plugins/meta/multi-agent/`).

`meta` is a **new** category: today `plugins/` only has `boss-dev`, `boss-experimental`, `boss-homelab` and `social-media`. R1 must confirm that nothing enumerates categories, such as `verify-structure.py`, `symlink_plugins.py`, `devtools/lint.py` path lists, the README tables or the docs index. Update every one that does in the same PR.

It packages the multi-agent framework we ran for the SEAF: Forever War game (repo bossjones/superearth_rts_game, local clone at `~/Documents/Cowork Playground/superearth_rts_game`; "game repo" below means that path; Oct 8–10 2026):

- about 30 concurrent agents (Codex workers, Claude Code leads and Claude subagents);
- coordinated through a SQLite "agent board";
- driven and observed through cmux panes;
- watched by background monitors and dashboards.

The plugin must:

- install with `/plugin install` in Claude Code;
- be usable from OpenAI Codex CLI;
- pass this repo's validators and CI.

The owner may run **several teams at once** (one per project or task, any size from a few agents to dozens), so everything is namespaced by team (see Design rules → Teams and namespacing).

Work in phases. **Phase 1 is parallel research. Don't write plugin files until Phase 2.**

**Prior research and decisions (2026-10-16).** Read `ai_docs/simonw_enhancements/README.md` first. It indexes eight reports, a Codex audit, and the owner's decisions:

- **Reports:** SQLite and Datasette tooling, the METR multi-agent incident, the existing dashboards, and interrupt and coordination patterns from the SEAF run.
- **Decisions:** recorded in this spec under *Authority, interrupts and escalation*, *Dashboard*, *Rejected alternatives*, and *Follow-ups*.

Don't re-litigate those decisions; build on them.

Docs to read first:

- <https://code.claude.com/docs/en/plugins-reference>
- <https://code.claude.com/docs/en/hooks>
- <https://code.claude.com/docs/en/skills#extend-claude-with-skills>

## What exists today (ground truth; verify, don't trust blindly)

### 1. The board: `~/.seaf-agent-board/`

`bin/agent_board.py`: 540 lines, stdlib only, PEP 723 header with no dependencies. This is the canonical copy; the game repo has `tools/agent_board.py`, which is older.

- **DB location:** `--db`, else `$SEAF_BOARD_DB`, else `~/.seaf-agent-board/board.sqlite`.
- **SQLite settings:**
  - WAL mode, `busy_timeout` 30 s, `synchronous=NORMAL`.
  - `BEGIN IMMEDIATE` for claims and progress.
  - Jittered retry: 12 tries, about 20 s total. Stress-tested with 64 processes.
- **Schema:**
  - `messages(id, ts, sender, recipient DEFAULT '*', kind, topic, ref, body, reply_to)`, index on `(recipient, id)`
  - `reads(message_id, agent, ts, PK(message_id, agent))`: per-agent read receipts, which are the only proof an agent saw a post
  - `claims(resource PK, owner, note, ts, expires_ts)`: resources look like `asset:<id>`, `branch:<x>`, `file:<p>`; TTL 240 min; exit code 3 means held by another agent
  - `progress(id, message_id → messages, ts_epoch, agent, task, started_epoch, budget_min, elapsed_min, owner_wait_min, eta_lo_min, eta_hi_min, finish_lo_epoch, finish_hi_epoch, marker, blockers)`, with indexes `(agent, task, id)` and `(ts_epoch)`: 🟢/🟡/🔴 by budget and ETA revisions. Copy the live DDL exactly; don't re-derive it.
  - The game-specific tables `image_analysis` and `audio_profile` don't belong in the plugin.
- **Subcommands:**
  - `init`
  - `post --from --to (* | name | a,b,c) --kind --topic --ref --reply-to --body/--body-file`
  - `inbox --for [--all --topic --since]`: at most 200 per call; excludes the agent's own posts; matches `*`, the exact name, or membership in a comma list
  - `ack ids... --by`
  - `thread id`
  - `watch --for [--interval --once --timeout --ack]`
  - `claim / release <res> --by [--ttl-min]`, `claims`
  - `progress --from --to --task --stage "name|State|remaining|risk" ...`
  - `digest --minutes --post`
  - Exit codes: 0 ok, 1 nothing, 2 usage, 3 claim held.
- **Kinds:** note, request, art_ready, review_package, feedback, approved, port_done, blocked, question, answer, status. Today they are enforced by argparse `choices=KINDS`. Make them configurable: the generic default set drops `art_ready` and `port_done`, and the SEAF profile adds them back. Kinds are validated only on `post`. Reads must accept any stored kind, because the existing DB already holds SEAF kinds.
- **Open side effects:** `connect()` runs `PRAGMA journal_mode=WAL` and `executescript(SCHEMA)` (`CREATE TABLE IF NOT EXISTS …`) on **every** open, so even `inbox` writes to the DB file. Keep in mind for any "read-only" access (see Design rules → Board).
- **Real usage:** 10,727 messages, 129,660 reads, 83 distinct senders, 2,110 comma-recipient posts, 2,687 replies. Main topics: progress, merge, ci, rules, inbox, idle-retire, godot-slot, digest.
- **Concurrency:** agents always call it with `python3 -I` (isolated mode, safe from any cwd). Codex sandboxes need `--add-dir ~/.seaf-agent-board` to write the DB.

### 2. Monitors and sync scripts

All are stdlib Python or bash. Each prints one line per event to stdout (the Claude Monitor tool turns lines into notifications) and/or posts to the board under a bot identity. JSON is written atomically (tmp + `os.replace`).

**Generic, port these into the plugin:**

| Script | What it does |
|---|---|
| `ack_monitor.py` | Every 60 s. Tracks who acked a standing order (`--order ID --name NAME --delivered ISO`). Probes each agent's cmux pane (`cmux tree`, `read-screen`, `ps -t tty`) for runtime, model, context %, activity and queued input. Checks rule-ack compliance against `RULE_POSTS`. Writes `acks.json` and pages the supervisor as `claude-ackmon`. Hard-coded today: ROSTER, TITLE_HINT, EXEMPT, RULE_POSTS. |
| `status_sync.py` | Every 20 s. Builds `status.json`, the "one-ping report". Generic parts: per-agent inbox backlog (INBOX-ZERO-1: ≤10 directed unread, oldest ≤15 min), agent_counts (the AGENTS bar), STALE-WORKER (idle on reserve 30+ min), open PRs + CI via `gh`, `board_recent.json` (newest 400 posts). Skips agents in `team/idle_hold.json`. Most of the rest is SEAF. |
| `page_watch.py` | Every 2 min. HTTP-checks every dashboard page and JSON freshness; prints PAGE-BROKEN / PAGE-STALE / PAGE-OK. Has `--dry-run`. |
| `stale_audit.py` | Every 15 min, IDLE-RETIRE-1. An idle pane with no board post for 15 min gets a RETIRE-CHECK, both as a board post and pasted into the pane (`cmux send --surface S -- msg; sleep 1; cmux send --surface S "\r"`). If there's no reply within 15 min, it posts RETIRED and runs `cmux close-surface --surface S --force --workspace W`. Honors the hold list. Exempts SUPERVISOR, coordinator and monitor titles. `name_of()` maps pane titles to agent names. |
| `team/worker_watch.py` | Supervisor's watcher. Finds cmux workspaces by a task tag in the title. Reports IDLE / BLOCKED / SILENT (12 min) / LONGTURN (60 min) / EXITED / BOARD-BLOCKED / AWAITING-SUPERVISOR. |
| `team/cmux_status.sh` | `cmux set-status <agent> "<agent> · <stage> · <text>" --icon --color --workspace W`: the sidebar pill per worker (CMUX-STATUS-1). |
| `board_watch.sh` | Every 10 s. Tails new posts as one line each. |
| `gh_watch.sh` | PR state and new comments. |
| `coordinator/ci_watch.sh` | Prints `CI pass\|fail #N @sha` once per PR head and `MAIN-CI ...` per main run; dedups with marker files. |
| `coordinator/stuck_watch.sh` | STUCK50-1. Screenshots and DOM-scrapes the acks page in a cmux browser surface; reports agents stuck 50+ min. Brittle; prefer reading `acks.json` directly. |
| `team_board.sh` | Team table: latest post per agent, 🔵/🟡/🔴 by minutes since last post. |
| `verdicts_sync.py` | Parses `VERDICT <item>: <WORD>` board posts into `verdicts.json`. |
| `movie_refs_merge.py` | Fragment-merge pattern: `<dir>.d/*.json` → one JSON file, so parallel writers never clobber each other. |

**SEAF-only, keep as an example profile only:** `image_analysis_sync.py`, `audio_profile_sync.py`, `sticker_check.py` (needs pillow + numpy), `ap.py`, `ia.py`, and `coordinator/artreview/*` (exact-head art PR review: `rv.sh`, `rvu.sh`, `ar.py`, `ci_emul.py`, using `uv run --with pillow --with numpy`).

**Known bugs not to carry over:**

- Three monitors hard-code a deleted scratchpad path to the board tool.
- Many hard-coded `/Users/bossjones/...`, `/private/tmp/claude-501/...`, `surface:1000010050`, `workspace:100001000N` and repo slug values.

The plugin must resolve everything from config and environment variables.

### 3. Dashboards

- **:8765 server:** `tools/sprite_compare/serve.py` in the game repo. It serves static files from `~/.seaf-agent-board/movie_frames/`.
  - `acks.html` (Ack Monitor): agent, runtime, model, context, activity, acks, a Rules column and an Inbox column. Generic.
  - `board.html?id=N`. Generic.
  - `periodic.html` and `audio.html`. SEAF.
  - Every page shows an AGENTS bar from `status.json › agent_counts`.
- **:8766 board viewer:** fully generic, the best candidate to lift. Lives at `<game repo>/.claude/worktrees/agent-a7e2fdc280918a661/contrib/board-viewer/` (`server.py`, `heuristics.py`, `static/`, `tests/`, README). Details:
  - PEP 723, stdlib only.
  - Read-only DB access: `mode=ro` + `PRAGMA query_only`.
  - Endpoints: `/api/meta`, `messages`, `message/<id>`, `graph`, `threads`, `topics`, `timeline`, `open-asks`, `merges`, `agents`, and SSE `/events?since=`.

### 4. cmux: how panes are driven and read

- **Subcommands used:**
  - `tree [--all] [--json]`: pane discovery. Lines look like `surface surface:N [terminal] "<title>" ... tty=ttysNNN`.
  - `read-screen --surface S --lines N [--scrollback]`
  - `send --surface S -- "text"`, then `sleep 1`, then `send ... "\r"`. Alternatively `paste --surface S --submit -`.
  - `close-surface --force --workspace W`
  - `set-status`, `list-status`
  - `browser --surface S screenshot|eval`
  - `agent message <surface> --from x`: unreliable.
  - `notify`: owner push notifications.
  - Read-only: `identify`, `capabilities --json`, `sidebar-state`, `top`, `surface-health`, `list-pane-surfaces`.
- **Available but unused:** `new-workspace --layout`, `new-split`, `new-surface --type agent-session --provider codex|claude`, `rename-tab`, `rename-workspace`, `events --name notification.requested`, `codex-teams`, `claude-teams`, `hooks`. Run `cmux --help` and `cmux help <group>` to confirm.
- **Pane-state classifier** (the core of the monitoring; port it as a tested library):

| State | How it's detected |
|---|---|
| working | `Working \(` or `esc to interrupt` (also Thinking, Running); turn age from `Working (Nh Nm` |
| queued | Codex `Queued follow-up` with `↳` lines |
| stalled | a frozen Working timer plus `Messages to be submitted after next tool call`; the fix is one Esc |
| idle | no Working line; last turn end from `Worked for … • H:MM PM` |
| needs approval | `Would you like to (run\|make\|apply)`, `Do you want to`, `(y/n)` |
| stopped | `ps -t <tty>` shows no codex or claude process |
| errored | `Stream disconnected`, `Reconnecting... 5/5` |
| model and context | Claude footer `[Opus\|Sonnet\|Haiku\|Fable N.N]` + `N% used`; Codex footer `GPT-… <effort>` + `Context N% left`; a Codex pane shows `Ask Codex` or `GPT-\d` |

- **Title convention:** tabs are `"<agent> · <task>"`, or `"<task> | <agent>"`. Workspaces are named by lane plus task tag (e.g. `🔊 AUDIO workers · AUDIO-NEXT-1`).
- **Interrupt rules:**
  - Esc only. **Ctrl+C on an empty Codex composer kills Codex.**
  - Codex reads queued input only at turn end.
  - Keep a restart's first paste short ("read PRIME-1"); long first pastes caused broken pipes.

### 5. Agents, runtimes, models, launch

- **Roles:**
  - `claude`: coordinator. Claude Code, the owner's session, Opus. It merges, routes CI failures, runs monitors and pages, and turns owner rulings into rules. It spawns in-session `claude-<task>` subagents (engine work, artreview, pagewatch, ackmon).
  - `supervisor`: Claude Code, Opus 5.5. Assigns work, gives EYEBALL/EAR verdicts, posts CLEARED and digests.
  - `monitor`: Claude Code, Sonnet 5.5, read-only (`claude --model claude-sonnet-5-5 --add-dir … --allowedTools <strict read-only allowlist> -- "$(cat prompts/monitor.md)"`). Posts a TABLES DIGEST every hour.
  - **Workers (Codex):** lanes `an-*` art, `tr-*` terrain, `au-*` audio, `ia-*` image analysis, `rs-*` feature lane, `codex-artist*` leads, `codex-trailer` CI/tooling.
- **Worker models:** GPT-6-Luna medium for most workers; GPT-6.1-Sol medium for codex-trailer. `~/.codex/config.toml` default is `gpt-6.1-sol`, effort medium. Read config.toml yourself; never print secrets.
- **Codex worker launcher** (`team/launch/<agent>.sh`): make a standalone clone (not a worktree, because the Codex sandbox can't write the owner's gitdir) at `/private/tmp/seaf-home/<agent>` on origin/main, then:

  ```
  unset CMUX_SURFACE_ID CMUX_PANEL_ID
  exec codex --sandbox workspace-write --ask-for-approval never --add-dir ~/.codex --add-dir ~/.seaf-agent-board -c sandbox_workspace_write.network_access=true "$(cat team/prompts/<agent>.md)"
  ```

  - Resume: `codex resume <uuid>` with the same flags (INTERRUPT-RECOVERY-1).
  - No `--dangerously-*` flags were used anywhere; keep it that way by default.
  - **Don't carry `--add-dir ~/.codex` into the template by default.** It lets the worker's shell commands write `config.toml`, `auth.json` and hooks. Codex writes its own session files without it. Make it an explicit opt-in launcher flag with a comment saying why.
  - **Workers can write only their own clone and their team's board directory:** `-C $MA_HOME/teams/<team>/workers/<agent> --add-dir $MA_HOME/teams/<team>/board`. Never pass `--add-dir $MA_HOME`: that would let any worker rewrite `$MA_HOME/bin/board.py`, which every agent (the coordinator included) runs, or edit other workers' clones (report 06, METR lessons).
  - The clone root `/private/tmp/seaf-home/` becomes `MA_WORKER_ROOT` (default `$MA_HOME/teams/<team>/workers/`).
- **Worker brief template** (`team/prompts/an-arty.md` + `*-common.md`):
  1. Identity line ("You are '<agent>'… autonomously, no clarifying questions").
  2. Board commands with `--from <agent>`, and times from `date '+%-I:%M %p'`.
  3. Claim the resource (exit code 3 means it's taken).
  4. Work in your own clone and branch; touch only your own files.
  5. Run the local gate, push, post `ready`.
  6. Fix review FAILs.
  7. End with `TASK-DONE: <agent> | <ids> <sha> review PASS`.
  - Post progress every 5 min; never end a turn before TASK-DONE.
- **Restart and recovery docs:**
  - `team/PRIME-1.md`: after a restart, read the board first.
  - `team/REDIRECT-1.md`: after a STUCK50 restart, catch up, diagnose in one line, pick the next step, ACK.
  - `team/CLAUDE-HANDOFF.md` and `team/SUPERVISOR-RESUME.md`: coordinator and supervisor runbooks.
  - `team/RULES-ALL.md`: every rule.
  - `team/idle_hold.json`: parked agents.
  - `team/subagents.json`: in-session subagents.
  - Issue bossjones/superearth_rts_game#424: the current spin-up prompt.
- **Coordinator runtime pattern:**
  - Long-running loops start as Claude Code background Bash (`run_in_background`) or the Monitor tool (`timeout_ms` 1800000, re-armed on each expiry).
  - The Monitor command filters stdout to actionable lines (e.g. `grep --line-buffered -E 'STALE|error|Traceback|INBOX-BACKLOG'`).

### 6. Protocol rules (generic; ship them as a rules reference + templates)

**Board discipline**

- **BOARD-POLL-1:** run `inbox` at every step boundary and at least every 3 min; never block on watch for more than 60 s.
- **INBOX-ZERO-1:** ack everything you read, broadcasts included. At most 10 directed unread, nothing older than 15 min. Over the limit is flagged every 30 min.
- **TALK-FIRST-1:** post before changing anything; ask an asset's owner before touching it; hand off on the board.
- **REVIEW-ADDRESS-1:** review requests go `--to supervisor --kind review_package`, never only to `*`.
- **Identity and time:** post only as yourself; use 12-hour local times.

**Progress and idle**

- **PROGRESS-5-1:** while you own unfinished work, post `<item> | <stage> | <change> | ETA` at least every 5 min.
- **IDLE-RESERVE-1:** when done, post `RESERVE <you> | done | ready for` and ask for work.
- **IDLE-RETIRE-1:** see stale_audit above.
- **Waiting is not idling:** start the next item while waiting on a review.

**Turns, interrupts and restarts**

- **LONGTURN-1:** short turns; turns over 60 min are stopped.
- **STUCK50-1:** silent mid-turn for 30 min is STUCK; at 50 min the agent is restarted with REDIRECT-1.
- **CODEX-INTERRUPT-1:** Esc, then paste STOP / REASSIGN / CLEARED / TIME-CHECK / REWORK. It is now implemented by VERB-1 + LOOK-1 below; never Ctrl+C.
- **COMPACT-IDLE-1:** idle at 50% context or less gets `/compact`.
- **INTERRUPT-RECOVERY-1:** restore a dead agent with `codex resume`.

**Workspace and resources**

- **WORKTREE-ONLY-1 / LAUNCH-WT-1:** never write the owner's checkout; each worker has its own clone.
- **SLOT-1** (generalized from GODOT-SLOT-1): a machine-wide exclusive resource. Implement it with board claims.

**Merging and CI**

- **CI-1:** push, post PR + SHA, move on; don't babysit CI.
- **MERGE-SELF-1 / MERGE-ON-GREEN-1:** merge with `gh pr merge N --merge --match-head-commit <sha>` once review PASS + CLEARED + all checks are green at that exact SHA. Never squash, force, or merge onto a red main.
- **Merge cadence:** after about 3 merges, wait for a green main run. A red main gets a top-priority fix-forward routed to whoever broke it.

**Dashboards**

- **TABLES-1:** periodic digest.
- **CMUX-STATUS-1:** keep your sidebar pill current.
- **PAGE-WATCH-1:** dashboards are health-checked.
- **New-rule procedure:** post the rule, add it to the rule registry, then put it in CLAUDE.md/AGENTS.md by PR.

**Authority, interrupts and escalation** (decided 2026-10-16; evidence in reports 06 and 08)

What the evidence showed:

- Peer coordination worked well: 713 worker-to-worker posts, and 181 of 195 peer requests were read. The owner wants more of it: agents playing off each other, interrupting when needed, and surfacing problems to the human.
- What went wrong was mechanical:
  - two deciders issuing competing orders (IMAGE-25);
  - pastes landing in the wrong pane or sitting unsubmitted;
  - Ctrl+C killing a Codex;
  - one mass order that missed 3 of about 25 panes.

So the plugin encodes a light role model, not a lockdown:

- **AUTH-ROLES-1:** who may send which verb, and through which channel. The matrix lives in `team.json` (defaults below) and in the rules reference.

  | From → to | Board post | Pane interrupt (Esc + paste) |
  |---|---|---|
  | owner | any | any |
  | coordinator / supervisor | any verb | STOP, REASSIGN, REWORK, TIME-CHECK, CLEARED, HALT |
  | worker → worker | ASK, HOLD, HANDOFF | no; ask a lead to interrupt if it's urgent |
  | monitor | status and alerts | RETIRE-CHECK only |

- **VERB-1:** orders are structured posts: `post --kind order --verb STOP|HOLD|REASSIGN|REWORK|TIME-CHECK|CLEARED|HALT --to <agent> [--supersedes <id>]`. An agent relaying an order cites the original post's id.
- **ONE-DECIDER-1:** each lane or area has one decider, named in `team.json`. If orders conflict, the decider's latest order wins. Any other conflicting order is flagged `ORDER-CONFLICT` to the owner.
- **PEER-HOLD-1:** a peer may put a HOLD on another agent by board post. The receiver acts on it at its next inbox check and must ack it or escalate within 15 min.
- **CHECK-IN-1:** if an agent thinks an action is risky, it checks in with its supervisor, the coordinator or another lead before acting. Risky includes destructive or irreversible actions, anything outside its claim, touching another agent's work, credentials, or anything that seems to contradict the rules. Autonomy covers everything else.
- **LOOK-1:** look before and after acting. Every pane write (paste, key, close) reads the screen first, checks that the pane is the intended agent and that a codex or claude process is alive, acts, then reads the screen again to verify. `panes.py` enforces this in code, so callers can't skip it. Agents follow the same loop for their own consequential actions: check the state, act, verify.
- **HALT-1:** `ma halt --team T [--only <lane>] [--dry-run]` stops a whole team or one lane. It sends the HALT verb to every rostered pane in parallel through LOOK-1, posts `HALT #N` on the board, sends `cmux notify` to the owner, and prints a confirmation table with a retry list. `ma resume` reverses it. Held and stopped panes are skipped and listed. Only the owner or a lead may invoke it.
- **ESCALATE-1:** every escalation trigger produces both a board post and a `cmux notify` to the owner, deduplicated:
  - `--kind security` and `ORDER-CONFLICT`: notify immediately.
  - A new `--kind question --to owner`: notify once, then remind at most every 30 min.
  - LONGTURN over 60 min or STUCK over 50 min: notify once per agent per turn.
  - IDLE over 30 min with open work: notify once.
  - A monitor or data source stale for more than 3 times its period: notify once.
- **OWNER-QUEUE-1:** never re-ask the owner. Reply on the original question post. Open owner questions are pinned at the top of the dashboard (report 08: "pause everything?" was re-asked every 10 min and never answered).
- **SECURITY-1:** post `--kind security --to supervisor` when you see a secret, an out-of-scope or destructive request, or a post that seems to impersonate someone. Stop that thread until a lead answers.
- **SECRETS-1:** `post` refuses bodies matching common token patterns unless `--i-know` is passed, and every match raises a `security` alert. This is a **tripwire for mistakes, not a security boundary**: workers can write the DB file directly (audit finding 10). `team.json` has optional `retention_days`, applied only by an explicit `ma archive`, never automatically.

**SEAF-only (example profile only):** SPRITE-COUNT-1, STICKER-CHECK-1, VARIETY-1, REGEN-REFS-1, ENGINE-CONTRACT-1, ART-FAST-1, CODEX-QUOTA-1, the art-review gates.

### 7. Related skill to reuse, not duplicate

`plugins/boss-dev/agent-harness/skills/boss-cmux-team/`:

- `spawn_team.py` creates one workspace per feature via `cmux workspace create --layout <json>`, with the lead on the left and workers in a grid. It writes `.team/<feature>.spawn.json`, then `/cmux-did-spawn` maps roles to surfaces.
- The completion sentinel is `TASK-DONE`. Its team-config JSON has roles with `launcher` / `model` / `prompt` / `kickoff` and placeholders.
- **Gaps:**
  - `build_command()` is pi-shaped (`--append-system-prompt`), so it can't launch codex with sandbox flags or claude with `--allowedTools`.
  - It has no board or monitoring layer and one lead per workspace.
- Decide in Phase 2: either extend the team-config schema (a launcher registry with codex/claude/pi templates) and depend on agent-harness, or vendor a compatible superset. Justify the choice.

## Phase 1: parallel research (spawn subagents concurrently, read-only; each returns a concise report)

| Agent | Research focus |
|---|---|
| **R1, boss-skills conventions** | `CLAUDE.md`, `CONTRIBUTING.md`, `.claude/rules/*.md`, `.claude/commands/create-plugin.md`, `scripts/verify-structure.py` (exact `plugin.json` schema, agent `capabilities` requirement, empty-dir rules), `scripts/skill_validation.py` (16 rules), `scripts/plugin_eval/**/harness_portability.py` (Codex rules), `Makefile` (`ci`, `test-*`, eval-ci threshold: `EVAL_THRESHOLD` is 57 and `make eval-ci` runs in CI, so every new skill must clear it), the `plugin.json` schema in `verify-structure.py` (`additionalProperties: False`; the allowed keys don't include `monitors` or `bin`), pytest config (`--import-mode=importlib`, `testpaths = ["tests", "plugins"]`), `devtools/lint.py` path lists (does it lint `plugins/meta/`?), `.github/workflows/ci.yml`, `.pre-commit-config.yaml` (shebang/executable checks, unicode hygiene, rumdl), `publishing.md` (versioning, marketplace sync), `docs/plugins/` page format, the README plugin tables. Use `plugins/boss-dev/agent-harness` (hooks.json, `uv-guard.sh`, PEP 723 scripts, `${CLAUDE_PLUGIN_ROOT}` / `${CLAUDE_SKILL_DIR}`, `userConfig`) as the model. |
| **R2, Claude Code plugin platform** | The three doc URLs above plus anything they link for: the plugin manifest (`userConfig`, `bin/`, monitors, `dependencies`, `channels`), including **which env vars userConfig values reach** (hooks/MCP only via `CLAUDE_PLUGIN_OPTION_*`, or also the Bash tool?), **whether the plugin root path is version-stamped in the cache** (so it changes on every bump), the hook events useful here (SessionStart, Stop, SubagentStop, Notification, PreCompact, PostCompact, UserPromptSubmit), skill frontmatter (`allowed-tools`, `argument-hint`, `disable-model-invocation`), the Monitor tool / background-task model, and how plugins ship executables on PATH. Note version-specific behavior. |
| **R3, Codex compatibility** | The current OpenAI Codex CLI docs (web search): skills (`~/.codex/skills`, `.agents/skills`, SKILL.md format), plugins/marketplace if they exist, AGENTS.md discovery, hooks (`~/.codex/hooks.json`, `[features] hooks`), `codex exec` / `codex resume`, sandbox flags and `--add-dir`, config.toml profiles. Inspect `~/.codex/config.toml`, `~/.codex/hooks.json` and `~/.codex/skills` locally (never print secrets). Output a concrete layout that lets one source tree serve both runtimes **without adding unknown keys to `plugin.json`**: e.g. SKILL.md files that are runtime-neutral, a sidecar such as `.codex-plugin/` or an install script that symlinks skills into `~/.codex/skills`, and an `AGENTS.md` fragment generator. **Also verify these sandbox boundaries,** since the safety model depends on them:<br>• Does `workspace-write` also make `/tmp` and `$TMPDIR` writable? If so, clones and state must not live there.<br>• Can a sandboxed worker reach the cmux socket and so paste into other agents' panes? If so, AUTH-ROLES-1's "workers don't interrupt panes" is convention only; say so in the rules.<br>• Can a `mode=ro` reader open the WAL DB without write access to the `-shm` file? |
| **R4, the live system** | Read `~/.seaf-agent-board/` (bin/agent_board.py, every script in sections 1–2, team/RULES-ALL.md, PRIME-1, REDIRECT-1, CLAUDE-HANDOFF, SUPERVISOR-RESUME, MONITOR-1, prompts/an-arty.md + *-common.md, launch/an-arty.sh, launch/monitor.sh, idle_hold.json) and the board viewer at the worktree path above. Also read the game repo's `CLAUDE.md` § Multi-agent operations and `AGENTS.md` (a fresh clone is at `~/.seaf-agent-board/coordinator/artreview/repo`), and run `sqlite3 -readonly ~/.seaf-agent-board/board.sqlite .schema`. Never open the live DB through `agent_board.py`, because its `connect()` writes. Ignore the zero-byte `board.sqlite3` and `agent_board.sqlite3` stray files. Produce a generic-vs-SEAF table per file, the list of hard-coded values that must become config, and the pane-state regexes with real sample screens: capture a few with `cmux read-screen` if panes are open, or synthesize from the regexes. Reports 07 (dashboards) and 08 (interrupts) in `ai_docs/simonw_enhancements/` already cover the dashboards and interrupt history. Extend them; don't redo them. Also confirm the board's timestamp formats: `messages.ts` is TEXT `%Y-%m-%dT%H:%M:%SZ` and `claims.expires_ts` is REAL epoch seconds. |
| **R5, cmux surface** | Run `cmux --help` and `cmux help <group>` for every group; read the cmux skills in `~/.claude/skills/cmux*` and `agent-harness/skills/boss-cmux*`. Confirm the exact syntax for: `tree --json` shape, `read-screen`, `send` vs `paste --submit`, `send-key`, `close-surface`, `set-status` / `list-status`, `new-workspace --layout`, `new-surface --type agent-session`, `events --name notification.requested`, `notify`, `browser`. Note which work without focus stealing, and which need `CMUX_SURFACE_ID`. `read-screen` needs `--workspace` as well as `--surface` when the caller is in a different workspace; otherwise it silently returns an empty screen (seen 2026-10-16). Confirm that, and what each command returns for an unfocused workspace, because LOOK-1 depends on it. Also confirm `send-key` names (`Escape`, `Enter`) and whether `paste --submit` is reliable enough to replace `send` + `\r`. |

Wait for all five, then write `specs/meta-multi-agent-design.md` summarizing the decisions. Then start Phase 2.

## Phase 2: design (write it to the spec; keep it short)

**Target layout** (adjust to R1–R3 findings):

```
plugins/meta/multi-agent/
  .claude-plugin/plugin.json     # $schema, name "multi-agent", version 0.1.0, skills "./skills/", userConfig: MA_HOME, MA_TEAM (default team), MA_DASHBOARD_PORT, MA_TIMEZONE (same names as the env vars; repo slug lives in team.json)
  README.md
  bin/                           # thin PATH wrappers if supported: mab (board), ma (install/halt/resume/archive/dashboard), ma-monitor, ma-team
  lib/multi_agent/               # importable stdlib package used by every script
    board.py                     # port of agent_board.py (schema, CLI, claims, progress, digest); kinds/topics configurable; order verbs (VERB-1); SECRETS-1 tripwire
    panes.py                     # cmux adapter: tree parse, read-screen, send/paste, close, set-status; classifier with fixtures; LOOK-1 enforced on every write
    halt.py                      # ma halt / ma resume (HALT-1), parallel, built on panes.py, --dry-run, confirmation table
    config.py                    # team resolution + team.json: roster, roles (AUTH-ROLES-1), deciders (ONE-DECIDER-1), lanes, runtimes, models, title rules, rules registry, hold list, exempt titles, paths
    queries/*.sql                # shared SQL used by the dashboard and monitors (and a future Datasette extra); tested against the live DDL
    monitors/{acks,status,stale_audit,pages,ci,inbox,worker_watch,escalate}.py   # each: --once/--watch/--dry-run, one-line stdout events, atomic JSON; escalate = ESCALATE-1 + OWNER-QUEUE-1
  skills/            # dirs prefixed "ma-": Codex skills share one flat global namespace, so bare "worker"/"monitor"/"board" would collide
    ma-board/         SKILL.md   # post/inbox/ack/claim/progress etiquette for ANY agent (runtime-neutral)
    ma-coordinator/   SKILL.md   # spin-up runbook (shells + monitors + re-arm), merge gates, routing, rule procedure; references/ for long parts
    ma-supervisor/    SKILL.md   # assignment, verdicts, CLEARED, digests, hold list
    ma-worker/        SKILL.md   # brief template, BOARD-POLL/INBOX-ZERO/PROGRESS-5/TASK-DONE, claims, worktree-only
    ma-spawn-team/    SKILL.md + scripts/   # launcher registry (codex/claude/pi), clones per worker, prompt files, cmux layout, title convention
    ma-monitor/       SKILL.md   # read-only monitor agent brief + TABLES digest
    ma-recovery/      SKILL.md   # PRIME / REDIRECT / resume / Esc-only interrupts / stuck & stalled playbook
  commands/  (only if they add value beyond skills: e.g. /ma-up, /ma-status, /ma-down)
  agents/    (e.g. board-monitor read-only subagent; needs `capabilities`, avoid names default/worker/explorer)
  hooks/hooks.json  # optional, uv-guard wrapped: e.g. SessionStart prints unread count for $MA_AGENT_NAME in $MA_TEAM; PreCompact/PostCompact reminds to re-read rules.
                    # Hooks fire in EVERY session where the plugin is enabled: exit 0 silently when MA_AGENT_NAME or MA_TEAM is unset, fail open, and
                    # open the DB read-only with a short timeout so a locked board never stalls session start.
  dashboard/        # ONE live dashboard: lifted :8766 viewer + acks health row + AGENTS bar + owner questions; ?team= switcher; SSE
    server.py       #   stdlib, mode=ro + query_only, 127.0.0.1, SQL-side filtering + pagination
    index.html      #   single self-contained file, vanilla JS, no CDN, agent text via textContent only
  templates/        # RULES.md (incl. authority rules), PRIME.md, REDIRECT.md, worker brief, team.json, AGENTS.md / CLAUDE.md fragments
  profiles/seaf/    # the SEAF example: team.json (lanes, roster, models), extra rules, art-review gate as an optional hook-in, no game code
  codex/            # whatever R3 decided (install script / sidecar manifest / AGENTS fragment)
  tests/            # pytest: board concurrency + recipients + acks + claims, classifier fixtures, config validation, monitors --dry-run
                    # conftest.py puts lib/ on sys.path (pytest runs --import-mode=importlib); no test may need cmux, gh or a network (CI is Linux)
```

New top-level dirs (`lib/`, `dashboard/`, `templates/`, `profiles/`, `codex/`) and any new manifest key must pass `verify-structure.py --strict`. If a key such as `monitors` is needed, update that schema and its tests in the same PR.

**Design rules**

- **Configuration**
  - Stdlib only for the core. Every script is PEP 723 `#!/usr/bin/env -S uv run --script` and also runs under `python3 -I`.
  - **`-I` doesn't put the script's directory on `sys.path`.** So `python3 -I lib/multi_agent/board.py` can't `import multi_agent.config` unless the entry script first inserts its own package root (`Path(__file__).resolve().parents[1]`) into `sys.path`. Each entry point does this bootstrap in its first lines, and a test runs every entry point under `python3 -I` from an unrelated cwd.
  - No hard-coded user paths, surface IDs, repo slugs or message IDs. Everything comes from `team.json` + userConfig + env (`MA_HOME`, `MA_TEAM`, `MA_DB`, `MA_AGENT_NAME`).
  - **One precedence chain, implemented once in `config.py`:**
    - DB: `--db` > `MA_DB` > `SEAF_BOARD_DB` > `$MA_HOME/teams/$MA_TEAM/board/board.sqlite`. If none of these resolves, fail with an error that lists the known teams; never fall back to a shared default board.
    - `MA_HOME`: `MA_HOME` > `~/.multi-agent`.
    - userConfig values reach only hooks and MCP (as `CLAUDE_PLUGIN_OPTION_*`, per R2). Treat them as one more env source. Codex workers and plain shells never see them.
  - **Stable tool path.** The plugin cache path changes with each version, and Codex workers can't see the Claude plugin at all. So briefs must not embed `${CLAUDE_PLUGIN_ROOT}`. Add a `ma install` step that copies the CLI to `$MA_HOME/bin/` with mode 0555, owner-only. Briefs and launchers call `python3 -I "$MA_HOME/bin/board.py" …`. Workers get write access only to their team's `board/` dir (see the launcher in §5).
  - Keep the `$SEAF_BOARD_DB` env var as a fallback so the existing board keeps working.
- **Teams and namespacing** (decided 2026-10-16)
  - The owner may run several teams at once, each of any size. A team ID is `<project>-<task-tag>` (e.g. `seaf-AUDIO-NEXT-1`), set by `MA_TEAM` or `team.json`, and validated against `^[a-z0-9][a-z0-9-]*-[A-Z0-9-]+$` or a configured pattern.
  - Each team gets its own tree and **its own board DB**, so the existing schema stays unchanged (no `team` column):

    ```
    $MA_HOME/
      bin/                       # owner-only tools (0555)
      teams/<team>/
        team.json                # roster, roles, deciders, lanes, repo slug, rules registry
        board/board.sqlite       # the ONLY dir workers may write
        workers/<agent>/         # one clone per worker
        state/                   # monitor JSON (panes, acks, status), owner-only
        logs/
    ```

  - The team ID ties the work together so a human can trace it. cmux workspace titles start with `[<team>]`, tabs stay `"<agent> · <task>"`, and every monitor event line and `cmux notify` carries the team ID. The dashboard picks a team with `?team=`.
  - Monitors, `ma halt` and the dashboard act on exactly one team unless given `--all-teams`. Agent names only need to be unique within a team.
  - The existing SEAF board joins as a team through `SEAF_BOARD_DB` or `MA_DB` (read-only checks only; see Phase 4).
- **Board**
  - Backward compatible with the existing `board.sqlite` (same tables, same CLI flags), so the SEAF board can be pointed at it unchanged.
  - **No implicit schema changes.** Run DDL and `journal_mode=WAL` only from `init` (and an explicit `migrate` if one is ever needed), never on every open. The plugin adds no tables to an existing DB. Read-only commands (`inbox` without `--ack`, `thread`, `claims`, `digest` without `--post`) and every monitor or dashboard read path open with `file:…?mode=ro` + `PRAGMA query_only`.
  - Rule registry: rules are board posts or IDs in config, not a dict in code.
- **Monitors**
  - One event per stdout line, with stable prefixes (`STALE`, `INBOX-BACKLOG`, `PAGE-BROKEN`, `STUCK`, `CI`, `MAIN-CI`, `RETIRE`), designed for Claude Code's Monitor tool and plain `tail`.
  - Writes are atomic. Every monitor that writes to panes has `--dry-run`.
  - **Destructive actions are opt-in.** `stale_audit` closes panes, so it defaults to report-only and closes surfaces only with `--apply` (or `team.json` `"auto_retire": true`).
  - The hold list suppresses all pane writes.
- **Safety**
  - Esc-only interrupts. Never send Ctrl+C to Codex.
  - LOOK-1 is enforced in `panes.py`. Each write reads the screen, checks that the title's agent matches the roster and the tty has a live codex or claude process, acts, reads the screen again, and verifies. It retries once and then reports FAILED. It refuses outright on a mismatch. Always pass `--workspace` with `--surface`.
  - Authority follows AUTH-ROLES-1 / ONE-DECIDER-1 (§6). Peers coordinate freely on the board. Pane interrupts come from leads, and risky actions get a CHECK-IN-1 first.
  - Never pkill; close panes only via `close-surface`.
  - Never default to `--dangerously-*` sandbox bypass.
- **Codex parity**
  - Skills are runtime-neutral (no Claude-only tool names in prose; follow `harness_portability.py`).
  - Long content goes in `references/`, keeping SKILL.md under 8 KB.
  - No `!`-backtick patterns in SKILL.md (parser bug #12781). Use `$ command` notation.
- **Dashboard** (decided 2026-10-16; evidence in reports 03 and 07)
  - **One required live dashboard.** The lifted :8766 viewer gains:
    - the acks.html health row per agent: runtime/model, context, activity, acks, rules, inbox, last post, and 🟢/🟡/🔴;
    - the AGENTS bar;
    - open owner questions pinned at the top;
    - a `?team=` switcher.

    It keeps the conversation graph, threads, open asks, merges and the SSE feed. This answers the questions the owner actually watched for: who is talking to whom, who acked whom and when, and who is behind.
  - Pane-derived data comes from **one** panes monitor that writes `teams/<team>/state/panes.json` atomically. Every panel shows how old its data is and turns red when a source is stale for more than 3 times its period. Silent staleness is what broke acks.html: `acks.json` was last written 10-10.
  - Endpoints filter and paginate in SQL (`LIMIT` + `?after=` cursor). They never load every message into Python; the lifted viewer took 0.87–1.8 s per endpoint on 10.7k rows.
  - The page is one self-contained HTML file: vanilla JS, no CDN, no build step. Agent-supplied text goes into the DOM only with `textContent` or `createElement`. No `innerHTML`, `insertAdjacentHTML`, or markdown rendering of post bodies. A lint test is a tripwire; safe DOM construction is the actual contract.
  - Bind `127.0.0.1` by default. The board holds every agent's messages, so a non-loopback bind is an explicit flag.
  - Game pages (periodic, audio, regen) stay in the SEAF profile docs only.
- **Shared SQL** (decided 2026-10-16)
  - Queries live in `lib/multi_agent/queries/*.sql`, shared by the dashboard and monitors.
  - Mind the column types: `messages.ts`, `reads.ts` and `claims.ts` are TEXT `%Y-%m-%dT%H:%M:%SZ`, so compare them with `strftime('%Y-%m-%dT%H:%M:%SZ','now',…)`, never `datetime('now',…)`, whose space separator makes every same-day row pass. `claims.expires_ts` and the `progress` `*_epoch` columns are REAL epoch seconds, so bind a numeric `:now_epoch`.

### Rejected alternatives and read-path rules (decided 2026-10-16)

Evidence for each is in `ai_docs/simonw_enhancements/`. Don't re-propose these during the build without new evidence.

- sqlite-utils on the live board: it has no read-only mode. It ran an UPDATE, created files from mistyped paths, and `enable-fts` added 5 tables and 3 triggers (report 01).
- Datasette `-i` (immutable) on a live DB: it serves stale rows (report 02).
- sqlite-http, sqlite-html and sqlite-tg: sqlite-http makes network calls even from a `mode=ro` + `query_only` connection, and there is no use case for the others (report 05).
- sqlite-wasm dashboards: they need the raw DB file served over HTTP (report 03).
- Vectors or FTS tables inside `board.sqlite`: an implicit schema change (reports 01 and 04).
- An LLM decision API for routing or merge gates: it isn't deterministic, and PR or board text can steer it (report 06).

Rules that follow from these:

- **READ-PATH-1:** nothing in the core, hooks or monitors calls `enable_load_extension(True)` or invokes a third-party SQLite tool. A test greps the package for both.
- **SNAPSHOT-1:** operator recipes (sqlite-utils, `llm -n`, a future Datasette) run only on a snapshot: `sqlite3 -readonly board.sqlite ".backup $SNAP"`. Never run them on the live board, and never publish it.

### Follow-ups (not in v0.1.0)

- Board search with stdlib FTS5 in a sidecar `teams/<team>/state/search.sqlite`, with a LIKE fallback, for the recovery skill: [#77](https://github.com/bossjones/boss-skills/issues/77).
- `ma datasette`: an optional drill-down. Datasette 0.65.5 pinned, run on a snapshot by default, `allow_sql: false`, canned queries generated from `queries/*.sql`, 127.0.0.1, no Datasette plugins (report 02).
- Semantic search (sqlite-vec) as an optional extra. It needs an interpreter that has `enable_load_extension`; sqlite-lembed is unmaintained (report 04).
- A `datasette-multi-agent` plugin, in a separate repo (report 03).

## Phase 3: build (TDD where there's logic)

**Build order and cut line.** This is a lot for one PR, so build in this order.

- **v0.1.0 (must ship):**
  - `board.py` (with order verbs and SECRETS-1), `config.py` (with teams and roles), `panes.py` (with the classifier and LOOK-1), and `halt.py` (`ma halt` / `ma resume`);
  - the `ma install` step and `queries/*.sql`;
  - the `acks`, `status`, `stale_audit`, `inbox` and `escalate` monitors, plus the single panes monitor;
  - **the one live dashboard** (the owner's main window into the team);
  - the seven skills, the templates (including the authority rules), the Codex path, and registration.
- **May slip to a follow-up PR:** the remaining monitors (`pages`, `ci`, `worker_watch`), `profiles/seaf/`, and hooks. The items under *Follow-ups* above are out of scope.

If the session runs long, open the PR at the cut line and list the rest in the final report. Don't half-finish everything.

1. Write the failing tests first:
   - board: recipients incl. comma lists, inbox excludes self, ack idempotence, claim exit 3 + TTL expiry, 32-process concurrent post stress (bounded wall-clock, marked so it can be skipped on slow CI runners, but it runs in `make test-multi-agent` by default);
   - compatibility: open a copy of a DB built with the **original** live DDL and check the port adds no tables, columns or indexes; read-only commands leave the file's mtime and `PRAGMA schema_version` unchanged;
   - every entry point runs under `python3 -I` from a temp cwd;
   - classifier fixtures for every state in section 4;
   - config validation, including team resolution: there is no default board, unknown teams produce an error, and two teams never share a DB or a state dir;
   - monitor `--once --dry-run` against a temp DB;
   - **queries:** every `queries/*.sql` runs against a fixture built from the exact live DDL, with expired and live claims and rows on both sides of each time window. `EXPLAIN QUERY PLAN` shows no full scan of `messages` unless the query is allow-listed;
   - **dashboard:** a stdlib server fixture on an unused 127.0.0.1 port. Every endpoint answers in under 200 ms on a 50k-message fixture. An XSS fixture (a body containing `<img onerror>`) renders as text. The tripwire rejects `innerHTML`, `insertAdjacentHTML` and CDN URLs. Stale sources show as stale;
   - **LOOK-1 and halt:** with a fake `cmux` on PATH, `panes.send_verb` refuses a title or agent mismatch and a dead process, never sends Ctrl+C, retries once and reports FAILED. `ma halt --dry-run` prints the plan and writes nothing. `ma halt` skips held and stopped panes and prints the confirmation table;
   - **authority and escalation:** `post --kind order` requires `--verb`; ORDER-CONFLICT is raised when a non-decider contradicts the decider; owner questions notify once and remind every 30 min or less often; SECRETS-1 blocks a fake token unless `--i-know` is passed and always raises a `security` alert;
   - **READ-PATH-1:** grep the package for `enable_load_extension` and third-party SQLite tool calls.
2. Port and generalize the scripts into `lib/multi_agent`. Keep the CLI-compatible `board.py` so `python3 -I .../board.py post --from x --to a,b ...` works exactly as before.
3. Write the skills: the coordinator skill embeds the spin-up runbook generalized from issue #424 and `CLAUDE-HANDOFF.md`. Then the templates and the `profiles/seaf/` example.
4. Add the Codex path chosen in Phase 2, and a `codex/README.md` with exact install steps.
5. Register the plugin:
   - marketplace entry in `.claude-plugin/marketplace.json` (fields matching `plugin.json`);
   - `docs/plugins/multi-agent.md` with the version header;
   - rows in `README.md` and `docs/plugins/README.md`;
   - a `test-multi-agent` Makefile target added to `ci`;
   - CHANGELOG via the repo's process.

## Phase 4: verify (show the output; don't claim success without it)

- `uv run scripts/verify-structure.py --strict`
- `uv run scripts/skill_validation.py` (or the repo's equivalent)
- `make eval-skill SKILL=...` for each new skill, then `make eval-ci`. CI fails if any skill scores below `EVAL_THRESHOLD` (57).
- `make test-multi-agent`, `make lint`, `pre-commit run --all-files`
- `claude --plugin-dir plugins/meta/multi-agent` smoke test:
  - The skills are listed.
  - On two temp teams, `board init` + `post` / `inbox` / `ack` round trips stay isolated per team.
  - One monitor `--once --dry-run` works.
  - The dashboard serves `index.html?team=<t>`.
  - `ma halt --team <t> --dry-run` against a throwaway cmux workspace shows the plan. The workspace runs 2–3 idle `codex` and `claude` sessions started just for this test; plain shells would be refused by LOOK-1, because they have no agent process.
  - A real `ma halt` / `ma resume` on that workspace (never on live agents) verifies every pane with read-screen.
- **Codex smoke test (manual; uses model calls, never in CI):**
  - A temp `CODEX_HOME` has no `auth.json`, and copying credentials is off-limits. So check discovery without a model call where possible (e.g. install into a temp project's `.agents/skills/` and list the skills).
  - Then run one `codex exec "use the ma-board skill to post a test note"` with the real `CODEX_HOME` and `MA_DB` pointed at a temp DB.
  - Confirm afterwards that `~/.codex/config.toml` is unchanged.
- **Read-only check against the real board:** `MA_DB=~/.seaf-agent-board/board.sqlite <plugin> inbox --for claude --all | head`. Don't pass `--ack`; never post to it during tests. First record `stat -f %m` of `board.sqlite` and `sqlite3 -readonly … 'PRAGMA schema_version'`, and confirm afterwards that the schema version is unchanged. Normal WAL writes from live agents can move mtime, so compare it only if the board is idle.

## Constraints

- Don't modify `~/.seaf-agent-board/` or any game repo; read only.
- Don't commit secrets, board DBs, screenshots or movie frames.
- Conventional Commits with scope `multi-agent` and a version suffix, e.g. `feat(multi-agent): initial plugin (v0.1.0)`. Branch `feature-multi-agent-system`. Merge commits only, no force-push. Open a PR when green and stop for review.
- Use 12-hour times in any user-facing text.

## Final report

List:

- files created;
- design decisions (reuse vs vendor of boss-cmux-team, Codex packaging);
- verification output;
- what's left for the owner: e.g. migrating the live SEAF setup onto the plugin, and the read-screen fixtures that couldn't be captured.
