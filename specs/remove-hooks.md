# Plan: Remove agent-harness hook runtime and hooks.json

## Task Description

Mirror the `Adobe-AIFoundations/aif-skills` hook-removal effort (`Adobe-AIFoundations/aif-skills#97` and `Adobe-AIFoundations/aif-skills#108`) into `bossjones/boss-skills`. Specifically, remove `plugins/boss-dev/agent-harness/hooks/hooks.json` and the entire `agent-harness` lifecycle-hook runtime (`hooks/` scripts, `utils/`, `validators/`, and `tests/`), remove hook-only components and configuration (`output-styles/tts-summary.md`, `commands/sentient.md`, inline hook blocks in commands and agents, and hook-specific `userConfig` keys), decouple standalone skills and scripts from `hooks/utils/`, clean up `.claude/` symlink mirrors, bump `agent-harness` from `0.32.0` to `0.33.0` (0.x breaking-change convention), and open a PR on `bossjones/boss-skills`.

## Objective

When this plan is complete:

1. `plugins/boss-dev/agent-harness/hooks/` (including `hooks.json`, all lifecycle hook scripts, `utils/`, `validators/`, and `tests/`) is completely deleted.
2. No dangling symlinks to removed `agent-harness` components remain under `.claude/hooks/`, `.claude/commands/`, or `.claude/output-styles/` (while preserving repo-owned `.claude/hooks/skill-edit-review.py` and `.claude/hooks/version-bump-reviewer.py`).
3. Standalone skills and scripts (`harness-doctor`, `setup-agent-harness`, `scripts/snyk-agent-scan.py`, and `status_lines/status_line_v{2,3,4,7}.py`) are self-contained and no longer import from `plugins/boss-dev/agent-harness/hooks/utils/`.
4. `boss-cmux` and `boss-cmux-team` use the portable completion-sentinel contract (`TASK-DONE: <role> #<attempt-id> | <summary>`) with bounded `read-screen` checks and regression test coverage (`test_completion_contract.py`), matching `Adobe-AIFoundations/aif-skills#108`.
5. `agent-harness` version is bumped in lockstep in `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` (`0.32.0` → `0.33.0`), and all documentation and tests pass validation (`make verify-structure`, `make symlink-plugins-check`, `make lint`, `make test`, `make markdown-lint`, `make eval-ci`).

## Problem Statement

In `Adobe-AIFoundations/aif-skills`, PRs `Adobe-AIFoundations/aif-skills#97` ("refactor(agent-harness): remove hook runtime") and `Adobe-AIFoundations/aif-skills#108` ("feat(agent-harness)!: remove hook runtime, release 4.0.0") removed the plugin-shipped lifecycle-hook runtime from `agent-harness` because:

1. **Cross-runtime incompatibility and overhead:** Shipping 13–20 lifecycle hooks (`hooks/hooks.json`) that fire `uv run` on every event (`PreToolUse`, `PostToolUse`, `SessionStart`, `Stop`, etc.) introduces cold-start latency, cross-runtime friction between Claude Code and GitHub Copilot CLI, and unintended side effects (TTS audio, auto-formatting, background LLM calls) in every consumer repository.
2. **Tightly coupled skills:** `harness-doctor`, `setup-agent-harness`, `scripts/snyk-agent-scan.py`, and status lines V2/V3/V4/V7 dynamically imported helpers from `plugins/boss-dev/agent-harness/hooks/utils/`, preventing standalone execution without the hook tree.
3. **cmux event fragility:** `boss-cmux` and `boss-cmux-team` relied on `cmux hooks setup` and `notification.requested` events, which do not fire deterministically in Claude Code. Replacing hook-event waiting with an attempt-correlated `TASK-DONE: <role> #<attempt-id> | ...` sentinel works portably across Claude Code, Copilot CLI, Codex, and pi.

`bossjones/boss-skills` is the personal upstream counterpart to `aif-skills` and still carries the full 20-event hook runtime in `plugins/boss-dev/agent-harness/hooks/`.

## Solution Approach

Port the architecture and changes from `Adobe-AIFoundations/aif-skills#97` and `Adobe-AIFoundations/aif-skills#108`, adapted to `boss-skills` conventions:

1. **Delete `plugins/boss-dev/agent-harness/hooks/` in full:** Remove `hooks.json`, all event handlers (`log_event.py`, `pre_tool_use.py`, `post_tool_use.py`, `ruff_autoformat.py`, `notification.py`, `tmux_notify.py`, `stop.py`, `subagent_start.py`, `subagent_stop.py`, `user_prompt_submit.py`, `pre_compact.py`, `session_start.py`, `snyk_agent_scan.py`, `session_end.py`, `permission_request.py`, `post_tool_use_failure.py`, `setup.py`, `uv-guard.sh`), `hooks/utils/`, `hooks/validators/`, and `hooks/tests/`.
2. **Delete hook-only plugin components and docs:**
   - Delete `plugins/boss-dev/agent-harness/output-styles/tts-summary.md`.
   - Delete `plugins/boss-dev/agent-harness/commands/sentient.md` (demo command whose sole purpose was triggering the `pre_tool_use.py` `rm -rf` hook).
   - Delete `plugins/boss-dev/agent-harness/docs/hooks.md`.
   - Remove inline `hooks:` frontmatter blocks from `plugins/boss-dev/agent-harness/agents/team/builder.md`, `plugins/boss-dev/agent-harness/commands/autobuild.md`, and `plugins/boss-dev/agent-harness/commands/plan_w_team.md`.
3. **Make coupled scripts and skills self-contained:**
   - **`harness-doctor`**: Inline namespace resolution (`.boss-skills` default), `resolve_harness_root`, `logs_root` (preserving read-only discovery of legacy `CLAUDE_HOOKS_LOG_DIR`), `data_dir`, `cache_dir`, and `check_env` directly into `harness_doctor.py`. Add regression tests for `CLAUDE_HOOKS_LOG_DIR` (relative and absolute) in `test_harness_doctor.py`.
   - **`setup-agent-harness`**: Inline `_plugin_namespace()` and `check_env()` into `setup_harness.py`, remove `tts-summary` from `OUTPUT_STYLES`, and update `SKILL.md` to list the 7 remaining output styles and describe residual/runtime artifact gitignore entries.
   - **`scripts/snyk-agent-scan.py` & `tests/test_snyk_agent_scan.py`**: Move the pure Snyk scan logic from `hooks/utils/snyk.py` and `snyk_token()` directly into `scripts/snyk-agent-scan.py` so the repo's pre-commit gate works standalone. Update `tests/test_snyk_agent_scan.py` to test `scripts/snyk-agent-scan.py` directly and remove the `SessionStart` hook wrapper tests (`test_sessionstart_*`).
   - **`status_lines/status_line_v{2,3,4,7}.py`**: Replace `from utils.harness_paths import data_dir` with a small self-contained `_data_dir(project_dir)` helper so all 10 status line variants remain functional without `hooks/`. Add a unit test in `tests/test_status_line_v10.py` (or a sibling test) covering status line `data_dir` resolution if needed.
4. **Port portable cmux completion sentinels (`Adobe-AIFoundations/aif-skills#108`):**
   - Update `plugins/boss-dev/agent-harness/skills/boss-cmux/SKILL.md`, `plugins/boss-dev/agent-harness/skills/boss-cmux-team/SKILL.md`, `assets/roles/{lead,build-be,build-fe,plan,test}.md`, `assets/team-config.example.json`, and `docs/cmux-tutorial.md` to use `TASK-DONE: <role> #<attempt-id> | <summary>` with bounded `read-screen` checks instead of `cmux hooks setup` / `notification.requested`.
   - Add `plugins/boss-dev/agent-harness/skills/boss-cmux-team/scripts/tests/test_completion_contract.py`.
5. **Clean up `.claude/` symlink mirrors:**
   - Remove all symlinks under `.claude/hooks/` that point into `../../plugins/boss-dev/agent-harness/hooks/`, plus empty subdirectories `.claude/hooks/{tests,utils,validators}`, while keeping `.claude/hooks/skill-edit-review.py` and `.claude/hooks/version-bump-reviewer.py`.
   - Remove `.claude/output-styles/tts-summary.md` and `.claude/commands/sentient.md`.
   - Run `uv run scripts/symlink_plugins.py` and `uv run scripts/symlink_plugins.py --check` to ensure all mirrors are clean and synchronized.
6. **Update manifests, repo config, and documentation:**
   - Update `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json`: bump `version` from `0.32.0` to `0.33.0`, update `description` to remove `"hooks, "`, and trim `userConfig` to retain only `ENGINEER_NAME`, `ENABLE_STATUS_LINE`, and `STATUS_LINE_VARIANT`.
   - Update `.claude-plugin/marketplace.json`: bump `agent-harness` `version` to `0.33.0` and align `description`.
   - Update `.env.sample`, `pyproject.toml` (remove `libtmux` dev dependency comment/entry if only used by deleted `test_tmux_notify.py`), `.github/workflows/ci.yml` (remove `Install tmux` step that existed solely for `test_tmux_notify.py`), `Makefile`, `CLAUDE.md`, `.github/copilot-instructions.md`, `README.md`, `docs/plugins/README.md`, `docs/plugins/agent-harness.md`, `docs/companion-ecosystem.md`, `docs/tutorials/agent-harness/README.md`, and `plugins/boss-dev/agent-harness/{README.md,docs/*.md}`.

## Relevant Files

Use these files to complete the task:

- `.claude-plugin/marketplace.json` — Bump `agent-harness` version (`0.32.0` → `0.33.0`) and remove `"hooks, "` from description.
- `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json` — Bump version (`0.32.0` → `0.33.0`), remove `"hooks, "` from description, remove hook-only `userConfig` entries (`ENABLE_TTS`, `HARNESS_DIR`, `HOOKS_LOG_RETENTION_DAYS`, `HOOKS_LOG_RETENTION_MAX_MB`, `tmux_notifications`, `tmux_notify_activate_bundle_id`, `tmux_notify_sound`, `ENABLE_SNYK_AGENT_SCAN`, `SNYK_TOKEN`).
- `plugins/boss-dev/agent-harness/hooks/**` — Delete entire directory (`hooks.json`, 17 Python scripts, 1 shell script, `utils/**`, `validators/**`, `tests/**`).
- `plugins/boss-dev/agent-harness/output-styles/tts-summary.md` — Delete hook-coupled TTS output style (and `.claude/output-styles/tts-summary.md` symlink).
- `plugins/boss-dev/agent-harness/commands/sentient.md` — Delete hook-demo command (and `.claude/commands/sentient.md` symlink).
- `plugins/boss-dev/agent-harness/docs/hooks.md` — Delete hook documentation page.
- `plugins/boss-dev/agent-harness/agents/team/builder.md` — Remove inline `hooks:` frontmatter block referencing `ruff_validator.py` and `ty_validator.py`.
- `plugins/boss-dev/agent-harness/commands/autobuild.md` — Remove inline `hooks:` frontmatter block referencing `ty_validator.py` and `ruff_validator.py`.
- `plugins/boss-dev/agent-harness/commands/plan_w_team.md` — Remove inline `hooks:` frontmatter block referencing `validate_new_file.py` and `validate_file_contains.py`.
- `plugins/boss-dev/agent-harness/commands/fix-gh-pr-comments.md` — Replace hook-script smoke-test example with standalone script/status-line guidance.
- `plugins/boss-dev/agent-harness/skills/harness-doctor/SKILL.md` — Reframe around residual runtime artifacts and read-only `CLAUDE_HOOKS_LOG_DIR` discovery.
- `plugins/boss-dev/agent-harness/skills/harness-doctor/scripts/harness_doctor.py` — Inline namespace, path, and `check_env` helpers so `harness-doctor` has zero dependency on `hooks/utils/`; ensure executable bit (`chmod +x`).
- `plugins/boss-dev/agent-harness/skills/harness-doctor/scripts/tests/test_harness_doctor.py` — Add `test_doctor_reports_residual_logs_in_legacy_custom_log_dir` for `CLAUDE_HOOKS_LOG_DIR`.
- `plugins/boss-dev/agent-harness/skills/setup-agent-harness/SKILL.md` — Update description and `outputStyle` list (drop `tts-summary`).
- `plugins/boss-dev/agent-harness/skills/setup-agent-harness/scripts/setup_harness.py` — Inline namespace and `check_env` helpers so `setup_harness.py` has zero dependency on `hooks/utils/`; drop `tts-summary` from `OUTPUT_STYLES`.
- `plugins/boss-dev/agent-harness/skills/setup-second-brain/scripts/setup_second_brain.py` and `scripts/tests/test_setup_second_brain.py` — Update comment referencing `settings.json` hook settings; ensure executable bit on `setup_second_brain.py`.
- `plugins/boss-dev/agent-harness/skills/release-notes-generator/SKILL.md` and `references/commit-categories.md` — Replace hook-specific commit examples with general state refactoring examples.
- `plugins/boss-dev/agent-harness/skills/boss-cmux/SKILL.md` — Replace `cmux hooks setup` / `notification.requested` wait instructions with the portable completion marker contract.
- `plugins/boss-dev/agent-harness/skills/boss-cmux-team/SKILL.md`, `assets/roles/{lead,build-be,build-fe,plan,test}.md`, `assets/team-config.example.json` — Adopt attempt-correlated `TASK-DONE: <role> #<attempt-id> | <summary>` completion contract.
- `plugins/boss-dev/agent-harness/status_lines/status_line_v{2,3,4,7}.py` — Inline `_data_dir(project_dir)` helper instead of importing `hooks/utils/harness_paths.py`.
- `scripts/snyk-agent-scan.py` and `tests/test_snyk_agent_scan.py` — Inline Snyk scan helpers into `scripts/snyk-agent-scan.py` and remove `SessionStart` hook tests from `tests/test_snyk_agent_scan.py`.
- `plugins/boss-dev/agent-harness/README.md` and `plugins/boss-dev/agent-harness/docs/{agents,cmux-tutorial,commands,getting-started,output-styles,skills,status-lines}.md` — Remove hook sections/tables and update component counts.
- `README.md`, `docs/plugins/README.md`, `docs/plugins/agent-harness.md`, `docs/companion-ecosystem.md`, `docs/tutorials/agent-harness/README.md`, `CLAUDE.md`, `.github/copilot-instructions.md`, `.env.sample`, `.github/workflows/ci.yml`, `Makefile` — Align repo-level docs and config with hook removal.

### New Files

- `specs/remove-hooks.md` — This implementation plan.
- `plugins/boss-dev/agent-harness/skills/boss-cmux-team/scripts/tests/test_completion_contract.py` — Regression test suite verifying attempt-correlated `TASK-DONE` markers and prompt-echo safety.

## Implementation Phases

### Phase 1: Foundation & Hook Runtime Deletion

Delete `plugins/boss-dev/agent-harness/hooks/`, `output-styles/tts-summary.md`, `commands/sentient.md`, and `docs/hooks.md`. Clean up `.claude/` symlinks pointing to those deleted files while keeping repo-local `.claude/hooks/{skill-edit-review,version-bump-reviewer}.py`.

### Phase 2: Core Implementation (Self-Contained Scripts & Portable cmux Sentinels)

Decouple `harness_doctor.py`, `setup_harness.py`, `scripts/snyk-agent-scan.py`, and `status_line_v{2,3,4,7}.py` from `hooks/utils/`. Update `boss-cmux` and `boss-cmux-team` to use attempt-correlated completion sentinels and add `test_completion_contract.py`. Strip inline `hooks:` frontmatter from `builder.md`, `autobuild.md`, and `plan_w_team.md`.

### Phase 3: Integration, Manifests, Documentation & PR

Bump `agent-harness` to `0.33.0` in `plugin.json` and `marketplace.json`, update `userConfig`, refresh plugin and root documentation, run all validation gates, commit, push, and open the PR on `bossjones/boss-skills` using the `bossjones` GitHub account.

## Step by Step Tasks

IMPORTANT: Execute every step in order, top to bottom.

### 1. Delete the `agent-harness` Hook Runtime and Hook-Only Components

- Delete `plugins/boss-dev/agent-harness/hooks/` recursively (including `hooks.json`, all `.py`/`.sh` scripts, `utils/`, `validators/`, `tests/`, and any untracked `logs/` or `__pycache__/` under the plugin).
- Delete `plugins/boss-dev/agent-harness/output-styles/tts-summary.md`.
- Delete `plugins/boss-dev/agent-harness/commands/sentient.md`.
- Delete `plugins/boss-dev/agent-harness/docs/hooks.md`.
- Remove inline `hooks:` frontmatter blocks from:
  - `plugins/boss-dev/agent-harness/agents/team/builder.md`
  - `plugins/boss-dev/agent-harness/commands/autobuild.md`
  - `plugins/boss-dev/agent-harness/commands/plan_w_team.md`

### 2. Clean Up `.claude/` Symlink Mirrors

- Remove all symlinks in `.claude/hooks/` that target `../../plugins/boss-dev/agent-harness/hooks/*` and remove `.claude/hooks/{tests,utils,validators}` directories, leaving `.claude/hooks/skill-edit-review.py` and `.claude/hooks/version-bump-reviewer.py` intact.
- Remove `.claude/output-styles/tts-summary.md` and `.claude/commands/sentient.md`.
- Run `uv run scripts/symlink_plugins.py` and `uv run scripts/symlink_plugins.py --check` to ensure all remaining plugin components are cleanly linked.

### 3. Make `harness-doctor`, `setup-agent-harness`, `snyk-agent-scan`, and Status Lines Self-Contained

- Update `plugins/boss-dev/agent-harness/skills/harness-doctor/scripts/harness_doctor.py`:
  - Remove `_load_hook_module` and `HOOKS_DIR` imports.
  - Inline `slug`, `namespace_from`, `plugin_namespace`, `namespace_source` (defaulting to `"boss-skills"` when no marketplace manifest is found), `resolve_harness_root`, `logs_root` (honoring `CLAUDE_HOOKS_LOG_DIR`), `data_dir`, `cache_dir`, and `check_env`.
  - In `build_report`, compute `storage` using `logs_root(repo_root)`, `data_dir(repo_root)`, and `cache_dir(repo_root)` so `CLAUDE_HOOKS_LOG_DIR` is reflected in `harness_root.storage.logs`.
  - Ensure `chmod +x` on `harness_doctor.py`.
  - Update `plugins/boss-dev/agent-harness/skills/harness-doctor/SKILL.md` and `scripts/tests/test_harness_doctor.py` (adding `test_doctor_reports_residual_logs_in_legacy_custom_log_dir`).
- Update `plugins/boss-dev/agent-harness/skills/setup-agent-harness/scripts/setup_harness.py`:
  - Remove `_shared_hook_util` and `_shared_preflight`.
  - Inline `_plugin_namespace()` (walking ancestors for `.claude-plugin/marketplace.json`, fallback `"boss-skills"`) and `check_env()` (`uv`, `python3`, `gh`).
  - Remove `"tts-summary"` from `OUTPUT_STYLES`.
  - Update `plugins/boss-dev/agent-harness/skills/setup-agent-harness/SKILL.md` accordingly.
- Update `scripts/snyk-agent-scan.py` and `tests/test_snyk_agent_scan.py`:
  - Inline `SEVERITY_KEYS`, `ScanStatus`, `Finding`, `ScanResult`, `resolve_targets`, `_parse_json_loose`, `severity_counts`, `run_scan`, `summarize`, and `snyk_token` into `scripts/snyk-agent-scan.py` so it no longer touches `plugins/boss-dev/agent-harness/hooks`.
  - Update `tests/test_snyk_agent_scan.py` to load `scripts/snyk-agent-scan.py` for both pure-function and pre-commit CLI tests, and remove the `SessionStart` hook tests (`test_sessionstart_*`).
- Update `plugins/boss-dev/agent-harness/status_lines/status_line_v{2,3,4,7}.py`:
  - Replace the `HOOKS_DIR` `sys.path` injection and `from utils.harness_paths import data_dir` with a self-contained `data_dir(project_dir)` function that resolves `CLAUDE_HARNESS_DIR` / `CLAUDE_PLUGIN_OPTION_HARNESS_DIR` / `HARNESS_DIR` or `.boss-skills/data`.

### 4. Port Portable cmux Completion Sentinels (`boss-cmux` & `boss-cmux-team`)

- Update `plugins/boss-dev/agent-harness/skills/boss-cmux/SKILL.md` and `plugins/boss-dev/agent-harness/docs/cmux-tutorial.md` to replace `cmux hooks setup` / `notification.requested` event waiting with the completion-marker loop.
- Update `plugins/boss-dev/agent-harness/skills/boss-cmux-team/SKILL.md`, `assets/roles/{lead,build-be,build-fe,plan,test}.md`, and `assets/team-config.example.json` to use `TASK-DONE: <role> #<attempt-id> | <summary>` with fresh `ID="$(date +%s)-$RANDOM"` attempt IDs and bounded `read-screen` polling.
- Create `plugins/boss-dev/agent-harness/skills/boss-cmux-team/scripts/tests/test_completion_contract.py` (adapted from `Adobe-AIFoundations/aif-skills#108` for `boss-cmux-team`).

### 5. Update Plugin Manifests, Repo Config, and Documentation

- Edit `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json`:
  - Bump `"version"` to `"0.33.0"`.
  - Update `"description"` to `"Agent harness tooling for Claude Code: subagents, commands, skills, and scripts that build and operate agentic dev workflows."`.
  - Keep only `ENGINEER_NAME`, `ENABLE_STATUS_LINE`, and `STATUS_LINE_VARIANT` in `userConfig`.
- Edit `.claude-plugin/marketplace.json`:
  - Bump `agent-harness` `"version"` to `"0.33.0"` and update `"description"` to match `plugin.json`.
- Update `.env.sample`, `.github/workflows/ci.yml`, `pyproject.toml`, `Makefile`, `CLAUDE.md`, `.github/copilot-instructions.md`, `README.md`, `docs/plugins/README.md`, `docs/plugins/agent-harness.md`, `docs/companion-ecosystem.md`, `docs/tutorials/agent-harness/README.md`, `plugins/boss-dev/agent-harness/README.md`, and `plugins/boss-dev/agent-harness/docs/{agents,commands,getting-started,output-styles,skills,status-lines}.md`.
- Update `plugins/boss-dev/agent-harness/commands/fix-gh-pr-comments.md`, `plugins/boss-dev/agent-harness/skills/release-notes-generator/SKILL.md`, `plugins/boss-dev/agent-harness/skills/release-notes-generator/references/commit-categories.md`, `plugins/boss-dev/agent-harness/skills/setup-second-brain/scripts/setup_second_brain.py`, and `plugins/boss-dev/agent-harness/skills/setup-second-brain/scripts/tests/test_setup_second_brain.py`.

### 6. Validate, Commit, Push, and Open Pull Request

- Run all validation commands (`make verify-structure`, `make symlink-plugins-check`, `make lint`, `make test`, `make markdown-lint`, `make eval-ci`).
- Switch `gh auth` to `bossjones` (`gh auth switch --hostname github.com --user bossjones`).
- Stage all changes, commit with a conventional commit message and `Co-authored-by` trailer, push `feature/remove-hooks` to `origin`, and create the pull request via `gh pr create`.
- Restore `gh auth` to `malcolm_adobe` (`gh auth switch --hostname github.com --user malcolm_adobe`) when finished.

## Testing Strategy

- **Unit & Integration Tests:** Run `make test` (`uv run pytest`) across both `tests/` and `plugins/` to verify:
  - `test_harness_doctor.py` passes with standalone path/env helpers and `CLAUDE_HOOKS_LOG_DIR` coverage.
  - `test_setup_harness.py` passes with 7 output styles and standalone namespace/env helpers.
  - `test_completion_contract.py` passes all attempt-ID correlation and prompt-echo checks.
  - `test_snyk_agent_scan.py` passes all pure-function and pre-commit CLI tests without `hooks/utils/snyk.py`.
  - `test_version_bump_reviewer_hook.py` continues to pass for `.claude/hooks/{version-bump-reviewer,skill-edit-review}.py`.
- **Structure & Symlink Checks:** Run `make verify-structure` and `make symlink-plugins-check` to verify manifest parity, absence of empty component directories, and absence of broken symlinks in `.claude/`.
- **Linting & Skill Quality:** Run `make lint`, `make markdown-lint`, and `make eval-ci`.

## Acceptance Criteria

1. `plugins/boss-dev/agent-harness/hooks/` does not exist (`hooks.json` and all plugin hook files are deleted).
2. No broken symlinks exist in `.claude/`; `.claude/hooks/` contains only repo-owned hooks (`skill-edit-review.py`, `version-bump-reviewer.py`).
3. `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` both declare `agent-harness` at version `0.33.0` with aligned hook-free descriptions.
4. `make verify-structure`, `make symlink-plugins-check`, `make lint`, `make test`, `make markdown-lint`, and `make eval-ci` all exit 0.
5. `specs/remove-hooks.md` is committed and a PR is opened against `bossjones/boss-skills`.

## Validation Commands

Execute these commands to validate the task is complete:

- `make verify-structure` — Verify marketplace and plugin manifest structure
- `make symlink-plugins-check` — Verify `.claude/` symlink mirrors have no broken links or drift
- `make lint` — Run codespell, ruff check, ruff format, and basedpyright
- `make test` — Run full pytest suite across `tests/` and `plugins/`
- `make markdown-lint` — Lint Markdown and `SKILL.md` files with `rumdl`
- `make eval-ci` — Run static PluginEval quality gate over all skills

## Notes

- Reference PRs in `Adobe-AIFoundations/aif-skills`: `Adobe-AIFoundations/aif-skills#97` and `Adobe-AIFoundations/aif-skills#108`.
- `boss-skills` keeps its own repo-level authoring hooks in `.claude/hooks/skill-edit-review.py` and `.claude/hooks/version-bump-reviewer.py` (wired in `.claude/settings.json`), which are separate from the distributed `agent-harness` plugin.
