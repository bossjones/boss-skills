# Plan: Remove the agent-harness hook runtime (hooks.json) and release v1.0.0

## Task Description

Port the `agent-harness` hook-runtime removal from `Adobe-AIFoundations/aif-skills`
(`Adobe-AIFoundations/aif-skills#97` "refactor(agent-harness): remove hook runtime" and
`Adobe-AIFoundations/aif-skills#108` "feat(agent-harness)!: remove hook runtime, release 4.0.0")
into `bossjones/boss-skills`. Delete `plugins/boss-dev/agent-harness/hooks/hooks.json` and the whole
lifecycle-hook runtime, remove every component that only worked because of those hooks, make the
remaining skills and scripts standalone, remove contradictions from the docs, and open a PR on
`bossjones/boss-skills`.

## Objective

When this plan is complete:

1. `plugins/boss-dev/agent-harness/hooks/` (with `hooks.json`, every event handler, `utils/`,
   `validators/`, and `tests/`) no longer exists.
2. No component depends on data the hooks used to write. Only `status_line_v10.py` ships;
   `update_status_line`, `sentient`, and the `tts-summary` output style are gone.
3. `harness-doctor`, `setup-agent-harness`, `setup-second-brain`, `pyrefly-typing`, and
   `scripts/snyk-agent-scan.py` have no imports from `hooks/utils/`.
4. `boss-cmux`, `boss-cmux-team`, and `docs/cmux-tutorial.md` describe one completion contract
   (a printed, attempt-correlated `TASK-DONE` marker checked with bounded `read-screen`), with
   regression tests.
5. The `.claude/` mirror, CI, Makefile, `.env.sample`, and all docs match what ships. Component
   counts are correct.
6. `agent-harness` is at `1.0.0` in both `plugin.json` and `marketplace.json`.

## Problem Statement

The plugin shipped 20 lifecycle-hook events in `hooks/hooks.json`. Each fired `uv run` on every
event, adding latency, cross-runtime friction (Copilot CLI rejects empty matchers), and side effects
(TTS audio, auto-formatting, background LLM calls) in every consumer repo. Other pieces silently
depended on the hooks:

- `harness-doctor`, `setup-agent-harness`, `setup-second-brain`, `pyrefly-typing`, and the
  `snyk-agent-scan` pre-commit gate imported `hooks/utils/*` by path.
- `status_line_v2/v3/v4` and `/agent-harness:update_status_line` read
  `.{plugin-repo}/data/sessions/<id>.json`, which only `user_prompt_submit.py` wrote.
- `boss-cmux` / `boss-cmux-team` waited on `cmux hooks setup` notification events, which never
  fire for Claude Code turns.
- Inline `hooks:` frontmatter in `team/builder.md`, `autobuild.md`, `plan_w_team.md`, and
  `.claude/commands/build_with_parallel.md` invoked hook validator scripts.

## Solution Approach

Follow `Adobe-AIFoundations/aif-skills#108`, adapted to this repo. Where aif left contradictions
(its `cmux-tutorial.md` still teaches `cmux hooks setup`), resolve them here instead of copying them.

| Area | Change |
| --- | --- |
| Hook runtime | Delete `hooks/` in full, `docs/hooks.md`, `commands/sentient.md`, `output-styles/tts-summary.md`, and inline `hooks:` frontmatter. |
| Status lines | Keep only `status_line_v10.py` (matches aif). Delete `status_line.py` and `v2`–`v9`, delete `update_status_line`, and drop the `STATUS_LINE_VARIANT` option. `install_status_line` still recognizes an old variant as "ours" and replaces it with v10. |
| Standalone scripts | Inline namespace, path, and environment checks into each script. `harness-doctor` keeps read-only discovery of legacy overrides (`CLAUDE_HARNESS_DIR`, `HARNESS_DIR`, `CLAUDE_HOOKS_LOG_DIR`) so it can still find residual artifacts. |
| Namespace | No code writes `.{plugin-repo}/` anymore. It is documented only as a legacy residual root (`.boss-skills/` here) that `setup-agent-harness` ignores and `harness-doctor` reports. The fallback namespace is `boss-skills`, as aif falls back to `aif-skills`. |
| Snyk | Move the scan helpers into `scripts/snyk-agent-scan.py`. Drop the session-start-only helpers (`resolve_targets`, `TARGET_GLOBS`) and the removed `CLAUDE_PLUGIN_OPTION_SNYK_TOKEN` lookup. |
| cmux | Use the attempt-id `TASK-DONE: <role> #<attempt-id> \| <summary>` contract and add `test_completion_contract.py`. Rewrite tutorial sections 1, 4, 5, and 8 to match. |
| Repo config | Remove the CI tmux step and the `libtmux` dev dependency, the `make logs` / `make logs-session` targets, and the hook-only `.env.sample` entries. |
| Version | Removing components is **Major** under the repo's `version-bump-reviewer` rubric, and aif bumped 3.2.0 → 4.0.0. Bump `0.32.0` → `1.0.0`. |

## Relevant Files

- `plugins/boss-dev/agent-harness/hooks/**`, `docs/hooks.md`, `commands/sentient.md`,
  `commands/update_status_line.md`, `output-styles/tts-summary.md`,
  `status_lines/status_line{,_v2..v9}.py`: delete.
- `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`:
  version `1.0.0`, description without "hooks", `userConfig` reduced to `ENGINEER_NAME` and
  `ENABLE_STATUS_LINE`.
- `agents/team/builder.md`, `commands/autobuild.md`, `commands/plan_w_team.md`,
  `.claude/commands/build_with_parallel.md`: strip inline `hooks:` blocks.
- `skills/harness-doctor/scripts/harness_doctor.py` (+ test),
  `skills/setup-agent-harness/scripts/setup_harness.py`,
  `skills/setup-second-brain/scripts/setup_second_brain.py`,
  `skills/pyrefly-typing/scripts/pyrefly_setup.py`: standalone helpers.
- `scripts/snyk-agent-scan.py`, `tests/test_snyk_agent_scan.py`: inline helpers, remove dead code.
- `scripts/install_status_line.py`, `commands/install_status_line.md`,
  `tests/test_install_status_line.py`: v10 only, with legacy-variant replacement.
- `skills/boss-cmux/SKILL.md`, `skills/boss-cmux-team/**`, `docs/cmux-tutorial.md`: completion
  contract.
- `.claude/` symlink mirror (`hooks/`, `commands/`, `output-styles/`, `status_lines/`): remove
  links to deleted files, keep repo-owned `.claude/hooks/{skill-edit-review,version-bump-reviewer}.py`.
- `.github/workflows/ci.yml`, `pyproject.toml`, `uv.lock`, `Makefile`, `.env.sample`, `CLAUDE.md`,
  `.github/copilot-instructions.md`: repo config.
- `README.md`, `docs/plugins/{README,agent-harness}.md`, `docs/companion-ecosystem.md`,
  `docs/tutorials/agent-harness/README.md`, `plugins/boss-dev/agent-harness/README.md`,
  `plugins/boss-dev/agent-harness/docs/*.md`: docs and component counts (21 skills, 16 commands,
  6 agents, 7 output styles, 1 status line).

### New Files

- `specs/remove-hooks.md`: this plan.
- `plugins/boss-dev/agent-harness/skills/boss-cmux-team/scripts/tests/test_completion_contract.py`:
  attempt-id correlation and prompt-echo regression tests.

## Implementation Phases

### Phase 1: Foundation

Delete the hook runtime and every hook-only component. Clean the `.claude/` mirror with
`uv run scripts/symlink_plugins.py`.

### Phase 2: Core Implementation

Make the remaining scripts standalone, port the cmux completion contract, and reduce status lines to
v10.

### Phase 3: Integration & Polish

Bump the version, align repo config and docs, validate, and open the PR.

## Step by Step Tasks

IMPORTANT: Execute every step in order, top to bottom.

### 1. Delete the hook runtime and hook-only components

- `git rm -r plugins/boss-dev/agent-harness/hooks` plus `docs/hooks.md`, `commands/sentient.md`,
  and `output-styles/tts-summary.md`.
- Strip inline `hooks:` frontmatter from `team/builder.md`, `autobuild.md`, `plan_w_team.md`, and
  `.claude/commands/build_with_parallel.md`.

### 2. Reduce status lines to v10

- Delete `status_line.py`, `status_line_v2.py` … `status_line_v9.py`, and
  `commands/update_status_line.md`.
- Remove the `STATUS_LINE_VARIANT` user-config option and the variant step from
  `commands/install_status_line.md`.
- Keep `is_ours()` matching any `agent-harness/status_lines/*` path so an installed legacy variant
  is replaced with v10, and cover it with a test.

### 3. Make the remaining scripts standalone

- Inline namespace, path, and `check_env` helpers into `harness_doctor.py`, `setup_harness.py`,
  `setup_second_brain.py`, and `pyrefly_setup.py`.
- Move the Snyk helpers into `scripts/snyk-agent-scan.py`, and drop `resolve_targets`,
  `TARGET_GLOBS`, `EXCLUDE_DIR_PREFIXES`, and the `CLAUDE_PLUGIN_OPTION_SNYK_TOKEN` lookup.

### 4. Port the cmux completion contract

- Update `boss-cmux`, `boss-cmux-team` (SKILL, roles, example config), and `docs/cmux-tutorial.md`
  §1, §4, §5, and §8. Add `test_completion_contract.py`.

### 5. Clean the mirror, repo config, and docs

- Run `uv run scripts/symlink_plugins.py`, and remove any `.claude/` links to deleted files.
- Remove the CI tmux step and the `libtmux` dev dependency, the `logs` / `logs-session` Makefile
  targets, and the hook-only `.env.sample` keys.
- Update every doc listed under Relevant Files, and add the missing `github-pr-review`,
  `harness-doctor`, and `setup-agent-harness` entries to `docs/skills.md`.

### 6. Version, validate, and ship

- Bump `agent-harness` to `1.0.0` in `plugin.json` and `marketplace.json`.
- Run the validation commands.
- Push to `bossjones/boss-skills` as `bossjones`. `.github/workflows/ci.yml` changes need either
  a token with `workflow` scope or the `bossjones` SSH key. Open or update the PR, then restore
  `gh auth` to `malcolm_adobe`.

## Testing Strategy

- `make test` covers `test_harness_doctor.py` (including the legacy `CLAUDE_HOOKS_LOG_DIR`),
  `test_setup_harness.py`, `test_completion_contract.py`, `test_snyk_agent_scan.py`,
  `test_install_status_line.py` (legacy-variant replacement), and
  `test_version_bump_reviewer_hook.py`.
- Smoke-run each standalone `detect` / report script to confirm none of them import the deleted
  `hooks/`.
- `make verify-structure` and `make symlink-plugins-check` catch manifest drift and broken links.

## Acceptance Criteria

1. `plugins/boss-dev/agent-harness/hooks/` does not exist, and nothing outside `specs/` refers to
   the deleted hook scripts.
2. `status_lines/` contains only `status_line_v10.py`, and `update_status_line` is gone.
3. `.claude/hooks/` contains only `skill-edit-review.py` and `version-bump-reviewer.py`, and
   `make symlink-plugins-check` reports no broken links.
4. No doc tells the reader to run `cmux hooks setup` or wait on `notification.requested`.
5. `plugin.json` and `marketplace.json` both declare `agent-harness` `1.0.0`.
6. All validation commands exit 0.

## Validation Commands

- `make verify-structure`: marketplace and plugin manifest structure
- `make symlink-plugins-check`: `.claude/` mirror has no broken links or drift
- `make lint`: codespell, ruff, and basedpyright
- `make test`: full pytest suite
- `make markdown-lint`: rumdl over docs and SKILL.md files
- `make eval-ci`: static PluginEval quality gate
- `uv run scripts/validate-unicode-hygiene.py`: Unicode hygiene gate

## Notes

- Reference PRs: `Adobe-AIFoundations/aif-skills#97`, `Adobe-AIFoundations/aif-skills#108`.
- Repo-local authoring hooks in `.claude/hooks/` (wired in `.claude/settings.json`) are separate
  from the distributed plugin and stay.
- Residual `.boss-skills/`, `logs/`, and `.claude/data/` directories in user projects are never
  migrated or deleted automatically. `harness-doctor` reports them for review.
