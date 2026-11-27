# Codex audit of simonw_enhancements

Model: GPT-6.1. Date: 2026-10-16.

## Summary

| Report | Accuracy (ok / minor / major issues) | Verdicts sound? (yes / partly / no) | Top issue |
|---|---|---|---|
| README.md | minor | partly | It repeats report 04's FTS5 recommendation as a firm “adopt now” despite report 01 saying defer and the core spec's narrow scope. |
| 01 sqlite-utils | minor | partly | Its FTS sidecar pipeline is a plausible optional recipe, but claims are mostly un-reproduced here and its recommendation invites a new search feature not requested by the spec. |
| 02 Datasette core | major | no | `active_claims` compares numeric `expires_ts` to a likely text parameter; more broadly, reports don't establish a safe read-only path for Codex sandbox access to a WAL database. |
| 03 Datasette plugins/tools | minor | yes | The main verdict is reasonable; some claimed upstream snapshots/counts are point-in-time and not independently reproduced in this audit. |
| 04 sqlite-vec/lembed | major | partly | The “every interpreter” FTS claim is overstated and proposes a sizable core search feature outside the spec; extension loading is a distinct issue. |
| 05 sqlite-http/html/tg | minor | yes | Rejection is sound; source versions are dated and two Observable sources were not fetched successfully by the report. |
| 06 LLM Decisions/METR | major | partly | Useful safety mapping, but proposed sender checks and secret scans are not security controls when workers can write the shared SQLite file directly; proposed halt also has broad destructive effects. |
| 07 existing dashboards | minor | partly | Useful feature inventory, but substantial “verified” claims rely on inaccessible local game-repo/session artifacts and aren't independently auditable from this checkout. |

## Findings

1. **Report 02, proposed Datasette canned queries (`active_claims`). Severity: high.**
   - **Claim:** `expires_ts > :now` is included as a working query, with a caveat that the column might be text or epoch.
   - **Evidence:** `sqlite3 -readonly ~/.seaf-agent-board/board.sqlite .schema` reports `expires_ts REAL NOT NULL`; `ts` is `TEXT`, and `progress.ts_epoch` is `REAL`. SQLite's storage-class comparison makes a text ISO timestamp parameter sort above numeric values, so a numeric expiry compared to text can include expired claims. The report's suggested `_now_epoch` is also not shown in the SQL block and Datasette's magic parameter name needs version-specific confirmation.
   - **Correction:** Bind a numeric epoch (`:now`) and compare `expires_ts > :now`; add a fixture test with both expired and live claims. Keep timestamps and epoch columns distinct throughout all queries.

2. **Report 02, Datasette extra and read-only safety. Severity: high.**
   - **Claim:** Plain Datasette mode on the live WAL DB is safe to “adopt,” because it opens `mode=ro` and sees writes.
   - **Evidence:** Report's own appendix says its read path does not set `PRAGMA query_only`; its risks section acknowledges a plugin's `execute_write` can open a writable connection. The spec requires read paths to be read-only and flags that opening a WAL DB may create/update `-shm`/`-wal`; Codex needs write access to the board directory. Datasette's CLI/docs describe `-i` separately and default loopback host; the cited [Datasette CLI reference](https://docs.datasette.io/en/stable/cli-reference.html) does not itself establish safe Codex sandbox filesystem semantics.
   - **Correction:** Treat the Datasette live-board proposal as unproven and outside core. If retained as an optional extra, test with the actual sandbox and WAL fixture, enforce `allow_sql: false`, ship no write-capable plugins, and document that the reader may require directory write access for WAL sidecars. Prefer a snapshot for an operator drill-down.

3. **Report 02, stale-agent query. Severity: medium.**
   - **Claim:** `max(ts) < datetime('now', ...)` identifies stale agents.
   - **Evidence:** Live DDL confirms `messages.ts TEXT`, not its encoding. This audit did not inspect the canonical board writer's timestamp formatter, and the report itself marks format as assumed.
   - **Correction:** Confirm `bin/agent_board.py` writes lexically sortable UTC timestamps and add a fixture asserting timezone/format behavior before adopting this query. Do not leave this assumption in a “shared canned SQL” contract.

4. **Report 04, FTS5 availability and core adoption. Severity: high.**
   - **Claim:** “FTS5 is compiled into every interpreter I tested,” leading to “Adopt now” and a sidecar search feature in core.
   - **Evidence:** This audit's fresh `python3 -I` check (pyenv Python 3.12.8, SQLite 3.51.0) succeeded creating an FTS5 virtual table, while `hasattr(conn, "enable_load_extension")` was false. These prove FTS5 availability and extension-loading absence only for this interpreter, not every supported host/interpreter. The report's own table lists multiple interpreter distributions; it is not a portability guarantee. Spec says stdlib-only core but does not request search, indexing, duplicate checks, or a `who-knows` command.
   - **Correction:** Phrase FTS as a capability probe with a `LIKE` fallback, run it under supported Python builds in CI, and keep search as a later optional sidecar feature until owners prioritize it. Do not infer FTS5 needs extension loading.

5. **Reports 01 and 04, FTS proposal conflict. Severity: medium.**
   - **Claim:** Report 01 says stdlib FTS5 is “Later” and recommends optional `ma search`; report 04 says sidecar FTS5 search, duplicate detection, and routing are “Adopt now” in core.
   - **Evidence:** Direct comparison of [01](01-sqlite-utils.md) and [04](04-sqlite-vec-and-lembed.md). Both say no FTS/schema objects belong in `board.sqlite`; only the timing/scope differs.
   - **Correction:** Resolve as a product-scope choice. Current spec has no search requirement; the conservative, spec-aligned disposition is defer core search and document a disposable sidecar as a future option.

6. **Reports 01/04, sidecar consistency and implementation caveats. Severity: medium.**
   - **Claim:** An attached read-only board can feed an incremental sidecar without changing the board; report 04 says messages are append-only and max indexed ID is sufficient.
   - **Evidence:** The live schema has no update/delete prevention on `messages`; the report's own sqlite-utils FTS recipe creates triggers and several FTS tables on its target DB. The `id > last` strategy misses edits to prior message bodies and deletions unless immutability is enforced elsewhere. The report only describes append-only behavior; it does not cite a database constraint enforcing it.
   - **Correction:** Either verify and specify the append-only invariant at every writer or rebuild/update changed rows (including delete handling). Keep sidecar writes isolated and test that the board's schema/data remain unchanged.

7. **Report 03, dashboard safety rules. Severity: medium.**
   - **Claim:** A static test rejecting interpolated template-literal `innerHTML` is an adequate guardrail for untrusted message rendering.
   - **Evidence:** The report acknowledges upstream `sqlite-wasm.html` uses `innerHTML` and recommends `textContent`, but the proposed regex only catches one syntactic form; concatenation, `insertAdjacentHTML`, DOM attributes/event handlers, and markdown renderers can still create injection paths. The spec's board bodies are agent-controlled.
   - **Correction:** Make safe DOM construction the actual implementation contract and review all HTML sinks; treat the regex as a narrow lint tripwire, not an XSS test. Keep no-CDN and loopback constraints.

8. **Report 04, semantic extra's Codex sandbox assumptions. Severity: medium.**
   - **Claim:** A semantic extra can fetch a model explicitly and work when wheels are cached; `uv run --offline` was confirmed once cached.
   - **Evidence:** Report's own appendix says extension loading fails on the default `python3 -I`; the spec requires Codex sandboxing and network restrictions are configurable. An offline `uv run` only demonstrates package resolution in that environment, not that native extension loading, model access, and execution work under Codex's actual sandbox or across supported hosts.
   - **Correction:** Keep it separate from core and require a platform-specific compatibility probe plus sandbox test; avoid presenting a cached local run as general Codex parity.

9. **Report 05, extension claim and dates. Severity: low.**
   - **Claim:** Extension wrappers and versions are reported as current; sqlite-html is effectively dormant and sqlite-http permits network calls on a read-only connection.
   - **Evidence:** The report states the Observable intro pages returned HTTP 429 and uses repo docs/releases instead. Its versions are dated 2026-09/2023; current-version assertions are time-sensitive. The read-only database/network side-effect distinction is sound in principle and aligns with its described local probe, but this audit did not load the native extensions.
   - **Correction:** Preserve the “no fit” verdict; label version numbers as checked-on dates and avoid describing the two failed URLs as fully verified by those sources.

10. **Report 06, authority guard and secret scanner. Severity: high.**
    - **Claim:** A `board.py post` sender guard and token-pattern scan reduce impersonation and credential disclosure risk.
    - **Evidence:** The report itself admits workers can write the SQLite DB directly, so sender identity is not authenticated. Regex token patterns are bypassable by encoding/fragmentation; the cited [METR incident report](https://metr.org/hugging-face-incident-report-aug-2026.pdf) describes scanner evasion and unauthenticated board identities (report cites pp. 48, 63–64).
    - **Correction:** Describe both as accidental-mistake tripwires only. Enforce trust at the process/filesystem boundary where possible; never authorize destructive actions from `sender`, `kind`, or body fields alone. Keep human escalation independent of the compromised board.

11. **Report 06, `ma halt` behavior. Severity: high.**
    - **Claim:** An emergency command should broadcast STOP, send Esc plus STOP to every non-held pane, and be adopted now.
    - **Evidence:** The spec says Codex panes can be killed by Ctrl+C and notes queued input behavior; it does not establish that sending Esc and text to discovered surfaces is idempotent, scoped, or safe under stale pane mappings. Report itself says this destructive broadcast needs dry-run and hold-list handling.
    - **Correction:** Defer until command targeting, preview, explicit operator invocation, confirmation/arming, and audit logging are specified and tested. Do not let an LLM/monitor invoke it based on board text.

12. **Report 06, source freshness. Severity: medium.**
    - **Claim:** The API's model availability, beta status, price, speed, and ZDR posture are presented as fixed facts.
    - **Evidence:** These are live product terms and can change. The cited [OpenAI Decisions guide](https://developers.openai.com/api/docs/guides/decisions) is the appropriate primary source, but the report's exact price/model claims are specifically date-bound and not encoded with a checked-on date in each claim.
    - **Correction:** Mark all API/model/pricing/privacy details “checked 2026-10-16,” and verify again before any implementation or operator recommendation. Don't send private pane/board contents to the endpoint by default.

13. **Report 07, evidence provenance. Severity: medium.**
    - **Claim:** Detailed dashboard behavior, owner requests, timestamps, and stale-data state are marked verified.
    - **Evidence:** Appendix points to a game repo under `~/Documents/Cowork Playground/...`, board files under `~/.seaf-agent-board/`, and session JSONL files under `~/.claude/projects/`; those are outside this repo and were not provided for this audit. Some dashboard claims can be corroborated only from those materials, not from report citations with stable URLs.
    - **Correction:** Separate independently reproducible repository facts from owner-local observations, include hashes/commit identifiers for the game repo and exact artifact timestamps, and mark inaccessible material as owner-supplied evidence rather than independently verified.

14. **Report 07 vs report 02, dashboard and query scope. Severity: low.**
    - **Claim:** Report 02 calls Datasette canned queries a current adoption (“Adopt now”), while report 07 says the hand-built viewer needs to remain the primary window and describes direct viewer endpoints.
    - **Evidence:** Report 02's own detailed verdict makes Datasette a separate optional drill-down, while its proposed “shared .sql files” are framed as immediate adoption. Report 07's fit section similarly says Datasette drill-down tables help but custom viewer is still needed.
    - **Correction:** State one scoped decision: keep the custom stdlib viewer as the only required dashboard; shared SQL files are optional refactoring only after queries are validated against the live DDL and operational need.

15. **README, summary accuracy. Severity: low.**
    - **Claim:** The README summarizes report 04 as adopting FTS5 sidecar search now.
    - **Evidence:** This is internally faithful to report 04 but conflicts with report 01's “Later” verdict and the spec's focus on board coordination, monitoring, and dashboards rather than search.
    - **Correction:** Change the synthesized recommendation to “defer; optional disposable sidecar if prioritized,” or explicitly call out the conflict for Phase 2 to decide.

## Cross-report conflicts

- **FTS timing:** 01 defers stdlib FTS5; 04 wants it in core immediately; README repeats 04. The shared safe point is no FTS tables/triggers in the live board. Recommend deferring all search until scoped and portability-tested.
- **Datasette/dashboard role:** 02's headline and proposed query files sound like adoption, while its body and 07 agree the custom viewer remains the main live dashboard and Datasette is only an optional drill-down. Normalize the verdict to optional.
- **Read-only guarantees:** 01 correctly warns sqlite-utils writes and 02 proposes Datasette's `mode=ro`; however, `mode=ro` alone is not equivalent to the spec's `mode=ro` plus `PRAGMA query_only`, and WAL sidecars/sandbox directory access remain operationally relevant. Keep third-party DB tools out of core read paths.
- **FTS versus extensions:** 04's default interpreter lacks `enable_load_extension`, but its FTS5 probe succeeds. Report 05's extension-loading concern should not be generalized to FTS5 availability.
- **Dashboard refresh model:** 02 correctly says Datasette canned query views require reload/cache expiry; 07's core dashboard needs SSE and freshness indicators. A canned-query table does not meet the live health-board requirement.

## Missed options

- **Make schema verification a generated artifact:** check every proposed SQL query against the actual `.schema` fixture, especially numeric `claims.expires_ts`, textual message/read timestamps, and the progress epoch fields. Avoid guessing based on column names.
- **Codex sandbox read-path reality:** test whether the actual read-only viewer can open the live WAL DB under the intended `--add-dir` arrangement without broadening writable shared roots. A `mode=ro` SQLite connection may still need WAL shared-memory access; prefer a consistent snapshot or isolated reader strategy where practical.
- **Read-only snapshots for operator analysis:** report 01 mentions `.backup`; make a snapshot the default for optional sqlite-utils/Datasette/LLM workflows, with clear retention and restrictive file permissions. Never publish the board.
- **Expose stale-source health in UI:** report 07 identifies silent stale JSON and multiple daemon failures; a visible age/health state is more valuable than adding another dashboard framework. If SSE is used, detect disconnect and stale polling explicitly.
- **Data retention/redaction:** the board stores arbitrary agent bodies and can receive credentials. Add retention/redaction and incident response procedures; a regex blocklist alone cannot protect the data.
- **Bound query cost:** report 02 notes O(agents × directed messages), but the proposed canned backlog query and viewer endpoints need limits, pagination, and indexes reviewed against growth; the existing recipient index may not support substring matching of comma-separated recipients.
- **Treat board content as prompt injection:** report 06 recommends authority lists, but all board text must remain untrusted data and not be passed to tools or pasted into panes without fixed templates and explicit human/coordinator policy.
- **Pin only where needed:** exact package pins and native model/extension compatibility belong to deferred extras. They should not pull network installs or opaque native binaries into the stdlib plugin core.

## Checks re-run

| Command | Result | Matches report? (yes/no) |
|---|---|---|
| `sqlite3 -readonly ~/.seaf-agent-board/board.sqlite .schema` | Read-only schema output: `messages.ts TEXT`, `reads.ts TEXT`, `claims.expires_ts REAL`, `progress.ts_epoch REAL`; includes game-specific `image_analysis` and `audio_profile` tables. | yes, for stated generic DDL and claim that game-specific tables exist |
| `python3 -I` in-memory FTS probe (Python 3.12.8 / SQLite 3.51.0): `hasattr(conn,"enable_load_extension")`, `sqlite_compileoption_used('ENABLE_FTS5')`, `CREATE VIRTUAL TABLE ... fts5` | Extension loading unavailable; FTS5 option is 1 and table creation succeeds. | yes, for this interpreter only |
| Opened cited live sources: [sqlite-utils PyPI JSON](https://pypi.org/pypi/sqlite-utils/json), [Datasette CLI docs](https://docs.datasette.io/en/stable/cli-reference.html), [sqlite-vec README](https://github.com/asg017/sqlite-vec), [METR PDF](https://metr.org/hugging-face-incident-report-aug-2026.pdf), [OpenAI Decisions guide](https://developers.openai.com/api/docs/guides/decisions), [simonw/tools](https://github.com/simonw/tools) | Sources loaded; version/API claims are time-sensitive and require point-in-time verification. METR PDF is 91 pages. | yes, sources reachable; not every cited detail independently checked |
| Datasette immutable/WAL experiment, sqlite-utils URI behavior/FTS trigger experiment, native sqlite-http extension, dashboard local artifacts | Not re-run: source report's original temporary files/local game repo are unavailable in this checkout; running these would require installing external tools or accessing unstaged artifacts. | no |
