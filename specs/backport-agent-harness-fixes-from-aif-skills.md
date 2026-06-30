# Plan: Backport agent-harness fixes from aif-skills (work) to boss-skills

## Context

`/Users/bossjones/dev/adobe-aifoundations/aif-skills` is the Adobe work mirror of this
personal `boss-skills` repo. The work copy received agent-harness fixes that need to come
back here.

A full content diff of both `agent-harness` plugins shows **boss-skills (v0.11.0) is mostly
ahead** of aif-skills (v0.5.0): it already has tmux notifications, status_lines v1–v10,
the `unicode-hygiene` / `worktree-doctor` / `stop-slop` skills, the unicode BLOCKER guard in
`pre_tool_use.py`, and a hook test suite. So almost every shared-file difference is aif-skills
being *stale*, not a fix — those are dropped.

Two things in aif-skills are genuinely worth backporting:

1. **A real bug in boss-skills.** v0.11.0 added `ENGINEER_NAME` as a plugin `userConfig`
   (so `/plugin` exports `CLAUDE_PLUGIN_OPTION_ENGINEER_NAME`), but the *consumers* were never
   wired to read it. They still read the bare `ENGINEER_NAME` env var, and
   `task_summarizer.py` hardcodes a `"bossjones"` fallback — so the configured name is ignored
   and any other user gets addressed as "bossjones". The work batch (dated 2026-06-23) fixes
   this.
2. **A net-new onboarding skill** (`setup-agent-harness`) that doesn't exist here.

Intended outcome: boss-skills' agent-harness honors the `ENGINEER_NAME` plugin user-config
correctly and ships the repo-onboarding skill, with a single coordinated version bump.

## Objective

Apply the ENGINEER_NAME plugin-config fix and add the `setup-agent-harness` skill to
`plugins/boss-dev/agent-harness`, resolving ENGINEER_NAME through the existing
`hooks/utils/config.py`, then bump the plugin version in both manifests and ship.

## Solution Approach

- **ENGINEER_NAME fix:** route all consumers through the existing
  `hooks/utils/config.py:engineer_name()` (which already does
  `CLAUDE_PLUGIN_OPTION_ENGINEER_NAME` → `ENGINEER_NAME` → `""`). This is cleaner than
  aif-skills' approach of duplicating a local `_engineer_name()` helper into each script.
  Mirror the established, resilient import pattern already used in `hooks/stop.py`
  (path insert + `from utils.config import …` inside a try/except with an inline fallback).
- **setup-agent-harness:** copy the skill verbatim, then rewrite the 3
  `agent-harness@aif-skills` references to `agent-harness@boss-skills`.
- **Version:** bug fix (patch) + new feature (minor) → take the higher tier → **minor bump to
  0.12.0**, in both `plugin.json` and `marketplace.json`.

## Relevant Files

Plugin root: `plugins/boss-dev/agent-harness/`

ENGINEER_NAME fix (consumers — currently read bare env / hardcode "bossjones"):
- `hooks/utils/llm/anth.py` — `engineer_name = os.getenv("ENGINEER_NAME", "").strip()` → use config.py
- `hooks/utils/llm/oai.py` — same change
- `hooks/utils/llm/ollama.py` — same change
- `hooks/utils/llm/task_summarizer.py` — `os.getenv("ENGINEER_NAME","").strip() or "bossjones"` →
  config.py + drop the `"bossjones"` fallback; stay generic when unset
- `agents/work-completion-summary.md` — `USER_NAME: "${ENGINEER_NAME}" # falls back to "bossjones"`
  → `USER_NAME: "${user_config.ENGINEER_NAME}" # falls back to addressing the user generically when unset`
- `output-styles/tts-summary.md` — doc line about the "bossjones" default → ENGINEER_NAME plugin
  user-config (env fallback), generic when blank

Reuse (already correct, do not modify):
- `hooks/utils/config.py` — `engineer_name()` resolver (single source of truth)
- `hooks/stop.py` — reference for the import pattern to copy

Manifests / registry:
- `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json` — add `"skills": "./skills/"`; bump version
- `.claude-plugin/marketplace.json` — bump agent-harness entry version (parity)

### New Files (port from aif-skills `skills/setup-agent-harness/`)
- `plugins/boss-dev/agent-harness/skills/setup-agent-harness/SKILL.md`
- `plugins/boss-dev/agent-harness/skills/setup-agent-harness/scripts/setup_harness.py` (507 lines, stdlib-only PEP 723)
- `plugins/boss-dev/agent-harness/skills/setup-agent-harness/scripts/tests/conftest.py`
- `plugins/boss-dev/agent-harness/skills/setup-agent-harness/scripts/tests/test_setup_harness.py`
  (do NOT copy `__pycache__/`)

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### 1. Persist this plan to specs/
- Write this plan to `specs/backport-agent-harness-fixes-from-aif-skills.md` (the location the
  `/agent-harness:plan` command targets).

### 2. Fix ENGINEER_NAME resolution in the 4 LLM scripts
- In `anth.py`, `oai.py`, `ollama.py`, `task_summarizer.py`, add near the top (after stdlib imports),
  mirroring `hooks/stop.py`:
  ```python
  sys.path.insert(0, str(Path(__file__).parent.parent))  # hooks/utils on path
  try:
      from config import engineer_name
  except Exception:  # resilient inline fallback
      def engineer_name() -> str:
          val = os.environ.get("CLAUDE_PLUGIN_OPTION_ENGINEER_NAME") or os.environ.get("ENGINEER_NAME")
          return (val or "").strip()
  ```
  (add `from pathlib import Path` if not already imported)
- Replace each `os.getenv("ENGINEER_NAME", "").strip()` with `engineer_name()`.
- In `task_summarizer.py`, remove the `or "bossjones"` fallback. When `engineer_name()` is empty,
  address the user generically (e.g. `"Address the user directly and conversationally"`), matching
  the work fix.

### 3. Fix the agent + output-style references
- `agents/work-completion-summary.md`: set
  `USER_NAME: "${user_config.ENGINEER_NAME}" # falls back to addressing the user generically when unset`
- `output-styles/tts-summary.md`: change the USER_NAME doc line to describe the `ENGINEER_NAME`
  plugin user-config (env-var fallback), generic when blank — no "bossjones" default.
- Sweep the plugin for any remaining hardcoded "bossjones" engineer-name defaults in docs
  (`grep -rn bossjones plugins/boss-dev/agent-harness`) and update for consistency (skip author email).

### 4. Add the setup-agent-harness skill
- Copy the four source files listed under **New Files** from
  `…/aif-skills/plugins/agent-harness/skills/setup-agent-harness/` (exclude `__pycache__/`).
- Rewrite the 3 marketplace references `agent-harness@aif-skills` → `agent-harness@boss-skills`:
  `scripts/setup_harness.py` line ~61 (`PLUGIN_ID`), and `SKILL.md` (2 occurrences).
- Confirm `outputStyle` choices in SKILL.md match boss-skills' 8 output styles (they do) and the
  statusLine note points at `status_lines/status_line_v10.py` (it does).

### 5. plugin.json + marketplace.json
- `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json`: add `"skills": "./skills/"`
  (before `userConfig`); bump `"version"` `0.11.0` → `0.12.0`. Keep boss-skills' existing
  `tmux_*` userConfig and `ENGINEER_NAME` default `""` (do NOT adopt aif's `"Friend"` default).
- `.claude-plugin/marketplace.json`: bump the agent-harness entry version to `0.12.0` for parity.

### 6. Validate
- Run lint + tests (see Validation Commands). Fix any ruff/type findings (zero-warning policy).

### 7. Commit
- Conventional commit, e.g.
  `feat(agent-harness): honor ENGINEER_NAME plugin config + add setup-agent-harness skill (v0.12.0)`,
  including the Co-Authored-By trailer. Commit only when the user asks to ship.

## Testing Strategy
- **ENGINEER_NAME fix:** with no env set, `engineer_name()` returns `""` and summaries stay generic
  (no "bossjones"). With `CLAUDE_PLUGIN_OPTION_ENGINEER_NAME=Malcolm`, the LLM scripts pick it up;
  bare `ENGINEER_NAME=Malcolm` still works via fallback. Verify the 4 scripts still import/run
  standalone under `uv run` (the PEP 723 entry path) — the try/except guards the import.
- **setup-agent-harness:** run its ported pytest suite; spot-check `setup_harness.py detect`
  (read-only JSON) and `apply --dry-run` emit diffs without writing.
- **Regression:** `make test-agent-harness` (and `make test`) stays green.

## Acceptance Criteria
- The 4 LLM scripts, the agent, and the output-style resolve ENGINEER_NAME via the plugin
  user-config; no hardcoded "bossjones" default remains anywhere in the plugin.
- `setup-agent-harness` skill present, references `agent-harness@boss-skills`, tests pass.
- `plugin.json` has `"skills": "./skills/"` and version `0.12.0`; `marketplace.json` agent-harness
  entry is `0.12.0`.
- `make lint` and `make test` pass with zero warnings.

## Validation Commands
- `make lint` — codespell + ruff (check --fix, format) + basedpyright; zero warnings required
- `make test-agent-harness` — plugin hook + skill tests, including the new setup-agent-harness tests
- `make test` — full suite stays green
- `uv run plugins/boss-dev/agent-harness/skills/setup-agent-harness/scripts/setup_harness.py detect`
  — read-only JSON report runs cleanly
- `grep -rn bossjones plugins/boss-dev/agent-harness` — returns no engineer-name default (author email OK)

## Notes
- Scope is deliberately narrow: every other shared-file difference is aif-skills being older
  (boss-skills is ahead) and is intentionally dropped — notably `pre_tool_use.py` (boss has the
  unicode BLOCKER guard aif lacks), all other hooks, commands, status_lines, and `fetch_diff.py`
  (a trivial line-wrap-only diff).
- Version bump rationale: the `version-bump-reviewer` skill is the canonical tool for this repo —
  a new skill is a minor bump; the bug fix alone would be a patch; the higher tier wins → 0.12.0,
  bumped in both `plugin.json` and `marketplace.json`.
- Do not adopt aif-skills' `ENGINEER_NAME` default of `"Friend"` or its removal of `required: false`
  — boss-skills' choices are intentional and newer.
