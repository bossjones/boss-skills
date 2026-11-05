# sqlite-utils

**Verdict:** worth recommending as an optional operator tool run through `uvx`, and useful in tests. It must stay out of the stdlib core and must never be pointed at the live board for anything that writes. FTS belongs in a separate sidecar DB.

Tags: **[V]** means verified (I ran it on a throwaway DB in `/private/tmp/claude-501/simonw-research/sqlite-utils/` or read it in the docs). **[I]** means inference.

## What it is

- A Python CLI and library for working with SQLite: `query`, `rows`, `tables --counts`, `schema`, `memory`, `insert`/`upsert`, `enable-fts`/`search`, `transform`, `analyze-tables`, and plugins. [V]
- Version 4.2.1 is on PyPI (uploaded 2026-08-13). It requires Python >=3.10. It depends on click, click-default-group, pluggy, python-dateutil, sqlite-fts4, tabulate and pip. It is licensed Apache-2.0. [V]
- `query`, `rows`, `search` and `memory` share one set of output flags: JSON (the default), `--nl`, `--csv`/`--tsv`, `--table`/`--fmt`, `--json-cols` and `--arrays`. [V]
- It is built for importing data with schema inference (Willison 2019; Evans 2022 used `insert_all`, `alter=True`, and `upsert_all(pk=...)`). The plugin's board does not need any of this. [V/I]

## Fit for the multi-agent plugin

| Idea | Plugin component | Verdict | Why |
|---|---|---|---|
| Ad-hoc board queries (`query`/`rows --where --table/--csv/--nl`) | operator docs, `ma-monitor`/`ma-coordinator` references | Optional extra | Works well, but has three hazards on the live board [V]: (1) it has no read-only mode, so `query "update ..."` printed `rows_affected: 1`; (2) a `file:...?mode=ro` URI is not parsed and silently created an empty file with that literal name; (3) a mistyped path creates an empty DB. Recommend it only together with `sqlite3 -readonly`, or on a snapshot. |
| `tables --counts`, `schema` | debugging, compat tests | Optional extra | Neither changed `PRAGMA schema_version` (stayed 4) [V]. The core can get the same result with `sqlite_master` plus `count(*)`. |
| `analyze-tables` (without `--save`) | digest/monitor ideas | Later | Shows distinct and most-common values for `topic`/`sender`, and did not change the schema [V]. `--save` creates `_analyze_tables_`, which would violate "adds no tables" [V docs]. The digest gets the same thing from a `GROUP BY`. |
| FTS on `messages.body` in the board | board | **No fit** | `enable-fts --create-triggers` added 5 `messages_fts*` tables and 3 triggers (`messages_ai/ad/au`), and moved `schema_version` from 4 to 12 [V]. That breaks "no implicit schema changes" and "adds no tables". The triggers would also add write cost inside every agent's `post` transaction. [I] |
| FTS in a **sidecar** `search.db` | optional `ma search` recipe | Optional extra | The pipeline `query board --nl \| upsert search.db messages - --nl --pk id && enable-fts search.db messages body topic --replace` worked, and the board's schema stayed 4 [V]. Hyphenated terms need `--quote`: `feat-7` failed with "no such column: 7" without it [V]. |
| Stdlib FTS5 in the core | `board.py search` (future) | Later | `python3 -I` has FTS5 (sqlite 3.51.0) [V]. A core `search` subcommand could build an in-memory or sidecar FTS5 index without any dependency. [I] |
| `transform` for migrations | `migrate` | No fit | It creates `<t>_new_<hash>`, copies the rows, drops the original and renames [V `--sql`]. That is too heavy for a board that live agents hold WAL locks on. The spec wants no schema changes at all. Use `--sql` only to *draft* DDL. |
| Python API in tests | `tests/` fixtures | Optional extra (dev only) | `Database(sqlite3.connect("file:..?mode=ro", uri=True))` together with `PRAGMA query_only` blocked writes ("attempt to write a readonly database") [V]. Handy for asserting schema, but stdlib `sqlite3` is enough, and the repo's test deps would grow. [I] |
| `memory` over `acks.json`/`status.json` | operator debugging | Optional extra | Lets you run SQL over the monitors' JSON outputs, and `--attach` lets you join them with the board [V docs]. In my test, `--attach` with a URI failed like any other URI. [V] |
| Plugins / `--functions` | none | No fit | Nothing on the board needs custom SQL functions. |

## Proposed spec changes

1. **Design rules → Board: add a sentence.** "Third-party SQLite tools (`sqlite-utils`, `datasette`) are never invoked by the core, hooks or monitors." This puts the existing stdlib-only rule in writing for read paths.
2. **New `references/operator-queries.md` (ma-coordinator or ma-monitor skill).** It holds read-only recipes, with `sqlite3 -readonly` first and `uvx` against a snapshot second:

   ```bash
   $ sqlite3 -readonly "$MA_DB" -cmd '.mode table' "select id,sender,topic,substr(body,1,80) from messages order by id desc limit 20"
   $ sqlite3 "$MA_DB" ".backup /tmp/board-snap.sqlite"   # snapshot first; the .backup target is a copy, the source DB is only read
   $ uvx sqlite-utils@4.2.1 rows /tmp/board-snap.sqlite messages --where "topic = :t" -p t merge --order "id desc" --limit 20 --table
   ```

   The recipes carry a warning: sqlite-utils has no read-only mode, does not accept `file:` URIs, and creates a missing path. Point it only at snapshots. [V]

3. **Optional `search` (future; Phase 2 "may slip" list).** `board.py search QUERY [--rebuild]` maintains `$MA_HOME/search.sqlite` with stdlib FTS5:

   ```text
   ro = connect("file:$MA_DB?mode=ro", uri=True); ro.execute("PRAGMA query_only=1")
   side = connect($MA_HOME/search.sqlite)  # separate file, plugin-owned
   side: CREATE VIRTUAL TABLE IF NOT EXISTS m USING fts5(body, topic, sender UNINDEXED, content='')
   copy rows WHERE id > max_indexed_id; MATCH with quoted terms
   ```

   The board schema is unchanged. The sidecar can be deleted and rebuilt. `uvx sqlite-utils enable-fts search.sqlite …` is the documented zero-code alternative.
4. **Phase 3 compat test (already planned): add one case.** After `search --rebuild`, the board's `schema_version` and `sqlite_master` are unchanged.
5. **`migrate`.** Keep it explicit and hand-written. If a column is ever added, use additive `ALTER TABLE ADD COLUMN` only. Do not use `transform`'s copy, drop and rename.

## Risks and costs

- **Dependencies:** seven runtime deps, including `pip` [V]. That is fine for `uvx` on an operator's machine. Inside Codex sandboxes, `uvx` needs network or a uv cache. [I] Nothing in the core depends on it, and nothing should.
- **Schema compatibility:** `enable-fts`, `analyze-tables --save`, `transform` and any write `query` mutate the DB, so read paths must never invoke them. The read commands I tested left `schema_version` unchanged [V]. Opening a WAL DB creates `-shm`/`-wal` files (seen with sqlite-utils; this is normal SQLite behavior [I]).
- **Silent DB creation:** a typo or a URI path produces an empty DB file, and then the error reads "no such table" rather than "file not found" [V]. This could confuse operators.
- **Licensing:** Apache-2.0, compatible with recommending or invoking it. Nothing gets vendored.
- **Maintenance:** active. Releases 4.0rc3 (2026-07-06) through 4.2.1 (2026-08-13) [V], with a 3.x→4.0 upgrade guide [V README]. Pin `sqlite-utils@4.2.1` in recipes so flag changes don't break docs. [I]

## Appendix: references

- <https://github.com/simonw/sqlite-utils> — README: feature list, Apache-2.0, plugins, 4.0 upgrade guide. The release list did not render.
- <https://sqlite-utils.datasette.io/en/stable/cli.html> — CLI flags for query/rows/memory/search/enable-fts/transform/analyze-tables (`_analyze_tables_` with `--save`). No read-only mode is documented.
- <https://pypi.org/pypi/sqlite-utils/json> — version 4.2.1, upload dates, requires_dist, Python >=3.10.
- <https://simonwillison.net/2019/Feb/25/sqlite-utils/> — 2019-02-25 intro: `--table`/`--csv`/`--nl` output, `tables --counts`, insert from JSON.
- <https://jvns.ca/blog/2022/05/12/sqlite-utils--a-nice-way-to-import-data-into-sqlite/> — 2022-05-12: `insert_all`, `alter=True`, `upsert_all(pk=)`, and `--convert`. These are import-side features that the board does not need.
- I did not fetch the separate Python API or plugins doc pages. Python API behavior was checked by running it (4.2.1).
- None of the URLs I fetched failed to load.
