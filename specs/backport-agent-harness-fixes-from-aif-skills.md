# Plan: Backport agent-harness fixes from aif-skills (work) to boss-skills (personal)

## Context

`/Users/bossjones/dev/adobe-aifoundations/aif-skills` is the Adobe-work mirror of this
personal repo. The `agent-harness` plugin has diverged in both directions:

- **boss-skills is newer overall** — v0.10.0 vs work's v0.5.0; it already has tmux desktop
  notifications, a `hooks/tests/` suite, and extra skills/commands the work repo lacks.
  (An earlier backport already brought over hooks.json wiring, the commit-push-pr/debug-ci/
  fix-gh-pr-comments commands, the security/reliability hook fixes, and status_line_v10 with
  public pricing.)
- **aif-skills diverged on two genuinely useful things** that never made it back:
  1. **TTS configurability.** Work added a shared `hooks/utils/config.py` resolver and a
     `tts_enabled()` gate wired into the three TTS-emitting hooks, plus `ENABLE_TTS` /
     `ENGINEER_NAME` plugin user-config options. **boss-skills currently cannot disable
     TTS at all** — `notification.py`, `stop.py`, and `subagent_stop.py` always attempt to
     speak. This is the core fix.
  2. **A `docs/` suite** — 8 markdown guides documenting the plugin's commands, agents,
     skills, hooks, output styles, status lines, and workflows.

Everything else in the work repo is either work-specific drift that must **not** come over
(Adobe-discounted pricing in `status_line_v10.py`, `malcolm@adobe.com` author/URLs in
`plugin.json`, `setup-gh-mcp` / `setup-repos` Makefile targets, `settings.local.json`
paths, README plugin catalogs) or already superseded in boss-skills.

**Outcome:** boss-skills' agent-harness gains a clean, env-driven TTS on/off switch
(without losing its tmux features) and a documentation suite, branded for boss-skills.

## Objective

1. Add `ENABLE_TTS` / `ENGINEER_NAME` configurability to the boss-skills agent-harness
   plugin via a shared `hooks/utils/config.py`, gating TTS in all three TTS hooks.
2. Add the 8-file `docs/` suite, rewritten for boss-skills (no Adobe references, correct
   `plugins/boss-dev/agent-harness` paths, bossjones marketplace/URLs).
3. Extend the existing hook test suite to cover the TTS toggle.
4. Bump the plugin version and sync `marketplace.json`.

## Problem Statement

The personal agent-harness plugin has no way to silence TTS. On machines without audio,
in CI, or during focus time, `notification.py` / `stop.py` / `subagent_stop.py` always
shell out to the TTS backend (failing silently, but still spawning `uv run` subprocesses
on every Stop/Notification). The work repo already solved this cleanly with a single
env-driven switch and a reusable config resolver; that improvement should live in the
canonical personal repo too. Secondarily, the plugin lacks end-user documentation that the
work fork has since written.

## Solution Approach

Port the **mechanism**, not the work-specific config values. Add `hooks/utils/config.py`
(identical to work — it's environment-neutral), refactor the three TTS hooks to import
`tts_enabled()` / `engineer_name()` with an inline fallback (so the hooks still run if the
module is ever missing), and **merge** `ENABLE_TTS` + `ENGINEER_NAME` into the existing
`userConfig` block alongside the current `tmux_notifications` options (do not overwrite).
Port the docs as new files with branding/paths rewritten. Cover the toggle with a test in
the existing `hooks/tests/` suite. Finish with a version bump + marketplace sync.

## Relevant Files

Source (read-only, work repo):
- `…/aif-skills/plugins/agent-harness/hooks/utils/config.py` — the module to copy verbatim.
- `…/aif-skills/plugins/agent-harness/hooks/{notification,stop,subagent_stop}.py` — show the
  exact `tts_enabled()` import + gate pattern to replicate.
- `…/aif-skills/plugins/agent-harness/docs/*.md` — 8 source docs to adapt.
- `…/aif-skills/plugins/agent-harness/.claude-plugin/plugin.json` — source of the
  `ENABLE_TTS` / `ENGINEER_NAME` userConfig schema.

Target (boss-skills — to modify/create):
- `plugins/boss-dev/agent-harness/hooks/utils/config.py` — **NEW** (copy).
- `plugins/boss-dev/agent-harness/hooks/notification.py` — gate `announce_notification()`.
- `plugins/boss-dev/agent-harness/hooks/stop.py` — gate TTS announcement.
- `plugins/boss-dev/agent-harness/hooks/subagent_stop.py` — gate TTS announcement.
- `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json` — merge 2 userConfig keys;
  this is also the version-bump artifact.
- `plugins/boss-dev/agent-harness/docs/*.md` — **NEW** (8 adapted files).
- `plugins/boss-dev/agent-harness/hooks/tests/` — **NEW** test for the toggle.
- `.claude-plugin/marketplace.json` — sync the agent-harness version entry.

Explicitly **out of scope** (do not touch / do not copy):
- `status_lines/status_line_v10.py` — boss-skills already has correct public list pricing;
  work's `ADOBE_PRICING` must never be backported.
- `plugin.json` author/email/url/homepage/repository/keywords — keep boss-skills values.
- `setup-agent-harness` skill, `setup-gh-mcp`/`setup-repos` Makefile targets,
  `settings.local.json`, README plugin catalogs — work-specific.
- `pre_compact.py` — the only diff is argparse line-wrapping (style drift); boss-skills'
  one-line form already passes `ruff format`. No change.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### 1. Persist this spec
- Copy this document to `specs/backport-agent-harness-fixes-from-aif-skills.md`. (done)

### 2. Add the shared config resolver
- Create `plugins/boss-dev/agent-harness/hooks/utils/config.py` as a verbatim copy of the
  work file: `_option()` (reads `CLAUDE_PLUGIN_OPTION_<KEY>`, falls back to bare env var),
  `tts_enabled()` (default True unless value in `{0,false,no,off}`), `engineer_name()`.
- Confirm `hooks/utils/` is importable as a package the same way work imports it
  (`sys.path.insert(0, str(Path(__file__).parent))` then `from utils.config import …`).

### 3. Gate TTS in notification.py
- At top of `notification.py`, add the import-with-fallback block (mirror work):
  `sys.path.insert(0, str(Path(__file__).parent))` then
  `try: from utils.config import engineer_name, tts_enabled` with an `except ImportError`
  defining inline equivalents.
- In `announce_notification()`, add `if not tts_enabled(): return` as the first line.
- Replace inline `engineer_name = os.getenv("ENGINEER_NAME", "").strip()` with
  `engineer_name_val = engineer_name()` and update the f-string usage accordingly.

### 4. Gate TTS in stop.py and subagent_stop.py
- Apply the same import-with-fallback block and `if not tts_enabled(): return` guard inside
  each file's TTS-announcement function. Use `subagent_stop.py`/`stop.py` from work as the
  reference for the exact insertion point.

### 5. Merge userConfig in plugin.json
- Into the existing `userConfig` object (which currently holds `tmux_notifications`,
  `tmux_notify_activate_bundle_id`, `tmux_notify_sound`), **add** without removing:
  - `ENABLE_TTS` — boolean, title "Enable spoken announcements (TTS)", description noting
    it silences Stop/SubagentStop/Notification TTS, `default: true`.
  - `ENGINEER_NAME` — string, title "Your name", used in ~30% of spoken messages,
    `default: ""` (keep boss-skills' blank-default convention, not work's "Friend").
- Keep all other boss-skills fields (author, urls, keywords, version) unchanged here except
  the version bump in step 8.

### 6. Add docs/ suite (boss-skills branded)
- Create `plugins/boss-dev/agent-harness/docs/{getting-started,commands,agents,skills,hooks,output-styles,status-lines,workflows}.md`
  from the work originals.
- Rewrite during copy: replace `Adobe-AIFoundations/aif-skills` → `bossjones/boss-skills`,
  `malcolm@adobe.com` → boss-skills author, `plugins/agent-harness` →
  `plugins/boss-dev/agent-harness`, and the marketplace/install name to the boss-skills
  marketplace. Reconcile counts/feature lists with what boss-skills actually ships
  (boss-skills has extra skills: stop-slop, unicode-hygiene, worktree-doctor; extra
  commands; tmux notification hooks + StopFailure) and document `ENABLE_TTS`/`ENGINEER_NAME`
  in `hooks.md`/`getting-started.md`.
- Follow the repo SKILL.md parser caveat (no leading-backtick command patterns in fenced
  blocks; use `$ command` notation) for any executable examples.

### 7. Add a test for the TTS toggle
- In `plugins/boss-dev/agent-harness/hooks/tests/`, add a test (matching the existing test
  style there) that imports `utils.config` and asserts:
  - `tts_enabled()` is True by default and with `ENABLE_TTS` unset.
  - `tts_enabled()` is False for each of `0/false/no/off` (case-insensitive) via both
    `ENABLE_TTS` and `CLAUDE_PLUGIN_OPTION_ENABLE_TTS`.
  - `engineer_name()` reads the option and trims whitespace; empty when unset.
- Use `monkeypatch.setenv`/`delenv`. Keep it stdlib + pytest; no network, no audio.

### 8. Version bump + marketplace sync
- Run the `version-bump-reviewer` skill against the change (or apply manually): this is a
  plugin-component change → bump `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json`
  `version` and the matching `.claude-plugin/marketplace.json` entry. New backward-compatible
  feature (TTS toggle + docs) → **minor** bump (0.10.0 → 0.11.0).

### 9. Validate
- Run the validation commands below and confirm all pass.

## Testing Strategy

- **Unit:** new `hooks/tests/` test exercises `tts_enabled()` / `engineer_name()` across
  truthy/falsy/case-variant/prefixed-env inputs (the core of the fix).
- **Behavioral smoke:** with `ENABLE_TTS=false`, run a hook that announces (e.g. pipe a
  minimal JSON event into `stop.py`) and confirm no TTS subprocess is spawned and exit 0;
  with `ENABLE_TTS` unset confirm the prior behavior (subprocess attempted, fails silently
  if no audio) still exits 0.
- **Regression:** existing `make test-agent-harness` suite continues to pass (the
  fallback-import block guarantees hooks run even if `utils/config.py` is absent).
- **Edge cases:** `ENABLE_TTS` with surrounding whitespace / mixed case; both
  `CLAUDE_PLUGIN_OPTION_ENABLE_TTS` and bare `ENABLE_TTS` set (option wins);
  `utils/config.py` missing (fallback path).

## Acceptance Criteria

- `plugins/boss-dev/agent-harness/hooks/utils/config.py` exists with `tts_enabled()` /
  `engineer_name()` and no Adobe-specific content.
- All three TTS hooks return early (no subprocess) when `ENABLE_TTS` is falsy and behave as
  before otherwise.
- `plugin.json` `userConfig` contains `ENABLE_TTS` and `ENGINEER_NAME` **and** retains the
  three `tmux_*` options; author/urls/keywords unchanged.
- 8 docs exist under the plugin's `docs/`, with zero `Adobe`/`aif-skills`/`malcolm` strings
  and correct `plugins/boss-dev/agent-harness` paths.
- New toggle test passes; full agent-harness test suite passes.
- Plugin version bumped (minor) and equal in `plugin.json` and `marketplace.json`.
- No changes to `status_line_v10.py` pricing.

## Validation Commands

- `make lint` — ruff + basedpyright clean (covers `plugins/`).
- `make test-agent-harness` — agent-harness skills + hooks tests pass.
- `uv run pytest plugins/boss-dev/agent-harness/hooks/tests/ -v` — including the new toggle test.
- `ENABLE_TTS=false uv run plugins/boss-dev/agent-harness/hooks/stop.py < /dev/null; echo "exit=$?"`
  — exits 0, no TTS subprocess (manual smoke; supply a minimal JSON event if the hook
  requires one on stdin).
- `! grep -rIl -e Adobe -e aif-skills -e malcolm plugins/boss-dev/agent-harness/docs/`
  — returns nothing (no leaked work branding).
- `grep -c ENABLE_TTS plugins/boss-dev/agent-harness/.claude-plugin/plugin.json` — ≥1, and
  `tmux_notifications` still present.
- `make markdown-lint` — docs lint clean.
- Confirm version parity: `plugin.json.version` == agent-harness entry in
  `.claude-plugin/marketplace.json`.

## Notes

- **Direction matters:** this is a *selective* backport. boss-skills is the newer trunk for
  most of agent-harness; only TTS-config and docs flow work→personal. Do not let work's
  older `notification.py`/`stop.py` bodies, status-line pricing, or manifest identity
  overwrite the newer boss-skills versions — apply only the additive TTS gate.
- No new third-party dependencies. `config.py` and the test are stdlib-only.
- The fallback-import block is intentional defensive design from the source; keep it so a
  packaging mishap can't break hook execution.
