# sqlite-http, sqlite-html and sqlite-tg

**Verdict:** none of the three earns a place in the `multi-agent` plugin, core or extra. Stdlib `urllib`/`html.parser`, plus reading `acks.json`, already cover every use case without a native binary. sqlite-http also undermines the board's read-only guarantee.

## What it is

- **sqlite-http** (Alex Garcia, Go): SQL functions `http_get`, `http_get_body`, `http_do`, `http_post`, `http_rate_limit`, `http_timeout_set`, and `http_headers_each`. The latest release is v0.1.2 (GitHub and PyPI, 2026-09-12). The repo is active and not archived, with wheels for macOS arm64 and x86_64, Linux, and Windows. *[verified: gh API, PyPI JSON, README, docs.md]*
- **sqlite-html** (Go, built on riyaz-ali/sqlite): CSS-selector extraction (`html_extract`, `html_text`, `html_each`, `html_attribute_get`) and HTML generation. The latest release is v0.1.3 (2023-08-06), with no push since that date. It isn't archived, but it's effectively dormant. There is a macOS arm64 wheel; the README still says "no arm", which is out of date. *[verified]*
- **sqlite-tg**: geometry functions (GeoJSON/WKT/WKB, point-in-polygon, intersects). The latest release is still alpha: 0.0.1-alpha.21 (2026-08-03). The author calls it "early alpha" with no indexing. *[verified: TIL dated 2023-09-25, gh API]*
- All three are pre-1.0 loadable extensions. Using one from Python requires `conn.enable_load_extension(True)` and the PyPI wrapper's `.load(conn)`.

## Fit for the multi-agent plugin

| Idea | Plugin component | Verdict | Why |
|---|---|---|---|
| HTTP checks of dashboard pages from SQL | `page_watch.py` (PAGE-BROKEN/PAGE-STALE) | No fit | `urllib.request` with a timeout already does this in stdlib. Running the check in SQL adds a native binary, a PyPI dependency and a load step, and buys no new capability, since the results are printed lines, not board rows. |
| Store HTTP results in board tables via `INSERT … SELECT http_get(...)` | board / `status` monitor | No fit | This would add tables or columns. The spec forbids schema changes on an existing DB. |
| `gh` PR/CI polling through `http_get` against the API | CI/PR monitors | No fit | It would need a token in SQL text (the README example puts `Authorization` in the query), and `gh` already handles authentication. |
| Replace the `stuck_watch.sh` DOM scrape with `html_text(http_get_body(acks.html), ...)` | `coordinator/stuck_watch.sh` | No fit | `acks.html` is rendered from `acks.json`. Read the JSON directly, as the spec already recommends; any HTML parse is a step backwards. If the page is JS-rendered, a non-browser fetch sees no data at all *(inference)*. |
| Parse dashboard HTML in tests | `dashboard/` tests | No fit | stdlib `html.parser` is enough to assert that elements exist. sqlite-html is dormant since 2023. |
| Geospatial anything | n/a | No fit | The plugin has no geometry. |

## Proposed spec changes

1. **None to adopt.** Add a short "Rejected alternatives" note under Design rules → Board:

   ```markdown
   - Rejected: SQLite loadable extensions (sqlite-http, sqlite-html, sqlite-tg).
     They break the stdlib-only core, cannot be loaded by Apple's python3
     (no enable_load_extension), and sqlite-http makes network calls even on
     `mode=ro` + `query_only` connections. Monitors use urllib/html.parser and
     read acks.json directly.
   ```

2. **Harden the read-only rule.** In `lib/multi_agent/` read paths, never call `enable_load_extension(True)`. Add one test that asserts read connections leave extension loading disabled (for example, `load_extension` raises). This is cheap and also guards against future "helpful" extras.
3. **Make the `stuck_watch.sh` replacement explicit:** a stdlib `stuck_watch.py` that reads `acks.json` (atomic `os.replace` writes make it safe to read) and emits `STUCK <agent> <minutes>` lines.

## Risks and costs

- **Python availability (verified locally, 2026-10-16):**
  - Apple `/usr/bin/python3` (CLT 3.9.6) and pyenv 3.12.8 have **no** `enable_load_extension` attribute. Extensions cannot load there at all.
  - Homebrew 3.13.5/3.14.6 and the uv-managed python-build-standalone 3.13.15 (`~/.local/share/uv/python/cpython-3.13.15-macos-aarch64-none`) have it. With `uv run --with sqlite-http --with sqlite-html --with sqlite-tg`, all three loaded and reported `v0.1.2`, `v0.1.3`, and `v0.0.1-alpha.21`.
  - Agents run `python3 -I`, and `python3` resolves differently per machine. Here it's a pyenv shim, which cannot load extensions. An extension-based extra would fail on that path.
- **Security (verified):** in a connection opened `file:t.db?mode=ro` with `PRAGMA query_only=1` and sqlite-http loaded, `select http_get_body('https://example.com')` succeeded. Read-only mode restricts writes to the DB, not side effects. Any agent able to run SQL on such a connection could exfiltrate data (for example, board message bodies) or hit internal URLs. docs.md admits this and offers an `OmitNet` build flag. There is no rate limit by default.
- **Correctness quirk (verified):** `html_extract('<tr><td>x</td></tr>','td')` returned NULL. Fragments are parsed in HTML5 context, so table rows outside a `<table>` vanish. This is a silent false negative for a stuck detector.
- **Codex sandboxes (inference):** a sandbox with `network_access=true` would allow sqlite-http traffic. A uv wheel download at first run needs network access and a writable cache, which a sandbox may not have.
- **Maintenance:** all three are pre-1.0 (`http0`/`html0` naming warns of breaking changes). sqlite-html has had no commits since 2023-08.

## Appendix: references

- <https://observablehq.com/@asg017/introducing-sqlite-http:> **FAILED (HTTP 429, retried twice).** Its content is covered instead by the repo README and docs.md below.
- <https://observablehq.com/@asg017/introducing-sqlite-html:> **FAILED (HTTP 429, retried twice).** Covered by the repo README.
- <https://til.simonwillison.net/sqlite/sqlite-tg:> TIL of 2023-09-25. Describes sqlite-tg as "early alpha", with no indexing; install is through `datasette install datasette-sqlite-tg`; version 0.0.1a6 at the time.
- <https://github.com/asg017/sqlite-http> (README, docs.md, releases API): v0.1.2, 2026-09-12; not archived; macOS arm64 build; `http_timeout_set`/`http_rate_limit`; the `OmitNet` security note; headers passed in SQL.
- <https://github.com/asg017/sqlite-html> (README, releases API): v0.1.3, 2023-08-06; last push 2023-08-06; written in Go; Python loading example.
- <https://github.com/asg017/sqlite-tg> (releases API): 0.0.1-alpha.21, 2026-08-03; not archived; macOS arm64 build.
- <https://pypi.org/pypi/{sqlite-http,sqlite-html,sqlite-tg}/json:> confirms the latest PyPI versions (0.1.2 / 0.1.3 / 0.0.1a21) and `macosx_11_0_arm64` wheels for all three.
- `/Users/bossjones/dev/bossjones/boss-skills/specs/meta-multi-agent-authoring-prompt.md`: the plugin constraints (stdlib core, `mode=ro` + `query_only`, the `stuck_watch.sh` "prefer acks.json" note, Codex sandbox flags).
- Local probes: `/private/tmp/claude-501/simonw-research/ext/{probe.py,load.py,html2.py}`.
