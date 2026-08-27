# Plan: Remove vendored mattpocock skills and install upstream at user/global scope

> Filename note: the path `specs/remove-vendored-mattpocok-skills.md` was requested verbatim
> (upstream is spelled `mattpocock`). Kept as-asked so the requested path resolves.

## Task Description

`boss-skills` carries 18 skill directories under `.claude/skills/` that were copied in from
[`mattpocock/skills`](https://github.com/mattpocock/skills) via `npx skills add` (the
[skills.sh](https://skills.sh/mattpocock/skills) route), plus the `skills-lock.json` manifest that
route writes. They landed in a single commit (`c9b0237 feat(skills): add 18 Matt Pocock skills and
reference docs`) and have not been meaningfully edited since. Upstream has moved on: skills were
renamed, promoted between buckets, or deleted outright, so the vendored copies are stale forks
nobody is maintaining.

This plan removes those copies from the repository and replaces them with a single
**user/global** installation of the upstream skills, for **both** Claude Code and GitHub Copilot
CLI, so one managed source serves every project on the machine instead of a per-repo snapshot.

Background research for this plan:
[gist 50805316cde7e86183c7111f01b095ae](https://gist.github.com/bossjones/50805316cde7e86183c7111f01b095ae)
plus direct inspection of the clone at `/Users/bossjones/dev/mattpocock/skills`.

## Objective

When this plan is complete:

1. No `mattpocock/skills`-derived content remains under `.claude/skills/`, and `skills-lock.json`
   is gone. Only repo-owned skills (real directories) and plugin symlinks remain.
2. Documentation that described the vendored copies is removed or rewritten to point upstream.
3. All upstream skills are installed once at user scope, via the `skills` CLI
   (`vercel-labs/skills`), for **both** Claude Code (`~/.claude/skills/`) and Copilot CLI
   (`~/.copilot/skills/`), with a single documented command that is safe to re-run.
4. Re-running that command updates or overrides an existing install rather than duplicating it, and
   `npx skills update -g -y` refreshes to newer upstream content.
5. `make lint`, `make test`, `make verify-structure`, `make markdown-lint`, and `make link-check`
   all pass, and neither harness lists any mattpocock skill twice.

## Problem Statement

Three distinct problems, all caused by the same vendoring decision:

**1. The copies are stale in ways that are invisible from inside the repo.** `skills-lock.json`
pins paths that no longer exist upstream. Verified against the current clone:

| Vendored name | Locked `skillPath` | Upstream today |
|---|---|---|
| `diagnose` | `skills/engineering/diagnose/SKILL.md` | renamed → `diagnosing-bugs` |
| `to-issues` | `skills/engineering/to-issues/SKILL.md` | renamed → `to-tickets` |
| `to-prd` | `skills/engineering/to-prd/SKILL.md` | renamed → `to-spec` |
| `review` | `skills/in-progress/review/SKILL.md` | promoted + renamed → `code-review` |
| `qa` | `skills/deprecated/qa/SKILL.md` | deleted |
| `design-an-interface` | `skills/deprecated/design-an-interface/SKILL.md` | deleted |
| `caveman` | `skills/productivity/caveman/SKILL.md` | deleted |
| `edit-article` | `skills/personal/edit-article/SKILL.md` | deleted (bucket gone) |
| `write-a-skill` | `skills/productivity/write-a-skill/SKILL.md` | deleted |
| `zoom-out` | `skills/engineering/zoom-out/SKILL.md` | deleted |
| `grill-me`, `grill-with-docs`, `handoff`, `improve-codebase-architecture`, `prototype`, `setup-matt-pocock-skills`, `teach`, `triage` | unchanged paths | still current, but stale content |

`npx skills update` cannot repair the first ten rows — the source paths are gone.

**2. Per-repo vendoring is the wrong scope for consumed (not forked) skills.** These are read-only
dependencies. Copying them into one repo means every other project on the machine goes without,
and the copies drift silently.

**3. Installing upstream on top of the copies produces duplicates.** Upstream's own README is
explicit: *"Pick one: installing both leaves you with every skill twice."* Eight vendored names
(`grill-me`, `grill-with-docs`, `handoff`, `improve-codebase-architecture`, `prototype`,
`setup-matt-pocock-skills`, `teach`, `triage`) are still shipped upstream under the same names, so
removal must happen **before** installation, not after.

## Solution Approach

Split the work along the "who owns this file" line:

- **Consumed, unmodified upstream content → delete from the repo, subscribe globally.** All 18
  directories plus `skills-lock.json`.
- **Repo-owned content stays put.** `doc-generator/`, `skill-evals/`, `version-bump-reviewer/` are
  this repo's own skills and are untouched; the 27 symlinks into `plugins/*/skills/*` are untouched.
- **Configuration produced by `setup-matt-pocock-skills` stays put.** The `## Agent skills` block in
  `CLAUDE.md` and `docs/agents/{issue-tracker,triage-labels,domain}.md` are repo configuration read
  by the upstream skills at runtime. They are not install artifacts, and the globally-installed
  skills will still read them. Deleting them would break `triage` / `to-tickets` / `to-spec`.
- **Global install: one command, both harnesses.** The `skills` CLI ([vercel-labs/skills](https://github.com/vercel-labs/skills),
  the tool behind `skills.sh`) installs to multiple agents in one invocation, so
  `--agent claude-code --agent github-copilot --global` covers both. Every flag is spelled out so
  nothing is written outside those two directories.

### Why the `skills` CLI rather than the Claude Code plugin

Both routes deliver the same upstream content. The chosen route is the `skills` CLI, and the
trade-off is worth stating plainly because it is not free:

| | `skills` CLI (chosen) | `claude plugin install` |
|---|---|---|
| Harness coverage | Both, one command | Claude Code only |
| Scope | User (`-g`) | User |
| Names | **Bare** (`code-review`) | **Namespaced** (`mattpocock-skills:code-review`) |
| Skills installed | 37 (25 promoted + 12 non-promoted) | 25 promoted |
| Updates | `npx skills update -g -y` | Automatic on upstream release |
| Files | Symlinks to one canonical copy | Read-only plugin cache |

The CLI wins on the thing that actually matters here — one route covering both harnesses, with
everything upstream ships. It loses on namespacing, and that loss is real rather than cosmetic:
personal skills have no plugin to be namespaced under, so `code-review` lands as a bare global name
in both harnesses. Step 10 resolves that one collision explicitly rather than leaving it implicit.

### What is verified vs. what is not

Verified directly during research (do not re-derive):

- Copilot CLI 1.0.80 discovers skills from `.github/skills/`, `.agents/skills/`, `.claude/skills/`
  (project); `~/.copilot/skills/`, `~/.agents/skills/` (personal); installed plugins; and custom
  directories added with `copilot skill add <dir>` (`copilot skill --help`).
- Copilot CLI parses `.claude-plugin/plugin.json`: `copilot --plugin-dir
  /Users/bossjones/dev/mattpocock/skills plugin list` reports `mattpocock-skills` under
  *External Plugins (via --plugin-dir)*.
- Upstream bucket counts exactly match `plugin.json`'s promoted set: `skills/engineering/` = 18
  `SKILL.md`, `skills/productivity/` = 7, total 25. `skills/in-progress/` = 8 and `skills/misc/` = 4
  are **not** promoted; `skills/deprecated/` = 0.
- `scripts/eval-skills.py` discovers skills under `plugins/` only (`discover_skills()`), so
  `make eval-ci` is unaffected by anything under `.claude/skills/`.
- `scripts/verify-structure.py` contains no `.claude/skills` references.
- **Both harnesses namespace *plugin* skills as `plugin-name:skill-name`; neither namespaces
  *personal* or *project* skills.** Claude Code: a live session's skill listing carries the built-in
  `code-review` and the plugin's `code-review:code-review` as separate entries, plus
  `superpowers:brainstorming`, `agent-harness:boss-cmux`. Copilot CLI: its slash-command picker
  offers `/superpowers:brainstorming`, `/superpowers:executing-plans`, and so on — `superpowers` is
  installed there as a plugin (`~/.copilot/config.json` `installedPlugins`), which is where the
  prefix comes from.
- **`copilot skill list` is not evidence about naming.** It renders every entry bare regardless of
  source — plugin skills included — and only groups them under *Project* / *Personal* / *Plugin* /
  *Builtin* headings. An earlier reading of that output wrongly concluded Copilot does not namespace;
  the slash-command picker is the authority, and it does.
- **The `skills` CLI installs personal skills, which are therefore bare in both harnesses.** Nothing
  namespaces them, because there is no plugin to namespace them under. Corroborated on this machine:
  the skills.sh-installed copies in this repo's `.claude/skills/` appear bare in a Claude session
  (`grill-me`, `triage`, `diagnose`), and the obsidian-wiki symlinks in `~/.copilot/skills/` appear
  bare under Copilot's *Personal skills*. This is the central trade-off of the chosen route, and
  Step 10 handles its one sharp consequence.
- **The `skills` CLI (`vercel-labs/skills`) discovers 37 skills in `mattpocock/skills`, not 25.**
  `npx skills@latest add mattpocock/skills --list` groups them as *Mattpocock Skills* (25, from
  `.claude-plugin/plugin.json`) and *General* (12, from the catalog walk over `in-progress/` and
  `misc/`). Manifest discovery **adds to** the catalog walk rather than restricting it.
- **`skills` CLI flags** (`npx skills@latest --help`): `-g/--global` for user scope;
  `-a/--agent` repeatable, **not** comma-separated; `-s/--skill '*'` for all; `-y/--yes`;
  `--copy` to opt out of the default symlinking; `-l/--list` to preview. `--all` is shorthand for
  `--skill '*' --agent '*' -y` and must be avoided — `--agent '*'` targets all 78 supported agents.
  Agent identifiers and their global paths: `claude-code` → `~/.claude/skills/`, `github-copilot` →
  `~/.copilot/skills/`.
- `trash` is macOS `/usr/bin/trash`. It recurses into directories with no `-r` flag (passing one is
  an error), moves to `~/.Trash`, and exits 0 — but it does **not** update the git index, so staging
  is a separate step.
- The only local drift in the 18 vendored skills is cosmetic: commit `98263aa` added blank lines
  after `<vertical-slice-rules>` / `<issue-template>` / `<user-story-example>` in `to-issues` and
  `to-prd` to satisfy `rumdl`. Nothing else has been edited since `c9b0237`.

**Not verified, and deliberately no longer on the critical path:** whether an *installed* Copilot
plugin surfaces skills declared through `plugin.json`'s explicit `skills` array of bucketed paths.
`--plugin-dir` could not answer it — a control run with this repo's own
`plugins/boss-dev/agent-harness` (conventional layout) showed `--plugin-dir` does not feed
`copilot skill list` at all — and upstream ADR 0002 records that *Codex* cannot express this manifest
shape. Choosing the `skills` CLI route sidesteps the question entirely: the CLI does its own manifest
and catalog discovery and writes plain skill directories, so Copilot's plugin-manifest handling never
comes into play. Left recorded here only so a future reader does not re-run the same dead end.

## Relevant Files

Use these files to complete the task:

**Deleted outright**

- `.claude/skills/{caveman,design-an-interface,diagnose,edit-article,grill-me,grill-with-docs,handoff,improve-codebase-architecture,prototype,qa,review,setup-matt-pocock-skills,teach,to-issues,to-prd,triage,write-a-skill,zoom-out}/` — the 18 vendored skills, all git-tracked, all introduced by `c9b0237`.
- `skills-lock.json` — the skills.sh manifest. Every one of its 18 entries is `mattpocock/skills`; nothing else in the repo uses skills.sh, so the file has no residual purpose.
- `docs/matt-pocock-skills.md` (265 lines) — a hand-written catalogue of the vendored skills. Its content is stale in exactly the ways the drift table above lists, and it opens with the skills.sh install command this plan is removing.

**Edited**

- `docs/README.md:34` — the "Background & reference" table row linking to `matt-pocock-skills.md`. Must go or `make link-check` fails on a dangling relative link.

**Explicitly untouched (verify, do not change)**

- `.claude/skills/{doc-generator,skill-evals,version-bump-reviewer}/` — repo-owned skills.
- The 27 `.claude/skills/*` symlinks into `plugins/*/skills/*`.
- `CLAUDE.md` `## Agent skills` section and `docs/agents/{issue-tracker,triage-labels,domain}.md` — repo configuration consumed by the now-global skills.
- `.rumdl.toml:27`, `.pre-commit-config.yaml:40,57,66`, `Makefile:193-200` — all use generic `.claude/skills/*/SKILL.md` globs. Fewer files match after removal; no edit needed.

**Read for context**

- [`vercel-labs/skills`](https://github.com/vercel-labs/skills) — the `skills` CLI behind `skills.sh`, and the installer this plan uses. Its README is the authority on flags, the supported-agent table (`claude-code` → `~/.claude/skills/`, `github-copilot` → `~/.copilot/skills/`), Skill Discovery, and Plugin Manifest Discovery.
- `/Users/bossjones/dev/mattpocock/skills/.claude-plugin/plugin.json` — the authoritative 25-skill promoted list, and the manifest the `skills` CLI reads on top of its catalog walk.
- `/Users/bossjones/dev/mattpocock/skills/.agents/install-block.md` — upstream's canonical install wording.
- `/Users/bossjones/dev/mattpocock/skills/scripts/link-skills.sh` — read to understand why it is **not** used here (see Notes).

### New Files

None required. Optional, at the user's discretion (Step 11): a short
`docs/external-skills.md` recording that mattpocock skills are now a global install rather than a
vendored dependency, so a future reader does not re-vendor them.

## Implementation Phases

### Phase 1: Foundation — audit and preserve

Confirm the delete list against `skills-lock.json` and git history, confirm no code, test, doc, or
lint config outside `.claude/skills/` depends on the 18 names, and capture the recovery commit so
anything deleted can be restored.

### Phase 2: Core implementation — removal and global install

Delete the 18 directories, `skills-lock.json`, and the stale doc; fix the docs index. Then install
upstream once at user scope with the `skills` CLI, targeting Claude Code and Copilot CLI in a single
invocation, and verify each harness sees exactly one copy of each skill.

### Phase 3: Integration & polish — collisions, validation, commit

Reconcile name collisions the install introduces (notably `code-review`), run the full local gate,
and commit as a conventional-commit chore with the version-bump review applied.

## Step by Step Tasks

IMPORTANT: Execute every step in order, top to bottom.

### 1. Capture the recovery point and confirm the delete list

- Record the recovery commit so any deleted skill can be restored later:

  ```bash
  git log -1 --format='%H %s' c9b0237
  ```

- Confirm the 18 vendored names match `skills-lock.json` exactly, with no extras and no omissions:

  ```bash
  python3 -c "import json;print('\n'.join(sorted(json.load(open('skills-lock.json'))['skills'])))" > /tmp/locked.txt && cat /tmp/locked.txt
  ```

- Confirm every locked name exists as a real directory (not a symlink) under `.claude/skills/`, and
  that the three repo-owned skills are **not** in that list:

  ```bash
  while read -r n; do [ -d ".claude/skills/$n" ] && [ ! -L ".claude/skills/$n" ] && echo "OK $n" || echo "MISSING $n"; done < /tmp/locked.txt
  ```

- Confirm `doc-generator`, `skill-evals`, and `version-bump-reviewer` are absent from
  `/tmp/locked.txt`. If any appears, stop — the lockfile is not what this plan assumes.

### 2. Confirm nothing outside the skills themselves depends on the 18 names

- Search the repo for references, excluding the directories being deleted and the lockfile:

  ```bash
  grep -rnE '\b(caveman|design-an-interface|diagnose|edit-article|grill-me|grill-with-docs|handoff|improve-codebase-architecture|prototype|qa|review|setup-matt-pocock-skills|teach|to-issues|to-prd|triage|write-a-skill|zoom-out)\b' --include="*.md" --include="*.py" --include="*.json" --include="*.toml" --include="*.yaml" --include="*.yml" --include="Makefile" . | grep -v '^\./\.claude/skills/' | grep -v '^\./skills-lock\.json'
  ```

- Expect hits only in `docs/matt-pocock-skills.md`, `docs/README.md:34`, and
  `docs/agents/triage-labels.md` (which mentions `mattpocock/skills` as a label-vocabulary source —
  legitimate, keep it). Anything else is a new dependency this plan did not anticipate: resolve it
  before continuing.

### 3. The six upstream-deleted skills: delete all of them

**Decided.** Six vendored skills no longer exist upstream under any name: `caveman`,
`design-an-interface`, `edit-article`, `qa`, `write-a-skill`, `zoom-out`. All six are deleted along
with the rest — none is re-homed into `plugins/boss-experimental/`. They are unmaintained upstream,
unreferenced anywhere in this repo (confirmed in Step 2), and `c9b0237` remains the recovery point
if that judgement ever needs revisiting.

This means Steps 4 and 5 operate on the full 18-name list with no exclusions, and no `plugins/`
file changes — which is what keeps Step 12's expected outcome at "no version bump".

### 4. Trash the vendored skills and the lockfile

Deletion goes through macOS `trash` (`/usr/bin/trash`), not `rm` or `git rm`, so everything lands
recoverably in `~/.Trash` on top of the `c9b0237` git recovery path.

- Move all 18 directories and the lockfile to the Trash. `trash` recurses into directories on its
  own — there is no `-r` flag, and passing one is an error:

  ```bash
  trash -v skills-lock.json $(while read -r n; do [ -d ".claude/skills/$n" ] && echo ".claude/skills/$n"; done < /tmp/locked.txt)
  ```

- **`trash` does not touch the git index** — this is the one real difference from `git rm`. Stage
  the deletions explicitly or they will not be part of the commit:

  ```bash
  git add -A .claude/skills skills-lock.json
  ```

- Confirm git recorded 18 directory deletions plus the lockfile, and nothing else:

  ```bash
  git diff --cached --name-status | grep -c '^D' && git diff --cached --name-status | grep -v '^D' || echo "only deletions staged"
  ```

- Verify what remains under `.claude/skills/` is exactly the three repo-owned directories — no other
  real directories:

  ```bash
  find .claude/skills -maxdepth 1 -mindepth 1 -type d
  ```

  Expected output: `doc-generator`, `skill-evals`, `version-bump-reviewer`.

### 5. Remove the stale documentation page

- Trash the catalogue, which documents the pre-rename names and the skills.sh install route, then
  stage the deletion:

  ```bash
  trash -v docs/matt-pocock-skills.md && git add -A docs/matt-pocock-skills.md
  ```

- Remove its row from the "Background & reference" table in `docs/README.md` (line 34, between the
  `LEARN.md` and `REFERENCES.md` rows). Leave the surrounding table intact.

### 6. Confirm the repo-side removal is clean

- Run the fast local gates that touch markdown and structure:

  ```bash
  make markdown-lint && make verify-structure && make link-check
  ```

- `link-check` is the one that catches a forgotten `docs/README.md` edit. Fix and re-run until green.

### 7. Install upstream globally for both harnesses with the `skills` CLI

One command covers both harnesses. Every flag is explicit so nothing lands anywhere unintended —
`--all` is deliberately **not** used, because it expands to `--agent '*'` and would write into all
78 supported agents' directories.

- Run it from **outside** any git repository. The CLI auto-detects project scope from the cwd, and
  `skills add` at project scope writes a `skills-lock.json` into that project — exactly the file
  Step 4 deleted:

  ```bash
  cd ~ && npx skills@latest add mattpocock/skills --skill '*' --agent claude-code --agent github-copilot --global --yes
  ```

  Flag by flag: `--skill '*'` takes every discovered skill; `--agent` is repeatable (not
  comma-separated) and names only the two wanted harnesses — `claude-code` → `~/.claude/skills/`,
  `github-copilot` → `~/.copilot/skills/`; `--global` selects user scope over project scope;
  `--yes` skips the interactive prompts. Symlinking is the default install method (each agent
  directory points at one canonical copy), which is what makes `skills update` a single operation —
  do **not** pass `--copy`.

- **This install is idempotent by design.** Re-running the same command re-installs over whatever is
  already there, so it doubles as the "override if it exists" path. For refreshing to newer upstream
  content later, use the update command rather than re-adding:

  ```bash
  cd ~ && npx skills@latest update --global --yes
  ```

  `update -y` auto-detects scope from cwd (project if in a project directory, else global), so the
  `cd ~` matters here too; `--global` makes it explicit regardless.

- Confirm what landed in each agent directory:

  ```bash
  npx skills@latest ls --global --agent claude-code --agent github-copilot
  ```

  ```bash
  ls ~/.claude/skills | wc -l && ls ~/.copilot/skills | wc -l
  ```

  Both counts should have grown by 37 relative to their pre-install values (capture those first).

- Confirm no `skills-lock.json` was recreated in this repo:

  ```bash
  test ! -e skills-lock.json && echo "no project lockfile recreated"
  ```

- Verify no duplication from inside this repo — none of the 37 names may resolve to a project-level
  copy, which is what Step 4 guaranteed:

  ```bash
  for n in ask-matt code-review codebase-design diagnosing-bugs domain-modeling grill-with-docs implement improve-codebase-architecture prototype research resolving-merge-conflicts setup-matt-pocock-skills tdd to-spec to-tickets triage wayfinder wizard grill-me grilling handoff teach to-questionnaire wait-what writing-for-agents; do [ -e ".claude/skills/$n" ] && echo "DUPLICATE $n"; done; echo "duplicate check done"
  ```

  Expect no `DUPLICATE` lines.

### 8. Decide whether to keep the 12 non-promoted skills

`--skill '*'` installs **37 skills, not 25.** Verified with `npx skills@latest add mattpocock/skills
--list`, which reports them in two groups:

- **"Mattpocock Skills" (25)** — sourced from `.claude-plugin/plugin.json`'s `skills` array. This is
  the promoted set: exactly what `claude plugin install mattpocock-skills` would give.
- **"General" (12)** — found by the CLI's own catalog walk of `skills/<category>/<name>/SKILL.md`,
  which sweeps up the non-promoted buckets. From `in-progress/`: `claude-handoff`, `implement-spec`,
  `loop-me`, `retro`, `setup-ts-deep-modules`, `writing-beats`, `writing-fragments`, `writing-shape`.
  From `misc/`: `git-guardrails-claude-code`, `migrate-to-shoehorn`, `scaffold-exercises`,
  `setup-pre-commit`.

The `--list` output is the authority here, not `plugin.json` — the CLI's Plugin Manifest Discovery
adds manifest-declared skills to what the catalog walk finds; it does not restrict the set to them.

- **Default: keep all 37.** They install cleanly and several (`git-guardrails-claude-code`,
  `setup-pre-commit`) are useful standalone. Upstream simply hasn't promoted them.
- To take only the promoted 25 instead, there is no exclusion flag — enumerate them with repeated
  `-s` flags, or install all 37 and remove the 12 afterwards:

  ```bash
  npx skills@latest remove --global --agent '*' claude-handoff implement-spec loop-me retro setup-ts-deep-modules writing-beats writing-fragments writing-shape git-guardrails-claude-code migrate-to-shoehorn scaffold-exercises setup-pre-commit
  ```

- Record the choice in the commit body.

### 9. Sanity-check that both harnesses actually see the skills

- Claude Code — confirm the personal skill directory is populated and readable:

  ```bash
  ls ~/.claude/skills | grep -E '^(ask-matt|grilling|wayfinder|to-spec|to-tickets|wizard)$' | wc -l
  ```

  Expect `6`.

- Copilot CLI — confirm they register as *Personal* skills:

  ```bash
  copilot skill list 2>&1 | sed -n '/^Personal skills:/,/^Plugin skills:/p' | grep -cE '^\s+(ask-matt|grilling|wayfinder|to-spec|to-tickets|wizard) '
  ```

  Expect `6`. If the count is `0`, check whether the CLI wrote symlinks Copilot cannot follow, and
  re-run Step 7 with `--copy` as a fallback.

### 10. Reconcile the name collisions the install introduces

The `skills` CLI route installs **personal** skills, which are bare in both harnesses (see *What is
verified*). Namespacing is a property of the *plugin* system, so choosing this route means accepting
bare global names and handling collisions by hand. There is one sharp collision and several soft
ones.

**Sharp: `code-review`.** After Step 7, `~/.claude/skills/code-review/` and
`~/.copilot/skills/code-review/` both exist, while both harnesses already carry a `code-review` skill
from the `anthropics/claude-plugins-official` plugin, and Claude Code additionally ships a built-in
`/code-review`. The plugin copies stay addressable as `code-review:code-review`; the newly installed
personal one takes the bare name.

- See what each harness ended up with:

  ```bash
  ls -d ~/.claude/skills/code-review ~/.copilot/skills/code-review 2>&1; copilot skill list 2>&1 | grep -nE '^\s+code-review '
  ```

- **Recommended:** drop just this one from the global install and keep reaching the official plugin's
  version by its namespaced name. This is the only exclusion worth making, and it is one command:

  ```bash
  npx skills@latest remove --global --agent '*' code-review
  ```

- If instead upstream's version is the one wanted, keep it and remember that the bare `code-review`
  now means upstream's while `code-review:code-review` means the official plugin's. Record whichever
  way it went in the commit body.

**Soft: generic names now global.** `implement`, `research`, `handoff`, `triage`, `prototype`,
`teach`, `tdd`, and `retro` are ordinary words occupying bare names in every project on the machine,
not just this repo. Nothing collides today — a scan of `~/.claude/skills/` and `~/.copilot/skills/`
before Step 7 found no overlap with any of the 37 — but a future skill from another source claiming
one of these names has no namespace to hide behind. Capture the pre-install listing (Step 7 already
requires it) so a later collision is diagnosable.

**Description-trigger overlap, unchanged by any of this.** Namespacing only ever fixed *addressing*,
never *autonomous selection*. Upstream's `code-review`, `tdd`, `grilling`, and `research` are all
model-invoked (no `disable-model-invocation`), so they compete by description with the official
`code-review` plugin, `superpowers:brainstorming`, and `superpowers:test-driven-development`
regardless of how they are named. No action; reach for the user-invoked wrapper (`/grill-me`) when
determinism matters.

**Unrelated to the collision:** prior guidance on this repo was that `/review` findings should carry
low/medium/high severity tags and post as inline `gh` PR comments. The vendored `review` never
encoded that (it is byte-identical to what `c9b0237` added), and upstream `code-review` does not
either. This repo's own `agent-harness:github-pr-review`, `pr-review`, and `add-review-comment`
skills already do inline `gh` comments — keep using those for that workflow rather than expecting it
from upstream.

### 11. Optionally record the decision

- If a future reader might re-vendor these, add a short `docs/external-skills.md` stating that
  mattpocock skills are consumed as a user-scope install (Claude Code plugin + Copilot personal
  skills) and must not be copied into `.claude/skills/`, and add a row for it to `docs/README.md`.
- Skip if the commit message is judged sufficient.

### 12. Validate everything and commit

- Run the full local gate:

  ```bash
  make lint && make test && make verify-structure && make markdown-lint && make link-check
  ```

- Run the repo's version-bump review over the uncommitted changes and apply whatever it decides.
  Expectation: **no bump**. None of the 18 removed skills carries `metadata.version` (they are
  vendored copies, not repo-internal skills), and no file under `plugins/` changed — Step 3 deletes
  all six upstream-deleted skills rather than re-homing any, so nothing under `plugins/` is touched.
- Commit as a conventional-commit chore, naming the six permanently-deleted skills and the recovery
  commit in the body so the loss is discoverable from `git log`.

## Testing Strategy

There is no new code, so testing is regression-focused: prove the removal broke nothing and the
installs took effect.

**Repo regressions (Step 6 and Step 12)**

- `make markdown-lint` — the `rumdl` globs at `.rumdl.toml:27` and `.pre-commit-config.yaml:40,57,66`
  match `.claude/skills/*/SKILL.md`. After removal they match 3 files instead of 21; the run must
  still pass.
- `make link-check` — the highest-signal check. `docs/README.md:34` links to the deleted
  `docs/matt-pocock-skills.md`; a forgotten edit fails here and nowhere else.
- `make verify-structure` — `scripts/verify-structure.py` has no `.claude/skills` references, so this
  is a guard against unrelated collateral, not a targeted assertion.
- `make test` — `tests/test_version_bump_reviewer_hook.py` references `.claude/skills/doc-generator/`
  and `.claude/skills/version-bump-reviewer/` (both kept) and a synthetic `.claude/skills/SKILL.md`.
  None of the removed paths appear in any test. `tests/test_snyk_agent_scan.py` uses fixtures, not
  the live tree.
- `make eval-ci` is **not** affected: `discover_skills()` in `scripts/eval-skills.py` walks
  `plugins/` only.

**Edge cases to check explicitly**

- *Partial deletion.* If `trash` skips a directory, or the follow-up `git add -A` is forgotten so a
  deletion never reaches the index, the duplicate check in Step 7 catches the first case and
  `git status` the second. Run the Step 7 duplicate check after Step 4 as well as after Step 7.
- *`trash` leaving the index untouched.* This is the one behavioural difference from `git rm` and the
  likeliest mistake: the files vanish from disk, the working tree looks correct, and the commit
  contains nothing. Step 4's `git diff --cached --name-status` check exists specifically for this.
- *Symlink damage.* A path list built from `skills-lock.json` cannot touch the 27 plugin symlinks,
  since no locked name matches a symlinked name. `trash` would also follow rather than delete a
  symlink target if one were passed. Confirm anyway with
  `find .claude/skills -maxdepth 1 -type l | wc -l` → expect 27 before and after.
- *Copilot silently installing the plugin but loading zero skills.* This is the whole point of the
  Step 8 grep. A bare `copilot plugin list` showing `mattpocock-skills` is **not** sufficient
  evidence — `--plugin-dir` demonstrated during research that a plugin can be recognized without its
  skills being loaded.
- *Global install duplicating what is already there.* Both harnesses must be checked from inside a
  project that has no local copies. Run the Step 7 duplicate check from this repo after removal, and
  once from an unrelated directory.
- *Install run from inside the repo.* `skills add` infers project scope from the cwd and writes a
  `skills-lock.json` there. The `cd ~` in Step 7 prevents it; the `test ! -e skills-lock.json` check
  after Step 7 catches it if the `cd` is dropped.
- *Idempotency.* Re-run the Step 7 command a second time and confirm `ls ~/.claude/skills | wc -l`
  is unchanged. A growing count means the install is duplicating rather than overriding.
- *Symlinks a harness cannot follow.* The CLI symlinks by default. If Step 9's Copilot check returns
  `0` while `~/.copilot/skills/` visibly contains the entries, re-run Step 7 with `--copy`.
- *Non-promoted leakage.* Only relevant if Step 8 chose the promoted-25 subset — confirm the 12 are
  gone: `ls ~/.claude/skills | grep -cE '^(retro|loop-me|setup-pre-commit|migrate-to-shoehorn)$'` → expect `0`. With the default (all 37) this check should return `4`.

## Acceptance Criteria

1. `skills-lock.json` no longer exists in the working tree or the index.
2. `find .claude/skills -maxdepth 1 -mindepth 1 -type d` outputs exactly `doc-generator`,
   `skill-evals`, `version-bump-reviewer` — no other real directories.
3. `find .claude/skills -maxdepth 1 -type l | wc -l` outputs `27` (unchanged).
4. `docs/matt-pocock-skills.md` is deleted and no link to it remains anywhere
   (`grep -rn "matt-pocock-skills" docs/` returns nothing).
5. `CLAUDE.md`'s `## Agent skills` block and all three `docs/agents/*.md` files are unchanged
   (`git diff --stat CLAUDE.md docs/agents/` is empty).
6. `~/.claude/skills/` and `~/.copilot/skills/` each contain the installed upstream skills — 37 by
   default, or 25 if Step 8 removed the non-promoted set.
7. Both harnesses resolve the skills: `ls ~/.claude/skills` and Copilot's *Personal skills* section
   each report `ask-matt`, `grilling`, `wayfinder`, `to-spec`, `to-tickets`, and `wizard`.
8. No project-level duplicate of any installed name remains under this repo's `.claude/skills/`.
9. The `code-review` collision from Step 10 is resolved, not left in place: either the bare personal
   copy was removed, or the choice to keep it is recorded in the commit body.
10. Re-running the Step 7 install command is a no-op-or-update, not a duplication — the counts in
    criterion 6 are unchanged after a second run.
11. No `skills-lock.json` was recreated at this repo's root by the install.
12. `make lint`, `make test`, `make verify-structure`, `make markdown-lint`, and `make link-check`
    all exit 0.
13. The change is one conventional commit whose body names the six permanently-deleted skills and
    the `c9b0237` recovery point.

## Validation Commands

Execute these to validate the task is complete:

- `test ! -e skills-lock.json && echo "lockfile removed"` — lockfile is gone.
- `find .claude/skills -maxdepth 1 -mindepth 1 -type d` — expect only `doc-generator`, `skill-evals`, `version-bump-reviewer`.
- `find .claude/skills -maxdepth 1 -type l | wc -l` — expect `27`.
- `grep -rn "matt-pocock-skills" docs/ ; echo "exit=$?"` — expect no matches (`exit=1`).
- `git diff --stat CLAUDE.md docs/agents/` — expect empty output.
- `make markdown-lint` — markdown ruleset still passes on the reduced file set.
- `make link-check` — no dangling link to the deleted docs page.
- `make verify-structure` — repository structure gate passes.
- `make lint` — ruff + basedpyright clean (unchanged; no Python touched).
- `make test` — `uv run pytest` suite passes.
- `ls ~/.claude/skills | grep -cE '^(ask-matt|grilling|wayfinder|to-spec|to-tickets|wizard)$'` — expect `6`; Claude Code's global install landed.
- `copilot skill list 2>&1 | sed -n '/^Personal skills:/,/^Plugin skills:/p' | grep -cE '^\s+(ask-matt|grilling|wayfinder|to-spec|to-tickets|wizard) '` — expect `6`; Copilot resolves them as personal skills.
- `npx skills@latest ls --global --agent claude-code --agent github-copilot` — both agents listed with the same skill set.
- `copilot skill list 2>&1 | grep -oE '^\s+[a-z0-9-]+ ' | sort | uniq -d` — expect no output. Copilot renders every skill bare, so any repeated name here is a genuine unaddressable collision.
- `test $(find .claude/skills -maxdepth 1 -mindepth 1 -type d | wc -l) -eq 3 && echo "only repo-owned skills remain"` — no vendored directory survived the trash step.
- `test ! -e skills-lock.json && echo "install did not recreate a project lockfile"` — re-check after Step 7, not just after Step 4.

## Notes

**Why not `scripts/link-skills.sh`.** Upstream ships a symlink installer targeting `~/.claude/skills`
and `~/.agents/skills`, and Copilot reads `~/.agents/skills` as a personal source, so one run would
appear to cover both harnesses. Three reasons not to use it: its own header states it is *"a dev-only
script, intended for use by maintainers of this repo. It is not a supported installer"*; it has no
selection flags, no update path beyond `git pull`, and no removal story; and it makes the clone
permanently load-bearing. The `skills` CLI does the same job with explicit scope, agent, and skill
selection, plus `update` and `remove`.

**Why not the Claude Code plugin.** Covered in *Why the `skills` CLI rather than the Claude Code
plugin* above. Worth recording one property that route had and this one does not: the official
marketplace listing pins a git SHA, so updates arrive automatically when upstream cuts a release.
With the `skills` CLI, updates are a deliberate `npx skills update -g -y`. That is a downgrade in
convenience and an upgrade in control; nothing changes under you unnoticed.

**Do not use `--all`.** It expands to `--skill '*' --agent '*' -y`, and `--agent '*'` means all 78
agents in the CLI's supported table — it would create `~/.aider-desk/skills/`, `~/.codebuddy/skills/`,
`~/.factory/skills/` and dozens more on a machine that uses none of them. Step 7 names the two wanted
agents explicitly for exactly this reason. Note `-a/--agent` is repeatable (`-a x -a y`), not
comma-separated.

**Run installs from outside a repository.** `skills add` and `skills update -y` both infer scope from
the cwd, defaulting to project when one is detected — and `skills add` at project scope writes a
`skills-lock.json` into that project. Running Step 7 from inside this repo would recreate the very
file Step 4 deletes. `cd ~` first; `--global` makes the intent explicit but the cwd still governs
`update -y`'s auto-detection.

**Clone dependency.** Nothing in the chosen route depends on `/Users/bossjones/dev/mattpocock/skills`
— the CLI fetches from GitHub. The clone stays purely a research artifact and can be removed freely.

**Telemetry.** The `skills` CLI sends anonymous usage data by default, including repository and skill
identifiers for repositories GitHub confirms are public. Set `DISABLE_TELEMETRY=1` or `DO_NOT_TRACK=1`
on the Step 7 command to opt out.

**No new repo dependencies.** Nothing to `uv add`; no Python is touched. `copilot` (1.0.80) is on
`PATH` at `/opt/homebrew/bin/copilot`; the `skills` CLI runs through `npx` and installs nothing
permanently.

**Recovery.** Two independent paths. From git:
`git checkout c9b0237 -- .claude/skills/<name>`. From the Trash: Step 4 moves each directory to
`~/.Trash/<name>` (all 18 basenames are distinct, so nothing overwrites anything), recoverable until
the Trash is emptied. For the ten skills renamed or deleted upstream — including all six deleted in
Step 3 — `c9b0237` is the *only* durable source; upstream no longer carries those paths.
