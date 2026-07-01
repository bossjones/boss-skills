# Plan: Vendor `github-pr-review` skill into agent-harness (hotfix gh PR review)

> Deliverable: this plan is the spec. As the **first implementation step**, copy it verbatim to
> `specs/hotfix-gh-pr-review.md` (plan mode only permits editing the plan file, so it lands in specs/
> during execution).

## Context

The user ran the external `/github-pr-review:github-pr-review` skill against
[`bossjones/mem_tui#2`](https://github.com/bossjones/mem_tui/pull/2) and disliked the result. The
posted review body and inline comment both contain a **literal** string —
`@/private/tmp/.../scratchpad/pr2-review-summary.md` and `@/private/tmp/.../pr2-comment-body.md` —
instead of rendered markdown.

Root cause (verified by reading the upstream SKILL.md): the skill itself is fine — it teaches inline
bodies via `-f 'comments[][body]=...'` and contains **no** `@file` patterns. The agent improvised:
it drafted the review to scratchpad files, then passed them as `@path` to `gh pr review --body` /
`gh api -f body=...`. `gh` only expands `@file` for `-F/--field`; for `-f/--raw-field` and
`gh pr review --body` it posts the string **literally**. So the skill's real gap is that it never
tells the model how to pass long/multi-line bodies safely.

The user wants to **own and iterate on this skill** rather than consume it remotely. The fix is to
vendor `aidankinzett/claude-git-pr-skill` (skill `github-pr-review`, MIT, upstream v1.1.1 @
`3660dca92424b91f1eb716b5815b476c3913450e`) into the local `agent-harness` plugin, adapt it to repo
conventions, add a section that closes the long-body bug, and validate it end-to-end against
mem_tui PR #2.

## Objective

A working, locally-editable `agent-harness:github-pr-review` skill at
`plugins/boss-dev/agent-harness/skills/github-pr-review/` that (a) faithfully reproduces the upstream
workflow, (b) declares the `gh` tools it actually uses, (c) records MIT provenance/attribution, and
(d) documents safe long-body passing so the literal-`@file` failure cannot recur — validated by
posting a clean review to mem_tui PR #2.

## Problem Statement

The external skill is referenced remotely (git-subdir, pinned) and cannot be edited in place. Its
guidance is silent on passing long review bodies, which let the agent post literal `@path` strings
to a public PR. The user needs an editable copy that fixes this and that they can experiment with.

## Solution Approach

Vendor the upstream skill as a normal agent-harness skill (auto-discovered via the plugin's
`"skills": "./skills/"` pointer — **no plugin.json/marketplace.json plugin entry needed for the
skill itself**). Adapt frontmatter to repo conventions, append a "Passing long review bodies safely"
section as the bug fix, and add an attribution file. Keep the existing external marketplace entry
untouched (run both side-by-side). Validate against the real PR.

Decisions confirmed with the user:
- **Name:** `github-pr-review` (invoked `/agent-harness:github-pr-review`; no collision with the
  external `github-pr-review@boss-skills` plugin since this is a skill inside agent-harness).
- **External entry:** keep both for now — do **not** touch `.claude-plugin/marketplace.json` lines
  104–127 or `docs/plugins/github-pr-review.md`.
- **Scope:** faithful copy **+** fix the long-body bug.

## Relevant Files

- `/private/tmp/.../scratchpad/claude-git-pr-skill/github-pr-review/skills/github-pr-review/SKILL.md`
  — upstream source already cloned; copy/adapt its body.
- `plugins/boss-dev/agent-harness/skills/add-review-comment/SKILL.md` — local convention reference
  for `allowed-tools` (`Bash(gh api:*)`, `Bash(gh pr view:*)`, `Skill`) and `references/` layout.
- `plugins/boss-dev/agent-harness/skills/pr-review/SKILL.md` — existing overlapping skill (drafts a
  schema-validated review locally, does **not** post); reference for tone/structure, not to be merged.
- `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json` — `version: 0.12.1`, `"skills":
  "./skills/"`; bump to `0.13.0` (adding a skill = minor feature).
- `.claude-plugin/marketplace.json` — agent-harness entry (lines 38–57) `version` must stay in sync
  with plugin.json; the external `github-pr-review` entry (lines 104–127) stays as-is.
- `CLAUDE.md` — "Critical Parser Bug (#12781)": no `!`backtick / `@file` patterns in SKILL.md fenced
  blocks; use `$ command` notation. (Upstream SKILL.md is already clean — verify after copy.)

### New Files

- `plugins/boss-dev/agent-harness/skills/github-pr-review/SKILL.md` — the vendored + adapted skill.
- `plugins/boss-dev/agent-harness/skills/github-pr-review/references/attribution.md` — upstream repo
  URL, pinned tag/SHA, MIT license text, author (Aidan Kinzett).
- (optional) `plugins/boss-dev/agent-harness/skills/github-pr-review/references/safe-body-passing.md`
  — long-form examples if the SKILL.md section gets large; otherwise keep inline.

## Step by Step Tasks

IMPORTANT: Execute every step in order, top to bottom.

### 1. Persist this spec
- Copy this plan verbatim to `specs/hotfix-gh-pr-review.md`.

### 2. Scaffold the skill directory
- `mkdir -p plugins/boss-dev/agent-harness/skills/github-pr-review/references`.

### 3. Vendor and adapt SKILL.md
- Copy the upstream SKILL.md body into the new skill dir.
- Rewrite frontmatter to repo conventions:
  - `name: github-pr-review`
  - keep upstream `description` (already concrete + trigger-shaped).
  - `allowed-tools:` expand beyond upstream's `AskUserQuestion` to what the skill actually runs:
    `AskUserQuestion`, `Bash(gh api:*)`, `Bash(gh pr view:*)`, `Bash(gh --version:*)`,
    `Bash(gh auth status:*)`.
- Add a short provenance line near the top of the body (vendored from upstream, tag/SHA, MIT, link
  to `references/attribution.md`).
- Scan the body for `#12781` patterns (` !`backtick ` and `@file` inside fenced blocks). Upstream is
  clean; if any appear, convert to `$ command` notation.

### 4. Add the bug-fix section (the reason for forking)
- Append a section **"Passing long or multi-line review bodies safely"** that makes the failure mode
  impossible to repeat:
  - **Preferred:** build a JSON payload and pipe it in — `gh api .../reviews --input payload.json`
    (or `--input -` from a heredoc). No shell-quoting of multi-line bodies, no `@` ambiguity.
  - **Field form:** only `-F 'comments[][body]=@/path/body.md'` reads a file; `gh pr review` uses
    `--body-file <path>`.
  - **Explicit warning:** NEVER pass `@/path` to `-f/--raw-field` or to `gh pr review --body` — it is
    posted **literally** (this is exactly what broke mem_tui PR #2).
- Add one line to the existing "Common Mistakes" / "Red Flags" tables referencing the literal-`@file`
  trap.

### 5. Add attribution
- Write `references/attribution.md`: upstream URL, `ref: v1.1.1`, `sha: 3660dca…`, MIT license text,
  author Aidan Kinzett. (Upstream ships no LICENSE file but README states MIT.)

### 6. Version bump
- Bump agent-harness `version` 0.12.1 → 0.13.0 in **both** `plugin.json` and the marketplace.json
  agent-harness entry (use the repo's `version-bump-reviewer` skill to confirm tier).

### 7. Validate structure & lint
- Run the structure/doc checks and markdown lint (see Validation Commands).

### 8. End-to-end validation against mem_tui PR #2
- Invoke `/agent-harness:github-pr-review` on `bossjones/mem_tui#2`; draft → approve → post using the
  new safe-body path.
- Confirm the posted body is rendered markdown, not a literal `@/…` string.
- (Optional) clean up the two broken bot comments/review already on PR #2.

## Testing Strategy

- **Structure:** the skill is markdown-only (no scripts), so no pytest. Validation is structural
  (`verify-structure`), lint (`rumdl`/`make markdown-lint`), and the live PR run.
- **Behavioral (the fix):** after posting to PR #2, assert no comment body matches `^@/` —
  `gh api repos/bossjones/mem_tui/pulls/2/comments --jq '.[].body'` must show real text.
- **Trigger sanity:** confirm `/agent-harness:github-pr-review` resolves and loads (distinct from the
  external `/github-pr-review:github-pr-review`).
- **Optional:** `make eval-skill` / `/skill-evals` to score the new skill (report only).

## Acceptance Criteria

- `plugins/boss-dev/agent-harness/skills/github-pr-review/SKILL.md` exists, parses, and lists `name`,
  `description`, and an `allowed-tools` set covering `gh api`/`gh pr view`/`AskUserQuestion`.
- SKILL.md contains a "Passing long review bodies safely" section explicitly forbidding `@path` to
  `-f`/`--body` and showing the `--input` / `--body-file` / `-F @file` alternatives.
- `references/attribution.md` records upstream URL, tag, SHA, and MIT/author.
- agent-harness version is 0.13.0 in both plugin.json and marketplace.json (in sync).
- No `#12781` parser-bug patterns in the SKILL.md.
- The external `github-pr-review` marketplace entry and its docs are unchanged.
- A review posted to mem_tui PR #2 shows rendered markdown bodies (no literal `@/…`).

## Validation Commands

- `ls plugins/boss-dev/agent-harness/skills/github-pr-review/` — skill scaffolded.
- `uv run scripts/verify-structure.py` (or `make` equivalent) — structure + plugin doc/version drift.
- `make markdown-lint` — lints the new SKILL.md (`rumdl`).
- `make lint` — repo lint gate (zero warnings required).
- `grep -nE '(@/|!`)' plugins/boss-dev/agent-harness/skills/github-pr-review/SKILL.md` — expect no
  parser-bug patterns (matches only inside the safe-body warning prose, which is allowed).
- `gh pr view 2 --repo bossjones/mem_tui --json url,state` — PR reachable.
- `gh api repos/bossjones/mem_tui/pulls/2/comments --jq '.[].body'` — after the run, no body starts
  with `@/`.

## Notes

- No new libraries; skill is markdown-only. Requires `gh` installed + authenticated (already true in
  this session).
- The repo already has `pr-review`, `add-review-comment`, `fetch-diff`, `fetch-unresolved-comments`
  under agent-harness. The vendored skill intentionally stays standalone (faithful fork) rather than
  composing with them — broader integration was offered and declined for now.
- Keeping both the external and vendored copies means two things answer to "review this PR." That is
  acceptable per the user's choice; a later cleanup can retire the external git-subdir entry.
- Commit message (conventional): `feat(agent-harness): vendor github-pr-review skill with safe-body
  fix` and end with the required `Co-Authored-By` trailer. Branch off `main` (currently on
  `feature-review-test`) per repo rules before committing.
