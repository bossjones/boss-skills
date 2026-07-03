# Plan: Break the OpenObserve verification CLI out into its own repo (`bossjones/openobservectl`)

## Context

`openobserve_cli.py` — a Typer/httpx CLI that verifies, introspects, and imports dashboards
into the cluster's OpenObserve over its REST API — currently lives as a **PEP 723 single-file
script** at `clusters/centralized_monitoring/scripts/openobserve_cli.py` inside the
`multipass-lab` repo. Unlike a self-contained subproject, it is coupled to the repo three ways:
it imports a sibling `_obs_common.py` (a stdlib-only helper *shared* with `grafana_cli.py` and
`prometheus_cli.py`), it reads dashboard JSON from `../openobserve/dashboards/**`, and it
resolves the live server URL by running `tofu output -json` in a sibling cluster dir
(`CLUSTERS_ROOT = parents[2]`). This plan lifts it into a public repo `bossjones/openobservectl`
as a proper `src/`-layout **uv package** (mirroring the lab's `ooctl`/`adguardctl` tools),
vendoring and decoupling the shared helper, vendoring the dashboards as package data, and
adding a new `~/.openobservectl/config.yaml` profile layer so the tool can target any
OpenObserve without a tofu checkout. Extraction is a **fresh copy** (no git history port).

## Objective

A public `github.com/bossjones/openobservectl` repo whose `main` has an initial README commit,
with a feature branch containing a working `src/openobservectl/` uv package: the ported CLI
(`cli.py`), a vendored + decoupled helper (`common.py`), a new profile-config layer
(`config.py`), the vendored dashboard JSON as package data, a rewritten hermetic test suite
(including new `test_config.py`), a fresh root-level CI workflow, a `justfile`, MIT LICENSE,
merged `.gitignore`, and README — cloned locally at `~/dev/bossjones/openobservectl`, with
`uv sync` + `just check` + `uv run openobservectl --help` green, ready to open a PR. The
installed CLI resolves its server URL/credentials in this precedence: explicit flags →
`$OPENOBSERVE_*` env → `~/.openobservectl/config.yaml` profile → `tofu output` fallback.

## Solution Approach

1. Create the remote repo public + `--add-readme` via `gh`; clone to `~/dev/bossjones/openobservectl`,
   branch `feature/port-openobservectl`.
2. Scaffold a `src/openobservectl/` uv package (hatchling + uv-dynamic-versioning, like `ooctl`):
   `pyproject.toml`, `.python-version`, `justfile`.
3. Port `openobserve_cli.py` → `src/openobservectl/cli.py` (rewrite the two couplings: the
   `_obs_common` import and `DASHBOARDS_DIR`).
4. Vendor + **decouple** `_obs_common.py` → `src/openobservectl/common.py` (drop the
   `CLUSTERS_ROOT`/`parents[2]` assumption; make the tofu chdir explicit).
5. **Add** `src/openobservectl/config.py` — the `~/.openobservectl/config.yaml` profile layer
   (modeled on `tools/ooctl/src/ooctl/config.py`), and wire `--profile`/`--config` into the
   CLI's `resolve()`.
6. Vendor the dashboard JSON → `src/openobservectl/dashboards/**` as package data; resolve the
   default via `importlib.resources`.
7. Port + rewrite the hermetic tests as a package suite; add `tests/test_config.py`.
8. Author fresh CI, README, LICENSE, `.gitignore`, and copy the design doc if present.
9. Validate locally (`uv sync`, `just check`, `--help`), commit, push, open PR.

Extraction is a **fresh copy** (no git history port). This is a **refactor-during-extraction**,
not a file copy — the source is one 666-line script, not a package.

## Relevant Files

Source (read-only, in `multipass-lab`):
- `clusters/centralized_monitoring/scripts/openobserve_cli.py` — the 666-line CLI to port.
  Change points: `import _obs_common as oc` (line 28) and
  `DASHBOARDS_DIR = Path(__file__).resolve().parent.parent / "openobserve" / "dashboards"` (line 39);
  `resolve()` (lines 98-121) is where the profile layer is wired in.
- `clusters/centralized_monitoring/scripts/_obs_common.py` — stdlib-only helper to vendor.
  Decouple points: `CLUSTERS_ROOT = Path(__file__).resolve().parents[2]` (line 32) and
  `default_chdir()` (lines 60-62). **Shared** by grafana/prometheus CLIs → copy, do not move.
- `clusters/centralized_monitoring/openobserve/dashboards/**` — 12 dashboard JSON files under
  `Correlation/`, `Infrastructure/`, `LogAnalysis/` to vendor as package data.
- `clusters/centralized_monitoring/tests/openobserve/test_openobserve_cli.py`,
  `.../test_openobserve_dashboards_cli.py`,
  `clusters/centralized_monitoring/tests/obs_common/test_obs_common.py` — hermetic tests to
  port (drop the `pythonpath = ["../../scripts"]` hack; switch to package imports).
- `tools/ooctl/src/ooctl/config.py` and `tools/ooctl/tests/test_config.py` — **template** for
  the new `config.py` + `test_config.py` (Profile/Config pydantic models, `~/.ooctl/config.yaml`
  loading, env overrides, `resolve_profile`). Reuse the shape; rename `OOCTL_*` → `OPENOBSERVE_*`
  and the path → `~/.openobservectl/config.yaml`.
- `tools/ooctl/pyproject.toml`, `tools/ooctl/justfile`, `tools/ooctl/.github/workflows/*` (if
  any) — templates for the new repo's build/tooling.

### New files (in `~/dev/bossjones/openobservectl`)
- `pyproject.toml` — hatchling + uv-dynamic-versioning; deps `typer>=0.12`, `rich>=13`,
  `httpx>=0.27`, `pyyaml>=6`, `pydantic>=2`; console script
  `openobservectl = "openobservectl.cli:app"`; dev group: pytest, pytest-httpserver,
  pytest-mock, pytest-cov, pytest-randomly, ruff, ty (or basedpyright), codespell.
- `.python-version`, `justfile`, `README.md`, `LICENSE` (MIT, Malcolm Jones, 2026), `.gitignore`.
- `src/openobservectl/__init__.py`, `__main__.py`, `cli.py`, `common.py`, `config.py`.
- `src/openobservectl/dashboards/{Correlation,Infrastructure,LogAnalysis}/*.json` — vendored.
- `tests/test_cli.py`, `tests/test_dashboards.py`, `tests/test_common.py`, `tests/test_config.py`,
  `tests/conftest.py`.
- `.github/workflows/ci.yml` — authored fresh (no workflow exists to re-home).
- `docs/design.md` — copy of `specs/cli-openobserve.md` if it exists in the source repo.

### Target repo layout
```
openobservectl/
├── pyproject.toml  .python-version  justfile  README.md  LICENSE  .gitignore
├── .github/workflows/ci.yml
├── docs/design.md
├── src/openobservectl/
│   ├── __init__.py  __main__.py  cli.py  common.py  config.py
│   └── dashboards/{Correlation,Infrastructure,LogAnalysis}/*.json
└── tests/
    ├── conftest.py  test_cli.py  test_dashboards.py  test_common.py  test_config.py
```

## Step by Step Tasks

IMPORTANT: Execute every step in order, top to bottom. `<source>` =
`/Users/bossjones/dev/bossjones/multipass-lab`. `<new>` = `~/dev/bossjones/openobservectl`.

### 1. Create the remote repo
- Confirm `gh auth status` shows account `bossjones` with `repo` + `workflow` scopes
  (`workflow` is required to push `.github/workflows/`).
- `gh repo create bossjones/openobservectl --public --description "CLI to verify, introspect, and import dashboards into an OpenObserve instance over its REST API" --add-readme`

### 2. Clone locally and branch
- `git clone git@github.com:bossjones/openobservectl.git <new>`
- `cd <new> && git switch -c feature/port-openobservectl`

### 3. Scaffold the uv package skeleton
- Create `pyproject.toml` modeled on `<source>/tools/ooctl/pyproject.toml`:
  - `[project]` name `openobservectl`, `requires-python = ">=3.11"`, `dynamic = ["version"]`,
    `license = { text = "MIT" }`, `readme = "README.md"`.
  - `dependencies = ["typer>=0.12", "rich>=13", "httpx>=0.27", "pyyaml>=6", "pydantic>=2"]`
    (pyyaml + pydantic are new — required by the config layer; the original PEP 723 block only
    had typer/rich/httpx).
  - `[project.scripts] openobservectl = "openobservectl.cli:app"`.
  - `[build-system]` hatchling + uv-dynamic-versioning; `[tool.hatch.version] source = "uv-dynamic-versioning"`;
    `[tool.uv-dynamic-versioning] vcs = "git"`, `style = "pep440"`, `bump = true`,
    `fallback-version = "0.0.0"`.
  - `[tool.hatch.build.targets.wheel] packages = ["src/openobservectl"]` — this ships
    `src/openobservectl/dashboards/**` JSON as package data automatically.
  - `[dependency-groups] dev = [...]` (pytest, pytest-httpserver, pytest-mock, pytest-cov,
    pytest-randomly, ruff, ty, codespell).
  - `[tool.pytest.ini_options] addopts = "-ra"`, `testpaths = ["tests"]`,
    `filterwarnings = ["ignore::SyntaxWarning"]`. **No `pythonpath`** — the src layout +
    `uv sync` editable install makes `import openobservectl` resolve.
  - `[tool.ruff]` line-length 100 (or 120 to match boss-skills); lint select E/F/UP/B/I.
- Create `.python-version` (`3.11` or the lab's pinned version) and `justfile` (targets:
  `check`, `test`, `lint`, `fmt`, `install`, and a `--help` smoke) modeled on
  `<source>/tools/ooctl/justfile` **minus** the `tofu ... server_ipv4` / `repo_root` lab recipes.
- Create `src/openobservectl/__init__.py` (empty or version passthrough) and
  `src/openobservectl/__main__.py` (`from openobservectl.cli import app; app()` under a
  `__main__` guard) so `python -m openobservectl` works.

### 4. Port the CLI → `src/openobservectl/cli.py`
- Copy `<source>/.../scripts/openobserve_cli.py` to `<new>/src/openobservectl/cli.py`.
- **Drop the PEP 723 header + shebang** (lines 1-9) — deps now live in `pyproject.toml`.
- Change the helper import (line 28): `import _obs_common as oc` → `from openobservectl import common as oc`.
- Change `DASHBOARDS_DIR` (line 39) from the `__file__/../../openobserve/dashboards` walk to
  package-data resolution:
  ```python
  from importlib.resources import files
  DASHBOARDS_DIR = Path(str(files("openobservectl") / "dashboards"))
  ```
- Extend the Typer callback `_main()` (lines 78-95) with two new global options and thread them
  into `Options`:
  - `profile: str = typer.Option(None, "--profile", "-p", help="~/.openobservectl/config.yaml profile")`
  - `config: str = typer.Option(None, "--config", help="config file path ($OPENOBSERVECTL_CONFIG)")`
  - Also add `lab_root: str = typer.Option(None, "--lab-root", help="multipass-lab checkout for tofu fallback ($MULTIPASS_LAB_ROOT)")`.
- Everything below (`health`, `streams`, `search`, `query`, `orgs`, the `dashboards`
  sub-typer, `check`, `_render_check`) is ported **unchanged** except the `resolve()` rewrite
  in Step 6. Keep the `if __name__ == "__main__": app()` guard so both `python -m` and the
  console script work.

### 5. Vendor + decouple the helper → `src/openobservectl/common.py`
- Copy `<source>/.../scripts/_obs_common.py` to `<new>/src/openobservectl/common.py`
  (it is stdlib-only — no new deps).
- **Remove** `CLUSTERS_ROOT = Path(__file__).resolve().parents[2]` (line 32) — there is no
  `clusters/` parent in the standalone repo.
- **Rework** `default_chdir()` to take an explicit lab root instead of deriving it:
  ```python
  def default_chdir(cluster: str, lab_root: str | Path) -> str:
      """The cluster dir `tofu` should run in, under an explicit multipass-lab checkout."""
      return str(Path(lab_root).expanduser() / "clusters" / cluster)
  ```
- `resolve_target()` keeps its precedence (`server_url` > `$url_env` > tofu) but the tofu branch
  now requires a caller-supplied `chdir` (the CLI passes `default_chdir(cluster, lab_root)`);
  if no URL source resolves and no `lab_root` is available, the CLI raises a clear error
  (Step 6) rather than blindly shelling tofu. Keep `resolve_credentials`, `http_get_json`,
  `poll`, `CheckReport`, `print_json`, `Target`, `HttpError` verbatim.
- Update the module docstring (drop the "imported by grafana/prometheus/openobserve" +
  `pythonpath` prose; it's now a package module).

### 6. Add the profile layer → `src/openobservectl/config.py` + wire `resolve()`
- Create `src/openobservectl/config.py` by adapting `<source>/tools/ooctl/src/ooctl/config.py`:
  - `Profile(BaseModel)`: `endpoint`, `organization="default"`, `username`, `password`,
    `timeout=10.0`, `verify=True`; keep the `endpoint` trailing-slash-strip validator.
  - `Config(BaseModel)`: `profiles: dict[str, Profile]`.
  - `default_config_path()` → `Path.home() / ".openobservectl" / "config.yaml"`.
  - `load_config(path)` and `resolve_profile(config, name, env)` — same logic; rename the env
    override map to `OPENOBSERVE_URL→endpoint`, `OPENOBSERVE_ORG→organization`,
    `OPENOBSERVE_USER→username`, `OPENOBSERVE_PASSWORD→password` so it reuses the CLI's existing
    env-var names.
- Rewrite `cli.resolve(opts)` to layer the profile in. Precedence:
  ```python
  def resolve(opts: Options) -> Ctx:
      profile = None
      cfg_path = opts.config or os.environ.get("OPENOBSERVECTL_CONFIG") or str(config.default_config_path())
      name = opts.profile or os.environ.get("OPENOBSERVECTL_PROFILE")
      if name or (opts.profile is None and Path(cfg_path).exists()):
          # load only if a profile was requested or a default config file exists
          try:
              profile = config.resolve_profile(config.load_config(cfg_path), name or "default")
          except config.ConfigError as exc:
              if opts.profile or name:   # explicit request must not silently fall through
                  _die(str(exc))
      # base URL precedence: --server-url > $OPENOBSERVE_URL > profile.endpoint > tofu(lab_root)
      server_url = opts.server_url or os.environ.get("OPENOBSERVE_URL") \
          or (profile.endpoint if profile else None)
      if server_url:
          base_url = server_url.rstrip("/")
      elif opts.lab_root or os.environ.get("MULTIPASS_LAB_ROOT"):
          lab_root = opts.lab_root or os.environ["MULTIPASS_LAB_ROOT"]
          base_url = oc.resolve_target(port=PORT, server_url=None, url_env=None,
                                       chdir=oc.default_chdir(opts.cluster, lab_root)).base_url
      else:
          _die("no OpenObserve URL: pass --server-url, set $OPENOBSERVE_URL, "
               "configure a profile in ~/.openobservectl/config.yaml, or point "
               "--lab-root at a multipass-lab checkout for the tofu fallback")
      # credentials: flags > env > profile > built-in defaults
      user, password = oc.resolve_credentials(
          opts.user, opts.password, user_env="OPENOBSERVE_USER", pass_env="OPENOBSERVE_PASSWORD",
          default_user=(profile.username if profile else DEFAULT_USER),
          default_password=(profile.password if profile else DEFAULT_PASSWORD))
      org = opts.org if opts.org != "default" else (profile.organization if profile else "default")
      return Ctx(base_url=base_url, user=user, password=password, org=org,
                 as_json=opts.as_json, timeout=opts.timeout, insecure=opts.insecure)
  ```
  (Pseudocode — implementer refines. The invariant: explicit flags/env always beat the profile;
  the profile beats built-in defaults; tofu is the last resort and only when a lab root is given.)
- Optionally add a `config` sub-typer with `list` (print profile names from the config file)
  and `path` (print `default_config_path()`), modeled on ooctl's `configure` command. Writing
  profiles can stay manual (edit the YAML). Mark `config add` an optional follow-up.

### 7. Vendor the dashboards
- Copy `<source>/clusters/centralized_monitoring/openobserve/dashboards/` (the `Correlation/`,
  `Infrastructure/`, `LogAnalysis/` folders and their JSON) into
  `<new>/src/openobservectl/dashboards/`, preserving the folder-per-OpenObserve-folder layout
  (`dashboards import` uses the parent dir name as the OpenObserve folder).
- Confirm the 12 files land: `Correlation/cause-effect.json`; `Infrastructure/{container-metrics,
  host-metrics,prometheus-health,traces-by-service,traces-overview,uptime}.json`;
  `LogAnalysis/{container-logs,error-triage,k0s-pods,log-overview,per-host}.json`.

### 8. Port + rewrite the tests
- `tests/test_cli.py` ← `<source>/.../tests/openobserve/test_openobserve_cli.py`: change
  `import openobserve_cli as oo` → `from openobservectl import cli as oo`; the CliRunner +
  pytest-httpserver + `--server-url` cases port unchanged.
- `tests/test_dashboards.py` ← `.../test_openobserve_dashboards_cli.py`: fix the import; point
  the "shipped JSON validity sweep" at the vendored package dir
  (`Path(files("openobservectl") / "dashboards")`).
- `tests/test_common.py` ← `.../tests/obs_common/test_obs_common.py`: change `import _obs_common`
  → `from openobservectl import common`; update the tofu test to pass an explicit `chdir`/`lab_root`
  through the reworked `default_chdir`/`resolve_target` (inject a fake `runner`, no real tofu).
- **New** `tests/test_config.py` ← adapt `<source>/tools/ooctl/tests/test_config.py`: load a temp
  `config.yaml`, `resolve_profile` happy path, `OPENOBSERVE_*` env overrides win, unknown-profile
  `ConfigError`. Add one CLI-level test: `--profile` sets the base URL (via pytest-httpserver).
- Add `tests/conftest.py` if fixtures (temp config, httpserver base) are shared.

### 9. Author CI, README, LICENSE, .gitignore, design doc
- `.github/workflows/ci.yml` — author fresh (there is no workflow to re-home). Model on the
  lab's tool CI: `uv sync`, `uv run ruff format --check .`, `uv run ruff check .`,
  `uv run ty check` (or `basedpyright`), `uv run codespell src tests`,
  `uv run pytest`. Trigger on push/PR to `main`. No `paths:`/`working-directory` (single-purpose repo).
- `README.md` — overwrite the seeded one: what the tool is, install (`uv tool install openobservectl`
  or `uv sync`), the four URL-resolution layers, `~/.openobservectl/config.yaml` example, and a
  command tour (`health`, `streams`, `search`, `query`, `orgs`, `dashboards {list,import,delete}`,
  `check`). Do **not** reference `tofu`/`clusters/` as required — tofu is now an optional fallback.
- `LICENSE` — MIT, `Copyright (c) 2026 Malcolm Jones`.
- `.gitignore` — Python/uv ignores (`.venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`,
  `.ruff_cache/`, `.coverage`), macOS (`.DS_Store`), and the Claude-hook noise
  (`.claude/settings.local.json`, `logs/`).
- `docs/design.md` — copy `<source>/specs/cli-openobserve.md` if it exists (the CLI docstring
  references it); otherwise skip and note it in the PR.

### 10. Local validation (before committing)
- `cd <new>`
- `uv sync` — resolves the new manifest (typer/rich/httpx/pyyaml/pydantic + dev group) and
  editable-installs the package.
- `uv run openobservectl --help` and `uv run python -m openobservectl --help` — both entrypoints.
- `just check` (ruff format --check + ruff check + ty check + codespell + pytest) — the CI gate.
- Smoke the profile layer: write a throwaway `~/.openobservectl/config.yaml` with a `default`
  profile and confirm `openobservectl --profile default health` targets its endpoint (or a
  local mock). Confirm the no-URL path errors with the guidance message.

### 11. Commit, push, open PR
- `git add -A`
- Commit (conventional): `feat: port openobserve verification CLI into its own repo as openobservectl`
  — body notes the source path, the PEP 723→uv-package refactor, the vendored+decoupled helper,
  the new config-profile layer, and vendored dashboards. Include the Co-Authored-By /
  Claude-Session trailers.
- `git push -u origin feature/port-openobservectl`
- `gh pr create --repo bossjones/openobservectl --base main --head feature/port-openobservectl
  --title "Port openobserve verification CLI into its own repo" --body "..."` (include the
  🤖 Generated-with footer).

## Testing Strategy

The port is a refactor, so tests are the primary correctness signal — the ported hermetic suite
plus the new config tests must pass in the new package layout:
- **`uv sync`** proves the new `pyproject.toml` resolves standalone and the src layout is importable.
- **`ruff` / `ty` / `codespell`** prove no module was corrupted in the port and the rewritten
  imports type-check.
- **`pytest`** (CliRunner + pytest-httpserver, hermetic — no live OpenObserve, no tofu) proves:
  the ported `health/streams/search/query/orgs` and the `check` matrix
  (`--require-streams/-metrics/-logs/-dashboards`) still behave; `dashboards {list,import,delete}`
  work against the **vendored** package-data JSON; and the **new** `config.py` loads/validates
  profiles, applies `OPENOBSERVE_*` env overrides, and errors on unknown profiles.
- **`openobservectl --help`** and **`python -m openobservectl`** smoke-test both entrypoints.
- Manual: point a profile (or `--server-url`) at a live OpenObserve and run
  `openobservectl check --require-metrics --require-logs` — the same assertion the lab's
  `verify-api` runs — plus `dashboards import` (idempotent upsert) for an end-to-end check.
- After push, **GitHub Actions** re-runs the gate on Ubuntu.

## Acceptance Criteria

- `gh repo view bossjones/openobservectl` shows a **public** repo; `main` has an initial README commit.
- Cloned at `~/dev/bossjones/openobservectl`; branch `feature/port-openobservectl` checked out.
- **uv src package:** `src/openobservectl/{__init__,__main__,cli,common,config}.py` exist; the
  package is NOT hoisted to the repo root; `pyproject.toml`/`.python-version`/`justfile` at root.
- `cli.py` has **no** PEP 723 header, imports `from openobservectl import common`, and resolves
  `DASHBOARDS_DIR` via `importlib.resources` (no `parents`/`__file__/..` walk).
- `common.py` has **no** `CLUSTERS_ROOT`; `default_chdir` takes an explicit lab root.
- `config.py` exists; `default_config_path()` returns `~/.openobservectl/config.yaml`; URL/cred
  precedence is flags → `$OPENOBSERVE_*` → profile → tofu(`--lab-root`), and the no-source path
  emits the guidance error.
- 12 dashboard JSON files vendored under `src/openobservectl/dashboards/**` and shipped as package
  data (present in a built wheel / resolvable via `importlib.resources`).
- Test suite (`test_cli.py`, `test_dashboards.py`, `test_common.py`, new `test_config.py`) passes
  with no `pythonpath` hack.
- `.github/workflows/ci.yml`, `justfile`, `README.md` (no required-tofu/`clusters/` prose),
  `LICENSE` (MIT, Malcolm Jones, 2026), `.gitignore` present.
- `uv sync`, `just check`, `uv run openobservectl --help`, `uv run python -m openobservectl --help`
  all succeed locally.
- A PR is open against `bossjones/openobservectl:main`; its CI run is green (or running).

## Validation Commands

Run in `<new>` = `~/dev/bossjones/openobservectl` unless noted:
- `gh repo view bossjones/openobservectl --json visibility,defaultBranchRef` — public + main exists.
- `test -f src/openobservectl/cli.py && test -f src/openobservectl/common.py && test -f src/openobservectl/config.py && test ! -d openobservectl && echo "src-layout OK"`
- `! grep -q 'PEP 723\|/// script' src/openobservectl/cli.py && grep -q 'from openobservectl import common' src/openobservectl/cli.py && grep -q 'importlib.resources\|files("openobservectl")' src/openobservectl/cli.py` — CLI couplings rewritten.
- `! grep -q 'CLUSTERS_ROOT' src/openobservectl/common.py` — helper decoupled.
- `grep -q '.openobservectl' src/openobservectl/config.py` — config path correct.
- `find src/openobservectl/dashboards -name '*.json' | wc -l` — expect `12`.
- `uv sync` — manifest resolves.
- `uv run ruff format --check . && uv run ruff check . && uv run ty check && uv run codespell src tests && uv run pytest` — full gate.
- `uv run openobservectl --help && uv run python -m openobservectl --help` — entrypoints.
- `uv run python -c "from importlib.resources import files; from pathlib import Path; print(len(list(Path(str(files('openobservectl')/'dashboards')).glob('**/*.json'))))"` — package data resolves (expect 12).
- `gh pr view --repo bossjones/openobservectl` and `gh run list --repo bossjones/openobservectl` — PR + CI status.

## Notes

- **Decisions confirmed with user:** scope = verification CLI only; repo `bossjones/openobservectl`;
  fresh copy (no history); layered URL resolution (flags → `$OPENOBSERVE_URL` → config profile →
  tofu fallback) plus a new `~/.openobservectl/config.yaml`.
- **Not a mechanical copy.** Unlike the `adguardctl` breakout, the source is a single PEP 723
  script sharing `_obs_common.py` with two other CLIs and hardcoding cluster paths. The bulk of
  this plan is the refactor (package skeleton, decoupled helper, new config layer, package-data
  dashboards), not file copying.
- **`_obs_common.py` is shared — copy, never move.** `grafana_cli.py` and `prometheus_cli.py`
  still import it in the source repo. The standalone repo gets its own decoupled `common.py`; the
  original stays put.
- **New runtime deps:** `pyyaml` + `pydantic` (for the config layer). The original PEP 723 block
  had only typer/rich/httpx. Install with `uv add pyyaml pydantic` (dev tools via
  `uv add --dev pytest pytest-httpserver pytest-mock pytest-cov pytest-randomly ruff ty codespell`).
- **Fresh copy, no history:** does not preserve `openobserve_cli.py`/`_obs_common.py` git history.
  `git filter-repo` would be the alternative — out of scope.
- **No changes to the source repo** beyond this spec. Removing `openobserve_cli.py` from
  `multipass-lab` and updating the root `Justfile`'s `verify-api`/`openobserve-*` targets (which
  special-case `openobserve_cli`) is an intentional **follow-up decommission** once the new repo
  is verified — and note `_obs_common.py` cannot be deleted then (still used by grafana/prometheus).
- **`uv` + `just`** must be installed locally for Step 10 validation.
- **Versioning** via git tags (uv-dynamic-versioning, `fallback-version = "0.0.0"`); tag `v0.1.0`
  after merge if a release is wanted.
