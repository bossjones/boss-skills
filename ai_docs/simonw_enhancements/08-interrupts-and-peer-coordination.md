# Interrupts, peer coordination and escalation in the SEAF run

Scope: the board (10,727 posts, 2026-10-08 13:54Z to 2026-10-10 22:11Z, 82 senders), the coordinator, supervisor and monitor Claude sessions, and the `~/.seaf-agent-board/team/` docs. **[V]** marks a verified fact (board id, transcript timestamp or doc line). **[I]** marks my inference. Times are UTC unless a post quotes ET.

## Interrupt flows that happened

**Mechanism and authority [V].** Until 2026-10-09 16:13Z, the supervisor could Esc-interrupt a Codex turn only when the owner asked. Monitor digest #3650 showed that TIME-CHECK-1 (#3437, "reply within 5 min") had been queued for 20+ min on 13 Codex workers, with queues 4 to 6 deep and the oldest item 87 min old. Codex drains input only at turn end, and turns ran 1 to 2.5 h. The supervisor escalated this as an A/B question (#3654). One minute later the owner ruled A (#3660), which became standing rule CODEX-INTERRUPT-1 (#3666). The supervisor or claude may Esc and then paste, only for STOP / REASSIGN / CLEARED-merge / owner TIME-CHECK / REWORK. The limit is once per worker per 30 min, and every interrupt is logged on topic `monitor` as `worker | item | reason`. The rule also adds: "workers that poll the board mid-turn don't need interrupting; check that first."

**Volume [V].** The board has 53 logged interrupts (`INTERRUPT <worker>` or `CODEX-INTERRUPT-1 log`), all between 2026-10-09 16Z and 2026-10-10 02Z, with a peak of 14 in the 22Z hour. A few log lines cover several workers at once (#4716 covers 10). After 21Z almost every reason is LONGTURN-1 (a turn over 60 min) or "N min quiet", so interrupts became a liveness tool, not just an urgent-content tool. Elsewhere on the board, STOP appears in 220 posts and REASSIGN in 194. Only 1 and 2 posts respectively *start* with the verb. The verbs sit inside prose such as "11:09 AM ET STOP on scavenger…" (#2997). The supervisor session issued 115 `cmux send-key` calls. The coordinator issued 11 send-keys and 20 `close-surface` calls.

**What went wrong [V]:**

- **Ctrl+C killed Codex.** On 10-09 at 17:22, a Ctrl+C sent to clear an empty composer quit an-charger's Codex. The interrupt paste that followed landed in a bare zsh in the owner's checkout. An open quote left the shell waiting, so nothing ran (#4038). Fix: Esc only; Ctrl+C once, only if queued text is visible.
- **Broken pipe plus a phantom queue.** Codex streams died with "Stream disconnected… Broken pipe" right after resumes (an-charger 13:24 ET, an-scav 13:46 ET). The re-paste then sat under "Messages to be submitted after next tool call" behind a dead turn whose `Working (Nm)` line was frozen. One Esc released it (#4124). ackmon gained a detector for this.
- **Pasted but never submitted.** A fix for codex-artist-2 "sat in its input box without being sent" until the supervisor pressed Enter (supervisor transcript 18:55). On 10-10 at 10:27 a stale instruction stayed unsent in codex-artist's box. It couldn't be cleared safely, so a board note marked it stale.
- **Wrong surface.** On 10-08, Codex sent five cmux messages to a surface in another workspace, and they "sat queued for hours" (coordinator 18:59). Two new Codex panes opened from the supervisor's pane inherited `CMUX_SURFACE_ID` and posted the supervisor's tab id as their own (#957, #960). That is why the launcher runs `unset CMUX_SURFACE_ID CMUX_PANEL_ID`.
- **Lost context after an interrupt.** After the 7:20 PM Esc, ia-1 "spent 16 min hunting for its own clone" and was retired (#6391). After Esc and a catch-up, ia-1 and au-alerts stayed silent for 30 and 115 min and were closed (#6393).

## Stop-everything moments

There was no fleet-wide halt. HALT appears 0 times on the board. Three mass actions served as halts:

1. **ORDERS-1 (10-09 16:43Z, owner-ordered) [V].** The owner said to "cancel in-flight work… resend everything in one message… show me a table of everyone ack-ing" (coordinator 16:40). claude posted #3835 ("This ONE message replaces any older directives still sitting in your input queue") and delivered it within about 2 min (#3862):
   - Esc+paste to 7 workers.
   - Plain paste to 10 idle workers.
   - Queued without Esc for 6 workers that were active and had posted recently.
   - Pasted mid-turn to the supervisor and monitor.

   It was **not delivered** to codex-artist-3 (its composer held typed text and another interrupt was in progress), codex-trailer (paused) or the stale codex-artist tab. Acks: 23 distinct agents within 10 min, 29 in total, the last at 23:39Z (about 7 h later). By 17:15Z ackmon had flagged 4 agents as "acked but quiet 30 min" (#4000-4003).
2. **IMAGE-25-REGEN-1 (10-09 20:24Z) [V].** The supervisor did Esc+REASSIGN on 10 workers (#4716) and pasted the claim map into 13 panes. At the same moment claude built a second map. Each withdrew in favor of the other, and #4718 was restored as final (coordinator 20:24-20:25). This was a near-miss race between two authorities.
3. **Pauses by ruling, not by keystroke [V].** PAUSE TRAILER-2 targeted one worker (#2269/#2270). CODEX-QUOTA-1 (#10558) limited Codex to in-flight items. On 10-10 at 20:21Z the owner asked "should we pause everything?" The supervisor answered with an A/B question (PAUSE-1) and repeated it every 10 min for 40+ min while the watchers kept running. No answer appears.

[I] A real fleet halt would have taken 2+ min of serial pastes, missed busy or dirty composers, and had no single confirmation. Ack completion took hours, not minutes.

## Peer coordination that worked

**[V]** There are 713 worker-to-worker posts out of 6,366 worker posts (11%), and 172 of them are replies. Kinds: 185 status, 160 note, 135 request, 127 answer and 60 question. Of 195 peer requests and questions, 181 were read by the recipient and 74 got a threaded reply, on average 17 min later. Many more were answered without `reply_to`.

- **Lane-lead pipelines.** The densest pairs are terrain workers handing work to an-terrain, the integrator: tr-fire to an-terrain 26 and back 21, tr-ridge 21/19, tr-props 18.
- **TALK-FIRST negotiation.** A worker announces before it acts and the owner of the asset answers. For example: tr-overlay offered titan_hole refs, and an-titan replied 4 min later "post a supplement (don't edit my owner fragment)" (#5509/#5539).
- **Claim handoffs.** 17 peer posts ask for a claim release, for example "please release asset:charger" (#2783).
- **Authority by citation.** 109 peer posts cite a supervisor or claude post id as the authority. Example: "Supervisor #2452 marked e710_pump REWORK" (#2463). Peers relay orders and don't issue their own.
- **Peers correct each other.** "I am no longer assigned to sandbag. Supervisor reassigned it to tr-overlay at #5863" (#6655, 1 min later).

[I] Overall the effect was good. Peers acted quickly on each other's posts, but they deferred to supervisor ids when ownership was at stake. The supervisor sometimes stepped into peer threads to fix a wrong owner (#5667). The one real hazard is a peer relaying a superseded order (next section).

## Escalation to the owner

**Path [V]:** worker → supervisor → claude (the owner's session) → owner, by chat plus `PushNotification`. MONITOR-1 forbids the monitor from contacting the owner "to avoid the conflicting-answer problem from TERRAIN-SAT-1". The board shows 6 OWNER-ESCALATION, 73 OWNER RULING and 30 OWNER DIRECTIVE posts. The coordinator sent 22 push notifications and the supervisor 9. The owner asked for "push notifications, with recommended options" and to be pinged "every hour till I pay attention" (10-08 18:33, 10-09 00:29). The supervisor's tick prompt encoded "push only for a decision, an idle agent you can't revive, red CI you can't route, budget".

**Worked [V]:** CODEX-INTERRUPT-1 went from monitor finding (16:12) to escalation (16:12) to ruling (16:13) to standing rule (16:14).

**Missed or late [V].** Each of these was something the owner saw first:

- "next time you need something surface it to the coordinator in a claude user input notification… I just happened to see your train of thought" (supervisor session 16:47, missing footage).
- Terrain workers had no board monitors running (16:25).
- an-titan's 3h40m turn (17:15).
- "the audio workers look like they're just standing around" (20:18). Ten more art and terrain workers turned out to be idle the same way, because idle Codex never polls.

Blocked posts: 61, with 39 threaded replies (about 13 min on average). Most went to `*` (29), not to a named decider.

## Abuse or confusion seen

No deliberate impersonation was found ("impersonat" and "spoof" return 0 hits). What the board does show:

- **Identity by inherited env.** Panes posted another surface's id (#957).
- **Owner answered twice, differently.** TERRAIN-SAT-1 was answered once to the supervisor (#3108) and once to claude (#3118). The supervisor issued a STOP based on the superseded answer (#3117) and later corrected it (#3270).
- **Order flip-flops.** Audio integrator ownership changed four times in 2 min (#3214→#3219→#3220→#3223). radar_station was reassigned to an-ui, released by codex-artist-2, then reversed by the supervisor 41 s later. codex-artist-2 kept announcing that its release was "complete" (#2792, #2803, #2806, #2813).
- **Peer overreach checked by the peer.** codex-artist corrected its own #246: "does NOT authorize any merge" (#248). It later told claude to wait for the supervisor's CLEAR (#1299).
- **Role guardrail held.** claude asked the read-only monitor to paste ACK-NOW into panes (#7478). The monitor refused, citing its hard block (#7531).
- **Collateral kill.** A `pkill -f` by claude-states killed another worktree's Godot run (#1082).
- **Loops.** PAUSE-1 was re-asked every 10 min; REDIRECT-1 lists "fighting a failing gate in a loop" as a stuck cause.

## Implications for the spec

The evidence supports trusting the board as a command channel. That trust needs authority scoping, a small set of verbs, and look-before-act checks, not "fixed templates only".

- **AUTH-ROLES-1:** Each role has a set of verbs it may send, configured in `team.json`.
  - Owner and coordinator: every verb.
  - Supervisor: STOP, REASSIGN, REWORK, CLEARED, TIME-CHECK, RESUME, RETIRE.
  - Lane lead: STOP and REWORK, inside its own lane.
  - Worker to worker: HOLD (a soft pause on a shared asset), ASK, HANDOFF, RELEASE-REQ.
  - Monitor: none. It sends FLAG to the supervisor only (#7531 precedent).
- **VERB-1:** Interrupt verbs are structured posts with fields `verb`, `target`, `item`, `reason` and `supersedes=<id>`, and they come from a CLI (`ma stop`, `ma reassign`…). Workers obey a verb only if the sender's role allows it. A peer post that cites a supervisor id (`per #2452`) is a relay. The worker checks that the cited post exists and is the latest ruling on that item before acting.
- **LATEST-WINS-1:** Each item has one current ruling. The CLI rejects a REASSIGN or STOP that doesn't name `supersedes` when an earlier ruling on that item exists. `ma ruling <item>` prints the current one (prevents the #2792/#2803 and #3108/#3118 flips).
- **PEER-INTERRUPT-1:** Workers may HOLD a peer on a shared asset by board post only, never by pane keystrokes. Only the supervisor or coordinator paste into another pane. A HOLD that no one has answered for 15 min auto-escalates to the supervisor.
- **LOOK-1:** Every pane write follows read-screen → classify → act → read-screen.
  - Write only when the pane title or agent name matches the target and the composer is empty, or the state is working or idle.
  - After writing, confirm `Working`, or press Enter once if the text is sitting in the composer, or fix a phantom queue with one Esc.
  - Abort, and FLAG the pane, if the screen shows a shell prompt.
  - Never send Ctrl+C on an empty composer. Never use `pkill`.
- **RATE-1:** Keep the 30-min-per-worker interrupt budget, logged automatically by `ma` rather than by hand. A monitor flags a second interrupt within the window.
- **HALT-1:** `ma halt [--lane L | --all] --reason R`. It posts one HALT verb (priority, superseding), then fans out Esc + a short paste ("HALT #id: stop at a safe point, post HALTED") in parallel with LOOK-1. It reports a table of delivered, refused (dirty composer) and HALTED-ack per pane, and re-tries the misses at turn end. It also pauses the destructive monitors (`stale_audit --apply`) and adds everyone to the hold list. `ma resume` reverses it. Target: under 60 s to deliver, with confirmation visible on acks.html.
- **ONE-DECIDER-1:** Owner questions go only through the coordinator, with an id (`Q-<n>`). A ruling is posted once and other agents cite it. A second answer to the same question triggers an automatic conflict post to the owner.
- **ESCALATE-1:** These auto-escalate to the owner (push, A/B, repeated hourly):
  - a blocked post unanswered for 30 min;
  - an agent idle for 30 min with an empty backlog (the case the owner caught first);
  - a needed external input such as footage or credentials;
  - two conflicting rulings;
  - a quota or budget threshold;
  - a HALT left unacked after 10 min.

  An unanswered question to the owner is repeated at most hourly and never blocks the watchers from running.

- **IDLE-WAKE-1:** Idle Codex workers don't poll the board, so any directed post to an idle pane gets a short paste ("inbox: #id") through LOOK-1.

## Appendix: references

**Sessions:**

- Coordinator: `~/.claude/projects/-Users-bossjones-Movies-pixel-art-references/cc5df7aa-1cda-4c83-81aa-ff4cbb538b48.jsonl` (2026-10-08 to 10-16).
- Supervisor: `~/.claude/projects/-Users-bossjones-Documents-Cowork-Playground-superearth-rts-game/05873659-f1b5-4056-8445-8e878e4010a4.jsonl` (10-08 to 10-13).
- Monitor: `~/.claude/projects/-Users-bossjones--seaf-agent-board-team-monitor/36272987-bbba-4f16-89f8-5baa35c7cc3c.jsonl` (found, not mined).

**Team docs:** RULES-ALL.md (§ Turns, interrupts; OVERNIGHT-2), ORDERS-1.md, PRIME-1.md, REDIRECT-1.md, LATEST-1.md, MONITOR-1.md and prompts/monitor.md (§ Escalation, Hard rules), CLAUDE-HANDOFF.md:46, SUPERVISOR-RESUME.md:76-85.

**SQL** (all run with `file:…board.sqlite?mode=ro` + `PRAGMA query_only`):

- `select kind,count(*) from messages group by kind`
- `… where upper(body) like '%STOP%'` (and the same for each verb)
- `… where body like '%CODEX-INTERRUPT-1 log%' or body glob '*PM INTERRUPT [a-z]*' group by substr(ts,1,13)`
- worker-to-worker: `sender glob 'an-*' or 'tr-*' or 'au-*' or 'ia-*' or 'rs-*' or 'codex-*'` on both sides, joined to `reads` and `reply_to`
- `select count(distinct sender) … like '%ACK ORDERS-1%'`
- reply latency for `kind in ('blocked','question')`
- ids cited: 2269, 2463, 2783-2813, 3108-3118, 3214-3223, 3270, 3437, 3650-3666, 3701, 3835, 3862, 4000-4003, 4038, 4050, 4124, 4716, 4718, 5509/5539, 6391/6393, 6655, 7478/7531, 957/960, 1082, 246/248, 10558.
