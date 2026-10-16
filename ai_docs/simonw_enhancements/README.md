# Simon Willison ecosystem: research for the multi-agent plugin

Research into whether Simon Willison's SQLite and Datasette projects (plus related articles) help the planned
`plugins/meta/multi-agent` plugin specified in
[`specs/meta-multi-agent-authoring-prompt.md`](../../specs/meta-multi-agent-authoring-prompt.md).
Each report judges fit only for that plugin and lists its sources in an appendix.

| # | Report | Headline verdict |
|---|---|---|
| 01 | [sqlite-utils](01-sqlite-utils.md) | Optional operator recipe on a snapshot only; never on the live board (no read-only mode) |
| 02 | [Datasette core, SQL queries, datasette-explain](02-datasette-core.md) | Optional drill-down extra only; custom viewer stays the required dashboard; never `-i` on a live DB. Query time-filter bugs fixed after audit |
| 03 | [Datasette plugin template and simonw/tools](03-datasette-plugins-and-tools.md) | Adopt single-file HTML dashboards and stdlib server test fixture; Datasette plugin later, separate repo |
| 04 | [sqlite-vec, sqlite-lembed, semantic search](04-sqlite-vec-and-lembed.md) | Stdlib FTS5 sidecar search is feasible (vectors optional, extension loading blocked on default interpreters). **Timing disputed**: 01 and the audit say defer; decided in the spec review |
| 05 | [sqlite-http, sqlite-html, sqlite-tg](05-sqlite-http-html-tg.md) | No fit; sqlite-http bypasses read-only guarantees |
| 06 | [llm-openai-decisions and the METR Hugging Face incident](06-llm-decisions-and-metr-incident.md) | Decisions API at most optional; METR lessons drive several safety rules |
| 07 | [Existing SEAF dashboards](07-existing-dashboards.md) | What the owner actually used the HTML pages for, and what the plugin must keep |
| 08 | [Interrupts and peer coordination](08-interrupts-and-peer-coordination.md) | How interrupts, peer work and escalation really went in the SEAF run; basis for the authority rules |

The Codex audit of all reports is in [`audit.md`](audit.md). It found 15 findings, 5 of them high severity. It ran as `gpt-6-luna` (pane footer "GPT-6-Luna medium"), though its header says GPT-6.1.

## Post-audit status

- **Fixed in 02:** `active_claims` now compares REAL `expires_ts` against the numeric `:_now_epoch`. The time filters use `strftime('%Y-%m-%dT%H:%M:%SZ', …)` to match the board's ISO `T…Z` timestamps. A plain `datetime('now')` uses a space, so every same-day row passed the filter (verified with sqlite3).
- **Audit caveats:**
  - The audit's statement that report 07's sources were "inaccessible" is wrong. They are local files on the owner's machine; the auditor didn't open them.
  - It re-ran only the schema check and the FTS5/extension probe.
- **Decided in the spec review (2026-10-16)** and recorded in `specs/meta-multi-agent-authoring-prompt.md`:
  - Per-team namespaces, each with its own DB. Workers can write only their team's `board/` directory.
  - A role-based authority model. Peers coordinate freely; leads interrupt panes; agents check in with a lead before risky actions.
  - LOOK-1 enforced in code, with `ma halt` / `ma resume` in v0.1.0.
  - Escalation through both the board and `cmux notify`, with an owner question queue.
  - SECRETS-1 as a tripwire only.
  - One live dashboard, with SQL-side pagination and shared tested `.sql` files.
  - Rejected alternatives and read-path rules written into the spec.
- **Deferred:**
  - FTS search, tracked in [#77](https://github.com/bossjones/boss-skills/issues/77).
  - `ma datasette`, semantic search, and a Datasette plugin.
- **Not adopted as proposed:** report 06's "board posts are never instructions" and "monitors paste fixed templates only". The owner wants agents to direct and interrupt each other, and report 08 supports the role-based model instead.
