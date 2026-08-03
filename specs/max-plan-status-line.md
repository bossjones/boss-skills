# Plan: Max-plan vs API auth badge in `status_line_v10.py` + global status-line installer

## Task Description

Two related pieces of work for the `agent-harness` plugin:

1. **Auth badge in the status line.** Teach
   [`status_lines/status_line_v10.py`](../plugins/boss-dev/agent-harness/status_lines/status_line_v10.py)
   to report whether the current session is billed against a Claude.ai subscription (Pro/Max) or an
   API key, using the `rate_limits` object that Claude Code includes in the status-line stdin
   payload. Built test-first.

2. **Programmatic global install.** Add a new plugin `userConfig` option that records whether the
   user wants this status line enabled globally, plus a `uv run` Python script that installs the
   `statusLine` block into `~/.claude/settings.json` — backing up, editing, validating, and
   atomically saving — with a first-class path back out (`--uninstall` for a surgical removal,
   `--restore` for a verbatim revert to the pre-install file). A slash command wraps the script.

Constraints from the request: **TDD**, **KISS**, `uv run` Python script, reversible, done on a git
worktree feature branch with a PR.

## Objective

When this plan is complete:

- `status_line_v10.py` renders a leading `[MAX]` / `[API]` / `[?]` badge next to the model name, with
  no false "API" reading during the pre-first-response window of a subscription session.
- `agent-harness` exposes an `ENABLE_GLOBAL_STATUS_LINE` (boolean) and `STATUS_LINE_VARIANT` (string)
  `userConfig` pair.
- `scripts/install_status_line.py` can install, check, uninstall, and restore the global
  `statusLine` setting without ever corrupting or silently clobbering `~/.claude/settings.json`.
- Both are covered by unit tests in `tests/`, and `make lint && make test` are clean.

---

## Problem Statement

Claude Code gives no direct signal in its UI for which billing path a session is on. Subscription
sessions and API-key sessions look identical, but they have very different cost consequences — the
existing v10 cost readout (`$0.0421`) is *list-price arithmetic from the transcript*, which is
meaningful on an API key and purely notional on a Max plan. A badge that says which regime you're in
makes the adjacent cost figure interpretable.

### Verified mechanism (checked against the shipped CLI, not assumed)

The premise for this feature came from a chat answer, so it was verified directly against the
installed binary (`~/.local/bin/claude`, **v2.1.220**) before writing this spec. The status-line
payload builder constructs its `rate_limits` field like this:

```js
let A = DYr(), I = {
  ...A.five_hour && {five_hour: {used_percentage: A.five_hour.utilization * 100, resets_at: A.five_hour.resets_at}},
  ...A.seven_day && {seven_day: {used_percentage: A.seven_day.utilization * 100, resets_at: A.seven_day.resets_at}}
};
return { ..., ...(I.five_hour || I.seven_day) && {rate_limits: I}, ... }
```

Three findings that materially shape the implementation:

- **`rate_limits` is emitted only when at least one window exists.** The whole key is spread away
  when both `five_hour` and `seven_day` are missing. So presence ⇒ subscription; absence ⇒ *either*
  API key *or* subscription-before-first-response. Confirms the caveat.
- **The status-line shape is NOT the SDK's `RateLimitInfo`.** The SDK dataclass
  (`claude_agent_sdk.types.RateLimitInfo`) has `status` / `utilization` / `rate_limit_type`. The
  status-line payload has neither — it exposes `used_percentage` (already `utilization * 100`) and
  `resets_at`, keyed by window name. Code written against the SDK shape would read `None` forever.
  We only depend on **presence of the `rate_limits` key**, which is the narrowest possible coupling.
- **There is no explicit auth field anywhere in the payload.** The full returned object is
  `cwd, session_name?, model, workspace, version, output_style, cost, context_window,
  exceeds_200k_tokens, fast_mode, effort?, thinking, rate_limits?, vim?, agent?, remote?, pr?,
  worktree?`. `rate_limits` is the *only* available tell, so this is an inference, not a reported
  fact — the spec treats it as such and the docs will say so.

### The tri-state problem, and its fix

A naive `if .rate_limits then "MAX" else "API"` is wrong at session start on a Max plan. But a naive
tri-state that shows `?` on absence is *also* wrong: on a genuine API key `rate_limits` never
arrives, so the badge would read `?` forever and never say `API`.

The disambiguator is already in the file. `compute_session_cost()` walks the transcript JSONL
counting `message.usage` entries. **If the transcript contains at least one assistant `usage` entry,
an API response has already landed in this session** — so absence of `rate_limits` at that point is
genuine, not pending. This resolves the tri-state exactly, from a pass over data v10 already reads:

| `rate_limits` present | assistant `usage` seen in transcript | badge |
| --- | --- | --- |
| yes | — | `MAX` |
| no | yes | `API` |
| no | no | `?` |

No cross-session cache, no clock, no extra file read.

### The `${CLAUDE_PLUGIN_ROOT}` trap

[`docs/status-lines.md`](../plugins/boss-dev/agent-harness/docs/status-lines.md) currently tells
users to wire up `"command": "uv run \"${CLAUDE_PLUGIN_ROOT}\"/status_lines/status_line_v10.py"`.
`CLAUDE_PLUGIN_ROOT` is substituted for **plugin-owned** hook/command entries; a `statusLine` block
in a user's `~/.claude/settings.json` has no owning plugin, and a string `command` runs through a
shell, so an unset variable expands to the empty string and yields a broken path. **The installer
therefore writes a fully resolved absolute path** derived from `Path(__file__)`, which is correct
for both a repo checkout and a marketplace install. The docs get a note to match.

---

## Solution Approach

Two independent, separately testable units, plus config and docs.

**Unit 1 — badge (pure functions in `status_line_v10.py`).** Replace `compute_session_cost()` with a
single-pass `scan_transcript()` returning a small frozen dataclass carrying both the cost and an
`assistant_usage_count`. Add `detect_auth_mode()` (pure: payload dict + a bool → one of three
literals) and `format_auth_badge()` (pure: literal → colored string). `generate_status_line()`
merges the badge into the existing first segment. Every new function is pure and directly unit
testable with synthetic dicts — no stdin, no subprocess, no filesystem except a `tmp_path` JSONL.

**Unit 2 — installer (`scripts/install_status_line.py`).** Deliberately modeled on the repo's
existing precedent, [`scripts/symlink_plugins.py`](../scripts/symlink_plugins.py), which already
solves this exact class of problem (mutate files the user owns, timestamped backup dir + manifest +
`latest` pointer, `--check` dry run, `--restore` undo, explicit path injection instead of
monkeypatched globals so the engine is testable). Reusing that shape means the reviewer, the test
suite, and the mental model are all already established in this repo.

Separation of concerns inside the installer:

- **Pure planner** — `plan(settings: dict, desired: dict) -> Plan`. No I/O. Classifies into
  `INSTALL` (no `statusLine` key), `CURRENT` (already exactly ours — no-op), `REPLACE_OURS` (ours,
  different variant/path), `FOREIGN` (someone else's statusLine — refuse without `--force`).
- **Mutating engine** — `execute()` / `restore()` / `uninstall()`, each taking explicit
  `settings_path` and `backup_root` arguments so tests drive them entirely under `tmp_path`.

**Unit 3 — consent.** `ENABLE_GLOBAL_STATUS_LINE` (boolean, default `false`) and
`STATUS_LINE_VARIANT` (string, default `status_line_v10.py`) in `plugin.json` `userConfig`. Per the
chosen rollout, **no hook ever writes `~/.claude/settings.json` unattended**. The flag is a declared
preference; the slash command reads
`CLAUDE_PLUGIN_OPTION_ENABLE_GLOBAL_STATUS_LINE` and refuses to install when it is unset/false,
directing the user to `/plugin` → Configure. `--yes` overrides for scripted use. This keeps the
"userconfig asks the user" requirement while keeping the global-settings write explicit.

### Write safety (the core of the "backup, edit, validate, save" ask)

Ordered, fail-closed:

1. **Read.** If `~/.claude/settings.json` exists but is not valid JSON → **abort**, touch nothing.
   Never write over a file we could not parse.
2. **Plan.** Pure. `CURRENT` exits 0 without a backup (idempotent re-runs leave no backup litter).
   `FOREIGN` exits non-zero with the conflicting command printed.
3. **Back up.** `shutil.copy2` the original to
   `~/.claude/backups/agent-harness-status-line/<UTC-timestamp>/settings.json`, write a
   `manifest.json` (`settings_path`, `existed`, `backup_path`, `plan_kind`, `variant`, `version`),
   and update the `latest` pointer file. If the settings file did **not** exist, record
   `existed: false` so `--restore` deletes the file rather than resurrecting an empty one.
4. **Render + validate.** Serialize the mutated dict, then `json.loads()` the rendered *string* to
   prove it round-trips before any bytes touch the target.
5. **Atomic save.** Write to a `settings.json.<pid>.tmp` sibling in the same directory, then
   `os.replace()`. Same-filesystem rename ⇒ no torn file even on crash mid-write.

Indent is sniffed from the original file (first indented line; default 2) so installing does not
reformat the user's whole settings file into a spurious diff. Key order is preserved by mutating the
loaded `dict` in place — `statusLine` is appended if new.

**Two distinct exits**, because they answer different regrets:

- `--uninstall` — surgically `del settings["statusLine"]` if and only if it is ours. Keeps every
  other edit the user made since installing.
- `--restore` — the literal ask ("revert to the original settings.json file"): copy the latest
  backup back verbatim, discarding anything changed since. Prints a warning naming what it will
  overwrite and requires `--yes` when stdin is not a TTY.

---

## Relevant Files

- [`plugins/boss-dev/agent-harness/status_lines/status_line_v10.py`](../plugins/boss-dev/agent-harness/status_lines/status_line_v10.py)
  — the target. 284 lines; `compute_session_cost()` (L170) and `generate_status_line()` (L221) are
  the two functions that change.
- [`scripts/symlink_plugins.py`](../scripts/symlink_plugins.py) — **architectural template** for the
  installer: `BACKUP_ROOT_REL` / `LATEST_POINTER` / `MANIFEST_NAME` constants (L77–79), `Action` /
  `RunResult` dataclasses (L92–110), `restore()` (L498), `--check`/`--restore`/`--yes` argparse
  surface (L626+). Mirror its conventions; do not invent new ones.
- [`tests/test_symlink_plugins.py`](../tests/test_symlink_plugins.py) — **test template**: the
  `_load()` `importlib.util.spec_from_file_location` helper for PEP 723 scripts, and the
  "inject explicit roots, never monkeypatch module globals" discipline. Copy both.
- [`plugins/boss-dev/agent-harness/.claude-plugin/plugin.json`](../plugins/boss-dev/agent-harness/.claude-plugin/plugin.json)
  — `userConfig` block (v0.29.0 → 0.30.0).
- [`.claude-plugin/marketplace.json`](../.claude-plugin/marketplace.json) — version parity with the
  above; the `version-bump-reviewer` skill enforces this.
- [`devtools/lint.py`](../devtools/lint.py) — `SRC_PATHS` already covers `plugins/` for ruff;
  `TYPE_CHECK_PATHS` (L16+) is a narrow allowlist and must gain the new installer.
- [`plugins/boss-dev/agent-harness/docs/status-lines.md`](../plugins/boss-dev/agent-harness/docs/status-lines.md)
  — v10 row, new auth-badge section, global-install section, `${CLAUDE_PLUGIN_ROOT}` correction.
- [`plugins/boss-dev/agent-harness/docs/commands.md`](../plugins/boss-dev/agent-harness/docs/commands.md)
  and [`README.md`](../plugins/boss-dev/agent-harness/README.md) — command tables (L104, L344–359).
- [`plugins/boss-dev/agent-harness/commands/update_status_line.md`](../plugins/boss-dev/agent-harness/commands/update_status_line.md)
  — naming/format precedent for the new command.

### New Files

- `plugins/boss-dev/agent-harness/scripts/install_status_line.py` — the installer. New `scripts/`
  directory under the plugin; `verify-structure.py` enforces no top-level allowlist, so this is safe.
  Kept out of `status_lines/` because that directory is documented as "ten status-line scripts" and
  is mirrored wholesale into `.claude/status_lines/` by `symlink_plugins.py`.
- `plugins/boss-dev/agent-harness/commands/install_status_line.md` — slash command wrapper
  (`/agent-harness:install_status_line`), pairing with the existing `update_status_line`.
- `tests/test_status_line_v10.py` — badge + transcript-scan unit tests.
- `tests/test_install_status_line.py` — planner + engine + restore tests, all under `tmp_path`.

---

## Implementation Phases

### Phase 1: Foundation

Write both test files first, red. Establish the `_load()` importlib harness for the two PEP 723
scripts and the synthetic-payload builders. No production code yet.

### Phase 2: Core Implementation

Badge functions in `status_line_v10.py` until its suite is green; then the installer's pure planner,
then its mutating engine, then restore/uninstall — each to green before the next.

### Phase 3: Integration & Polish

`userConfig` entries, slash command, docs, `lint.py` type-check registration, version bump +
marketplace parity, manual end-to-end verification against a real `~/.claude/settings.json` copy,
PR.

---

## Step by Step Tasks

IMPORTANT: Execute every step in order, top to bottom. Steps 1, 3, 5, and 7 are **red** — they must
fail before the following step makes them pass. Do not write production code ahead of its test.

### 1. Write `tests/test_status_line_v10.py` (RED)

- Add the `_load()` importlib helper (copied from `tests/test_symlink_plugins.py`) pointed at
  `plugins/boss-dev/agent-harness/status_lines/status_line_v10.py`.
- Add a `_payload(**overrides)` builder producing a minimal valid status-line dict.
- Add a `_transcript(tmp_path, entries)` builder writing JSONL lines.
- Assert on `scan_transcript`, `detect_auth_mode`, `format_auth_badge`, `generate_status_line`
  (see Testing Strategy for the full case list). These fail with `AttributeError` — that is the
  expected red.

### 2. Implement the badge in `status_line_v10.py` (GREEN)

- Add `from dataclasses import dataclass` and `from typing import Literal`.
- Add `AuthMode = Literal["max", "api", "pending"]`.
- Add a frozen `TranscriptStats` dataclass: `cost_usd: float`, `assistant_usage_count: int`.
- Rename `compute_session_cost()` → `scan_transcript(transcript_path) -> TranscriptStats`, keeping
  the existing per-line parsing and the existing "return zeros on any failure" contract; increment
  `assistant_usage_count` on every entry that yields a `message.usage` dict.
- Keep a one-line `compute_session_cost(path) -> float` wrapper delegating to `scan_transcript`, so
  the public name documented in the README keeps working.
- Add `detect_auth_mode(input_data: dict, saw_usage: bool) -> AuthMode` implementing the truth table
  above. Treat a present-but-falsy `rate_limits` (`{}`, `None`) as absent — the CLI never emits an
  empty one, but a defensive truthiness check costs nothing.
- Add `format_auth_badge(mode: AuthMode) -> str` → `GREEN[MAX]`, `YELLOW[API]`, `DIM[?]`.
- In `generate_status_line()`, call `scan_transcript()` once (replacing the `compute_session_cost`
  call, so the transcript is still read exactly once), derive the mode, and make the first segment
  `f"{badge} {CYAN}[{model_name}]{RESET}"`.
- Update the module docstring's example line to include the badge.

### 3. Write `tests/test_install_status_line.py` (RED)

- `_load()` the not-yet-existing installer. Add planner cases, engine cases, restore/uninstall
  cases, and the malformed-JSON abort case (see Testing Strategy).

### 4. Implement the installer's pure core (GREEN, part 1)

- Create `plugins/boss-dev/agent-harness/scripts/install_status_line.py` with the PEP 723 header
  (`requires-python = ">=3.13"`, `dependencies = ["rich>=13.0.0"]`) matching `symlink_plugins.py`.
- Constants: `BACKUP_ROOT = Path.home() / ".claude" / "backups" / "agent-harness-status-line"`,
  `LATEST_POINTER = "latest"`, `MANIFEST_NAME = "manifest.json"`, `SETTINGS_REL =
  Path(".claude") / "settings.json"`, `DEFAULT_VARIANT = "status_line_v10.py"`, and plan-kind
  constants `INSTALL` / `CURRENT` / `REPLACE_OURS` / `FOREIGN`.
- `resolve_variant_path(variant, plugin_root=None) -> Path` — `Path(__file__).resolve().parent.parent
  / "status_lines" / variant`; raise `FileNotFoundError` for an unknown variant, and reject a
  `variant` containing a path separator or `..` (it comes from user config).
- `build_status_line_block(script_path: Path) -> dict` → `{"type": "command", "command": f'uv run
  "{script_path}"', "padding": 0}`. Absolute path, quoted for spaces.
- `is_ours(block: dict) -> bool` — a `statusLine` whose `command` resolves into the plugin's
  `status_lines/` directory.
- `plan(settings: dict, desired: dict) -> Plan` — pure classification, no I/O.
- `sniff_indent(text: str) -> int` — leading-space count of the first indented line, default 2.

### 5. Extend the installer tests to the mutating engine (RED, part 2)

- Only if step 3 left engine cases stubbed; otherwise this is already red from step 3.

### 6. Implement the installer's engine and CLI (GREEN, part 2)

- `execute(settings_path, backup_root, desired, *, force=False) -> int` — the ordered read → plan →
  back up → render → validate → `os.replace` sequence from Solution Approach. Creates parent dirs
  when the settings file is absent.
- `write_backup(settings_path, backup_root, plan_kind, variant) -> Path` — timestamped dir, `copy2`,
  `manifest.json`, `latest` pointer. Timestamp is `datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")`
  with a `-1`, `-2` … suffix on collision.
- `uninstall(settings_path, *, force=False) -> int` — remove `statusLine` only when `is_ours()`;
  same backup + atomic-save path.
- `restore(backup_root, *, yes=False) -> int` — read `latest`, honor `existed: false` by unlinking,
  else `copy2` back. Print what will be overwritten; require `--yes` when `not sys.stdin.isatty()`.
- `check(settings_path, desired) -> int` — dry run printing the plan kind; exit `0` for
  `CURRENT`/`INSTALL`, `1` for `FOREIGN`. Suitable for CI.
- `main(argv=None) -> int` with argparse: default action install; flags `--check`, `--uninstall`,
  `--restore`, `--variant`, `--settings PATH`, `--backup-root PATH`, `--force`, `--yes`. Mutually
  exclusive group for the four actions.
- `if __name__ == "__main__": raise SystemExit(main())`.

### 7. Add the `userConfig` entries

- In `plugin.json`, add to `userConfig`:
  - `ENABLE_GLOBAL_STATUS_LINE` — `boolean`, default `false`, title "Enable the agent-harness status
    line globally", description stating that enabling it authorizes
    `/agent-harness:install_status_line` to write `~/.claude/settings.json` (with a backup), and that
    `--restore` reverts.
  - `STATUS_LINE_VARIANT` — `string`, default `"status_line_v10.py"`, description listing that any
    filename from `status_lines/` is valid.

### 8. Add the slash command

- Create `commands/install_status_line.md` following the frontmatter shape of
  `update_status_line.md` (`description`, `argument-hint: "[--check|--uninstall|--restore]"`).
- Workflow: read `CLAUDE_PLUGIN_OPTION_ENABLE_GLOBAL_STATUS_LINE`; if unset/false, stop and tell the
  user to enable it via `/plugin` → Configure (or pass `--yes`). Otherwise run the script with
  `uv run` and report the plan kind, backup path, and the exact revert command.

### 9. Register the installer for type checking

- Append `f"{_AGENT_HARNESS_PLUGIN}/scripts/install_status_line.py"` to `TYPE_CHECK_PATHS` in
  `devtools/lint.py`, adding the plugin-root constant alongside the existing `_AGENT_HARNESS_SKILLS`.

### 10. Update documentation

- `docs/status-lines.md`: new "Auth badge (Max vs API)" section with the truth table, an explicit
  "this is inferred from `rate_limits`, not a reported fact" caveat; new "Installing globally"
  section covering install/check/uninstall/restore and the backup location; correct the
  `${CLAUDE_PLUGIN_ROOT}` wiring guidance to note it does not expand in user settings.
- `docs/commands.md` + `README.md`: add `install_status_line` to both command tables; update the v10
  row in both status-line tables to mention the badge.

### 11. Bump the version

- `plugin.json` `0.29.0` → `0.30.0` (minor: additive feature, no breaking change).
- Matching `version` in the `agent-harness` entry of `.claude-plugin/marketplace.json`.

### 12. Validate

- Run every command in Validation Commands below.
- Manual end-to-end: copy the real `~/.claude/settings.json` to a scratch path, run the script
  against it with `--settings`, confirm the block lands, `--check` reports `CURRENT`, `--uninstall`
  removes it, and `--restore` reproduces the original byte-for-byte.
- Manual badge check: pipe a hand-built payload with and without `rate_limits` into
  `status_line_v10.py` and confirm all three badge states render.

---

## Testing Strategy

All tests are plain `pytest` under `tests/`, loading the PEP 723 scripts via
`importlib.util.spec_from_file_location` — the pattern established by `tests/test_symlink_plugins.py`
and required by `CLAUDE.md` (the `if __name__ == "__main__"` guard keeps import side-effect-free).
The installer engine takes explicit `settings_path` / `backup_root` arguments, so **no test
monkeypatches module globals and no test touches the real `~/.claude/`**.

### `tests/test_status_line_v10.py`

`detect_auth_mode` (pure, table-driven):

- `rate_limits` with `five_hour` only → `"max"`
- `rate_limits` with `seven_day` only → `"max"`
- `rate_limits` with both → `"max"`
- no `rate_limits`, `saw_usage=True` → `"api"`
- no `rate_limits`, `saw_usage=False` → `"pending"`
- `rate_limits: {}` and `rate_limits: None`, `saw_usage=True` → `"api"` (falsy treated as absent)
- **regression guard for the SDK-shape trap:** a payload carrying the *SDK* shape
  (`{"status": "allowed", "utilization": 0.42}`) still yields `"max"` — asserts we key off presence,
  not off any inner field name.

`scan_transcript`:

- missing path / `None` / empty string → `TranscriptStats(0.0, 0)`
- a JSONL with two assistant `usage` entries → `assistant_usage_count == 2` and a cost matching a
  hand-computed expectation (pins the cache multipliers)
- malformed lines and blank lines are skipped without raising, and do not inflate the count
- entries without `message.usage` do not increment the count

`format_auth_badge`: each of the three modes contains its expected label and the expected ANSI
prefix.

`generate_status_line` (integration over the pure layer):

- a Max payload renders `[MAX]` before `[Opus 5]` and still renders the context bar, `%`, tokens
  left, session id, and cost — i.e. **the badge is additive and nothing regressed**
- an API payload with a used transcript renders `[API]`
- an empty payload `{}` does not raise and renders `[?]`

`main` robustness: invalid JSON on stdin still exits `0` (the existing never-break-the-status-line
contract) — exercised by subprocess, per the `CLAUDE.md` carve-out for CLI-semantics assertions.

### `tests/test_install_status_line.py`

`plan` (pure):

- settings without `statusLine` → `INSTALL`
- settings with an identical block → `CURRENT`
- settings with our block pointing at a different variant → `REPLACE_OURS`
- settings with a third-party `statusLine` → `FOREIGN`

`execute` (under `tmp_path`):

- absent settings file → created, contains the block, manifest records `existed: false`
- existing settings file → all pre-existing keys survive, key order preserved, indent preserved
  (4-space in, 4-space out), backup exists and matches the original byte-for-byte
- re-running when `CURRENT` → exit `0`, **no new backup directory created** (idempotent)
- `FOREIGN` → non-zero exit, settings file **unmodified**
- `FOREIGN` with `--force` → replaced, original preserved in the backup
- settings file containing malformed JSON → non-zero exit, file left byte-identical (fail-closed)
- no `.tmp` file remains in the directory after a successful run

`resolve_variant_path`: a variant containing `/` or `..` raises; an unknown filename raises
`FileNotFoundError`.

`uninstall`: removes only our block, leaves other keys; refuses on a foreign block without `--force`.

`restore`: after install, restores the original byte-for-byte; when the manifest says
`existed: false`, deletes the file; with no `latest` pointer, exits `0` with a "nothing to restore"
message (matching `symlink_plugins.restore()`'s behavior).

### Edge cases explicitly covered

- Backup timestamp collision within the same second → `-1` suffix, no overwrite.
- `~/.claude/settings.json` absent entirely (fresh machine).
- Settings file present but empty (`""`) → treated as malformed, fail-closed.
- A variant filename supplied from `STATUS_LINE_VARIANT` user config is untrusted input and is
  path-validated.

---

## Acceptance Criteria

1. `status_line_v10.py` prints `[MAX]` when the payload contains a non-empty `rate_limits`, `[API]`
   when it does not and the transcript shows at least one assistant `usage` entry, and `[?]`
   otherwise.
2. The badge depends only on the **presence** of `rate_limits`, never on `utilization`, `status`, or
   any other inner field — proven by the SDK-shape regression test.
3. The transcript is read exactly once per status-line invocation (cost and usage count come from
   the same pass); the existing cost, context bar, percentage, tokens-left, cwd, branch, and session
   id segments are unchanged.
4. `status_line_v10.py` still exits `0` and prints something on every input, including invalid JSON.
5. `plugin.json` declares `ENABLE_GLOBAL_STATUS_LINE` (boolean, default `false`) and
   `STATUS_LINE_VARIANT` (string, default `status_line_v10.py`).
6. `install_status_line.py` writes a `statusLine` block containing an **absolute** path to the chosen
   variant — no `${CLAUDE_PLUGIN_ROOT}`.
7. Every mutation is preceded by a timestamped backup with a `manifest.json` and an updated `latest`
   pointer; a no-op run creates no backup.
8. The installer never writes to a settings file it could not parse, and never leaves a partial file
   (temp-file + `os.replace`).
9. A pre-existing third-party `statusLine` is never clobbered without `--force`.
10. `--restore` reproduces the pre-install `~/.claude/settings.json` byte-for-byte;
    `--uninstall` removes only our block and preserves later user edits.
11. No hook or automatic process writes `~/.claude/settings.json` — installation only happens when
    the user runs the command.
12. New tests exist in `tests/test_status_line_v10.py` and `tests/test_install_status_line.py`, and
    no test reads or writes the real `~/.claude/`.
13. `make lint` and `make test` pass with zero warnings; the installer is in `TYPE_CHECK_PATHS` and
    passes `basedpyright`.
14. `plugin.json` and `marketplace.json` both read `0.30.0`.

---

## Validation Commands

```bash
make lint
```

```bash
uv run pytest -s tests/test_status_line_v10.py tests/test_install_status_line.py
```

```bash
make test
```

```bash
./scripts/verify-structure.py
```

```bash
make markdown-lint
```

Badge smoke test — expect a leading `[MAX]`:

```bash
echo '{"model":{"display_name":"Opus 5"},"rate_limits":{"five_hour":{"used_percentage":42.0,"resets_at":1234567890}},"context_window":{"used_percentage":12.5,"context_window_size":200000}}' | uv run plugins/boss-dev/agent-harness/status_lines/status_line_v10.py
```

Badge smoke test — expect a leading `[?]` (no rate limits, no transcript):

```bash
echo '{"model":{"display_name":"Opus 5"},"context_window":{"used_percentage":12.5,"context_window_size":200000}}' | uv run plugins/boss-dev/agent-harness/status_lines/status_line_v10.py
```

Installer dry run against the real settings file (read-only, safe):

```bash
uv run plugins/boss-dev/agent-harness/scripts/install_status_line.py --check
```

Full install/revert round trip against a scratch copy:

```bash
cp ~/.claude/settings.json /tmp/settings-probe.json && uv run plugins/boss-dev/agent-harness/scripts/install_status_line.py --settings /tmp/settings-probe.json && uv run plugins/boss-dev/agent-harness/scripts/install_status_line.py --settings /tmp/settings-probe.json --check && uv run plugins/boss-dev/agent-harness/scripts/install_status_line.py --settings /tmp/settings-probe.json --restore --yes && diff ~/.claude/settings.json /tmp/settings-probe.json && echo "round trip clean"
```

---

## Notes

- **No new dependencies.** The installer uses `rich>=13.0.0` via PEP 723 inline metadata, matching
  `scripts/symlink_plugins.py`; nothing is added to `pyproject.toml`. No `uv add` required.
- **`rate_limits` is an inference, not a reported fact.** Claude Code exposes no auth-source field in
  the status-line payload. If a future CLI version emits `rate_limits` for API-key sessions, or adds
  a real auth field, the badge logic is one pure function (`detect_auth_mode`) and one test table to
  update. The docs will state the inference explicitly so nobody treats `[MAX]` as authoritative for
  billing.
- **Verified against CLI v2.1.220.** The payload shape above was read out of the shipped binary. Note
  it is unversioned and undocumented; the narrow key-presence coupling is deliberate insulation.
- **Fields available but deliberately unused.** The payload also carries `session_name`, `fast_mode`,
  `effort.level`, `thinking.enabled`, `vim.mode`, `agent.name`, `remote.session_id`,
  `pr.{number,url,review_state,kind}`, `worktree.{name,path,branch,original_cwd,original_branch}`,
  `workspace.{added_dirs,git_worktree,repo}`, and `cost.total_cost_usd`. All out of scope here;
  worth a follow-up issue for a future status-line variant. In particular `cost.total_cost_usd` is
  the CLI's own cost figure and could eventually replace v10's transcript arithmetic.
- **v10 changes contract.** Editing v10 in place (as directed) means the documented "v10 =
  context bar + cost" description shifts to "+ auth badge"; both status-line tables are updated in
  step 10 to match. Anyone already pointing at v10 gets the badge on next session with no action.
- **`.claude/status_lines/` is a symlink mirror.** `scripts/symlink_plugins.py` mirrors the plugin's
  `status_lines/` into `.claude/`, so the v10 edit is picked up in this repo automatically. The new
  plugin-level `scripts/` directory is **not** in that mirror list, which is fine — the installer
  resolves its own location from `Path(__file__)`.
- **Delivery.** Work happens on the existing worktree
  (`.claude/worktrees/eloquent-jones-41b55b`, branch `claude/max-plan-status-line-4185c5`); the PR
  targets `main`. The `version-bump-reviewer` skill applies at commit time and will check
  `plugin.json` ↔ `marketplace.json` parity.
