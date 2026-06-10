# Plan: Backport agent-harness cosmetic churn + structural hook rewrites from aif-skills

## Task Description

A prior backport (`specs/backport-agent-harness-fixes-from-aif-skills.md`, shipped at v0.4.0)
intentionally **excluded** two classes of aif-skills change under a "substantive-only" scope decision:

1. **Cosmetic Python churn** (aif commit `eb789ae`): `open(path, "r")` → `open(path)`, `Optional[X]` →
   `X | None` (+ dropping `from typing import Optional`), `except (OSError, IOError)` → `except OSError`,
   removal of now-stale inline comments, and multi-line reformatting of long `argparse`/`subprocess` calls.
2. **Structural hook rewrites** in two command files: `autobuild.md`'s `Stop` → `PostToolUse`
   (matcher `Write|Edit|MultiEdit`) event change and the validator hook paths
   `$CLAUDE_PROJECT_DIR/.claude/hooks/validators/...` → `${CLAUDE_PLUGIN_ROOT}/hooks/validators/...`
   in both `autobuild.md` and `plan_w_team.md`.

This plan ports those two classes now, bringing `plugins/boss-dev/agent-harness/` into near byte-alignment
with the aif fork — **while still excluding** the `ENABLE_TTS` kill-switch (skipped item #3) and aif's
Adobe identity / "boss-skills"→generic de-branding.

`$AIF` = `/Users/bossjones/dev/aif-skills/plugins/agent-harness`.
`$BOSS` = `/Users/bossjones/dev/bossjones/boss-skills/plugins/boss-dev/agent-harness`.

## Objective

Every agent-harness hook script adopts aif's cosmetic style (config-compatible with boss's
`line-length = 120` ruff format), and the two command files use plugin-root-relative validator paths
plus the `PostToolUse` validator event — with `make lint`/`make test` green and a follow-on plugin
version bump. No behavioral change to the hooks themselves except `autobuild`'s validator trigger timing.

## Problem Statement

The two repos have diverged on ~20 hook files purely on style, plus two command files on hook wiring.
This makes future diffs/cherry-picks between the repos noisy, and the boss command files still point
their inline validator hooks at `$CLAUDE_PROJECT_DIR/.claude/hooks/validators/...` — a path that does
not exist when agent-harness is installed as a plugin (the validators live under the plugin tree). The
prior backport deferred both; this closes the gap.

## Solution Approach

Two mechanisms, chosen per file by what the remaining `$BOSS`↔`$AIF` diff contains:

- **Wholesale copy** (`cp "$AIF/<f>" "$BOSS/<f>"`) for any hook script whose *entire* remaining diff is
  cosmetic — i.e. it contains no `ENABLE_TTS`, no `adobe`, and no behavioral/identity lines. aif's file
  is then byte-identical to the boss-desired result.
- **Selective hand-edit** for the three files that also carry *excluded* content:
  `notification.py` and `subagent_stop.py` (skip the `ENABLE_TTS` gate) and `task_summarizer.py`
  (keep the boss `bossjones` fallback added in the prior backport).

The two command files get targeted edits for the event/path rewrites only (keep boss identity wording).
After all edits, `make lint` (ruff format + check) arbitrates final formatting — magic trailing commas
preserve aif's multi-line wraps; anything that fits 120 chars collapses, which is acceptable and
boss-canonical. A **verify-diff gate** precedes every `cp` to guard against importing unaudited content.

## Relevant Files

### Wholesale-copy candidates (verify cosmetic-only first)
Hook scripts whose remaining diff is the `eb789ae` cosmetic set — representative paths (full list
enumerated by the Step 1 audit):
- `$BOSS/hooks/post_tool_use.py`, `post_tool_use_failure.py`, `pre_compact.py`, `session_end.py`,
  `session_start.py`, `setup.py`, `stop.py`, `subagent_start.py`
- `$BOSS/hooks/pre_tool_use.py`, `permission_request.py`, `user_prompt_submit.py`,
  `utils/tts/tts_queue.py` (already carry the prior substantive edits; aif == boss-desired + cosmetic)
- `$BOSS/hooks/validators/ruff_validator.py`, `ty_validator.py`, `validate_file_contains.py`,
  `validate_new_file.py`
- `$BOSS/hooks/utils/llm/anth.py`, `oai.py`, `ollama.py`; `$BOSS/hooks/utils/tts/openai_tts.py`

### Selective hand-edit (exclude flagged content)
- `$BOSS/hooks/notification.py` — apply cosmetic hunks (open-mode, stale-comment removal); **omit** the
  `if os.getenv("ENABLE_TTS", ...)` gate.
- `$BOSS/hooks/subagent_stop.py` — apply cosmetic hunks (`Optional`→union, open-mode, `IOError`→`OSError`,
  argparse wrap); **omit** the `ENABLE_TTS` gate.
- `$BOSS/hooks/utils/llm/task_summarizer.py` — apply `Optional`→union + argparse wrap; **keep** the
  `os.getenv("ENGINEER_NAME", "").strip() or "bossjones"` address block.

### Structural command files
- `$BOSS/commands/autobuild.md` — frontmatter `Stop:` → `PostToolUse:` w/ `matcher: "Write|Edit|MultiEdit"`;
  validator commands `$CLAUDE_PROJECT_DIR/.claude/hooks/validators/{ty,ruff}_validator.py` →
  `${CLAUDE_PLUGIN_ROOT}/hooks/validators/{ty,ruff}_validator.py`. Keep "boss-skills" wording.
- `$BOSS/commands/plan_w_team.md` — validator commands
  `$CLAUDE_PROJECT_DIR/.claude/hooks/validators/{validate_new_file,validate_file_contains}.py` →
  `${CLAUDE_PLUGIN_ROOT}/hooks/validators/...`.

### Version artifacts
- `$BOSS/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` — bump 0.4.0 → 0.4.1 (patch).

## Implementation Phases

### Phase 1: Foundation — audit & classify
Diff every candidate file; bucket each as wholesale-copy (cosmetic-only) or selective (carries
ENABLE_TTS / identity). Produce the definitive file lists before touching anything.

### Phase 2: Core Implementation — apply churn + structural rewrites
Copy the cosmetic-only files; hand-edit the three flagged files; rewrite the two command files.

### Phase 3: Integration & Polish — lint, test, bump
`make lint` to settle formatting, `make test`, re-diff vs aif to confirm only intended differences
remain (ENABLE_TTS, Adobe, identity), patch-bump the version.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### 1. Audit & classify every candidate file
- For each hook `.py` under `$BOSS/hooks/` (and `validators/`, `utils/llm/`, `utils/tts/`), run
  `diff "$BOSS/hooks/<f>" "$AIF/hooks/<f>"`.
- Classify: if the diff contains `ENABLE_TTS`, `adobe` (case-insensitive), or any non-cosmetic
  behavior/identity line → **selective**; otherwise → **wholesale-copy**.
- Expected selective set: `notification.py`, `subagent_stop.py`, `task_summarizer.py`. Confirm no others
  surface (especially scan `grep -rinE 'ENABLE_TTS|adobe'` across `$AIF/hooks`).

### 2. Wholesale-copy the cosmetic-only hook files
- For each file classified wholesale-copy in Step 1: `cp "$AIF/hooks/<f>" "$BOSS/hooks/<f>"`.
- Do **not** copy `notification.py`, `subagent_stop.py`, `task_summarizer.py`.

### 3. Selective edit: notification.py
- Apply only the cosmetic hunks: `open(log_file, "r")` → `open(log_file)`, remove the stale
  `# Get current script directory...` and `# Fall back to pyttsx3...` comments.
- **Do not** add the `ENABLE_TTS` early-return block.

### 4. Selective edit: subagent_stop.py
- Apply cosmetic hunks: drop `from typing import Optional`; `Optional[str]` → `str | None` (both sites);
  `open(..., "r")` → `open(...)` (both sites); `except (OSError, IOError)` → `except OSError`; the
  multi-line argparse/`debug_log` wraps (with trailing commas so ruff keeps them).
- **Do not** add the `ENABLE_TTS` early-return block.

### 5. Selective edit: task_summarizer.py
- Apply cosmetic hunks: drop `from typing import Optional`; `Optional[str]` → `str | None`; wrap the
  long `argparse` calls (trailing commas).
- **Keep** the existing `user_name = os.getenv("ENGINEER_NAME", "").strip() or "bossjones"` block and the
  `- {address}` prompt line — do not revert to aif's generic-fallback form.

### 6. Structural rewrite: autobuild.md
- In frontmatter, change the validator hook block from `Stop:` to
  `PostToolUse:` with `- matcher: "Write|Edit|MultiEdit"` then `hooks:`.
- Rewrite both validator commands to `uv run "${CLAUDE_PLUGIN_ROOT}"/hooks/validators/ty_validator.py`
  and `.../ruff_validator.py`.
- Leave the "boss-skills specs follow the `/agent-harness:plan` format" wording unchanged.

### 7. Structural rewrite: plan_w_team.md
- Rewrite both inline validator commands from
  `uv run $CLAUDE_PROJECT_DIR/.claude/hooks/validators/validate_new_file.py` and
  `.../validate_file_contains.py` to `uv run ${CLAUDE_PLUGIN_ROOT}/hooks/validators/...`.

### 8. Lint & format settle
- Run `make lint`. Let ruff format normalize wrapping; fix any ruff-check violations it surfaces.

### 9. Re-diff vs aif (confirm only intended differences remain)
- `diff -rq "$BOSS" "$AIF"` (ignore `__pycache__`, `logs/`, `.claude/`, `status_lines`, `plugin.json`,
  `README.md`). The only expected *content* differences now: `ENABLE_TTS` absent in
  notification.py/subagent_stop.py; `bossjones` fallback in task_summarizer.py + the two TTS md files;
  boss identity wording in command files; status_line set (boss keeps v1–v9, generic pricing in v10).

### 10. Version bump + validate
- Bump `$BOSS/.claude-plugin/plugin.json` and the marketplace entry 0.4.0 → **0.4.1** (patch: style +
  internal hook-path correctness, no new user-facing feature). Confirm with `version-bump-reviewer`.
- Run the Validation Commands below.

## Testing Strategy

- **Lint:** `make lint` must exit 0 (ruff format leaves files unchanged on a second pass; basedpyright
  0 errors). The `Optional`→`X | None` ports must not introduce missing-import errors.
- **Tests:** `make test` — all suites green (no logic touched; the prior 500-test baseline holds).
- **Hook import smoke:** re-run the prior behavioral check
  (`/tmp/verify_harness_fixes.py` from the previous build) to prove the copied `pre_tool_use.py` /
  `permission_request.py` still enforce SEC-1/SEC-2/REL-2 (16/16).
- **Edge cases:** verify `notification.py` and `subagent_stop.py` contain **no** `ENABLE_TTS` string;
  verify `task_summarizer.py` still contains `"bossjones"`.

## Acceptance Criteria

- Every wholesale-copied hook file is byte-identical to its `$AIF` counterpart.
- `notification.py`, `subagent_stop.py` carry the cosmetic style but **no** `ENABLE_TTS` gate.
- `task_summarizer.py` carries the cosmetic style **and** the `bossjones` fallback.
- `autobuild.md` uses `PostToolUse` + `${CLAUDE_PLUGIN_ROOT}` validator paths; `plan_w_team.md` uses
  `${CLAUDE_PLUGIN_ROOT}` validator paths; boss identity wording preserved.
- No `adobe`/`aifoundations`/`malcolm@adobe` strings introduced anywhere under `$BOSS`.
- `plugin.json` + `marketplace.json` both read `0.4.1`.
- `make lint` and `make test` pass; the SEC/REL hook behavioral check is 16/16.

## Validation Commands

- `grep -RIl 'ENABLE_TTS' plugins/boss-dev/agent-harness/hooks/ ; test $? -ne 0` — ENABLE_TTS not present
- `grep -c 'bossjones' plugins/boss-dev/agent-harness/hooks/utils/llm/task_summarizer.py` — ≥1
- `grep -R 'CLAUDE_PLUGIN_ROOT.*validators' plugins/boss-dev/agent-harness/commands/autobuild.md plugins/boss-dev/agent-harness/commands/plan_w_team.md` — plugin-root paths present
- `grep -R 'PostToolUse' plugins/boss-dev/agent-harness/commands/autobuild.md` — event changed
- `grep -RniE 'adobe|aifoundations|malcolm@adobe' plugins/boss-dev/agent-harness/ ; test $? -ne 0` — no Adobe leakage
- `grep '"version": "0.4.1"' plugins/boss-dev/agent-harness/.claude-plugin/plugin.json .claude-plugin/marketplace.json` — version parity
- `python3 /tmp/verify_harness_fixes.py` — SEC-1/SEC-2/REL-2 behavioral checks still 16/16
- `make lint` — ruff + basedpyright clean
- `make test` — pytest suites green

## Notes

- **Why patch (0.4.1), not minor:** this is internal style + a validator-path correctness fix in two
  commands; no new commands, skills, or user-facing capability. The `Stop`→`PostToolUse` change alters
  *when* autobuild's validators fire (after each edit vs at stop) — a behavior tweak to one command, but
  not a new feature; patch is appropriate. Confirm via `version-bump-reviewer`.
- **Explicitly excluded** (scope decision): the `ENABLE_TTS` kill-switch (skipped item #3), aif's Adobe
  pricing/identity, and aif's "boss-skills"→generic de-branding. If the auto-firing TTS on install is a
  concern, `ENABLE_TTS` is a separate, easy follow-up.
- **The `cp` verify-gate matters:** several candidate files have large diffs (`session_start.py` ~47,
  `setup.py` ~25, validators ~34–42). Step 1 must confirm these are purely the `eb789ae` cosmetic set
  before copying — do not `cp` a file whose diff includes an unaudited behavioral line.
- **No new dependencies.**
- **Commit/PR** is out of scope for this plan (that was the separate skipped item). The changes can ride
  the existing PR #16 branch or a follow-up commit when you choose to ship.
