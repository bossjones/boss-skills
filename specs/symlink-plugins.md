# Plan: Symlink plugin components into `.claude/` for local dogfooding

## Context

`boss-skills` ships Claude Code plugins to a public marketplace from `plugins/<category>/<plugin>/`.
Today the repo's own dev environment (`.claude/skills`, `.claude/commands`, `.claude/agents`, …)
holds **separate copies** of much of that content — e.g. `.claude/commands/build.md` and
`plugins/boss-dev/agent-harness/commands/build.md` both exist. Two copies drift. When they drift,
the version you test locally is not the version marketplace users install, so breakage (bad paths,
missing files, the SKILL.md backtick parser bug) is discovered by *users*, not by us.

`/Users/bossjones/dev/obsidian-wiki` solves the equivalent problem with a single source of truth
(`.skills/`) that every agent dir symlinks into. We replicate that pattern here, with `plugins/` as
the source of truth: `.claude/*` becomes **relative symlinks pointing into `plugins/`**, so working
in this repo dogfoods the exact bytes that ship. The intended outcome is a `make symlink-plugins`
task (with backup + restore) that makes local `.claude/` an always-in-sync mirror of the plugins —
a pre-marketplace smoke test.

## Task Description

Add a Python script (`scripts/symlink_plugins.py`) and Make targets that:

1. Back up any real (non-symlink) file/dir in `.claude/` that is about to be replaced.
2. Create **relative** symlinks in `.claude/` pointing into matching components under `plugins/`.
3. Leave `.claude/` items that have **no** plugin counterpart untouched.
4. Support dry-run/verify and a clean restore (`make unlink-plugins`).

## Objective

`make symlink-plugins` makes `.claude/{skills,commands,agents,hooks,output-styles,status_lines}`
mirror the corresponding `plugins/*/*/` components via relative symlinks, with originals safely
backed up; `make symlink-plugins-check` verifies the mirror (and flags broken links / drift) without
mutating anything; `make unlink-plugins` restores the pre-symlink state exactly.

## Problem Statement

Content duplicated between `.claude/` and `plugins/` drifts silently. There is no local mechanism to
exercise the shipped plugin content the way an installing user would, so regressions reach the
marketplace before they're caught.

## Solution Approach

- **Source of truth = `plugins/`.** Discover local plugin roots by globbing
  `plugins/*/*/.claude-plugin/plugin.json` (external `git-subdir` plugins like `github-pr-review`
  have no local dir and are simply absent — fine).
- For each plugin, walk its component dirs and create relative symlinks under the matching
  `.claude/<component>/` target, mirroring obsidian-wiki's `setup.sh`/`cli.py` logic
  (`Path.symlink_to`, relative target via `os.path.relpath`).
- **Per-component granularity** (this is the key design decision):
  - `skills/` → symlink each **immediate subdirectory** (`<skill>/` is atomic; validated by `SKILL.md`).
  - `commands/`, `agents/`, `output-styles/`, `status_lines/`, `hooks/` → symlink each **leaf file**,
    recreating intermediate directories as real dirs in the target (handles nested `agents/team/…`,
    `hooks/validators/…`). File-level granularity is required because `.claude/commands` is one shared
    namespace fed by many plugins.
- **Backup before replace:** any existing *real* target that has a matching source is moved into a
  timestamped backup dir and recorded in a manifest before the symlink is created. Orphans (no source)
  are never touched (per decision).
- **Idempotent:** a target that is already the correct symlink is skipped (no backup churn); a symlink
  pointing elsewhere is repointed; a real item is backed-up-then-replaced.
- **Collisions across plugins** (two plugins expose the same leaf name) → **warn and skip the second**,
  logging the loser explicitly (no silent drops — repo norm).

## Relevant Files

Use these files to complete the task:

- `Makefile` — add `symlink-plugins`, `symlink-plugins-check`, `unlink-plugins` targets alongside the
  existing `test-plugins` / `verify-structure` plugin group (same section, same `uv run` style).
- `.claude-plugin/marketplace.json` — reference only, to sanity-check which plugins are local vs
  external `git-subdir`; discovery is filesystem-driven, not marketplace-driven.
- `plugins/*/*/.claude-plugin/plugin.json` — presence marks a valid local plugin root.
- `scripts/verify-structure.py`, `scripts/eval-skills.py` — existing `scripts/` conventions
  (argparse CLI, `rich` output, PEP 723 / `uv run` invocation) to match.
- `devtools/lint.py` — confirms `scripts/` is linted (ruff + basedpyright); new script must pass clean.
- `.gitignore` — add the backup dir; decide symlink-commit policy (see Notes).
- `/Users/bossjones/dev/obsidian-wiki/setup.sh` & `obsidian_wiki/cli.py` — reference implementation
  for symlink/backup/skip logic and relative-path calculation.

### New Files

- `scripts/symlink_plugins.py` — the sync engine (discover → plan → backup → symlink → verify → restore).
- `tests/test_symlink_plugins.py` — pytest coverage over a synthetic `plugins/` + `.claude/` tmp layout.

## CLI / Make interface

```
scripts/symlink_plugins.py [--check] [--restore] [--copy]
                           [--components skills,commands,agents,hooks,output-styles,status_lines]
                           [--repo-root PATH] [--yes]
```

- `--check` — dry run: print the plan (create / repoint / skip / conflict / orphan-left) and verify
  existing links resolve; **exit non-zero** if any managed symlink is broken or drift is detected.
  CI- and pre-commit-friendly.
- `--restore` — read the latest backup manifest, remove created symlinks, move originals back.
- `--copy` — fallback for symlink-hostile filesystems (`shutil.copytree`/`copy2` instead of symlink),
  mirroring obsidian-wiki's copy mode.
- `--components` — subset (default: all six). Lets a user skip the riskier `hooks` sync.

Make targets (thin wrappers, matching repo style):

```make
symlink-plugins:        ## Back up .claude/ originals and symlink plugin components in
	uv run python scripts/symlink_plugins.py

symlink-plugins-check:  ## Dry-run + verify links (no changes); used by CI/pre-commit
	uv run python scripts/symlink_plugins.py --check

unlink-plugins:         ## Restore .claude/ from the latest backup manifest
	uv run python scripts/symlink_plugins.py --restore
```

## Backup & restore model

- Backup root: `.backups/symlink-plugins/<UTC-timestamp>/` at repo root (gitignored).
- Preserve the target's repo-relative path inside the backup (`.backups/…/.claude/commands/build.md`)
  so restore is an unambiguous move-back.
- Manifest `manifest.json` in each backup dir: list of `{target, action, backup_path?, source}`
  entries. `--restore` consumes the **latest** manifest: delete each created symlink, move each backed-up
  original back to `target`. A pointer file `.backups/symlink-plugins/latest` records the newest run.
- Restore is idempotent: missing symlink → skip; target already restored → skip.

## Implementation Phases

### Phase 1: Foundation
- Discovery + planning core: enumerate plugin roots, build the per-component action list
  (create / repoint / skip / conflict / orphan), with **no filesystem mutation**. This is what
  `--check` prints. Pure and unit-testable.

### Phase 2: Core Implementation
- Mutating executor: timestamped backup dir + manifest, relative-symlink creation via
  `os.path.relpath` + `Path.symlink_to`, idempotency handling, `--copy` mode.
- `--restore` reading the manifest.

### Phase 3: Integration & Polish
- Make targets, `.gitignore` entry, `rich` output (created/backed-up/skipped/conflict counts),
  post-run verification (skills resolve to a real `SKILL.md`; every leaf link resolves), pytest suite,
  `make lint` clean. Optionally wire `symlink-plugins-check` into `ci` / pre-commit as a drift gate.

## Step by Step Tasks

IMPORTANT: Execute every step in order, top to bottom.

### 1. Persist the spec
- Write this document to `specs/symlink-plugins.md`. (done)

### 2. Discovery + planning core (no mutation)
- In `scripts/symlink_plugins.py`, add `discover_plugins(repo_root)` globbing
  `plugins/*/*/.claude-plugin/plugin.json`.
- Add `plan_actions(plugins, components)` returning a typed list of actions per component using the
  granularity rules above (skills = dir-level; others = leaf-file-level with intermediate real dirs).
- Compute the relative link target with `os.path.relpath(source, target.parent)`.
- Classify each candidate: `create` (no target), `skip` (already correct symlink),
  `repoint` (symlink to wrong place), `backup+replace` (real item, has source),
  `conflict` (second plugin claims a name already taken — skip, warn),
  `orphan-left` (target exists, no source — untouched, informational only).

### 3. Dry-run / verify (`--check`)
- Print the planned actions grouped by component with counts.
- Verify existing managed symlinks resolve (skills → `SKILL.md` exists; leaves → target exists).
- Exit non-zero on any broken link or pending drift.

### 4. Backup + symlink executor
- Create `.backups/symlink-plugins/<timestamp>/`, write `manifest.json`, update `latest` pointer.
- For `backup+replace`: move original into backup (preserving relative path), then symlink.
- For `create`/`repoint`: (remove stale symlink if present), create relative symlink;
  `--copy` copies instead.
- Recreate intermediate target dirs as real directories as needed.
- Post-run verification pass; fail loudly (non-zero) on any broken result.

### 5. Restore (`--restore`)
- Read latest manifest; remove created symlinks; move backups back to their targets; idempotent.

### 6. Make targets + gitignore
- Add the three targets to `Makefile` (plugin-testing section) with `##` help text.
- Add `.backups/` to `.gitignore`.

### 7. Tests
- `tests/test_symlink_plugins.py` with a synthetic `plugins/` + `.claude/` under `tmp_path`.

### 8. Validate
- Run the validation commands below; ensure `make lint` and the new tests pass, and a real
  `make symlink-plugins` → `make symlink-plugins-check` → `make unlink-plugins` round-trips cleanly
  with `git status` clean afterward.

## Testing Strategy

Load the script per repo convention (importlib, or subprocess for CLI exit-code assertions). Cover:

- **Skill dir symlink** created and resolves to a real `SKILL.md`; link is relative.
- **Command/agent leaf-file** symlinks created; nested `agents/team/x.md` recreates the intermediate
  dir and symlinks the leaf.
- **Orphan untouched:** a `.claude/skills/<core-only>` with no source is neither moved nor linked.
- **Backup+replace:** a real `.claude/commands/build.md` is moved into the backup and replaced by a
  symlink; manifest records it.
- **Idempotency:** second run creates zero new backups and reports all `skip`.
- **Collision:** two synthetic plugins exposing the same command name → one linked, other logged as
  conflict; no crash.
- **`--check`** exits non-zero when a managed symlink is broken; zero when the mirror is consistent.
- **`--restore`** returns the tree bit-for-bit to its pre-run state.
- **`--copy`** produces real copies, not symlinks.

## Risks & Gotchas

- **Double-registration:** agent-harness skills already load via `enabledPlugins` (marketplace path).
  Also symlinking them into `.claude/skills/` may surface a skill under two names
  (`agent-harness:foo` and `foo`). Document that the symlink mirror is a *testing* aid; note the
  interaction and let `--components` exclude anything that conflicts. Confirm behavior during Step 8.
- **Hooks are path-sensitive:** `.claude/hooks/*` are referenced by `settings.json`; symlinked hook
  trees must keep the same relative paths. Highest-risk component — `--components` can omit it.
- **Committing generated symlinks:** default is **transient / not committed** (create → test →
  `unlink`). `symlink-plugins-check` can act as a pre-commit gate to prevent stray symlinks from being
  staged. See Notes.

## Acceptance Criteria

- `make symlink-plugins` backs up every replaced real item and creates relative symlinks for all
  matching plugin components across the six component types.
- `.claude/` items with no plugin source are left untouched.
- `make symlink-plugins-check` reports drift/broken links and exits non-zero on problems, zero when clean.
- `make unlink-plugins` restores the exact pre-symlink state (`git status` clean).
- Re-running `make symlink-plugins` is idempotent (no new backups, all skips).
- New script passes `make lint`; `tests/test_symlink_plugins.py` passes.

## Validation Commands

- `uv run python -m py_compile scripts/symlink_plugins.py` — script compiles.
- `make lint` — ruff + basedpyright clean on the new script.
- `uv run pytest -s tests/test_symlink_plugins.py` — unit suite passes.
- `make symlink-plugins-check` — dry-run plan prints; exits 0 on a clean checkout.
- `make symlink-plugins && make symlink-plugins-check && make unlink-plugins && git status --porcelain`
  — round-trips with empty final status.
- `find .claude -type l` — lists created symlinks after a run; empty after `unlink`.

## Notes

- No new dependencies required (stdlib `pathlib`/`os`/`shutil`/`json`/`argparse`; reuse `rich` if
  present, else plain prints). If a helper lib is wanted: `uv add`.
- Discovery is filesystem-driven; external `git-subdir` plugins (e.g. `github-pr-review`) have no
  local dir and are correctly skipped.
- **Open decision — commit policy for generated symlinks:** recommend *not* committing them (keep them
  transient, gitignore the backup dir, optionally gate with `symlink-plugins-check` in pre-commit).
  The alternative — committing the symlinks so every contributor dogfoods automatically — is possible
  but risks the double-registration issue above. Flag for the user at implementation time.
