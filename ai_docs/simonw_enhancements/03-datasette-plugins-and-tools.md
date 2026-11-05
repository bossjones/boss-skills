# Datasette plugin template and simonw/tools

**Verdict:** borrow the single-file HTML and stdlib test-server patterns now. Skip sqlite-wasm. If a `datasette-multi-agent` plugin ever exists, build it later in its own repo from the cookiecutter, not inside this plugin.

## What it is

- **Verified:** `simonw/datasette-plugin` is a cookiecutter template. Its prompts are `plugin_name`, `description`, `github_username`, `author_name`, `include_static_directory` and `include_templates_directory`. It generates `pyproject.toml` (setuptools, a `datasette` entry point, `package-data` for `static/*` and `templates/*`), one smoke test, `test.yml` and `publish.yml`, and an Apache-2.0 `LICENSE`. The template's own tests run cookiecutter into `tmpdir` and assert the generated file tree.
- **Verified:** `simonw/datasette-plugin-template-demo` is regenerated from the template by a `push.yml` workflow in the template repo. Its whole test checks that the plugin appears in `/-/plugins.json`, using `Datasette(memory=True)` and `datasette.client` (in-process, pytest-asyncio strict mode). CI runs Python 3.11–3.15. `publish.yml` runs on a release and uses PyPI trusted publishing (`id-token: write`, `pypa/gh-action-pypi-publish@release/v1`).
- **Verified:** `simonw/tools` holds 241 root-level `.html` tools (counted in a clone at `7792844`, 2026-10-15) and is Apache-2.0. A `build.sh` runs Python scripts (`gather_links.py`, `build_colophon.py`, `build_index.py`, and others) that generate the index, colophon, sitemap and per-tool `.docs.md`, and it injects `footer.js` into every page. The tools themselves have no build step.
- **Verified:** the tools are tested with `pytest-playwright`. `tests/conftest.py` starts `python -m http.server` on an unused port bound to `127.0.0.1`, waits for it to answer, and stops it after the test.

## Fit for the multi-agent plugin

| Idea | Plugin component | Verdict | Why |
|---|---|---|---|
| Single self-contained HTML file, vanilla JS, no build | `dashboard/acks.html`, `board.html` | **Adopt now** | It matches the stdlib-only core: no npm and no toolchain, and CI checks are just a file read. The spec already describes these pages as static files fed JSON. |
| Zero CDN or external script loads (stricter than simonw) | dashboards | **Adopt now** | Inference: these pages run on loopback over private agent traffic and should work offline. simonw's tools load from jsDelivr and cdnjs, which is fine for a public site but wrong here. |

| `textContent` rendering; DOMPurify only when Markdown is unavoidable | board/thread view | **Adopt now** | Verified: `sqlite-wasm.html` builds cells with `` `<td>${row[column]}</td>` `` and `innerHTML`, which is an XSS pattern to avoid. `claude-code-timeline.html` sanitises Markdown with DOMPurify 3.2.3 and SRI. Message bodies come from agents, so treat them as untrusted. |
| Unused-port `http.server` fixture with a readiness loop | `tests/` for the dashboard server and `page_watch` | **Adopt now** | It is stdlib-only and fits the existing pytest setup. Bind to `127.0.0.1`, and get the port by binding to 0. |
| Playwright browser tests (offline vs network-marked) | dashboard JS | **Later** | The repo has no Playwright dependency (checked in `pyproject.toml`), and adding one brings browser downloads into CI. Static assertions on the HTML cover most of the risk. |
| sqlite-wasm loading the board DB in the browser | board viewer | **No fit** | It would mean serving the raw `.db` over HTTP, which exposes every message and bypasses the `mode=ro` and `query_only` server path. Inference: frames still in `-wal` would not be visible from the `.db` file alone. The demo tool also only builds an in-memory sample DB. |
| Session-JSONL timeline viewer UX (drop zone, filters, timezone switch) | `board.html` thread/timeline view | **Optional extra** (patterns only) | `claude-code-timeline.html` (80 KB) is a good UX reference for filtering and searching an event stream. Re-implement the ideas rather than copying code, which avoids Apache-2.0 notice duties. |
| Colophon, `.docs.md`, `footer.js` injection build | dashboards | **No fit** | It is a site-publishing build step and adds nothing to a local tool. |
| `datasette-multi-agent` plugin (templates, `render_cell` for bodies, thread view) | optional extra | **Later**, separate repo | The template gives packaging, CI and PyPI publishing for free. In this repo it would clash with the Claude-plugin layout, `verify-structure`, and basedpyright on Datasette types. It would duplicate the lifted board viewer. |
| Cookiecutter "generate into tmpdir, assert tree" test | `ma install` / `templates/` | **Adopt now** | It applies directly to the spec's install step: render the templates into `tmp_path` and assert the file set. |

## Proposed spec changes

1. **§3 Dashboards and the "Dashboard" constraints:** add a page contract.
   > Each dashboard page is one self-contained `.html` file (inline CSS, one `<script type="module">`), with no build step and no external `src`/`href` (no CDN). Data comes only from same-origin `fetch('acks.json')`, `status.json` or `/api/*`. Agent-supplied text is rendered with `textContent`/`createElement`, never with interpolated `innerHTML`.
2. **Tests section:** add `tests/test_dashboard_static.py` (stdlib only):

   ```python
   for page in DASHBOARD.glob("*.html"):
       html = page.read_text()
       assert not re.search(r'(src|href)=["\']https?://', html)   # no CDN
       assert not re.search(r'innerHTML\s*=\s*`[^`]*\$\{', html)  # no interpolated innerHTML
   ```

3. **Tests section:** add a `dashboard_server` fixture modelled on `simonw/tools/tests/conftest.py`. It starts the plugin's own server (not `http.server`) on `127.0.0.1:0`, polls `urllib.request.urlopen` for up to 5 s, then terminates the server and waits on it. Use it for the smoke check "dashboard serves `acks.html`", for `page_watch --once --dry-run`, and to assert the server refuses a non-loopback bind unless the explicit flag is set.
4. **Package layout / `templates/`:** add a test that renders the install templates into `tmp_path` and asserts the exact path set, as the cookiecutter repo does.
5. **Non-goals:** "No in-browser SQLite (sqlite-wasm). The DB file is never served over HTTP."
6. **Optional extras (new subsection, deferred):** "A Datasette extra may come later. Ship config-only first (canned queries plus a metadata file, covered by the sibling Datasette report). A `datasette-multi-agent` Python plugin, if one is built, lives in its own repo generated from `simonw/datasette-plugin` and is not vendored into `plugins/meta/multi-agent`."

## Risks and costs

- **Datasette plugin in-repo:** it would add `datasette` to dev dependencies, async tests, and a second packaging model (setuptools wheel) beside the PEP 723 scripts. `verify-structure --strict` and basedpyright recommended mode would likely need exceptions (inference). A separate repo costs a release cadence and Datasette-version drift, but its CI is already done by the template.
- **No-CDN rule:** the pages must hand-roll small renderers instead of using markdown-it and DOMPurify, so they will be plainer. That is acceptable for an operations view.
- **Playwright deferral:** JS regressions in the dashboards go uncaught until a browser test exists. `page_watch` only checks HTTP status and freshness.
- **Licensing:** `simonw/tools` and the generated plugins are Apache-2.0. `gh repo view simonw/datasette-plugin` reports no license (`licenseInfo: null`), although its template ships one. Copying code from either repo means keeping the notice. Re-implementing the patterns avoids that.
- **Version churn:** the template's CI uses `actions/*@v7` and Python 3.15. Pin your own versions rather than tracking upstream.

## Appendix: references

- <https://github.com/simonw/datasette-plugin:> cloned at `ee9f1f1` (2026-10-12). Read `README.md`, `cookiecutter.json`, `tests/test_cookiecutter_template.py`, `.github/workflows/push.yml`, and the template tree. 27 stars. `gh` reports no license.
- <https://github.com/simonw/datasette-plugin-template-demo:> cloned at `fab9736` (2026-10-12). Read `pyproject.toml`, `test.yml` and `publish.yml` (3.11–3.15, trusted publishing), the `/-/plugins.json` smoke test, and the Apache-2.0 LICENSE.
- <https://github.com/simonw/tools:> cloned at `7792844` (2026-10-15). 1,909 stars, Apache-2.0. Read `README.md`, `build.sh`, `build_colophon.py` (head), `pyproject.toml` (`pytest-playwright`, `pytest-unused-port`), `.github/workflows/test.yml`, `tests/conftest.py`, `tests/test_sqlite_query_explainer.py`, `sqlite-wasm.html` (`@sqlite.org/sqlite-wasm@3.46.1-build4` from jsDelivr, in-memory sample DB, `innerHTML` cells), and `claude-code-timeline.html` (80 KB; DOMPurify 3.2.3 and markdown-it from cdnjs with SRI; drop zone and file loading). Also listed the JSON/SQLite tools (`json-diff`, `apsw-query` via Pyodide 0.27.2, `sqlite-query-explainer`, `codex-timeline`).
- <https://simonwillison.net/2024/Dec/19/one-shot-python-tools/> (2024-12-19): his custom instructions are "plain HTML and vanilla JavaScript and CSS with minimal dependencies", `<script type="module">`, and the PEP 723 header for Python tools. The post does not state a no-CDN or no-build rule.
- `specs/meta-multi-agent-authoring-prompt.md` (local): the dashboard, board-viewer, read-only and loopback constraints this report is checked against.
- No URLs failed to load.
