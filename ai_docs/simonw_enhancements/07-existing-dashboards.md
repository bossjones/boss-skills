# Existing SEAF dashboards: what the owner actually used

**Verdict:** two dashboards exist. One is the `acks.html` family of hand-edited pages on :8765. The other is the generic SSE board viewer on :8766. The owner watched `acks.html` most closely, and an agent wrote on the board (#4719) that the owner watches it. Port the generic questions it answers (activity, acks, inbox, rules, staleness) and the AGENTS bar into the :8766 viewer, so the plugin ships one generic server. Leave the SEAF pages (periodic and audio) out.

Tags: **[V]** means I read it in code, JSON or the session logs, or I ran it on a copy of the DB. **[I]** means it is my inference.

## Questions the pages answer

| Question the owner asked | Page/panel | Data source | Generic or SEAF |
|---|---|---|---|
| How do agents talk to each other? | :8766 **Agent graph** tab: sender→recipient edges sized by count, `*` hub, time-window replay | `/api/graph` (`messages`) | Generic |
| What is this thread about? | :8766 drawer and **Reply threads**; :8765 `board.html?id=N` (parent, post, replies) | `/api/message/<id>`, `/api/threads`; `board_recent.json` (newest 400 only) | Generic |
| Who acked whom, and when? | `acks.html` columns Ack status, Acked, Last read; :8766 feed ACK chips (green when the recipient read it) | `acks.json` (ack_monitor.py, from `reads` + "ACK <ORDER>" posts); SSE `reads` events | Generic |
| Who's behind on their inbox? | `acks.html` **Inbox** column: directed unread count, oldest age, red when over INBOX-ZERO-1 (more than 10, or older than 15 min) | `status.json › inbox[agent]` (`directed_unread`, `oldest_directed_min`, `broadcast_unread_recent`, `over`) | Generic |
| Who is stuck, stalled, stopped, or waiting on approval? | `acks.html` Activity column and status sort order (STALLED/ERRORED/STOPPED/NEEDS APPROVAL/NO ACK first) | `acks.json` rows (`activity`, `activity_detail`, `queued`) from cmux `read-screen` | Generic (needs cmux) |
| Is it Claude or Codex, which model, how much context is left? | `acks.html` Runtime · model and Context columns (red at 15% or less) | `acks.json` (`runtime`, `model`, `context`) | Generic |
| Has everyone read the latest rules? | `acks.html` **Rules read** column, `ok/total` with the missing rules in a tooltip | `acks.json` (`rules_ok`, `rules_total`, `rules_missing`), from hard-coded `RULE_POSTS` ids | Generic idea, hard-coded data |
| How many agents are running, at each level? | **AGENTS bar** on every :8765 page | `status.json › agent_counts` (total, workers, activity, runtime, lanes, subagents) | Generic data, SEAF labels |
| Who has gone quiet? | :8766 **Agents** cards: last-post age green under 10 min, amber 10–15, red over 15 | `/api/agents` (`messages`, `claims`, `progress`) | Generic |
| Is work on track (🟢/🟡/🔴)? | :8766 Agents cards list the latest progress rows (marker, finish range, blockers) | `progress` table; the marker comes from `agent_board.py` (over budget is 🔴, at risk is 🟡) | Generic |
| What's still waiting for an answer? | :8766 **Open asks**, with an "ACKed but unanswered" toggle | `/api/open-asks` | Generic |
| Did merges follow the handshake? | :8766 **Merge handshakes** (intent → ACK → merged) | `/api/merges` | Generic |
| Who claimed what, and are there conflicts? | `acks.html` **Regen claims** panel; :8766 active claims | `status.json › regen`; `claims` table | Panel is SEAF, claims are generic |
| Which assets have had no progress for 5–15 min? | `periodic.html` Progress check / quiet tables | `status.json › regen_progress`, `movie_frames.open_reruns` | SEAF |
| Sprite/audio coverage and verdicts | `periodic.html`, `audio.html` | `verdicts.json`, `audio_index.json`, sticker/image indexes | SEAF |

## How each page works

**:8765 static pages** (`acks.html`, `board.html`, `periodic.html`, `audio.html`) [V]

- Server: `tools/sprite_compare/serve.py`, a stdlib server bound to 127.0.0.1 that sends `Cache-Control: no-store`. It is a sprite viewer. The dashboards are served through its `/movie-frames/<rel>` static route, so they live outside the repo in `~/.seaf-agent-board/movie_frames/`.
- Refresh: polling only. Each page fetches its JSON every 30 s, runs a 1 s ET clock, and some fetches add a `?Date.now()` cache-buster.
- JSON producers: `ack_monitor.py` writes `acks.json` every 60 s (read-only DB plus cmux pane probes every 55 s). `status_sync.py` writes `status.json` every 20 s; it holds `inbox`, `agent_counts`, `regen` and `regen_progress`, plus `board_recent.json`. `verdicts_sync.py` writes `verdicts.json` every 30 s. `page_watch.py` checks the open cmux pages every 120 s and posts PAGE-BROKEN/stale alerts.
- Pain points:
  - **Stale data** [V]. `acks.json` was last written 2026-10-10 22:19Z, but `status.json` is from 2026-10-14. The page still shows that old data without a warning beyond "Data as of". Board #4599: "the :8765 … status.json server and your ack_monitor.py --watch are DOWN since the restart (curl 000)". There were five or more separate daemons to keep alive, and the owner had to say "You also need to pick up all 5 shells and 5 monitors".
  - **Hard-coded values** [V]. `ROSTER`, `RULE_POSTS` (board ids 3835, 4058…), `TITLE_HINT`, `FALLBACK_OWNER` and `REGEN_DONE` are baked into the monitors. `status_sync.py` reads from a `/private/tmp/...scratchpad/wt-viewer-live` path. The AGENTS bar hard-codes its lane names and the line "owner 1 (you) → supervisor 1 → coordinator 1 (claude)". Every page hard-codes `America/New_York` and the GitHub repo URL.
  - **Copy-paste** [V]. The `agentbar-js` block is pasted into all four pages. The pages evolved through hand edits with timestamped backups: `periodic.html` has 10 backups from one day, and `acks.html` grew from 6 columns plus a 6 KB file to 11 columns, a regen panel and 12 KB.
  - **Brittle links** [V]. `board.html` treats a 4–5 digit `#N` as a board id and a 2–3 digit `#N` as a PR. That rule contradicts `heuristics.py`. It also only knows the newest 400 posts.

**:8766 board viewer** (`contrib/board-viewer/`) [V]

- Server: a stdlib `server.py` with all the guessing in `heuristics.py`. Every query opens a `mode=ro` + `PRAGMA query_only` connection. It checks `Host`, has tests, and its static page is vanilla JS with no CDN.
- Refresh: SSE `/events?since=` polls the DB every 1.5 s and emits `messages` and `reads` events, honouring `Last-Event-ID`. Other tabs fetch on demand.
- Data: it reads `messages`, `reads`, `claims` and `progress` directly. It needs no monitor process.
- Timing [V, measured on a copy with 10,727 messages and 129,660 reads, port 18766]: graph, threads and agents took about 35 ms. Open-asks took 0.87 s, merges 1.8 s, and timeline returned 2.9 MB. Every endpoint loads `all_messages()` into Python, so the cost grows linearly with the board [I].
- Gaps [V]: no cmux activity, runtime, model or context; no rules-read status; no per-agent inbox count; no AGENTS bar. `family()` hard-codes the families claude, codex, supervisor, owner and watchdog. The page bound to `/private/tmp` and lived only in a worktree, so it was never merged into the repo.

## Owner requests from session history

Session files are under `~/.claude/projects/`. Times are UTC, and the owner works in ET (UTC−4).

- "how will they pass messages back and forth between each other? should we use something like a sqlite database … like a message board": `-Users-bossjones-Documents-Cowork-Playground-superearth-rts-game/2886575d…jsonl`, 2026-09-14.
- "I also expect you to periodically update with … an overall status table timeline and all that jazz": `…superearth-rts-game/05873659…jsonl`, 2026-10-08.
- "I manually oped <http://127.0.0.1:8765/movie-frames/acks.html> … here's a screenshot of my view": `-Users-bossjones-Movies-pixel-art-references/cc5df7aa…jsonl`, 2026-10-09 17:06.
- "Update the ack monitor I want to know who is claude/codex/model … can we add a current time to the top": cc5df7aa, 2026-10-09 17:09.
- "if theres anything running for a long time in ack, like an-titan which says 3h 40m 20s? have supervisor stop them": cc5df7aa, 17:15.
- "is anyone talking about it on the message board? … who's making sure all workers are compliant and have the latest rules ?": cc5df7aa, 17:59. This request produced the Rules read column.
- "it should include rich links … I want to be able to click on it": cc5df7aa, 19:09.
- "audio.html needs the same level of love as … acks.html and … periodic.html": cc5df7aa, 19:18.
- "200 unread messages is way too many": cc5df7aa, 23:37. This request produced INBOX-ZERO-1 and the Inbox column.
- "audit everyone who is behind on this ack board, force them to ack": cc5df7aa, 2026-10-10 01:47.
- These requests were relayed through the board rather than appearing in the sessions [V, board copy]: "every page shows how many agents are running, at every level" (the AGENTS bar, owner at 4:40 PM, quoted in the page comment); the owner's question about who hasn't updated progress within 5 min (`periodic.html` comment, 2:47 PM); and "so we don't have things going stale again" (#4649, RULES-ALL).

## Must-keep features for the plugin

1. **One per-agent health row**, which is `acks.html` made generic. It shows agent, runtime·model, context %, activity state (from the cmux classifier), ack status, inbox backlog and oldest age, rules read, last post, last read and current task. The page sorts problems to the top, so they show first.
2. **AGENTS bar on every view.** It shows total, working, idle and needs-attention counts, by role and by runtime. Roles and lanes should come from team config, not literals.
3. **Live updates over SSE** from the DB, plus a visible "data as of / source down" banner. This replaces five JSON-writing daemons whose silent failure produced stale pages.
4. **Conversation graph and threads**, with time-window replay and click-to-filter (:8766).
5. **Ack visibility**: read-receipt chips per message, and a who-acked-the-current-order view. The order and rule post ids should come from config or a `rules` tag, not from hard-coded ids.
6. **Staleness and progress**: quiet thresholds (10/15 min, configurable) and the latest 🟢/🟡/🔴 progress rows.
7. **Open asks and merge handshakes.**
8. **Clickable links** for board `#id`s, PRs, agents and SHAs, using one shared resolver (`heuristics.py`).
9. A wall clock in the owner's timezone, set by config.

Leave out: `periodic.html` and `audio.html`, the regen-claims panel, and the verdict pipeline. All of these are SEAF-specific [I].

## Fit with the options in reports 02–04

- **Datasette canned queries (02, 03)** handle drill-down tables well: inbox backlog, stale agents, recent acks, live claims, conversation edges, open asks as SQL, and rules-read counts if rule posts are tagged. All of this is DB-only. Report 02 already ran these queries. A canned query can't do cmux-derived columns (activity, model, context), auto-refresh, colour thresholds, or the AGENTS bar [V for 02's runs, I for the rest].
- **The custom viewer is still needed** for the graph and its replay, SSE live feed, the colour-coded per-agent health row, merge chains (multi-step heuristics), and the cmux probe join. Report 03's "single-file HTML + stdlib server" pattern matches what :8766 already is [I].
- **FTS5 search (04's sidecar, 01's recipe)** fits as a search box in the :8766 Live feed, which today uses `LIKE`-style `q=`, and as a Datasette `_search` once the sidecar exists. It never belongs on the live board schema (01, 02). The owner never asked for search. His questions were all about status [V, from the session grep], so this is low priority.
- **Performance** [I]: if the boards get bigger than SEAF's 10.7k messages, port the open-asks and merges logic to SQL or cache it by max id. The canned queries from 02 can share that SQL.

## Appendix: references

- Spec: `/Users/bossjones/dev/bossjones/boss-skills/specs/meta-multi-agent-authoring-prompt.md` (§3)
- Reports: `ai_docs/simonw_enhancements/01-sqlite-utils.md`, `02-datasette-core.md`, `03-datasette-plugins-and-tools.md`, `04-sqlite-vec-and-lembed.md`, `README.md`
- Game repo (actual path `~/Documents/Cowork Playground/superearth_rts_game`, not `~/dev/bossjones/`): `tools/sprite_compare/serve.py`, `tools/agent_board.py`, `.claude/worktrees/agent-a7e2fdc280918a661/contrib/board-viewer/{server.py,heuristics.py,README.md,static/app.js,tests/}`. Tracked HTML: `tools/sprite_compare/compare.html` and `docs/art-direction/…/index.html`, neither of them a dashboard.
- Board dir: `~/.seaf-agent-board/movie_frames/{acks,board,periodic,audio}.html` and `*.backup-*.html`; `team/acks.backup-1312.html`, `team/periodic.backup-2046.html`; `ack_monitor.py`, `status_sync.py`, `verdicts_sync.py`, `page_watch.py`, `stale_audit.py`, `bin/agent_board.py`; JSON shapes of `acks.json`, `status.json`, `board_recent.json`, `verdicts.json` (keys only).
- DB copy: `/private/tmp/claude-501/simonw-research/dash/board.sqlite` (`.backup` from a `-readonly` handle). I ran the viewer on it on 127.0.0.1:18766, and stopped it afterwards.
- Sessions: `-Users-bossjones-Movies-pixel-art-references/cc5df7aa-1cda-4c83-81aa-ff4cbb538b48.jsonl`, `-Users-bossjones-Documents-Cowork-Playground-superearth-rts-game/{2886575d-7e29-4e86-b928-bd2ae7f46363,05873659-f1b5-4056-8445-8e878e4010a4}.jsonl`. I searched only the owner's messages.
