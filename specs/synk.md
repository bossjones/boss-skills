# Spec: Snyk agent-scan pre-commit + SessionStart integration

> Note: this file is `specs/synk.md` (the requested filename/spelling); the underlying tool is
> `snyk-agent-scan`. This spec is a blueprint — it describes the implementation but does not
> perform it.

## Context

`boss-skills` is a repository of Claude Code skills, agents, commands and MCP configs. That is
exactly the artifact class that Snyk's **`agent-scan`** (formerly Invariant Labs' `mcp-scan`,
now `snyk/agent-scan`) inspects: it is an **AI-agent supply-chain scanner** for MCP servers,
agent skills (`SKILL.md`), prompts and resources, detecting prompt injection, tool
poisoning/shadowing, toxic flows, malware payloads, obfuscation (hidden Unicode) and insecure
credential handling. It is **not** a generic SAST/SCA/secrets scanner — pointing it at arbitrary
source is meaningless; pointing it at this repo's skill/agent artifacts is a genuine fit.

Two entry points are wanted:

1. A **pre-commit hook** that scans staged skill/agent/command artifacts.
2. A **SessionStart hook** (per the Claude Code hooks docs) that scans the current project at the
   start of every Claude session and surfaces findings as session context.

Both must be **opt-in and fail-open**: no Snyk token → silently skip; scanner error/timeout →
skip; never block a commit or a session by default. Packaging is into the **`agent-harness`
plugin** so the SessionStart behavior applies across every project the user opens.

## Objective

Ship an advisory Snyk `agent-scan` integration, gated by plugin `userConfig`, that:

- Adds an **enable toggle** (`ENABLE_SNYK_AGENT_SCAN`, boolean, default `false`) and a **token
  field** (`SNYK_TOKEN`, string) to the agent-harness plugin `userConfig`.
- Runs at **SessionStart** (hand-rolled PEP 723 wrapper) and injects a findings summary as
  `additionalContext` — never blocks, swallows errors.
- Runs as a **pre-commit `repo: local` hook** over staged skill/agent/command markdown, advisory
  by default (exit 0), with an opt-in enforce toggle.
- **Silently skips** when disabled or when no `SNYK_TOKEN` is resolvable (via plugin option or
  `.env`/`load_dotenv()`).

## Problem Statement

There is currently no automated agent-security gate in this repo. The existing security posture
is a PR-time `uv audit` + `anthropics/claude-code-security-review` action and the advisory
`boss-security-review` skill — none of which inspect MCP/skill artifacts for agent-specific risks
(prompt injection in tool descriptions, tool shadowing, toxic flows, hidden-Unicode obfuscation).
`agent-scan` closes that gap, but three constraints shape the design:

1. **Exit codes are undocumented.** A `--ci` flag exists (and `--ignore-issues-codes` composes
   with it), implying a pass/fail exit signal, but the contract is unconfirmed. Gating must not
   trust the exit code blindly — parse `--json` severity counts instead.
2. **Auth + network required.** `SNYK_TOKEN` is mandatory and verification is cloud-based; the
   tool is not fully offline. Contributors without a token must be unaffected.
3. **Non-interactive server-launch hazard.** Scanning MCP *server configs* can launch stdio MCP
   servers (interactive consent prompt, or `--dangerously-run-mcp-servers` to auto-start). In a
   pre-commit/SessionStart context that would hang or be unsafe. Scope targets to **static skill
   artifacts** and never pass `--dangerously-run-mcp-servers`.

## Solution Approach

Package everything in the `agent-harness` plugin, reusing its established config + hook
conventions, plus one repo-level pre-commit hook:

- **Config** via the plugin's existing `userConfig` → env-injection mechanism. Values resolve as
  `CLAUDE_PLUGIN_OPTION_<KEY>` with fallback to a bare env var of the same name (shared resolver
  `plugins/boss-dev/agent-harness/hooks/utils/config.py:_option`). So `SNYK_TOKEN` resolves from
  the plugin option **or** from `.env` (`load_dotenv()`), giving both hooks one code path.
- **Shared helper** (`hooks/utils/snyk.py`) does invoke + JSON-parse + summarize, so both the
  SessionStart wrapper and the pre-commit script share one tested implementation and one
  injectable scanner command (for offline testing).
- **SessionStart wrapper** appends a second entry to the `SessionStart` array in the plugin's
  `hooks.json` (mirroring the `Stop` event's two-entry style) and injects
  `{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": ...}}`.
- **Pre-commit hook** is a `repo: local` hook in `.pre-commit-config.yaml` calling
  `uv run scripts/snyk-agent-scan.py` with `pass_filenames: true`, scoped by an anchored `files:`
  regex (same shape as the existing `validate-unicode-hygiene` hook).

**Gating decision (default): advisory.** SessionStart is always advisory. Pre-commit is advisory
(exit 0, prints findings) unless `SNYK_AGENT_SCAN_ENFORCE=1`, in which case it exits non-zero when
High/Critical findings are present. Rationale: undocumented exit codes + network/token dependency
make hard-blocking fragile; advisory + opt-in enforce is the safe path.

## Relevant Files

Existing files to modify:

- `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json` — add two `userConfig` fields; bump
  `version` `0.16.0` → `0.17.0` (minor: new feature).
- `.claude-plugin/marketplace.json` — bump the `agent-harness` entry `version` in lockstep
  (`verify-structure.py` + `version-bump-reviewer` enforce parity).
- `plugins/boss-dev/agent-harness/hooks/hooks.json` — append a SessionStart entry invoking the new
  wrapper (`uv run "${CLAUDE_PLUGIN_ROOT}"/hooks/snyk_agent_scan.py`).
- `plugins/boss-dev/agent-harness/hooks/utils/config.py` — add `snyk_enabled()` and `snyk_token()`
  helpers reusing the existing `_option()` resolver.
- `.pre-commit-config.yaml` — add a `repo: local` hook `snyk-agent-scan`.
- `.env.sample` — add `SNYK_TOKEN=` (empty).
- `plugins/boss-dev/agent-harness/README.md` + `docs/hooks.md` — document the toggle, the token
  field, the SessionStart hook and the resolution order. (Both are `rumdl`-linted — mirror
  existing `userConfig`/hook docs.)
- `Makefile` — optional advisory `snyk-scan` target; note that `make install` does **not** run
  `pre-commit install`.

### New Files

- `plugins/boss-dev/agent-harness/hooks/utils/snyk.py` — shared library: `resolve_targets()`,
  `run_scan(targets, *, token, timeout) -> ScanResult`, `severity_counts()`, `summarize()`. Honors
  a `SNYK_AGENT_SCAN_CMD` env override (defaults to `uvx snyk-agent-scan@latest`) so tests inject a
  fake scanner and never hit the network.
- `plugins/boss-dev/agent-harness/hooks/snyk_agent_scan.py` — SessionStart PEP 723 wrapper (reads
  hook JSON from stdin, resolves config, scans the session's project skills, prints
  `additionalContext`, exits 0 on any error).
- `scripts/snyk-agent-scan.py` — pre-commit PEP 723 entrypoint (`load_dotenv()`, filters staged
  paths, advisory/enforce, imports the shared helper via a deterministic `sys.path` insert of the
  plugin `hooks/` dir).
- `tests/test_snyk_agent_scan.py` — unit + subprocess tests using a fake scanner (no network).

## Implementation Phases

### Phase 1: Foundation

Config plumbing and the shared helper — the parts both hooks depend on.

- Add `ENABLE_SNYK_AGENT_SCAN` (boolean, `default: false`) and `SNYK_TOKEN` (string, `default: ""`)
  to `plugin.json` `userConfig`. Attempt `"sensitive": true` on the token field. **Open caveat:**
  no `sensitive` flag is documented in this repo or the bundled official plugin-dev docs — masking
  is an unverified assumption; if Claude Code rejects or ignores it, fall back to a plain string
  field and rely on `.env` for the real secret. `verify-structure.py` does not constrain inner
  field shape, so extra keys pass structure validation regardless.
- Extend `hooks/utils/config.py`: `snyk_enabled()` (parse the bool via `_option`), `snyk_token()`
  (via `_option("SNYK_TOKEN")`).
- Write `hooks/utils/snyk.py` with the injectable-command scanner + defensive `--json` parser.

### Phase 2: Core Implementation

The two entrypoints.

- SessionStart wrapper `hooks/snyk_agent_scan.py`.
- Pre-commit entrypoint `scripts/snyk-agent-scan.py`.

### Phase 3: Integration & Polish

Wiring, secrets template, docs, version bump, tests.

- Wire `hooks.json` SessionStart + `.pre-commit-config.yaml` local hook.
- `.env.sample` `SNYK_TOKEN=`; README/docs; version bump; Makefile note; tests.

## Step by Step Tasks

IMPORTANT: Execute every step in order, top to bottom.

### 1. Empirically pin the scanner contract (do this first)

- With a valid `SNYK_TOKEN`, run against a known-good and a known-bad artifact and record both the
  exit code and the JSON shape:
  - `uvx snyk-agent-scan@latest --json <path/to/SKILL.md>; echo "exit=$?"`
  - `uvx snyk-agent-scan@latest --json --ci <path/to/skills-dir>; echo "exit=$?"`
- Capture the exact `--json` field names for findings and severity (Critical/High/Medium/Low). The
  parser in `snyk.py` keys off these; do not assume names.
- Confirm behavior with **no** `--dangerously-run-mcp-servers` when the target contains only
  `SKILL.md`/markdown (must not attempt to launch servers, must not prompt). Record the safe flag
  set.

### 2. Add userConfig fields + bump version

- Edit `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json`: add the two `userConfig` fields
  (shape: `type`/`title`/`description`/`default`/`required`, matching existing fields); set
  `version` to `0.17.0`.
- Edit `.claude-plugin/marketplace.json`: set the `agent-harness` entry `version` to `0.17.0`.

### 3. Extend the config resolver

- Add `snyk_enabled()` / `snyk_token()` to `hooks/utils/config.py` using `_option`.

### 4. Write the shared scan helper

- `hooks/utils/snyk.py`: `run_scan()` builds argv from `SNYK_AGENT_SCAN_CMD` (default
  `["uvx","snyk-agent-scan@latest"]`), appends `--json` + targets, runs via `subprocess.run` with a
  `timeout`, sets `SNYK_TOKEN` in the child env. Returns a `ScanResult` (findings list, severity
  counts, raw stdout, ok/skip/error state). `summarize()` renders a short human string
  (e.g. "Snyk agent-scan: 2 High, 1 Medium in 3 skills — run `uvx snyk-agent-scan@latest .claude/skills`").

### 5. Write the SessionStart wrapper

- `hooks/snyk_agent_scan.py` (PEP 723, `#!/usr/bin/env -S uv run --script`, dep `python-dotenv`):
  read hook JSON from stdin; `load_dotenv()`; if `not snyk_enabled()` or `not snyk_token()` →
  emit nothing and `sys.exit(0)`. Resolve targets = skill roots under cwd (e.g. `.claude/skills`,
  `plugins/**/skills`) — **static artifacts only, never `mcp.json`** to avoid launching servers.
  Run scan with a short timeout (e.g. 60s); on timeout/error → exit 0 silently. On findings, print
  `{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": <summary>}}` and
  exit 0. Optional throttle: skip if a scan ran in the last N hours (timestamp in the plugin
  `logs/` dir) to avoid re-scanning on every session.

### 6. Write the pre-commit entrypoint

- `scripts/snyk-agent-scan.py` (PEP 723, `#!/usr/bin/env -S uv run --script --quiet`, dep
  `python-dotenv`): `load_dotenv()`; if `not snyk_token()` → `sys.exit(0)` **silently** (contributors
  without a token are unaffected). Filter argv paths to skill/agent/command markdown; if none →
  exit 0. Run scan; print findings. Exit 0 unless `os.environ.get("SNYK_AGENT_SCAN_ENFORCE") == "1"`
  **and** High/Critical count > 0, in which case exit 1. Import the shared helper via
  `sys.path.insert(0, "plugins/boss-dev/agent-harness/hooks")`.

### 7. Wire the hooks

- `hooks.json`: append to the `SessionStart` array a new
  `{"matcher": "", "hooks": [{"type": "command", "command": "uv run \"${CLAUDE_PLUGIN_ROOT}\"/hooks/snyk_agent_scan.py"}]}`.
- `.pre-commit-config.yaml`: add under `repo: local`:

  ```yaml
  - id: snyk-agent-scan
    name: Snyk agent-scan (advisory)
    entry: uv run scripts/snyk-agent-scan.py
    language: system
    pass_filenames: true
    files: ^(plugins/.+/(SKILL\.md|agents/.+\.md|commands/.+\.md)|\.claude/skills/.+/SKILL\.md|\.claude/commands/.+\.md)$
  ```

### 8. Secrets template + docs

- `.env.sample`: add `SNYK_TOKEN=` (empty; never read `.env` via tools — the repo's `PreToolUse`
  guard blocks `.env` access; rely on `load_dotenv()` + `os.environ` at runtime only).
- Update `plugins/boss-dev/agent-harness/README.md` and `docs/hooks.md`: document
  `ENABLE_SNYK_AGENT_SCAN`, `SNYK_TOKEN`, the `CLAUDE_PLUGIN_OPTION_*` → bare-env resolution order,
  the SessionStart hook, and the advisory/enforce pre-commit behavior. Match existing doc style;
  keep `rumdl` happy.

### 9. Makefile note (optional)

- Add an advisory `snyk-scan` target (`uvx snyk-agent-scan@latest .claude/skills || true`) and a
  help line noting `make install` does not run `pre-commit install`.

### 10. Tests

- `tests/test_snyk_agent_scan.py` with a fake scanner via `SNYK_AGENT_SCAN_CMD`. Cover: no token →
  skip exit 0 (both); disabled → skip; fake Critical findings → advisory prints exit 0, enforce
  exit 1; no relevant staged files → exit 0; SessionStart emits valid `hookSpecificOutput` JSON;
  timeout → exit 0. Pure functions (`severity_counts`, `summarize`, target filtering) tested via
  `importlib` load; CLI exit-code semantics via `subprocess` (`sys.executable`) per the repo's
  PEP 723 testing exception.

### 11. Validate

- Run the validation commands below; fix all lint/type/test failures before completion.

## Testing Strategy

- **No network in tests.** Inject `SNYK_AGENT_SCAN_CMD` pointing at a fake script that echoes canned
  `--json` payloads (clean, and High/Critical) so gating logic is exercised deterministically.
- **Unit** (`importlib`): `severity_counts`, `summarize`, target/path filtering, gating decision.
- **CLI/behavioral** (`subprocess`): the skip-without-token, disabled, advisory-vs-enforce,
  no-files, timeout, and SessionStart `additionalContext`-emission paths.
- **Manual smoke** (needs a real token): run both hooks against this repo's `.claude/skills` and
  confirm advisory output + non-blocking exit.

## Acceptance Criteria

- With `ENABLE_SNYK_AGENT_SCAN=false` **or** no resolvable `SNYK_TOKEN`: both hooks exit 0 and
  produce no blocking output (SessionStart emits no context; pre-commit is a silent no-op).
- With enable=true + a valid token: SessionStart injects a findings summary via `additionalContext`
  and never blocks; pre-commit prints findings and exits 0 (advisory).
- `SNYK_AGENT_SCAN_ENFORCE=1` + High/Critical staged findings → pre-commit exits non-zero.
- No MCP stdio server is ever launched by either hook (targets are static skill artifacts;
  `--dangerously-run-mcp-servers` is never passed).
- `SNYK_TOKEN=` is present in `.env.sample`; no code reads `.env` directly.
- `plugin.json` and `marketplace.json` both show `agent-harness` `0.17.0`.
- `make lint`, `make check`, and the new tests pass; `verify-structure.py` passes.

## Validation Commands

Execute these commands to validate the task is complete:

- `uv run scripts/verify-structure.py` — plugin/marketplace structure + version parity.
- `make lint` — codespell + ruff check/format + basedpyright over `scripts/`, `plugins/`.
- `make check` — `ty` type check.
- `uv run pytest -s tests/test_snyk_agent_scan.py` — the new test suite (fake scanner, no network).
- `make markdown-lint` — rumdl over README/docs edits.
- `pre-commit run snyk-agent-scan --all-files` — exercises the local hook (silent no-op without a
  token; advisory with one).
- Confirm the SessionStart wrapper emits valid JSON (or nothing) and exits 0:
  `echo '{"session_id":"x","source":"startup"}' | uv run plugins/boss-dev/agent-harness/hooks/snyk_agent_scan.py`

## Notes

- **Filename:** this spec lives at `specs/synk.md` (requested spelling) even though the tool is
  `snyk-agent-scan`.
- **`sensitive` flag is unverified** — see Phase 1 caveat. The dependable secret path is `.env` /
  `SNYK_TOKEN`; the `userConfig` token field is a convenience that may or may not be masked by the
  Claude Code UI.
- **Undocumented exit codes** — the whole design deliberately parses `--json` severity rather than
  trusting exit status; Step 1 pins the real contract before finalizing the parser.
- **Not offline** — both hooks are network-dependent and therefore fail-open; this is intentional so
  offline commits and token-less contributors are never blocked.
- **`snyk-agent-scan guard`** exists (Snyk's own Claude Code hook installer) and was considered; the
  hand-rolled wrapper was chosen for control, graceful skip, and consistency with the plugin's
  existing PEP 723 hooks. `guard` remains a future alternative to evaluate.
- No new Python dependency beyond `python-dotenv` (already used); the scanner runs via `uvx`.
