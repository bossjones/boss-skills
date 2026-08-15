# Plan: Augment the `meta-skill` for this repo's dual skill-location model, safe commits, and interview-driven evals

## Context

`plugins/boss-dev/agent-harness/skills/meta-skill/` is a newly-vendored skill (indydevdan/disler) whose `SKILL.md` teaches an agent to author *other* Agent Skills. It was written for Anthropic's stock personal/project model and does not fit this repo's conventions:

- It hardcodes `.claude/skills/` as the only destination and even points users at `~/.claude/skills/` for personal skills. This repo has **two** valid destinations — repo-internal (`.claude/skills/`) and plugin (`plugins/<category>/<plugin>/skills/`) — and **never** wants an agent writing into `~/.claude/skills/` (users choose install scope when they add the marketplace).
- Its "Test the Skill" step (Step 7) hardcodes `.claude/skills/` paths, so the agent will use the wrong path for plugin skills.
- Its "Commit to Version Control" step (Step 8) auto-runs `git add/commit/push` straight to the current branch — the user wants to verify first, commit only on a feature branch with a conventional message, and never push to main.
- It has **no** evaluation step at all, despite the repo having three eval systems. The user wants the skill to *interview* the user for which system and how deep, never assuming.

This plan rewrites `SKILL.md` to fix all of the above while reusing existing repo tooling (`version-bump-reviewer`, `commit-push-pr`, `skill-evals`/PluginEval, `scaffold-skill-eval`/`run-skill-eval`, `.claude/rules/*`) rather than duplicating it. The vendored `docs/` reference copies are left untouched; an authoritative override note in `SKILL.md` supersedes them.

## Objective

`plugins/boss-dev/agent-harness/skills/meta-skill/SKILL.md` guides an agent to:
1. Choose the correct skill destination (repo-internal vs plugin), asking the user when it isn't clear from context, and **never** using `~/.claude/skills/`.
2. Validate/test the new skill correctly regardless of which destination was chosen.
3. Run an **interview-driven** eval step offering all three repo eval systems at a depth matched to the skill's maturity — never assuming.
4. Never auto-commit: stop for user verification, then delegate versioning and committing to `version-bump-reviewer` + `commit-push-pr`, always on a feature branch with a conventional message, never pushing to main.

## Problem Statement

The vendored `SKILL.md` encodes a skill-authoring workflow that is subtly wrong for this repo: wrong destinations, an unwanted `~/.claude/skills/` target, path bugs in the test step, unsafe auto-commit, and a complete absence of the repo's evaluation tooling. An agent following it today would misplace skills, skip version bumps required by the marketplace, push to the wrong branch, and never evaluate the result.

## Solution Approach

Rewrite `SKILL.md` in place with targeted edits — the `docs/` reference files stay as vendored upstream copies. Wherever the repo already has authoritative guidance, **link to it** instead of duplicating: `.claude/rules/plugin-structure.md`, `.claude/rules/skill-development.md`, `CLAUDE.md`, `version-bump-reviewer`, `commit-push-pr`, `skill-evals`, `scaffold-skill-eval`, `run-skill-eval`. Detailed menus (the eval systems and their depths) go into a new `references/` file for progressive disclosure so the main body stays focused. Introduce a location abstraction — call the chosen directory `<skill-dir>` throughout, defined once as either `.claude/skills/<skill-name>/` or `plugins/<category>/<plugin-name>/skills/<skill-name>/`.

## Relevant Files

- **`plugins/boss-dev/agent-harness/skills/meta-skill/SKILL.md`** — primary edit target. All behavioral changes land here (Steps 2, 7, 8→renumbered, plus a new override callout and a new eval step, plus example path fixes).
- **`plugins/boss-dev/agent-harness/skills/meta-skill/docs/*.md`** — vendored Anthropic reference copies. **Leave unchanged**; they are superseded by the new override callout in `SKILL.md`.
- **`.claude/rules/plugin-structure.md`** — authoritative plugin layout, categories, `plugin.json`/`marketplace.json` rules. Link from Step 2.
- **`.claude/rules/skill-development.md`** — skill directory layout, trigger-pattern guidance, and the GitHub #12781 `!`backtick parser-bug warning. Link from Step 2 and Step 7.
- **`CLAUDE.md`** — repo-internal vs plugin skill distinction, eval-report locations (`docs/evals/`), `eval/` directory rules, `-workspace/` scratch convention. Link where relevant.
- **`.claude/skills/skill-evals/SKILL.md` + `references/plugin-eval.md`** — PluginEval (`/skill-evals`, `make eval-skill`, depths quick/standard/deep/thorough). Source for the eval menu.
- **`plugins/boss-experimental/boss-experimental/skills/scaffold-skill-eval/SKILL.md` and `.../run-skill-eval/SKILL.md`** — skillgrade fixture suites (`eval/` dir; smoke/reliable/regression presets). Source for the eval menu.
- **`version-bump-reviewer` (`.claude/skills/version-bump-reviewer/SKILL.md`) and `commit-push-pr` (`agent-harness` skill)** — the delegated commit/version flow.

### New Files

- **`plugins/boss-dev/agent-harness/skills/meta-skill/references/eval-systems.md`** — the full eval-system menu (the three systems, their invocations, depth knobs, output locations, and the "first draft = fastest, improvement loop = deeper" guidance + the PluginEval depths table). Referenced from the new eval step for progressive disclosure.
- **`plugins/boss-dev/agent-harness/skills/meta-skill/references/repo-conventions.md`** *(optional)* — condensed statement of the two destinations, the `~/.claude/skills/` prohibition, and the version-bump/commit rules, linking to the `.claude/rules/*` files. Only add this if Step 2 + the override callout grow too long to keep inline; otherwise keep inline and skip this file.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### 1. Add a "Repository Conventions (authoritative)" override callout
- Insert immediately after the `### Prerequisites` block (after line 17) in `SKILL.md`.
- State plainly: the `docs/` files are Anthropic's **general** reference; where they conflict with this repo, **this callout and `.claude/rules/*` win**.
- Enumerate the two hard rules:
  - Skills are created in exactly one of two places — repo-internal `.claude/skills/<skill-name>/` **or** a plugin `plugins/<category>/<plugin-name>/skills/<skill-name>/`.
  - **Never** create or write into `~/.claude/skills/` (or any home-directory skills dir). Users choose install scope by adding the marketplace themselves.
- Link to `.claude/rules/plugin-structure.md`, `.claude/rules/skill-development.md`, and `CLAUDE.md`.

### 2. Rewrite Step 2 (Create the Skill Directory Structure) for two destinations
- Replace current lines 46–59 (the `.claude/skills/`-only guidance and the `~/.claude/skills/` note).
- Explain the two destinations and how to choose:
  - **Repo-internal** (`.claude/skills/<skill-name>/`): locally-scoped tooling for *this* repo's own use; versioned by a `metadata.version` field in the skill's own frontmatter.
  - **Plugin** (`plugins/<category>/<plugin-name>/skills/<skill-name>/`): a shippable unit distributed via `marketplace.json`; versioned by the owning plugin's `plugin.json` **and** its `marketplace.json` entry (kept in lockstep).
- Add an explicit decision rule: **If the destination is not clear from the user's request or context, STOP and ask** via `AskUserQuestion` — (a) repo-internal or plugin; (b) if plugin, which existing category/plugin (list `plugins/*/*`) or a new plugin. Do not assume.
- Provide both `mkdir -p` forms, and define the placeholder `<skill-dir>` used by later steps as the chosen path.
- Keep the naming-conventions bullets. Link to `.claude/rules/plugin-structure.md` for categories and to `CLAUDE.md` for the repo-internal-vs-plugin distinction.

### 3. Update Step 7 (Test the Skill) to be destination-agnostic + repo-aware
- Replace the hardcoded `.claude/skills/<skill-name>/` paths (lines 174, 179) with the `<skill-dir>` placeholder defined in Step 2.
- Add repo-specific validation actions:
  - Run `./scripts/verify-structure.py` (structural validation; recognizes `-workspace/` scratch and `eval/` suites).
  - Run `make lint` and `make markdown-lint`.
  - Call out the GitHub #12781 parser bug: never use `!`backtick patterns or `@` file-refs in `SKILL.md` code fences — use `$ command` notation (link `.claude/rules/skill-development.md`).
- Keep the "test with relevant queries / iterate" guidance.

### 4. Insert a new eval step (interview-driven) before the commit step
- Add as a new numbered step (e.g. "Step 8: Evaluate the Skill"), pushing commit to Step 9.
- Core behavior: **interview the user, never assume** — ask (a) *which* eval system and (b) *how deep*, and explicitly tie depth to maturity: first draft → fastest/cheapest; later improvement loops → deeper.
- Summarize the three systems inline (one line each) and link to the new `references/eval-systems.md` for the full menu:
  1. **skill-creator loop** — conversational benchmark (with-skill vs baseline, variance) + description/trigger optimizer.
  2. **PluginEval** — `/skill-evals` or `make eval-skill SKILL=<skill-dir> DEPTH=<depth>`; depths **quick / standard / deep / thorough**; reports to `docs/evals/<plugin>/<skill>.md` (repo-internal → `docs/evals/<skill>.md`).
  3. **skillgrade suites** — `scaffold-skill-eval` to generate `<skill-dir>/eval/`, then `run-skill-eval` (local) or `run_eval.sh` presets **smoke / reliable / regression**.
- Include the PluginEval depths table (quick/standard/deep/thorough — layers/confidence/time/cost) in the reference file.
- Note the maturity guidance concretely: e.g. first draft = PluginEval `quick` or skillgrade `smoke`; improvement loop = `deep`/`thorough` or `reliable`/`regression`.

### 5. Rewrite Step 8 → Step 9 (Commit) to delegate and never auto-commit
- Replace current lines 192–202 (`git add/commit/push` + "shared with your team" note).
- New behavior:
  - **Do NOT auto-commit.** Stop and instruct the user to verify the skill first.
  - When the user is ready: **never push to `main`**; work on a **feature branch**.
  - For **plugin** skills: run **`version-bump-reviewer`** first (bumps `plugin.json` + `marketplace.json` in lockstep; note the `meta-skill` itself lives in `agent-harness`). For **repo-internal** skills: bump the skill's own `metadata.version`.
  - Then hand off to the **`commit-push-pr`** skill (or a manual conventional commit on the feature branch) — conventional commit message, feature branch, PR.
- Link `version-bump-reviewer` and `commit-push-pr`.

### 6. Fix destination paths in the four Examples
- Update the `mkdir`/`cat`/`touch` paths in Examples 1–4 (lines 262, 301–302, 340, 370, 377) to use the `<skill-dir>` placeholder and reference the Step 2 location decision, so examples no longer imply `.claude/skills/` is the only choice.
- Optionally add a one-line note to at least one example showing the plugin-path variant so both destinations appear in worked examples.

### 7. Create `references/eval-systems.md`
- Write the full three-system menu with exact invocations, depth knobs, output locations, and the maturity-based depth guidance + PluginEval depths table (sourced from `skill-evals/references/plugin-eval.md`, `scaffold-skill-eval`, `run-skill-eval`, and the skill-creator loop).

### 8. Update the Summary section
- Add the two new principles to the Summary (lines 392–402): "Choose the right destination (repo-internal vs plugin) — ask if unclear" and "Evaluate before shipping — interview for system + depth; commit only on a feature branch after you verify."

### 9. Validate
- Run the Validation Commands below; confirm no `~/.claude/skills` references remain, no auto-push, structure/lint pass.

## Testing Strategy

- **Static/grep checks** (see Validation Commands): confirm `~/.claude/skills` is fully removed from `SKILL.md`, the auto `git push` block is gone, and both destination paths + the `AskUserQuestion` decision rule are present.
- **Structure/lint**: `./scripts/verify-structure.py`, `make lint`, `make markdown-lint` all pass.
- **Behavioral trigger test** (manual, in a fresh session): ask "create a new skill for X". Confirm the agent (a) asks repo-internal vs plugin when unclear, (b) never proposes `~/.claude/skills/`, (c) reaches an eval step that interviews for system + depth, and (d) at commit time creates a feature branch + delegates to `version-bump-reviewer`/`commit-push-pr` rather than auto-pushing.
- **Dog-food eval** (optional): run `make eval-skill SKILL=plugins/boss-dev/agent-harness/skills/meta-skill DEPTH=quick` to score the rewritten skill.

## Acceptance Criteria

- `SKILL.md` contains **zero** references to `~/.claude/skills/` (or any home skills dir) and includes an explicit prohibition on writing there.
- `SKILL.md` documents **both** destinations (repo-internal + plugin) and a "STOP and ask via AskUserQuestion when unclear" rule.
- Step 7 uses a destination-agnostic `<skill-dir>` and adds `./scripts/verify-structure.py` + lint + the #12781 warning.
- A new interview-driven eval step exists, offers all **three** systems, ties depth to maturity, and does not assume a system/depth. `references/eval-systems.md` exists with the full menu + depths table.
- The commit step never auto-commits/pushes, mandates a feature branch (never `main`) + conventional message, and delegates to `version-bump-reviewer` (plugin) / `commit-push-pr`.
- Examples no longer hardcode `.claude/skills/` as the sole path.
- `./scripts/verify-structure.py`, `make lint`, `make markdown-lint` pass.

## Validation Commands

Run from repo root `/Users/malcolm/dev/bossjones/boss-skills`:

- `grep -rn "~/.claude/skills" plugins/boss-dev/agent-harness/skills/meta-skill/SKILL.md` — must return **nothing**.
- `grep -n "git push" plugins/boss-dev/agent-harness/skills/meta-skill/SKILL.md` — must **not** show an auto-push step (only, at most, guidance text within the delegated flow).
- `grep -n "plugins/<category>" plugins/boss-dev/agent-harness/skills/meta-skill/SKILL.md` — must show the plugin destination is documented.
- `grep -ni "AskUserQuestion\|STOP and ask\|not clear" plugins/boss-dev/agent-harness/skills/meta-skill/SKILL.md` — must show the location decision rule.
- `test -f plugins/boss-dev/agent-harness/skills/meta-skill/references/eval-systems.md && echo OK` — reference file exists.
- `./scripts/verify-structure.py` — structure passes.
- `make markdown-lint` and `make lint` — clean.

## Notes

- **Version bump for this change itself:** the `meta-skill` lives in the `agent-harness` plugin (currently v0.28.0) and is currently untracked (`?? .../meta-skill/`). Adding + editing it is a feature-bearing plugin change, so the *execution* session must bump `agent-harness` in both `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json` and its `.claude-plugin/marketplace.json` entry via `version-bump-reviewer` before committing — the same delegated flow this plan teaches the skill to use.
- **Keep the `docs/` files vendored/unchanged.** Do not edit the upstream Anthropic copies; the override callout (Step 1) is what reconciles them with repo rules.
- **Optional, out of scope:** the frontmatter `name: Create New Skills` overlaps with the repo's `write-a-skill` and `skill-creator`. Consider tightening the `description` triggers later to reduce activation collisions, but this plan does not change the skill's identity.
- No new dependencies. All referenced tooling (`scripts/verify-structure.py`, `make lint`, `make eval-skill`, the eval/commit skills) already exists in the repo.
