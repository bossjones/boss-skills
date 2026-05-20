# Plan: Port & slim the version-bump-reviewer skill for boss-skills

## Task Description

A `version-bump-reviewer` skill was copied into `.claude/skills/version-bump-reviewer/`
from a different repository (an Adobe-flavored marketplace with a
`skills/{1p,3p,shared}/` layout, per-skill `metadata.version` frontmatter, an
`adobe_mandatory_init` JSON block, and a bespoke JSON eval harness). None of those
assumptions hold in `boss-skills`. The port also shipped a broken PostToolUse hook
(`.claude/hooks/version-bump-reviewer.py`) that only matches `skills/{1p,3p,shared}/`
paths that never exist here, and two orphaned eval JSON files that `plugin-eval`
does not consume.

Re-home and slim the skill so its **primary job is to verify whether a version bump
is needed and at what semver tier**, using `plugin-eval` score/anti-pattern deltas as
a corroborating signal, then bump the correct per-repo version artifact and
auto-commit with a conventional message.

## Objective

When complete:

- `.claude/skills/version-bump-reviewer/SKILL.md` is a boss-skills-native skill that,
  given an uncommitted `SKILL.md` change, classifies the semver impact, runs a
  `plugin-eval` before/after delta as supporting evidence, decides **bump vs. no
  bump** and the tier, bumps the correct artifact, validates, and commits.
- It covers **both** skill classes: plugin skills under `plugins/**/skills/` and
  repo-internal skills under `.claude/skills/**`.
- The PostToolUse hook is rewritten to fire on real boss-skills paths and is
  **registered** in `.claude/settings.json` (it currently is not).
- The orphaned Adobe-specific eval JSON files are removed.
- `make verify-structure` and a `plugin-eval` score on the changed skill both pass.

## Problem Statement

The ported skill is unusable in `boss-skills` because every concrete reference is
wrong for this repo:

| Ported assumption | boss-skills reality |
|---|---|
| Skills at `skills/{1p,3p,shared}/<name>/SKILL.md` | Plugin skills at `plugins/<cat>/<plugin>/skills/<name>/SKILL.md`; repo-internal at `.claude/skills/<name>/SKILL.md` |
| Per-skill `metadata.version` in every SKILL.md | `doc-generator/SKILL.md` has no version field; marketplace versions **per plugin** |
| `adobe_mandatory_init` JSON block w/ `skill_version` | Does not exist anywhere in the repo |
| `.claude-plugin/marketplace.json` single `metadata.version` drives all skills | marketplace.json has a top-level `metadata.version` **and** per-plugin `plugins[].version`; plugins also carry `version` in their own `plugin.json` |
| `make validate-skills SKILLS=<name>` | No such target — repo uses `plugin-eval` via `make eval` / `eval-ci` / `eval-skill` and `make verify-structure` |
| Custom `trigger-evals.json` / `workflow-evals.json` harness | `plugin-eval` does **not** read those files; they are dead weight |
| `.claude/hooks/version-bump-reviewer.py` matches `skills/{1p,3p,shared}/` | That path never exists here; hook is dead. It is also **not registered** in `.claude/settings.json` |

## Solution Approach

Rewrite the skill around two skill classes and a `plugin-eval` evidence signal:

1. **Skill-class resolution.** From the changed `SKILL.md` path, determine whether
   it is a **plugin skill** (`plugins/<cat>/<plugin>/skills/<name>/SKILL.md`) or a
   **repo-internal skill** (`.claude/skills/<name>/SKILL.md`). This selects which
   version artifact gets bumped.

2. **Version artifacts per class.**
   - **Plugin skill** → bump, in lockstep:
     - `plugins/<cat>/<plugin>/.claude-plugin/plugin.json` → `version`
     - the matching entry in `.claude-plugin/marketplace.json` `plugins[]`, located
       by `source == "./plugins/<cat>/<plugin>"` → `version`
     - Edge: a plugin with a `plugin.json` but no marketplace entry (e.g.
       `proxmox-infra` when this spec was written) → bump `plugin.json` only and
       surface a finding that the plugin is unregistered.
   - **Repo-internal skill** → add/bump `metadata.version` in the SKILL.md
     frontmatter (introduce the field at `0.1.0` if absent). No marketplace or
     plugin.json artifact applies.

3. **plugin-eval as a bump signal (not the decider).** The semver rubric applied to
   the content diff stays the primary classifier. `plugin-eval` provides
   corroborating evidence:
   - **BEFORE score**: copy the skill directory to a temp dir, overwrite its
     `SKILL.md` with `git show HEAD:<path>`, run
     `plugin-eval score <tmpdir> --depth quick --output json`.
   - **AFTER score**: `plugin-eval score <skilldir> --depth quick --output json`.
   - `--depth quick` is static-only: deterministic, free, no API key — safe for a
     gating signal. `standard`/`certify` depths are optional, manual, opt-in.
   - Compare `composite.score` and the summed `anti_patterns` count. Fold the delta
     into the decision: anti-pattern count rose → at least `fix`/patch and flag a
     regression; composite dropped materially → flag; structural additions with a
     score gain → corroborates a minor bump. The rubric tier may be **escalated** by
     the eval delta, never silently downgraded.
   - New/untracked skill → no HEAD revision → no BEFORE; report AFTER as a sanity
     gate only and treat as initial publish.
   - Reuse the existing invocation contract from `scripts/eval-skills.py`:
     `uvx --from "$PLUGIN_EVAL_SOURCE" plugin-eval score ...`, default
     `git+https://github.com/wshobson/agents.git#subdirectory=plugins/plugin-eval`,
     overridable via the `PLUGIN_EVAL_SOURCE` env var. `scripts/eval-skills.py
     --skill <path>` already accepts an arbitrary directory containing a `SKILL.md`
     (works for `.claude/skills/` too), so prefer it for the AFTER score.

4. **Verify-vs-no-bump is a first-class outcome.** A genuine no-op touch, or a
   change that is purely cosmetic with no eval regression and no author version
   intent, can resolve to **no bump** (report and stop) — this is the "help me
   verify when a version needs to be bumped or not" core ask. Author-bump floor
   logic is retained: an author-written version is a floor, never a ceiling.

5. **Auto-commit.** Keep the full pipeline through to a conventional commit whose
   subject ends with the `(v<NEW_VERSION>)` grep anchor. Do not push.

6. **Repo hygiene.** Delete the orphaned eval JSON files, rewrite the hook for real
   paths, and register the hook (and the companion `skill-edit-review.py`) in
   `.claude/settings.json` `PostToolUse`, ordered so skill-review fires before
   version-bump.

## Relevant Files

- `.claude/skills/version-bump-reviewer/SKILL.md` — **rewrite**. The skill body:
  remove all Adobe/`{1p,3p,shared}`/`adobe_mandatory_init` references; add
  skill-class resolution, the plugin-eval signal, and boss-skills version artifacts.
- `.claude/skills/version-bump-reviewer/evals/trigger-evals.json` — **delete**
  (Adobe paths; `plugin-eval` doesn't consume it).
- `.claude/skills/version-bump-reviewer/evals/workflow-evals.json` — **delete**
  (same). Remove the now-empty `evals/` directory.
- `.claude/hooks/version-bump-reviewer.py` — **rewrite** path matching and nudge
  text for boss-skills (plugin skills + repo-internal skills); drop
  `adobe_mandatory_init` wording.
- `.claude/settings.json` — **modify**. Register `skill-edit-review.py` and
  `version-bump-reviewer.py` under `PostToolUse` (neither is registered today).
- `scripts/eval-skills.py` — **reference only**. Source of the canonical
  `uvx`/`PLUGIN_EVAL_SOURCE` invocation and the `--skill <path>` entrypoint reused
  by the skill.
- `Makefile` — **reference only**. `eval`, `eval-ci`, `eval-skill`,
  `verify-structure` targets and `EVAL_THRESHOLD ?= 57`.
- `.claude-plugin/marketplace.json` — **reference for logic**. Top-level
  `metadata.version` + per-plugin `plugins[].version` matched by `source`.
- `plugins/<cat>/<plugin>/.claude-plugin/plugin.json` — **reference for logic**.
  Per-plugin `version` field, bumped in lockstep with the marketplace entry.
- `.claude/hooks/skill-edit-review.py` — **reference**. The companion skill-review
  nudge whose path scope and ordering this skill mirrors.
- `.claude/skills/doc-generator/SKILL.md` — **reference**. Example repo-internal
  skill with no `metadata.version` (the field-introduction case).
- `skills.zip` (repo root, untracked, ~2.8 MB) — the port artifact. **Do not
  commit**; ensure it is removed from the working tree or gitignored.

### New Files

None. (Optional, called out in Notes: a `tests/test_version_bump_reviewer_hook.py`
for the rewritten hook's path matcher.)

## Implementation Phases

### Phase 1: Foundation

Establish the contracts the rewritten skill depends on, so the SKILL.md can
reference them precisely:

- Confirm the skill-class → version-artifact mapping (plugin skill vs.
  `.claude/skills/`), including the unregistered-plugin edge case.
- Confirm the `plugin-eval` invocation contract and the BEFORE/AFTER mechanism
  (temp-dir + `git show HEAD:<path>`), and that `--depth quick` is deterministic.
- Decide the `allowed-tools` set the skill needs (git read/write, `Read`, `Edit`,
  `Bash(uvx *)`, `Bash(./scripts/eval-skills.py *)`, `Bash(make *)`, `Bash(mkdir *)`,
  `Bash(cp *)`, `Bash(git show *)`).

### Phase 2: Core Implementation

- Rewrite `SKILL.md` (frontmatter + body) with the new workflow.
- Rewrite `.claude/hooks/version-bump-reviewer.py` path matcher and nudge text.
- Delete the orphaned eval JSON files and empty `evals/` dir.

### Phase 3: Integration & Polish

- Register both hooks in `.claude/settings.json` `PostToolUse` (skill-review
  before version-bump).
- Validate: lint the hook, run `make verify-structure`, score the rewritten skill
  with `plugin-eval`, dry-run the skill against a synthetic plugin-skill diff and a
  synthetic repo-internal diff.
- Remove `skills.zip` from the working tree (or gitignore it).

## Step by Step Tasks

IMPORTANT: Execute every step in order, top to bottom.

### 1. Verify contracts and inputs

- Re-read `scripts/eval-skills.py` for the exact `uvx --from` command, the
  `PLUGIN_EVAL_SOURCE` env override, and the `--skill <path>` behavior.
- Confirm `.claude-plugin/marketplace.json` maps a plugin by `source ==
  "./plugins/<cat>/<plugin>"` and that `plugins[].version` mirrors that plugin's
  `.claude-plugin/plugin.json` `version`.
- Confirm `.claude/skills/doc-generator/SKILL.md` has no `metadata.version` (the
  field-introduction path) and that the current ported
  `.claude/skills/version-bump-reviewer/SKILL.md` likewise has none.

### 2. Rewrite SKILL.md frontmatter

- `name: version-bump-reviewer` (unchanged).
- `description`: rewrite to boss-skills triggers — drop "skills/{1p,3p,shared}",
  "adobe_mandatory_init", "marketplace.json metadata.version" single-source
  wording. Cover: a `SKILL.md` under `plugins/**/skills/` or `.claude/skills/**`
  was edited/created and is uncommitted; user says "bump the version", "cut a
  release", "does this need a version bump", "verify the version". Keep "Run this
  AFTER skill-review".
- `allowed-tools`: `Bash(git diff *) Bash(git status *) Bash(git log *) Bash(git
  show *) Bash(git add *) Bash(git commit *) Bash(make *) Bash(uvx *) Bash(mkdir
  *) Bash(cp *) Read Edit`.

### 3. Rewrite SKILL.md body — Phase 1: Pick exactly one skill

- Discover changed files with `git diff --name-only HEAD --
  'plugins/**/SKILL.md' '.claude/skills/**/SKILL.md'`; also `git status --short`
  for untracked new `SKILL.md`.
- Zero → tell the user nothing needs a bump and stop.
- One → that's the target. More than one → handle the alphabetically first, list
  the rest for re-run (one independent commit each).

### 4. Rewrite SKILL.md body — Phase 2: Resolve skill class & version artifacts

- If path matches `plugins/<cat>/<plugin>/skills/<name>/SKILL.md` → **plugin
  skill**. Owning plugin manifest: `plugins/<cat>/<plugin>/.claude-plugin/
  plugin.json`. Marketplace entry: the `plugins[]` element whose `source` is
  `./plugins/<cat>/<plugin>`. If no marketplace entry exists, record an
  "unregistered plugin" finding and bump `plugin.json` only.
- If path matches `.claude/skills/<name>/SKILL.md` → **repo-internal skill**.
  Version artifact: `metadata.version` in this SKILL.md's own frontmatter
  (introduce at `0.1.0` if the field is absent).

### 5. Rewrite SKILL.md body — Phase 3: Read current versions

- Capture the relevant CURRENT version(s): plugin skill → `plugin.json.version`
  and marketplace `plugins[].version`; repo-internal → SKILL.md
  `metadata.version` (or "absent").
- Detect author intent: from `git diff HEAD -- <path>` (and the manifests for
  plugin skills), find any removed `version`/`metadata.version` line to establish
  the pre-edit baseline `ORIGINAL_VERSION`. If none, `ORIGINAL_VERSION =
  CURRENT_VERSION`.

### 6. Rewrite SKILL.md body — Phase 4: plugin-eval before/after signal

- BEFORE (skip if untracked/new): create a temp dir, `cp -R` the skill directory
  into it, overwrite the copy's `SKILL.md` with `git show HEAD:<path>`, run
  `uvx --from "${PLUGIN_EVAL_SOURCE:-git+https://github.com/wshobson/agents.git#subdirectory=plugins/plugin-eval}"
  plugin-eval score <tmpdir> --depth quick --output json`. Capture
  `composite.score` and summed `anti_patterns`.
- AFTER: same against the working-tree skill directory (prefer
  `./scripts/eval-skills.py --skill <skilldir>` for parity with CI).
- Record `Δscore` and `Δanti_patterns`. Document in the SKILL.md that this is a
  **signal feeding the tier decision**, not the decider, and that the eval delta
  may escalate the rubric tier but never silently lowers it.

### 7. Rewrite SKILL.md body — Phase 5: Classify the diff (de-Adobe'd rubric)

- Keep the Major/Minor/Patch(semantic)/Patch(cosmetic) tier table. Triggers:
  - **Major**: a workflow step removed; a tool removed from `allowed-tools` or the
    body; `name` changed; skill directory relocated; required inputs/outputs
    changed breakingly; a user-facing `description` trigger narrowed.
  - **Minor**: new workflow step; tool added; description broadened; new optional
    behavior; new edge-case handling.
  - **Patch (semantic)**: small behavioral fix not changing inputs/outputs.
  - **Patch (cosmetic)**: typos, prose, reordering, link/format-only.
- **Remove** the Adobe-only edge cases (`license`, `metadata.visibility`,
  `adobe_mandatory_init`). Keep "ambiguous → prefer the higher tier".
- Fold in the Phase 4 eval delta as corroborating evidence per Step 6.

### 8. Rewrite SKILL.md body — Phase 6: Decide bump-or-not & compute new version

- Allow an explicit **NO BUMP** outcome: empty/no-op diff, or cosmetic-only with
  no eval regression and no author version intent → report rationale and stop
  before editing.
- Otherwise compute `RUBRIC_NEW_VERSION` from `ORIGINAL_VERSION` by tier. Apply
  the author-bump floor: `max(CURRENT_VERSION, RUBRIC_NEW_VERSION)`; if the rubric
  (or escalated eval signal) demands higher, raise and explain in the commit body.
- Brand-new/untracked skill → no bump; accept the author's version (default
  `0.1.0`); commit type `feat`.
- Preserve any pre-release suffix verbatim (never drop `-alpha` etc.).

### 9. Rewrite SKILL.md body — Phase 7: Apply the version edit(s)

- **Plugin skill**: `Edit` `version` in `plugins/<cat>/<plugin>/.claude-plugin/
  plugin.json` and the matching `plugins[].version` in
  `.claude-plugin/marketplace.json` to the new version (same tier bump). If the
  plugin is unregistered in marketplace.json, edit only `plugin.json` and surface
  the finding.
- **Repo-internal skill**: `Edit` (or introduce) `metadata.version` in the
  SKILL.md frontmatter. Use enough surrounding context to be unambiguous.
- Remove the entire Adobe `adobe_mandatory_init`/`skill_version` Phase.

### 10. Rewrite SKILL.md body — Phase 8: Validate (boss-skills targets)

- Replace `make validate-skills` with: for any change touching
  `marketplace.json`/`plugin.json`, run `make verify-structure`; always run a
  `plugin-eval` score (AFTER, already computed in Phase 4) and require it did not
  regress below the prior anti-pattern/score baseline.
- On failure: **abort before committing**, leave edits on disk, surface the tool
  output, tell the user to fix and re-run. No rollback.

### 11. Rewrite SKILL.md body — Phase 9: Stage & commit

- `git add` exactly the touched files (SKILL.md and/or plugin.json +
  marketplace.json). Conventional commit via heredoc; subject **must** end with
  `(v<NEW_VERSION>)`. Keep the tier→type table (`feat!`/`feat`/`fix`/`chore`,
  new skill = `feat`). Body notes the eval delta and any author-floor escalation.
  Confirm with `git status` and `git log -1 --oneline`. Do not push.
- Update "What this skill is NOT" and "Edge cases" sections to boss-skills reality
  (remove Adobe references; add the unregistered-plugin and field-introduction
  cases; note repo-internal skills bump only their own `metadata.version`).

### 12. Delete orphaned eval files

- Delete `.claude/skills/version-bump-reviewer/evals/trigger-evals.json` and
  `workflow-evals.json`. Remove the empty `evals/` directory.

### 13. Rewrite the PostToolUse hook

- Rewrite `.claude/hooks/version-bump-reviewer.py` so the matcher accepts:
  - `plugins/<cat>/<plugin>/skills/<name>/SKILL.md` (≥ 6 path parts, first part
    `plugins`, `skills` segment present, basename `SKILL.md`), and
  - `.claude/skills/<name>/SKILL.md` (4 parts: `.claude`, `skills`, `<name>`,
    `SKILL.md`).
- Rewrite the `reason` text: remove `adobe_mandatory_init`/marketplace
  single-version wording; instruct invoking `version-bump-reviewer` to classify
  and bump the **owning plugin's `plugin.json` + marketplace entry** (plugin
  skills) or the SKILL.md `metadata.version` (repo-internal); keep "address
  skill-review findings first".

### 14. Register hooks in settings.json

- Add `PostToolUse` command entries for `uv run $CLAUDE_PROJECT_DIR/.claude/hooks/
  skill-edit-review.py` and `uv run $CLAUDE_PROJECT_DIR/.claude/hooks/
  version-bump-reviewer.py`, alongside the existing `post_tool_use.py` entry,
  matcher `""` (PostToolUse has no per-tool matcher need here; the scripts
  self-filter on `tool_name`). Ensure skill-review is listed before version-bump.
- Mirror the JSON shape already used by the existing `post_tool_use.py` entry.

### 15. Remove the port artifact

- Remove `skills.zip` from the working tree, or add it to `.gitignore`. It must
  not be committed.

### 16. Validate the work

- Run the Validation Commands below; all must pass before the task is complete.

## Testing Strategy

- **Hook unit test (optional but recommended):** add
  `tests/test_version_bump_reviewer_hook.py` driving the rewritten hook's
  path-matching with stdin payloads: a `plugins/.../skills/.../SKILL.md` Edit
  (should nudge), a `.claude/skills/.../SKILL.md` Edit (should nudge), a
  `skills/1p/.../SKILL.md` (should NOT nudge — proves de-Adobe'd), a non-SKILL.md
  Edit (should NOT nudge), a non-Edit tool (should NOT nudge).
- **Skill dry-run, plugin-skill case:** make a throwaway whitespace/typo edit to
  an existing plugin skill (e.g.
  `plugins/social-media/twitter-tools/skills/twitter-to-reel/SKILL.md`), invoke
  the skill, confirm it classifies cosmetic/patch, computes the
  `plugin.json` + marketplace `plugins[].version` bump, runs the plugin-eval
  before/after, and produces a `chore(...)(vX.Y.Z)` commit. Revert.
- **Skill dry-run, repo-internal case:** make a throwaway edit to
  `.claude/skills/doc-generator/SKILL.md`, invoke the skill, confirm it
  introduces/bumps `metadata.version` in that SKILL.md only (no marketplace
  touch). Revert.
- **No-bump case:** invoke against a no-op touch and confirm the skill reports
  "no bump needed" and stops without editing.
- **Edge: unregistered plugin:** dry-run against a
  `plugins/boss-homelab/proxmox-infra/skills/proxmox-infrastructure/SKILL.md` edit
  (proxmox-infra was unregistered when this spec was written) and confirm the skill
  bumps `plugin.json` only and surfaces the unregistered-plugin finding.
- **plugin-eval self-score:** the rewritten SKILL.md itself scores cleanly at
  `--depth quick` (no new anti-patterns vs. the ported baseline).

## Acceptance Criteria

- `SKILL.md` contains zero occurrences of `1p`, `3p`, `shared`,
  `adobe_mandatory_init`, `skill_version`, or `make validate-skills`.
- `SKILL.md` documents both skill classes and their distinct version artifacts
  (plugin → `plugin.json` + marketplace `plugins[].version`; repo-internal →
  SKILL.md `metadata.version`), including the unregistered-plugin and
  field-introduction edge cases.
- `SKILL.md` documents the `plugin-eval` before/after signal (temp-dir + `git
  show HEAD:<path>`, `--depth quick`, `PLUGIN_EVAL_SOURCE` override) and states it
  feeds — but does not solely decide — the tier, and may escalate but never
  silently lower it.
- "No bump needed" is an explicit, documented outcome.
- `.claude/skills/version-bump-reviewer/evals/` is gone.
- `.claude/hooks/version-bump-reviewer.py` nudges for
  `plugins/**/skills/**/SKILL.md` and `.claude/skills/**/SKILL.md`, and does **not**
  nudge for `skills/1p/**`, non-SKILL.md edits, or non-Edit tools.
- `.claude/settings.json` `PostToolUse` registers both
  `skill-edit-review.py` and `version-bump-reviewer.py`, skill-review first, and
  remains valid JSON.
- `make verify-structure` passes (marketplace/plugin manifests still valid).
- `make eval-skill SKILL=.claude/skills/version-bump-reviewer` (or
  `./scripts/eval-skills.py --skill .claude/skills/version-bump-reviewer`)
  produces a score with no new anti-patterns vs. baseline.
- `skills.zip` is not tracked and not staged.
- `make lint` and `make markdown-lint` pass.

## Validation Commands

Execute these to validate the task is complete:

- `python3 -c "import json,sys; d=json.load(open('.claude/settings.json')); blob=json.dumps(d['hooks']['PostToolUse']); assert 'skill-edit-review' in blob and 'version-bump-reviewer' in blob, 'hooks not registered'; print('hooks registered OK')"`
  — settings.json registers both hooks and is valid JSON.
- `! test -d .claude/skills/version-bump-reviewer/evals && echo "evals/ removed OK"`
  — orphaned eval dir is gone.
- `grep -niE '1p|3p|shared|adobe_mandatory_init|skill_version|validate-skills' .claude/skills/version-bump-reviewer/SKILL.md && echo "FAIL: Adobe refs remain" || echo "de-Adobe'd OK"`
  — no ported Adobe references remain.
- `uv run python -m py_compile .claude/hooks/version-bump-reviewer.py` — hook
  compiles.
- `printf '%s' '{"tool_name":"Edit","tool_input":{"file_path":"plugins/social-media/twitter-tools/skills/twitter-to-reel/SKILL.md"}}' | CLAUDE_PROJECT_DIR=$(pwd) uv run .claude/hooks/version-bump-reviewer.py | grep -q version-bump-reviewer && echo "plugin-skill nudge OK"`
- `printf '%s' '{"tool_name":"Edit","tool_input":{"file_path":".claude/skills/doc-generator/SKILL.md"}}' | CLAUDE_PROJECT_DIR=$(pwd) uv run .claude/hooks/version-bump-reviewer.py | grep -q version-bump-reviewer && echo "repo-internal nudge OK"`
- `printf '%s' '{"tool_name":"Edit","tool_input":{"file_path":"skills/1p/foo/SKILL.md"}}' | CLAUDE_PROJECT_DIR=$(pwd) uv run .claude/hooks/version-bump-reviewer.py | grep -q version-bump-reviewer && echo "FAIL: still matches Adobe path" || echo "Adobe path correctly ignored"`
- `make verify-structure` — marketplace and plugin manifests validate.
- `./scripts/eval-skills.py --skill .claude/skills/version-bump-reviewer` — skill
  scores under plugin-eval with no errors.
- `make lint` — devtools/skills lint clean.
- `make markdown-lint` — SKILL.md markdown lint clean.
- `git status --porcelain | grep -q '^?? skills.zip' && echo "FAIL: skills.zip untracked & present" || echo "skills.zip handled OK"`

## Notes

- **plugin-eval is pulled on demand, not vendored.** Default source is
  `git+https://github.com/wshobson/agents.git#subdirectory=plugins/plugin-eval`
  via `uvx`, overridable with `PLUGIN_EVAL_SOURCE` (same escape hatch as
  `scripts/eval-skills.py` and `make eval-ci`). The skill must reuse this contract
  verbatim — do not hardcode a different invocation.
- `--depth quick` (static layer only) is the gating signal: deterministic, free,
  no API key, CI-safe. `standard`/`certify` (LLM judge / Monte Carlo, uses Claude
  Code Max) are optional manual deep-dives the skill may *mention* but must not
  require for the bump decision.
- The repo's top-level `.claude-plugin/marketplace.json` `metadata.version`
  (currently `0.1.0`) is intentionally **out of scope** for this skill per the
  chosen version model (plugin skills → owning plugin; repo-internal skills →
  per-skill `metadata.version`). Document this explicitly in "What this skill is
  NOT" so a future maintainer doesn't wire it back in.
- `EVAL_THRESHOLD` is `57` in the `Makefile` (regression floor =
  `min(baseline) - 5`). The skill should report the AFTER score against this floor
  as context but the bump decision is driven by the *delta*, not the absolute
  floor.
- No new third-party Python dependencies are required (`uvx` and the stdlib cover
  the eval invocation). If the optional hook test is added, it uses the existing
  `pytest` setup — no `uv add` needed.
- Follow the project audit protocol when finally auditing the rewritten skill:
  pass only the path, no context about what was changed.
