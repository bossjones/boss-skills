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
3. The upstream skills are installed at user scope through the **plugin system** on both harnesses —
   `claude plugin install` and `copilot plugin install` — so every skill is addressable under the
   `mattpocock-skills:` namespace rather than as a bare global name.
4. Re-running an install updates in place rather than duplicating, and `claude plugin update` /
   `copilot plugin update` refresh to newer upstream releases.
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
- **Global install: the plugin system, on both harnesses.** `mattpocock-skills` is a Claude Code
  plugin listed in the official marketplace, and Copilot CLI installs plugins from any GitHub repo
  with `owner/repo`. Both read the same `.claude-plugin/plugin.json`, so both get the same 25
  promoted skills.

### Why the plugin system rather than the `skills` CLI

Both routes deliver upstream content at user scope. The plugin route is chosen for one decisive
reason — **namespacing** — and it costs coverage:

| | Plugin system (chosen) | `skills` CLI (`npx skills add`) |
|---|---|---|
| Names | **Namespaced** (`mattpocock-skills:code-review`) | Bare (`code-review`) |
| Harness coverage | Claude Code confirmed; Copilot needs Step 8's check | Both, one command |
| Skills installed | **25** (the promoted set only) | 37 (25 promoted + 12 non-promoted) |
| Updates | `claude plugin update` / `copilot plugin update`; Claude's official listing auto-updates on release | `npx skills update -g -y` |
| Files | Read-only plugin cache | Symlinks to one canonical copy |

Namespacing is the whole point: it is a property of the plugin system, and only the plugin system.
Personal skills — what `npx skills add` writes into `~/.claude/skills/` and `~/.copilot/skills/` —
have no plugin to be namespaced under, so they take bare global names and `code-review` collides
head-on with the official `code-review` plugin in both harnesses. Under the plugin route that
collision evaporates: the two live at `mattpocock-skills:code-review` and `code-review:code-review`.

**The cost is the 12 non-promoted skills.** `plugin.json`'s `skills` array names exactly 25 paths, so
`retro`, `loop-me`, `setup-pre-commit`, `git-guardrails-claude-code`, `implement-spec`,
`claude-handoff`, `setup-ts-deep-modules`, `writing-beats`, `writing-fragments`, `writing-shape`,
`migrate-to-shoehorn`, and `scaffold-exercises` are not installable this way — upstream keeps them in
`in-progress/` and `misc/` and deliberately does not ship them. If any of those turn out to be wanted,
add them separately with the `skills` CLI (`npx skills@latest add mattpocock/skills -s retro -s
setup-pre-commit -g -a claude-code -a github-copilot -y`), accepting bare names for those few.

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
- **Personal and project skills are bare in both harnesses**, because there is no plugin to namespace
  them under. Corroborated on this machine: the skills.sh-installed copies in this repo's
  `.claude/skills/` appear bare in a Claude session (`grill-me`, `triage`, `diagnose`), and the
  obsidian-wiki symlinks in `~/.copilot/skills/` appear bare under Copilot's *Personal skills*. This
  is precisely why the plugin route is chosen over the `skills` CLI.
- **`plugin.json` ships exactly 25 skills.** Its `skills` array names 18 paths under
  `./skills/engineering/` and 7 under `./skills/productivity/`. The 12 skills in `in-progress/` and
  `misc/` are not in it and are therefore not installable via either plugin manager.
- **Copilot's two install commands accept different sources.** `copilot plugin install` (singular)
  takes `plugin@marketplace`, `owner/repo`, `owner/repo:path`, or `https://…` — **no local path**.
  `copilot plugins install` (plural) additionally accepts a **local path**. Rung 9a stages a plugin
  on disk, so it must use the plural form. Copilot does parse `.claude-plugin/plugin.json`:
  `copilot --plugin-dir /Users/bossjones/dev/mattpocock/skills plugin list` reports
  `mattpocock-skills` under *External Plugins*.
- **`claude plugin` and `claude plugins` are aliases** for the same command group. `claude plugin
  install` takes `-s/--scope <user|project|local>`, defaulting to `user`, plus `-y/--yes` for
  non-TTY runs. `claude plugin details <name>` prints a plugin's full component inventory (skill
  names included) and its projected per-session token cost — the best single verification that all
  25 skills loaded.
- **Naming the marketplace changes whether the catalog is refreshed.** Per Claude Code's
  [discover-plugins docs](https://code.claude.com/docs/en/discover-plugins): installing
  `plugin-name@marketplace-name` refreshes that marketplace *before* the lookup, whereas
  `claude plugin install plugin-name` (bare) "reads the cached catalogs without refreshing". Always
  use the fully-qualified form, or an install can silently resolve against a stale catalog.
- **Auto-update defaults differ by marketplace origin.** `claude-plugins-official` and most official
  Anthropic marketplaces have auto-update **on** by default; third-party and local development
  marketplaces have it **off**. So the official listing keeps itself current, but a
  `mattpocock` marketplace added by hand would not.
- **Claude Code's docs state the namespacing rule outright**: "Plugin skills are namespaced by the
  plugin name", giving `/commit-commands:commit` as the worked example. This corroborates the live
  skill-listing observation rather than resting on it alone.
- **Removing a marketplace uninstalls every plugin installed from it** (documented warning). Relevant
  only to the fallback routes, but destructive enough to note.
- **A shell `claude plugin install` does not affect the running session.** Plugins load on next
  start, or on `/reload-plugins` in an open session.
- **Copilot's default marketplaces do not carry this plugin.** `copilot plugin marketplace list`
  shows only `copilot-plugins` (github/copilot-plugins) and `awesome-copilot`
  (github/awesome-copilot); browsing both for "mattpocock" returns zero hits. Any Copilot marketplace
  route therefore has to add upstream's own marketplace first.
- **Upstream ships its own single-plugin marketplace.** `.claude-plugin/marketplace.json` declares
  marketplace `mattpocock` with one plugin, `mattpocock-skills`, `source: "./"`. Upstream keeps it as
  a fallback and deliberately does not document it. **Caveat:** GitHub's marketplace docs say each
  plugin entry requires `name`, `description`, `version`, and `source` — and upstream's entry has no
  `version` field, so Copilot may reject or mis-handle the catalog. Untested; Step 8b finds out.
- **Copilot's uninstall/update take a plugin name**, not a repo slug: `copilot plugin uninstall
  <plugin-name|plugin-name@marketplace>`, `copilot plugin update <name>` or `--all`.
- **Escape hatch for the 12 non-promoted skills, if ever wanted** (`npx skills@latest --help`):
  `-g/--global`, `-a/--agent` (repeatable, **not** comma-separated; `claude-code` →
  `~/.claude/skills/`, `github-copilot` → `~/.copilot/skills/`), `-s/--skill`, `-y/--yes`,
  `-l/--list` to preview. Never `--all` — it expands to `--agent '*'`, targeting all 78 supported
  agents. Skills installed this way are bare, not namespaced.
- `trash` is macOS `/usr/bin/trash`. It recurses into directories with no `-r` flag (passing one is
  an error), moves to `~/.Trash`, and exits 0 — but it does **not** update the git index, so staging
  is a separate step.
- The only local drift in the 18 vendored skills is cosmetic: commit `98263aa` added blank lines
  after `<vertical-slice-rules>` / `<issue-template>` / `<user-story-example>` in `to-issues` and
  `to-prd` to satisfy `rumdl`. Nothing else has been edited since `c9b0237`.

**Not verified, and Step 8 must resolve it before the Copilot half of this plan is real:** whether an
*installed* Copilot plugin surfaces skills declared through `plugin.json`'s explicit `skills` array of
bucketed paths (`./skills/engineering/…`) rather than a conventional flat `skills/` directory.

Every avenue short of a real install was tried and none settles it:

- `--plugin-dir` does not feed skill enumeration at all — neither `copilot skill list` nor
  `copilot plugins list --kind skill`. A control run with this repo's own
  `plugins/boss-dev/agent-harness` (conventional layout, skills that *do* load when installed)
  produced the same empty result, so the absence of mattpocock names there is an artifact of
  `--plugin-dir`, not evidence about the manifest.
- No natural experiment exists among the plugins already installed: all eleven
  (`superpowers`, `frontend-design`, `skill-creator`, `documentation-generation`,
  `documentation-standards`, `claude-md-management`, …) use a conventional `skills/` directory and
  **none** declares an explicit `skills` array.
- Upstream ADR 0002 records that *Codex* cannot express this manifest shape, which is suggestive but
  says nothing definitive about Copilot.

One reversible command settles it: `copilot plugin install mattpocock/skills`, then the grep in
Step 8. Step 9 is the fallback ladder if it comes back short.

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

- [Claude Code — Discover and install prebuilt plugins](https://code.claude.com/docs/en/discover-plugins) — the authority for Step 7: the official marketplace, the `plugin@marketplace` refresh semantics, auto-update defaults, scopes, `/reload-plugins`, and the explicit statement that plugin skills are namespaced by plugin name.
- [Copilot CLI — Finding and installing plugins](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/plugins-finding-installing) — the `PLUGIN-NAME@MARKETPLACE-NAME` install form and the list/update/uninstall commands.
- [Copilot CLI — Plugin marketplaces](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/plugins-marketplace) — `marketplace add`, and the required `marketplace.json` fields that upstream's catalog does not fully satisfy (Step 8b).
- `/Users/bossjones/dev/mattpocock/skills/.claude-plugin/plugin.json` — the authoritative 25-skill promoted list.
- `/Users/bossjones/dev/mattpocock/skills/.claude-plugin/marketplace.json` — upstream's own single-plugin marketplace (`mattpocock`), the basis for Step 8b. Note its plugin entry has no `version` field.
- `/Users/bossjones/dev/mattpocock/skills/.agents/install-block.md` — upstream's canonical install wording, which documents the plugin route for Claude Code and states the two routes are exclusive.
- [`vercel-labs/skills`](https://github.com/vercel-labs/skills) — the `skills` CLI behind `skills.sh`. Not the chosen route; consulted for rung 9b and the non-promoted-skills escape hatch. Its README is the authority on flags and the supported-agent table (`claude-code` → `~/.claude/skills/`, `github-copilot` → `~/.copilot/skills/`).
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
`mattpocock-skills` as a plugin at user scope on Claude Code and on Copilot CLI, verifying on each
that the skills load and resolve under the `mattpocock-skills:` namespace.

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

### 7. Install the plugin at user scope for Claude Code

- Confirm the official marketplace is registered. Claude Code adds it automatically on first
  interactive start, and it is already present here:

  ```bash
  claude plugin marketplace list 2>&1 | grep -A1 claude-plugins-official
  ```

  If it is ever missing: `claude plugin marketplace add anthropics/claude-plugins-official`.

- Install **fully qualified**, not by bare name. Naming the marketplace makes Claude Code refresh
  that catalog before the lookup; the bare form reads the cached catalog without refreshing, so it
  can resolve against a stale listing or miss a recent release outright. Pass `--scope user`
  explicitly too — it is the default, but this runs from inside a project directory where `project`
  and `local` are equally valid and a silent default is the wrong thing to rely on:

  ```bash
  claude plugin install mattpocock-skills@claude-plugins-official --scope user
  ```

  If the result reports `marketplace not refreshed`, the refresh failed and the install fell back to
  the cached catalog. Force it and retry:

  ```bash
  claude plugin marketplace update claude-plugins-official && claude plugin install mattpocock-skills@claude-plugins-official --scope user
  ```

- **Verify with the component inventory, not the JSON.** This is the single best check that the
  manifest's 25 skills all loaded, and it names them:

  ```bash
  claude plugin details mattpocock-skills
  ```

  Expect `Skills (25)` listing `ask-matt … writing-for-agents`, `Source:
  mattpocock-skills@claude-plugins-official`. Note the *Projected token cost* line while it is on
  screen: 25 skill descriptions are always-on context in every session from here on, so if that
  number looks unacceptable, this is the moment to reconsider scope rather than after the fact.

- Confirm the scope recorded is `user`:

  ```bash
  claude plugin list 2>&1 | grep -A3 mattpocock
  ```

- A shell `claude plugin install` does not touch an already-running session — the plugin loads on
  next start, or immediately via `/reload-plugins` in an open session (`--force` if it warns about
  re-reading the conversation). If skills still fail to appear, the documented remedy is to delete
  `~/.claude/plugins/cache`, restart Claude Code, and reinstall.

- Auto-update needs no configuration here: `claude-plugins-official` has it enabled by default, so
  upstream releases arrive on their own. Third-party and local marketplaces default to auto-update
  **off**, which matters only if a fallback route below is used.

- Verify no duplication: from inside this repo, confirm none of the 25 names resolves to a
  project-level copy — this is what Step 4 guaranteed:

  ```bash
  for n in ask-matt code-review codebase-design diagnosing-bugs domain-modeling grill-with-docs implement improve-codebase-architecture prototype research resolving-merge-conflicts setup-matt-pocock-skills tdd to-spec to-tickets triage wayfinder wizard grill-me grilling handoff teach to-questionnaire wait-what writing-for-agents; do [ -e ".claude/skills/$n" ] && echo "DUPLICATE $n"; done; echo "duplicate check done"
  ```

  Expect no `DUPLICATE` lines. In a fresh session the skills should appear as
  `mattpocock-skills:grill-me`, `mattpocock-skills:code-review`, and so on.

### 8. Install the plugin for Copilot CLI, and verify its skills actually load

**This step decides whether Step 9 is needed.** Copilot recognises the repo as a plugin — that much
is confirmed — but whether it loads skills declared through `plugin.json`'s `skills` array is the one
open question in this plan (see *What is verified*). There are two independent ways in; try both
before dropping to the fallback ladder, because they use different discovery paths.

`mattpocock-skills` is in neither of Copilot's two bundled marketplaces (`copilot-plugins`,
`awesome-copilot`) — browsing both for the name returns nothing — so there is no "official listing"
equivalent here.

**8a — direct repo install.** Note this tracks the repo's default branch at install time, not the SHA
Claude's official listing pins, so the two harnesses can sit on different commits:

```bash
copilot plugin install mattpocock/skills
```

```bash
copilot plugin list 2>&1 | grep -i mattpocock
```

Then run the decisive check below. If it passes, skip 8b and Step 9.

**8b — upstream's own marketplace.** Upstream ships `.claude-plugin/marketplace.json` declaring
marketplace `mattpocock` with the single plugin `mattpocock-skills`. It keeps this as a fallback and
does not document it to users, but it is a legitimate second discovery path and may resolve the
manifest differently from a direct repo install. Only try this if 8a's check came back short —
uninstall 8a's copy first:

```bash
copilot plugin uninstall mattpocock-skills
```

```bash
copilot plugin marketplace add mattpocock/skills && copilot plugin install mattpocock-skills@mattpocock
```

**Expect this one to be fragile.** GitHub's marketplace documentation says every plugin entry
requires `name`, `description`, `version`, and `source` — and upstream's entry carries no `version`
field. If Copilot validates strictly, the add or the install fails here; that is informative, not a
bug to work around. Also note that `copilot plugin marketplace remove mattpocock` would uninstall any
plugin installed from it, so unwind in that order if abandoning this route.

**The decisive check** (run after 8a, and again after 8b if needed). These names exist only upstream,
so a hit cannot come from anything already installed:

```bash
copilot skill list 2>&1 | sed -n '/^Plugin skills:/,/^Builtin skills:/p' | grep -cE '^\s+(ask-matt|grilling|wayfinder|to-spec|to-tickets|wizard) '
```

- Result `6` → the plugin route works on Copilot. **Skip Step 9.** Confirm the namespaced form is
  what the slash picker offers (`/mattpocock-skills:grill-me`); `copilot skill list` prints bare
  names for every source and is not evidence about naming.
- Result `0`, or fewer than 6, after **both** 8a and 8b → Copilot registers the plugin but does not
  load its manifest-declared skills. Remove whatever is installed and work down Step 9's ladder:

  ```bash
  copilot plugin uninstall mattpocock-skills
  ```

### 9. Fallback ladder for Copilot CLI

Only if Step 8 came back short. Try these in order and stop at the first that works — each rung
trades away less than the one below it.

**9a — Wrap the promoted skills in a conventional-layout plugin.** Copilot demonstrably loads skills
from a plugin's `skills/` directory (every one of the eleven plugins already installed works this
way). Build a thin local plugin that presents the same 25 skills in that shape, keeping the
`mattpocock-skills:` namespace:

```bash
mkdir -p ~/.local/share/mattpocock-skills-copilot/{.claude-plugin,skills} && git -C /Users/bossjones/dev/mattpocock/skills pull --ff-only
```

```bash
python3 -c "
import json,os,shutil,pathlib
src=pathlib.Path('/Users/bossjones/dev/mattpocock/skills')
dst=pathlib.Path(os.path.expanduser('~/.local/share/mattpocock-skills-copilot'))
m=json.load(open(src/'.claude-plugin/plugin.json'))
for rel in m['skills']:
    s=src/rel
    d=dst/'skills'/s.name
    if d.exists(): shutil.rmtree(d)
    shutil.copytree(s,d)
m['skills']='./skills'
json.dump(m,open(dst/'.claude-plugin/plugin.json','w'),indent=2)
print(len(os.listdir(dst/'skills')),'skills staged')
"
```

Copy rather than symlink — plugin installers copy the tree and drop symlinks. Then install from the
local path and re-run Step 8's decisive check:

```bash
copilot plugins install ~/.local/share/mattpocock-skills-copilot
```

**The plural `plugins install` is required here** — the singular `copilot plugin install` accepts
only `plugin@marketplace`, `owner/repo`, `owner/repo:path`, and `https://…`, and will not take a
local path. Refreshing later means re-running the staging script after a `git pull`, then
`copilot plugin update mattpocock-skills`. Record that as the maintenance cost.

**9b — Personal skills, namespacing sacrificed on Copilot only.** If 9a fails, fall back to the
`skills` CLI for the Copilot half. Claude Code keeps its namespaced plugin from Step 7; Copilot gets
bare names:

```bash
cd ~ && npx skills@latest add mattpocock/skills --skill '*' --agent github-copilot --global --yes
```

Run it from `~`, never from inside a repository — `skills add` infers project scope from the cwd and
would write a `skills-lock.json` there, recreating the file Step 4 deleted. This rung installs all 37
discovered skills (25 promoted + 12 non-promoted) and reintroduces the bare `code-review` collision
on Copilot, which Step 10 then has to handle for that harness.

- Record which rung was used in the commit body — it determines the update procedure from here on.

### 10. Reconcile the name collisions the install introduces

The plugin route resolves the sharp collision by construction — that is why it was chosen. What
remains is a check that it actually did, plus two overlaps namespacing cannot touch.

**`code-review`, resolved by namespacing.** Both harnesses already carry a `code-review` skill from
`anthropics/claude-plugins-official`, and Claude Code ships a built-in `/code-review` command.
Upstream's promoted `code-review` makes a third — but under the plugin system all three are
distinctly addressable: `mattpocock-skills:code-review`, `code-review:code-review`, and the built-in.
No removal, no disabling.

- Confirm all three coexist rather than shadowing each other. In Claude Code, a fresh session's skill
  listing should show `mattpocock-skills:code-review` and `code-review:code-review` as separate
  entries. In Copilot, the slash picker should offer `/mattpocock-skills:code-review`:

  ```bash
  copilot skill list 2>&1 | grep -cE '^\s+code-review '
  ```

  `copilot skill list` prints bare names for every source, so a count of `2` here is expected and
  benign under the plugin route — the picker disambiguates. It is only a problem if Step 9b was used.
- **If Step 9b was used**, Copilot's copy is a bare personal skill and genuinely collides. Drop just
  that one and keep reaching the official plugin's version by its namespaced name:

  ```bash
  npx skills@latest remove --global --agent github-copilot code-review
  ```

**Description-trigger overlap, which namespacing does not fix.** Namespacing governs *addressing*,
never *autonomous selection*. Upstream's `code-review`, `tdd`, `grilling`, and `research` are all
model-invoked (no `disable-model-invocation`), so they still compete by description with the official
`code-review` plugin, `superpowers:brainstorming`, and `superpowers:test-driven-development`. No
action — but when determinism matters, reach for a user-invoked wrapper (`/grill-me`) or the
fully-qualified `mattpocock-skills:<name>` form, neither of which has a competing interpretation.

**Version skew between harnesses.** Claude's official-marketplace listing pins a SHA that moves on
upstream release; `copilot plugin install mattpocock/skills` tracks the default branch at install
time. The two can drift apart. Harmless for skills, but worth knowing before debugging a behaviour
difference between harnesses:

```bash
python3 -c "import json,os;d=json.load(open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')));print([e.get('gitCommitSha') for k,v in d.items() if 'mattpocock' in k for e in v])"
```

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
- *Plugin recognised but skills not loaded.* The whole point of Step 8's grep. `copilot plugin list`
  showing `mattpocock-skills` is **not** sufficient evidence — `--plugin-dir` already demonstrated
  that a plugin can be recognised without its skills being enumerated.
- *Reading `copilot skill list` as evidence about naming.* It prints bare names for every source,
  plugin skills included. Two `code-review` lines there are expected and benign under the plugin
  route. The slash picker is the authority on namespacing.
- *Rung 9b silently reintroducing a lockfile.* Only 9b runs `skills add`, which infers project scope
  from the cwd. The `cd ~` guards it; the `test ! -e skills-lock.json` check catches a dropped `cd`.
- *Rung 9a staged with symlinks.* Plugin installers copy the tree and drop symlinks, so the staging
  script must `copytree`. If Copilot shows the plugin but zero skills after 9a, check for symlinks
  under `~/.local/share/mattpocock-skills-copilot/skills/`.
- *Bare-name install resolving against a stale catalog.* `claude plugin install <name>` reads cached
  catalogs without refreshing; only the `<name>@<marketplace>` form forces a refresh first. A missing
  or outdated plugin here looks like an upstream problem but is a local cache one.
- *Marketplace validation failing in 8b.* Upstream's `marketplace.json` plugin entry omits the
  `version` field GitHub's docs list as required. A failure at `marketplace add` or at install is the
  expected outcome, not something to patch around — record it and move to Step 9.
- *Unwinding 8b in the wrong order.* Removing a marketplace uninstalls the plugins installed from it.
  Uninstall the plugin first, then remove the catalog.
- *Silent version skew.* Claude tracks the marketplace's pinned SHA; Copilot tracks the default
  branch at install time. Not a failure, but check both before attributing a behaviour difference to
  a harness rather than a commit.
- *Wrong Copilot install verb in rung 9a.* `copilot plugin install` (singular) rejects local paths;
  only `copilot plugins install` (plural) accepts them. A singular call there fails at the argument
  parser, which is loud rather than silent — but easy to mistype given the alias-like naming.
- *Scope drift on Claude.* `claude plugin install` defaults to `--scope user`, but the plan runs it
  from inside a project directory. If `claude plugin list` reports `Scope: project`, uninstall and
  re-install with `--scope user` — a project-scoped install would follow this repo rather than the
  machine.
- *Always-on token cost.* 25 skill descriptions load into every session. `claude plugin details
  mattpocock-skills` reports the projected figure; check it once rather than discovering the cost
  through degraded context later.

## Acceptance Criteria

1. `skills-lock.json` no longer exists in the working tree or the index.
2. `find .claude/skills -maxdepth 1 -mindepth 1 -type d` outputs exactly `doc-generator`,
   `skill-evals`, `version-bump-reviewer` — no other real directories.
3. `find .claude/skills -maxdepth 1 -type l | wc -l` outputs `27` (unchanged).
4. `docs/matt-pocock-skills.md` is deleted and no link to it remains anywhere
   (`grep -rn "matt-pocock-skills" docs/` returns nothing).
5. `CLAUDE.md`'s `## Agent skills` block and all three `docs/agents/*.md` files are unchanged
   (`git diff --stat CLAUDE.md docs/agents/` is empty).
6. `claude plugin details mattpocock-skills` reports `Skills (25)`, and `claude plugin list` shows the
   plugin at `Scope: user`, `Status: ✔ enabled`.
7. Copilot reports the plugin's skills — `ask-matt`, `grilling`, `wayfinder`, `to-spec`, `to-tickets`,
   `wizard` all present — via Step 8 or a recorded rung of Step 9.
8. Skills resolve under the `mattpocock-skills:` namespace on both harnesses (Claude Code's skill
   listing; Copilot's slash picker), except on Copilot if Step 9b was the rung used.
9. No project-level duplicate of any of the 25 names remains under this repo's `.claude/skills/`.
10. All three `code-review` skills coexist addressably rather than shadowing one another — or, if
    Step 9b was used, Copilot's bare personal copy was removed.
11. Re-running an install updates in place rather than duplicating, and no `skills-lock.json` was
    recreated at this repo's root.
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
- `claude plugin marketplace list 2>&1 | grep -A1 claude-plugins-official` — the official catalog is registered.
- `claude plugin details mattpocock-skills` — expect `Skills (25)` and `Source: mattpocock-skills@claude-plugins-official`.
- `claude plugin list 2>&1 | grep -A3 mattpocock` — expect `Scope: user` and `Status: ✔ enabled`.
- `copilot plugin list 2>&1 | grep -i mattpocock` — the plugin is registered with Copilot.
- `copilot plugin marketplace list` — records which route Step 8 landed on: a `mattpocock` entry means 8b was used and that catalog needs manual refreshing.
- `copilot skill list 2>&1 | sed -n '/^Plugin skills:/,/^Builtin skills:/p' | grep -cE '^\s+(ask-matt|grilling|wayfinder|to-spec|to-tickets|wizard) '` — expect `6`; Copilot loaded the plugin's skills.
- `test $(find .claude/skills -maxdepth 1 -mindepth 1 -type d | wc -l) -eq 3 && echo "only repo-owned skills remain"` — no vendored directory survived the trash step.
- `test ! -e skills-lock.json && echo "no project lockfile"` — re-check after Step 9 if rung 9b was used, not just after Step 4.

## Notes

**Marketplace command reference.** Both harnesses use the same two-step model — register a catalog,
then install from it — with different spellings:

| | Claude Code | Copilot CLI |
|---|---|---|
| List catalogs | `claude plugin marketplace list` | `copilot plugin marketplace list` |
| Add | `claude plugin marketplace add <owner/repo\|url\|path>` | `copilot plugin marketplace add <owner/repo\|url\|path>` |
| Browse | `/plugin` → **Discover** tab | `copilot plugin marketplace browse <name>` |
| Refresh | `claude plugin marketplace update <name>` | `copilot plugin marketplace update [name]` |
| Install | `claude plugin install <plugin>@<marketplace> [--scope user\|project\|local]` | `copilot plugin install <plugin>@<marketplace>` |
| Install direct from repo | n/a — marketplace only | `copilot plugin install <owner/repo>` (also `owner/repo:path`, git URL) |
| Install from local path | via `marketplace add ./path` first | `copilot plugins install <path>` (**plural**) |
| Remove catalog | `claude plugin marketplace remove <name>` | `copilot plugin marketplace remove <name>` |

Bundled catalogs: Claude Code auto-registers `claude-plugins-official`
(`anthropics/claude-plugins-official`); Copilot ships `copilot-plugins` (`github/copilot-plugins`) and
`awesome-copilot` (`github/awesome-copilot`). `mattpocock-skills` is listed in Claude's official
marketplace and in **neither** of Copilot's — which is the whole reason Step 8 needs two attempts.

Two traps worth repeating: **removing a marketplace uninstalls every plugin installed from it** on
Claude Code, so unwind installs before catalogs. And **auto-update is on by default only for official
Anthropic marketplaces** — a hand-added `mattpocock` catalog (Step 8b) would need refreshing by hand.

**Why not `scripts/link-skills.sh`.** Upstream ships a symlink installer targeting `~/.claude/skills`
and `~/.agents/skills`, and Copilot reads `~/.agents/skills` as a personal source, so one run would
appear to cover both harnesses. Three reasons not to use it: its own header states it is *"a dev-only
script, intended for use by maintainers of this repo. It is not a supported installer"*; it has no
selection flags, no update path beyond `git pull`, and no removal story; and it makes the clone
permanently load-bearing. The `skills` CLI does the same job with explicit scope, agent, and skill
selection, plus `update` and `remove`.

**What "auto-update" means on each harness.** Claude Code's official listing pins a git SHA, not a
branch: updates arrive when upstream cuts a release, not on every commit to `main` — upstream's ADR
0002 records the listing once lagging `main` by two commits. Copilot's `owner/repo` install tracks
the default branch at install time and refreshes on `copilot plugin update`. Neither is
bleeding-edge by default, and the two can sit on different commits.

**If the `skills` CLI is used at all** (only rung 9b, or the escape hatch for the 12 non-promoted
skills): run it from outside a repository. `skills add` and `skills update -y` infer scope from the
cwd and default to project when one is detected, and `skills add` at project scope writes a
`skills-lock.json` there — recreating the file Step 4 deletes. Never pass `--all`: it expands to
`--agent '*'`, targeting all 78 agents in the CLI's table and creating `~/.aider-desk/skills/`,
`~/.factory/skills/` and dozens more on a machine that uses none of them. `-a/--agent` is repeatable,
not comma-separated. The CLI also sends anonymous telemetry by default — `DISABLE_TELEMETRY=1` or
`DO_NOT_TRACK=1` opts out.

**Clone dependency.** Steps 7 and 8 fetch from GitHub and do not touch
`/Users/bossjones/dev/mattpocock/skills`. Only rung 9a makes the clone load-bearing, as the staging
source that must be re-run after each `git pull`. If Step 8 succeeds, the clone stays purely a
research artifact and can be removed freely.

**No new repo dependencies.** Nothing to `uv add`; no Python is touched. `claude` and `copilot`
(1.0.80, `/opt/homebrew/bin/copilot`) are both on `PATH`; anything routed through `npx` installs
nothing permanently.

**Recovery.** Two independent paths. From git:
`git checkout c9b0237 -- .claude/skills/<name>`. From the Trash: Step 4 moves each directory to
`~/.Trash/<name>` (all 18 basenames are distinct, so nothing overwrites anything), recoverable until
the Trash is emptied. For the ten skills renamed or deleted upstream — including all six deleted in
Step 3 — `c9b0237` is the *only* durable source; upstream no longer carries those paths.
