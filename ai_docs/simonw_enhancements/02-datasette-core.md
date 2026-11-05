# Datasette (core, SQL queries, search, datasette-explain)

**Verdict:** keep the hand-built stdlib :8766 viewer as the core. Offer Datasette as an optional `ma datasette` extra **alongside** it, serving in plain (mutable, `mode=ro`) mode and **never with `-i`**, and driven by canned queries that share their SQL with the viewer. datasette-explain is a dev-time nicety and isn't worth shipping.

Legend: **[ran]** = I ran it against a throwaway DB on 2026-10-16; **[doc]** = read in the docs or source; **[inf]** = my inference.

## What it is

- An ASGI web app (uvicorn) that turns SQLite files into a browsable site plus a JSON API, with arbitrary read-only `SELECT`s and named "canned queries". Stable is **0.65.5 (PyPI, 2026-09-17)**. The 1.0 line is still alpha (**1.0a41, 2026-09-24**). Apache-2.0. [doc]
- `requires_python >=3.10` (0.65.5). It depends on about 20 packages (uvicorn, Jinja2, httpx, PyYAML, pluggy, asgi-csrf, janus, ...). `uvx datasette` installed **28 packages, about 22 MB**. [ran]
- Defaults: binds **127.0.0.1:8001**, no auth, anonymous `execute-sql` **allowed**, `sql_time_limit_ms` 1000, `max_returned_rows` 1000, `Cache-Control: max-age=5`. [doc] [ran]
- Search is FTS3/4/5 only, over FTS tables that **you** create beforehand (`?_search=`). Datasette never creates them. The docs search for "semantic" returned nothing, and so did the datasette.io plugin directory. [doc]
- datasette-explain **0.2.2 (2026-09-20)**: a SQL-editor JS helper plus a route that runs `EXPLAIN` / `EXPLAIN QUERY PLAN` on each keystroke and lists the tables a query touches. [doc] [ran]

## Fit for the multi-agent plugin

| Idea | Plugin component | Verdict | Why |
|---|---|---|---|
| Replace the :8766 viewer with Datasette | dashboard/ | **No fit** | It has no SSE, no live push, no thread graph or timeline UI, and it isn't stdlib-only. The viewer already exists, is generic and stdlib-only. |
| `ma datasette` ad-hoc explorer next to the viewer | dashboard/, `ma` CLI | **Optional extra** | It gives free table browsing, facets, filters and CSV export over all 4 tables for one `uvx` command, at zero core weight. |
| Serve with `-i` (immutable) | dashboard | **No fit (forbidden)** | [ran] It **never** saw new rows: 5 rows stayed 5 after 3 WAL inserts, and still after `wal_checkpoint(TRUNCATE)`. SQLite's `immutable=1` also risks wrong results on a changing file. |
| Plain mode on a live WAL DB | dashboard | **Adopt (for the extra)** | [doc] The source opens `file:…?mode=ro`. [ran] It saw new WAL rows at once (5→8), and a checkpoint from another process still succeeded. |
| Canned queries: open asks, inbox backlog, stale agents, live claims | dashboard extra and viewer SQL | **Adopt now (as shared .sql files)** | [ran] All four ran over `/board/<q>.json?...&_shape=array`. The plugin owns the SQL either way. |
| JSON API as the monitor data source | monitors/ | **No fit** | Monitors must be stdlib and must work with no server running. Direct `mode=ro` SQLite is simpler and has no HTTP hop. |
| Writable canned queries (e.g. ack from the UI) | board | **No fit** | They'd open a non-ro write connection (`qs=""` in `Database.connect`). That breaks "read paths strictly read-only". |
| `allow_sql: false` lockdown | dashboard extra | **Adopt (for the extra)** | [ran] With it, `?sql=` returns 403 and canned queries still work, so only reviewed SQL runs. |
| `datasette publish` | anything | **No fit** | It uploads the DB to Cloud Run or Heroku, and the docs warn crawlers can index every row. The board holds every agent's messages. |
| FTS `_search` over `messages.body` | board viewer search | **Later** | It needs a `messages_fts` table plus triggers. That's a schema change, which the spec forbids on existing DBs. Only an opt-in `ma migrate` could add it. |
| datasette-explain | authoring canned queries | **Later / dev-only** | [doc] Its `/explain` route doesn't check `execute-sql`. `sqlite3` with `EXPLAIN QUERY PLAN` in a test gives the same plan check using only the stdlib. |

### Against the owner's three questions (acks.html and the :8766 viewer are the main window)

| Question | Datasette (core, no plugins) | Hand-built pages | Winner |
|---|---|---|---|
| How do agents talk to each other (conversation graph)? | A canned query gives a `sender → recipient, n, last_ts` **edge table**. [ran] The comma-recipient split uses `json_each`. It can't draw a node graph, and it can't follow a thread visually beyond a recursive-CTE table. | `/api/graph` plus a static graph UI and threads | **Hand-built** |
| Who acked whom recently? | A canned query over `reads ⋈ messages` gives `agent, acks, last_ack_ts, acked_senders` for the last N min. [ran] The result is a sortable, filterable table, but it has no colour cues and no auto-refresh. | acks.html Acks/Inbox columns, AGENTS bar | **Hand-built for at-a-glance**, Datasette for drill-down |
| Who is falling behind (backlog, staleness)? | The `inbox_backlog` and `stale_agents` canned queries answer it exactly. [ran] But nothing re-polls: you reload the page, and there's 5 s of caching. | Live (SSE / 20 s `status.json`), thresholds coloured | **Hand-built** |

So Datasette doesn't replace the owner's window: it answers each question only as a static table. What it's good for is the follow-up step: "show me every unacked directed message to w7 since 2 PM", via facets and `?recipient__contains=w7`, with no new endpoint code. That supports keeping it as an **optional drill-down extra**, linked from the viewer, with the edge and acks SQL added to the shared `queries/` set:

```sql
-- conversation_edges
select m.sender, trim(j.value) recipient, count(*) n, max(m.ts) last_ts
from messages m, json_each('["' || replace(m.recipient, ',', '","') || '"]') j
where m.recipient != '*' group by 1, 2 order by n desc;
-- recent_acks
select r.agent, count(*) acks, max(r.ts) last_ack_ts, group_concat(distinct m.sender) acked_senders
from reads r join messages m on m.id = r.message_id
where r.ts >= strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-' || cast(:minutes as integer) || ' minutes') group by r.agent;
```

## Proposed spec changes

**1. Phase 2 → Design rules → Board: ban immutable readers.** Add: "Never open the board with `immutable=1` (or `datasette -i`): it doesn't see WAL writes. Read paths use `mode=ro` + `PRAGMA query_only`." Datasette's own `mode=ro` connections do **not** set `query_only` [doc, source]. That's acceptable only when `allow_sql: false` is set and no writable canned queries exist.

**2. Phase 2 → layout: shared query files.** Add `lib/multi_agent/queries/{open_asks,inbox_backlog,stale_agents,active_claims}.sql`. The viewer's `/api/open-asks` and the `inbox`/`status` monitors load them with stdlib `sqlite3`. A test runs `EXPLAIN QUERY PLAN` on each one against a fixture DB built from the live DDL. That replaces datasette-explain.

**3. Phase 2 → Dashboard: optional `ma datasette` subcommand (may slip to the follow-up PR).** The subcommand:

- generates `metadata.yaml` from those `.sql` files
- runs `uvx --from 'datasette==0.65.5' datasette serve "$MA_DB" -m <generated> -h 127.0.0.1 -p 8767 --setting sql_time_limit_ms 2000`, pinned
- refuses `-i`, `--cors` and any non-loopback host unless `--bind-public` is given
- prints a clear message and exits 0 if `uvx` is missing

It's documented as an extra and is never a dependency of the core. Here's the sample I ran, against the spec's `messages`/`reads`/`claims` columns:

```yaml
allow_sql: false            # 0.65.x: top-level metadata key; ad-hoc ?sql= -> 403
databases:
  board:
    queries:
      open_asks:
        sql: |-
          select m.id, m.ts, m.sender, m.recipient, m.kind, m.topic, substr(m.body,1,200) body
          from messages m
          where m.kind in ('request','question')
            and not exists (select 1 from messages r where r.reply_to = m.id)
            and m.ts >= strftime('%Y-%m-%dT%H:%M:%SZ','now','-' || cast(:hours as integer) || ' hours')
          order by m.id desc
      inbox_backlog:   # INBOX-ZERO-1: directed (non-'*') unread per agent
        sql: |-
          with agents as (select distinct sender agent from messages),
          directed as (
            select a.agent, m.id, m.ts from agents a join messages m
              on m.recipient != '*' and m.sender != a.agent
             and (',' || replace(m.recipient,' ','') || ',') like '%,' || a.agent || ',%'
            where not exists (select 1 from reads r where r.message_id = m.id and r.agent = a.agent))
          select agent, count(*) unread, min(ts) oldest_unread_ts from directed
          group by agent order by unread desc
      stale_agents:
        sql: |-
          select sender agent, max(ts) last_post_ts from messages group by sender
          having max(ts) < strftime('%Y-%m-%dT%H:%M:%SZ','now','-' || cast(:minutes as integer) || ' minutes')
      active_claims:
        sql: select resource, owner, note, ts, expires_ts from claims
             where expires_ts > :_now_epoch order by expires_ts
```

Caveats [inf]:

- **Corrected after audit (2026-10-16):** the live DDL has `messages.ts`/`reads.ts`/`claims.ts` as TEXT written by `agent_board.py now()` as `%Y-%m-%dT%H:%M:%SZ` (ISO-8601 with `T` and `Z`), and `claims.expires_ts` as REAL epoch seconds. So the time filters above use `strftime('%Y-%m-%dT%H:%M:%SZ', 'now', …)`. A plain `datetime('now', …)` returns `YYYY-MM-DD HH:MM:SS` with a space, and because `'T' > ' '` every same-day row would pass. `active_claims` compares against the numeric `:_now_epoch`. Add a fixture test with expired and live claims plus rows on both sides of each window.
- `inbox_backlog` is O(agents × directed messages). Benchmark it on a copy of the 10.7k / 129k-row DB.
- The `_now_*` magic parameters work only in canned queries [doc].

**4. Version note (Phase 3).** Pin 0.65.x. Under 1.0a, the same block moves into `datasette.yaml`, passed with `-c` (0.65.5 has no `-c` [ran]). 1.0a41 also adds `--default-deny` [ran], which is the better lockdown once 1.0 is final.

**5. Phase 4 verify.** Add a check that starts `ma datasette` against a fixture DB, writes a row from another process, and asserts the canned-query JSON count increases. Also assert that `/board.json?sql=select+1` returns 403.

## Risks and costs

- **Dependency weight:** 28 packages and about 22 MB in the uv cache, plus a network fetch on first `uvx`. That's fine for an extra and unacceptable in the core. [ran]
- **Cache staleness:** the default `max-age=5` means browser views can lag by up to 5 s. Use `--setting default_cache_ttl 0` for a live board. [doc] [ran header]
- **No `query_only`:** the read connections are only `mode=ro`. Any third-party plugin that calls `execute_write` would open a real write connection, so the plugin should ship with no Datasette plugins enabled. [doc, source]
- **Security defaults:** anonymous `execute-sql` is on by default. Without `allow_sql: false`, anyone who can reach the port can run arbitrary SELECTs over every agent's messages. Loopback-only is the default, but `--cors` or `-h 0.0.0.0` would expose it. [doc]
- **Two UIs to maintain:** limited by generating the Datasette metadata from the same `.sql` files. [inf]
- **1.0 churn:** config, permissions and the write API are still moving across 1.0a releases. [doc]
- **WAL side files:** like any `mode=ro` reader, it needs write access to the `-shm` file in WAL mode. That's the same as the hand-built viewer. [inf, SQLite behaviour]

## Appendix: references

- <https://github.com/simonw/datasette:> Apache-2.0, "requires Python 3.11 or higher" (main branch). The README lists no release.
- <https://docs.datasette.io/en/stable/:> table of contents. The changelog's newest entry is 0.65.5.
- <https://docs.datasette.io/en/stable/sql_queries.html:> canned queries, `:named` params passed as strings, `write: true`, magic parameters, `.json`, the PRAGMA ban.
- <https://docs.datasette.io/en/stable/ecosystem.html:> sqlite-utils and Dogsheep. Nothing on live updates.
- <https://docs.datasette.io/en/stable/search.html?q=semantic&check_keywords=yes&area=default:> rendered with **no results** (client-side search). I followed it to the full-text page.
- <https://docs.datasette.io/en/stable/full_text_search.html:> FTS3/4/5 detection, `_search`, `fts_table`. No semantic search.
- <https://github.com/simonw/datasette-explain:> what the plugin does and how to install it.
- <https://docs.datasette.io/en/stable/performance.html:> `-i` disables locking and change detection and assumes the file is unchanged. `default_cache_ttl` is 5 s.
- <https://docs.datasette.io/en/stable/json_api.html:> `_shape` (arrays, objects, array, `array&_nl=on`, arrayfirst, object), `_size`, `_ttl`, `--cors`.
- <https://docs.datasette.io/en/stable/authentication.html:> no auth by default, `execute-sql` allowed by default, `--root`, `allow_sql`.
- <https://docs.datasette.io/en/stable/cli-reference.html:> default host 127.0.0.1, port 8001, `-i`, `--nolock`, `--get`. `publish` targets are cloudrun and heroku.
- <https://docs.datasette.io/en/stable/metadata.html:> `databases.<db>.queries` in YAML.
- <https://docs.datasette.io/en/latest/configuration.html:> the 1.0 `datasette.yaml` layout with `settings`, `allow` and `queries`.
- <https://docs.datasette.io/en/stable/publish.html:> cloud upload, crawler warning. That rules it out.
- <https://docs.datasette.io/en/stable/settings.html:> `sql_time_limit_ms` 1000, `max_returned_rows` 1000, `num_sql_threads` 3.
- <https://datasette.io/plugins?q=semantic:> "No matches found".
- <https://pypi.org/pypi/datasette/json> and <https://pypi.org/pypi/datasette-explain/json:> versions, upload dates and `requires_dist` (fetched via curl).
- Local source, `datasette/database.py` (0.65.5): `connect()` uses `?mode=ro` when mutable, `?immutable=1` with `-i`, and no query string for writes.
- Local source, `datasette_explain/__init__.py` (0.2.2): the explain route runs with no permission check.
- Experiment files: `/private/tmp/claude-501/simonw-research/datasette/` (board.sqlite, metadata.yaml, datasette.yaml, logs). All servers on 127.0.0.1:8771–8773 were killed.
