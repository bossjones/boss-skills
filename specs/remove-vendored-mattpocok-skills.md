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
3. The upstream skills are installed once, at user scope, for Claude Code.
4. The same upstream skills are reachable from Copilot CLI at personal (user) scope.
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
- **Global install: one command per harness.** Claude Code takes the official plugin. Copilot CLI
  takes either the same repo as a plugin or the two promoted bucket directories registered as
  personal skill directories — decided by a verification step, not by assumption.

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
- The only local drift in the 18 vendored skills is cosmetic: commit `98263aa` added blank lines
  after `<vertical-slice-rules>` / `<issue-template>` / `<user-story-example>` in `to-issues` and
  `to-prd` to satisfy `rumdl`. Nothing else has been edited since `c9b0237`.

**Not verified, and Step 8 must resolve it:** whether an *installed* Copilot plugin surfaces skills
declared through `plugin.json`'s explicit `skills` array of bucketed paths (`./skills/engineering/…`)
rather than a conventional flat `skills/` directory. `--plugin-dir` cannot answer this — a control
run with this repo's own `plugins/boss-dev/agent-harness` (which has a conventional layout) showed
`--plugin-dir` does not feed `copilot skill list` at all, so the absence of mattpocock names there
proves nothing either way. Upstream ADR 0002 records that *Codex* cannot express this manifest
shape; Copilot may or may not share that limitation. Step 8 tests it and Step 9 is the fallback.

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

- `/Users/bossjones/dev/mattpocock/skills/.claude-plugin/plugin.json` — the authoritative 25-skill promoted list.
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
upstream once at user scope for Claude Code, and once at personal scope for Copilot CLI, verifying
each harness sees exactly one copy of each skill.

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

### 3. Decide the fate of the six upstream-deleted skills

Six vendored skills no longer exist upstream under any name: `caveman`, `design-an-interface`,
`edit-article`, `qa`, `write-a-skill`, `zoom-out`. Deleting them means losing them permanently from
the working tree (they stay recoverable from `c9b0237`).

- Default: delete all six along with the rest. They are unmaintained upstream and unreferenced here.
- If any is genuinely still wanted, **do not leave it in `.claude/skills/`.** Re-home it as an owned
  fork under a repo plugin so it gets the repo's normal treatment (`metadata.version`, eval suite,
  markdown lint, symlink into `.claude/skills/`), per `CLAUDE.md`'s skill layout rules:

  ```bash
  git mv .claude/skills/<name> plugins/boss-experimental/boss-experimental/skills/<name>
  ```

  Then add `metadata.version` to its frontmatter and a `.claude/skills/<name>` symlink matching the
  existing pattern (`../../plugins/boss-experimental/boss-experimental/skills/<name>`).
- Record the decision in the commit body either way.

### 4. Delete the vendored skills and the lockfile

- Remove all 18 directories (minus anything re-homed in Step 3) and the lockfile in one shot:

  ```bash
  git rm -r --quiet skills-lock.json $(while read -r n; do [ -d ".claude/skills/$n" ] && echo ".claude/skills/$n"; done < /tmp/locked.txt)
  ```

- Verify what remains under `.claude/skills/` is exactly the three repo-owned directories plus
  symlinks — no other real directories:

  ```bash
  find .claude/skills -maxdepth 1 -mindepth 1 -type d
  ```

  Expected output: `doc-generator`, `skill-evals`, `version-bump-reviewer` (plus anything re-homed
  in Step 3 is now a symlink, so it will not appear here).

### 5. Remove the stale documentation page

- Delete the catalogue, which documents the pre-rename names and the skills.sh install route:

  ```bash
  git rm docs/matt-pocock-skills.md
  ```

- Remove its row from the "Background & reference" table in `docs/README.md` (line 34, between the
  `LEARN.md` and `REFERENCES.md` rows). Leave the surrounding table intact.

### 6. Confirm the repo-side removal is clean

- Run the fast local gates that touch markdown and structure:

  ```bash
  make markdown-lint && make verify-structure && make link-check
  ```

- `link-check` is the one that catches a forgotten `docs/README.md` edit. Fix and re-run until green.

### 7. Install upstream globally for Claude Code

- Install at user scope from the official marketplace (`claude-plugins-official` is registered by
  default; there is no marketplace to add first):

  ```bash
  claude plugin install mattpocock-skills
  ```

- Verify the install landed at user scope:

  ```bash
  python3 -c "import json,os;d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')));print([ (k,[e.get('scope'),e.get('version')]) for k,v in d.items() if 'mattpocock' in k for e in v])"
  ```

  Expect one `mattpocock-skills@claude-plugins-official` entry with `scope: "user"`.

- Verify no duplication: from inside this repo, confirm none of the 25 promoted names resolve to a
  project-level copy:

  ```bash
  for n in ask-matt code-review codebase-design diagnosing-bugs domain-modeling grill-with-docs implement improve-codebase-architecture prototype research resolving-merge-conflicts setup-matt-pocock-skills tdd to-spec to-tickets triage wayfinder wizard grill-me grilling handoff teach to-questionnaire wait-what writing-for-agents; do [ -e ".claude/skills/$n" ] && echo "DUPLICATE $n"; done; echo "duplicate check done"
  ```

  Expect no `DUPLICATE` lines.

### 8. Try the plugin route for Copilot CLI, and verify it actually exposes skills

- Install the repo as a Copilot plugin (Copilot's `owner/repo` form reads `.claude-plugin/plugin.json`,
  which was confirmed during research):

  ```bash
  copilot plugin install mattpocock/skills
  ```

- **This is the verification that decides Step 9.** Check whether the promoted skills actually
  surface, using names that exist only upstream (so a hit cannot come from anything already installed):

  ```bash
  copilot skill list 2>&1 | grep -cE '^\s+(ask-matt|grilling|wayfinder|to-spec|to-tickets|wizard) '
  ```

  - Result `6` → the plugin route works. **Skip Step 9.**
  - Result `0` (or fewer than 6) → Copilot installed the plugin but did not load its
    `skills`-array-declared skills. Uninstall and go to Step 9:

    ```bash
    copilot plugin uninstall mattpocock-skills
    ```

### 9. Fallback for Copilot CLI: register the promoted bucket directories

Only if Step 8 came back short.

- Ensure the clone is present and current (this becomes the update mechanism — `git pull` replaces
  `copilot plugin update`):

  ```bash
  git -C /Users/bossjones/dev/mattpocock/skills pull --ff-only
  ```

- Register exactly the two promoted buckets as personal skill directories. `skills/engineering/`
  holds 18 skills and `skills/productivity/` holds 7 — the exact 25 in `plugin.json`, so this
  registers the promoted set and nothing from `in-progress/` (8) or `misc/` (4):

  ```bash
  copilot skill add /Users/bossjones/dev/mattpocock/skills/skills/engineering
  ```

  ```bash
  copilot skill add /Users/bossjones/dev/mattpocock/skills/skills/productivity
  ```

- Re-run the same verification as Step 8; expect `6`. If `copilot skill add` rejects a directory of
  skill subdirectories, fall back to symlinking each promoted skill into `~/.copilot/skills/`,
  matching the existing obsidian-wiki pattern already on this machine:

  ```bash
  for d in /Users/bossjones/dev/mattpocock/skills/skills/engineering/*/ /Users/bossjones/dev/mattpocock/skills/skills/productivity/*/; do [ -f "$d/SKILL.md" ] && ln -sfn "${d%/}" "$HOME/.copilot/skills/$(basename "$d")"; done
  ```

- Do **not** run upstream's `scripts/link-skills.sh` for this (see Notes).

### 10. Reconcile the name collisions the install introduces

- `code-review` is the sharp one. Both harnesses already carry a `code-review` skill from
  `anthropics/claude-plugins-official`, and Claude Code ships a built-in `/code-review` command.
  Upstream's promoted `code-review` (the former vendored `review`) now makes a third. List them and
  decide which wins:

  ```bash
  copilot skill list 2>&1 | grep -nE '^\s+code-review '
  ```

  Options, in order of preference: leave both installed and always reach the upstream one through a
  fully-qualified invocation; or disable one with `copilot plugins disable <name> --skill`. Record
  whichever is chosen.
- Note two description-level overlaps that need no action but are worth knowing: upstream `grilling`
  competes with `superpowers:brainstorming` for "let's think this through before building" prompts,
  and upstream `tdd` competes with `superpowers:test-driven-development`. Both pairs push toward the
  same behavior; reach for the user-invoked wrapper (`/grill-me`) when determinism matters.
- Separately: prior guidance on this repo was that `/review` findings should carry low/medium/high
  severity tags and post as inline `gh` PR comments. The vendored `review` never encoded that (it is
  byte-identical to what `c9b0237` added), and upstream `code-review` does not either. This repo's
  own `agent-harness:github-pr-review`, `pr-review`, and `add-review-comment` skills already do
  inline `gh` comments — keep using those for that workflow rather than expecting it from upstream.

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
  vendored copies, not repo-internal skills), and no file under `plugins/` changed — unless Step 3
  re-homed a skill into `plugins/boss-experimental/`, which *is* a feature-bearing plugin change and
  does require a bump.
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

- *Partial deletion.* If `git rm` misses a directory (e.g. an untracked stray file inside one blocks
  removal), the duplicate check in Step 7 catches it. Run it after Step 4 as well as after Step 7.
- *Symlink damage.* `git rm -r` on a path list built from `skills-lock.json` cannot touch the 27
  plugin symlinks, since no locked name matches a symlinked name. Confirm anyway with
  `find .claude/skills -maxdepth 1 -type l | wc -l` → expect 27 before and after.
- *Copilot silently installing the plugin but loading zero skills.* This is the whole point of the
  Step 8 grep. A bare `copilot plugin list` showing `mattpocock-skills` is **not** sufficient
  evidence — `--plugin-dir` demonstrated during research that a plugin can be recognized without its
  skills being loaded.
- *Global install duplicating what is already there.* Both harnesses must be checked from inside a
  project that has no local copies. Run the Step 7 duplicate check from this repo after removal, and
  once from an unrelated directory.
- *Non-promoted leakage.* If Step 9's symlink fallback is used, confirm nothing from `in-progress/`
  or `misc/` was linked: `ls ~/.copilot/skills | grep -cE '^(retro|loop-me|setup-pre-commit|migrate-to-shoehorn)$'` → expect `0`.

## Acceptance Criteria

1. `skills-lock.json` no longer exists in the working tree or the index.
2. `find .claude/skills -maxdepth 1 -mindepth 1 -type d` outputs exactly `doc-generator`,
   `skill-evals`, `version-bump-reviewer` — no other real directories.
3. `find .claude/skills -maxdepth 1 -type l | wc -l` outputs `27` (unchanged), or `27` plus one per
   skill re-homed in Step 3.
4. `docs/matt-pocock-skills.md` is deleted and no link to it remains anywhere
   (`grep -rn "matt-pocock-skills" docs/` returns nothing).
5. `CLAUDE.md`'s `## Agent skills` block and all three `docs/agents/*.md` files are unchanged
   (`git diff --stat CLAUDE.md docs/agents/` is empty).
6. `~/.claude/plugins/installed_plugins.json` contains a `mattpocock-skills@claude-plugins-official`
   entry with `scope: "user"`.
7. `copilot skill list` reports `ask-matt`, `grilling`, `wayfinder`, `to-spec`, `to-tickets`, and
   `wizard` — all six, via either Step 8 or Step 9.
8. No skill name appears twice in either harness's listing from inside this repo.
9. `make lint`, `make test`, `make verify-structure`, `make markdown-lint`, and `make link-check`
   all exit 0.
10. The change is one conventional commit whose body names the six permanently-deleted skills and
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
- `python3 -c "import json,os;d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')));print([k for k in d if 'mattpocock' in k])"` — expect `['mattpocock-skills@claude-plugins-official']`.
- `copilot skill list 2>&1 | grep -cE '^\s+(ask-matt|grilling|wayfinder|to-spec|to-tickets|wizard) '` — expect `6`.
- `copilot skill list 2>&1 | grep -oE '^\s+[a-z0-9-]+ ' | sort | uniq -d` — expect no output (no duplicate skill names).

## Notes

**Why not `scripts/link-skills.sh`.** Upstream ships a symlink installer, and it is tempting because
it targets `~/.claude/skills` and `~/.agents/skills` — and Copilot reads `~/.agents/skills` as a
personal source, so one run would appear to cover both harnesses. Three reasons not to use it here:
its own header states it is *"a dev-only script, intended for use by maintainers of this repo. It is
not a supported installer"*; it links every non-`deprecated` skill, which is 37 including 12
non-promoted ones from `in-progress/` and `misc/`; and writing into `~/.claude/skills` would collide
head-on with the Step 7 plugin install, reproducing exactly the "every skill twice" problem this
plan exists to remove. Step 9's targeted alternative writes only where Copilot reads and only for
promoted skills.

**What "auto-update" means for the Claude plugin.** The official marketplace listing pins a git SHA,
not a branch. Updates arrive when upstream cuts a release, not on every commit to `main`. Upstream's
own ADR 0002 records a case where the listing lagged `main` by two commits. If bleeding-edge is ever
wanted, the fallback is the repo's own single-plugin marketplace
(`/plugin marketplace add mattpocock/skills`), which upstream keeps but deliberately does not
document to users.

**Clone dependency.** Step 9 (only) makes `/Users/bossjones/dev/mattpocock/skills` load-bearing for
Copilot: deleting it leaves dangling registrations rather than reverting cleanly. If Step 8 succeeds,
the clone stays purely a research artifact and can be removed freely.

**No new dependencies.** Nothing to `uv add`; no Python is touched. `claude` and `copilot` are both
already on `PATH` (Copilot CLI 1.0.80 at `/opt/homebrew/bin/copilot`).

**Recovery.** Anything deleted here is one command away:
`git checkout c9b0237 -- .claude/skills/<name>`. For the ten skills renamed or deleted upstream, that
commit is the *only* remaining source — upstream no longer carries those paths.
