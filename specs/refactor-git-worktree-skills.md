# Plan: Refactor git-worktree skills (language-agnostic, script-backed, TDD)

## Context

`plugins/boss-dev/agent-harness/` ships four worktree skills — `git-worktree`, `git-worktree-clean`, `git-worktree-remove`, `git-worktree-status` — as prose-only `SKILL.md` files (no scripts, no references). They bake in JavaScript/TypeScript assumptions (`node_modules` symlinking, `npx tsc --noEmit`, `npx vitest run --reporter=json`, pnpm/yarn lockfile detection) and create worktrees in `.worktrees/` or `worktrees/`. This conflicts with how the repo actually works (Python + `uv`) and with the official Claude Code worktree convention, which puts worktrees in `.claude/worktrees/<value>/`.

This refactor: (1) gives each skill a tested PEP 723 Python script (`uv run`, TDD) that owns the deterministic logic; (2) makes the skill bodies language-agnostic and moves language-specific setup into per-language `references/` loaded via progressive disclosure, with first-class Python/`uv` support; (3) aligns worktree placement with `.claude/worktrees/<repo>-<name>/` (repo prefix from `.git/config`) on branch `worktree-<name>`; and (4) adds a new `worktree-doctor` skill that analyzes the repo and suggests `.worktreeinclude` contents.

**Consult these docs when unsure or when implementing the corresponding behavior:**
- Skills authoring & progressive disclosure: https://code.claude.com/docs/en/skills
- Worktrees (`.claude/worktrees/`, `.worktreeinclude`, cleanup, base ref): https://code.claude.com/docs/en/worktrees
- Hooks (`WorktreeCreate`/`WorktreeRemove`, non-git VCS): https://code.claude.com/docs/en/hooks
- Worktree settings (`worktree.baseRef` = `"fresh"`/`"head"`, `cleanupPeriodDays`): https://code.claude.com/docs/en/settings#worktree-settings
- Worktree isolation definition: https://code.claude.com/docs/en/glossary#worktree-isolation
- Permission modes (`acceptEdits`/`auto`/`dontAsk`/`bypassPermissions`, `--permission-mode`, `defaultMode`, protected paths): https://code.claude.com/docs/en/permission-modes
- Security (trust verification, `-p` skipping it): https://code.claude.com/docs/en/security
- Non-interactive / headless runs (`-p`): https://code.claude.com/docs/en/headless

### Key doc facts driving the design
- `claude --worktree <value>` creates `.claude/worktrees/<value>/` on branch `worktree-<value>`. The skills replicate this layout but prefix `<value>` with the repo name.
- `.worktreeinclude` uses `.gitignore` syntax; only files that are **both** matched and gitignored are copied. **Crucially, `.worktreeinclude` is processed only by Claude's native `--worktree`/`EnterWorktree`/subagent worktrees — a manual `git worktree add` does NOT process it.** Therefore `git_worktree.py` must replicate this copy step itself.
- Tip from docs: add `.claude/worktrees/` to `.gitignore`. (Repo `.gitignore` already contains `.worktrees/`, `.claude/worktrees/`, `.git/worktrees/` — verify, no change expected.)
- Keep `SKILL.md` under 500 lines; reference supporting files with relative links; invoke scripts via `uv run "${CLAUDE_SKILL_DIR}/scripts/<name>.py"`.
- **`.claude/worktrees` is exempt from protected paths.** The protected-paths list blocks auto-approved writes to `.claude` *except* `.claude/worktrees` ("where Claude stores its own git worktrees"). So creating/copying into `.claude/worktrees/<repo>-<name>/` does **not** trip protected-path prompts — the chosen layout is friction-free for autonomous runs.
- **`.envrc` IS a protected file.** Copying `.envrc` into a worktree (the `.worktreeinclude` step) is auto-approved only under `auto` (routed to the classifier) or `bypassPermissions`; in `default`/`acceptEdits` it still prompts. `.env`/`.env.local` are not protected. The script should not assume the `.envrc` copy is silent.
- **Never read `.env`/`.envrc` contents.** The script copies these files as-is but must not `cat`, `print`, log, or otherwise surface their contents — they contain secrets. Claude itself must not read them either: do not pass their paths to `Read` or display them in reports.
- **Trust + interactivity.** First-time `claude --worktree` interactively requires accepting the workspace trust dialog once at the repo root (saved per-directory to disk; home-dir trust is session-only and not persistable). `claude -p` (non-interactive) skips the trust check entirely. There is no settings key to pre-seed trust — `-p` is the supported headless escape hatch.

## Objective

When complete: each of the four worktree skills has a tested PEP 723 script under `scripts/`, the skill bodies are language-agnostic with per-language reference docs (Python via `uv` first-class), worktrees are created under `.claude/worktrees/<repo>-<name>/` on branch `worktree-<name>`, a new `worktree-doctor` skill suggests `.worktreeinclude` contents, all tests pass, `make lint` is clean, and the `agent-harness` plugin version is bumped.

## Problem Statement

The skills are unusable as-is for a Python/`uv` repo and diverge from the official worktree convention. Their logic lives entirely in prose, so it is untestable, non-deterministic, and tightly coupled to a JS/TS toolchain. There is no mechanism to discover which local files should follow a worktree, and manual `git worktree add` silently drops `.env`/`.envrc`.

## Solution Approach

Split each skill into three layers:
1. **Deterministic core** → a PEP 723 Python script (`scripts/<skill>.py`) with pure, unit-tested functions (repo-name parsing, branch/dir naming, `.worktreeinclude` matching, `git worktree list --porcelain` parsing, merge classification) plus thin IO wrappers around `git`, file copies, and `direnv`.
2. **Agent reasoning** → a lean, language-agnostic `SKILL.md` that calls the script and decides language-specific setup by reading a reference file.
3. **Knowledge** → `references/setup-{python,node,rust,go,generic}.md`, `references/worktreeinclude.md`, `references/database-branching.md`, loaded on demand (progressive disclosure).

Follow existing repo conventions exactly: PEP 723 header `#!/usr/bin/env -S uv run` + `# /// script` block (`requires-python = ">=3.13"`); script filenames use underscores (e.g. `git_worktree.py`) to stay importable, matching `fetch_diff.py`; tests in `scripts/tests/` with a `conftest.py` that inserts the sibling `scripts/` dir on `sys.path`; full type hints; `from __future__ import annotations`; `pathlib.Path`; `rich` for CLI output.

## Relevant Files

Existing skills to rewrite (each currently a single `SKILL.md`):
- `plugins/boss-dev/agent-harness/skills/git-worktree/SKILL.md`
- `plugins/boss-dev/agent-harness/skills/git-worktree-clean/SKILL.md`
- `plugins/boss-dev/agent-harness/skills/git-worktree-remove/SKILL.md`
- `plugins/boss-dev/agent-harness/skills/git-worktree-status/SKILL.md`

Pattern references to copy from:
- `plugins/boss-dev/agent-harness/skills/fetch-diff/scripts/fetch_diff.py` — PEP 723 header + pure-function/IO split
- `plugins/boss-dev/agent-harness/skills/fetch-diff/scripts/tests/conftest.py` + `test_fetch_diff.py` — TDD/import pattern
- `plugins/boss-dev/agent-harness/skills/stop-slop/SKILL.md` + its `references/` — inline progressive-disclosure linking
- `plugins/boss-dev/agent-harness/skills/release-notes-generator/` — `references/` + `assets/` + "Reference Files" section

Config to wire up:
- `devtools/lint.py` — add the 5 new scripts to `TYPE_CHECK_PATHS` (`SRC_PATHS` already includes `plugins`)
- `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json` — version `0.6.1` → `0.7.0`
- `.claude-plugin/marketplace.json` — `agent-harness` entry version `0.6.1` → `0.7.0`
- `.gitignore` — verify `.claude/worktrees/` present (already is; no change expected)
- `pyproject.toml` — no change needed (`testpaths` already includes `plugins`, `--import-mode=importlib` set, ruff `per-file-ignores` already broadly covers `plugins/boss-dev/agent-harness/**`); `pyrightconfig.json` already excludes `plugins/**/scripts/tests/**`

### New Files

`git-worktree/` skill:
- `scripts/git_worktree.py`
- `scripts/tests/conftest.py`, `scripts/tests/test_git_worktree.py`
- `references/setup-python.md`, `setup-node.md`, `setup-rust.md`, `setup-go.md`, `setup-generic.md`
- `references/worktreeinclude.md`, `references/database-branching.md`

`git-worktree-clean/`, `git-worktree-remove/`, `git-worktree-status/` skills (each):
- `scripts/<name>.py` (`git_worktree_clean.py`, `git_worktree_remove.py`, `git_worktree_status.py`)
- `scripts/tests/conftest.py`, `scripts/tests/test_<name>.py`

New `worktree-doctor/` skill:
- `SKILL.md`
- `scripts/worktree_doctor.py`
- `scripts/tests/conftest.py`, `scripts/tests/test_worktree_doctor.py`
- `references/worktreeinclude-patterns.md`

## Implementation Phases

### Phase 1: Foundation
Establish the shared naming/path conventions and the script+test scaffold (one skill end-to-end as the template), so the remaining skills follow a proven shape.

### Phase 2: Core Implementation
Implement and test all five scripts (TDD), rewrite the four skill bodies to be language-agnostic, author the reference files, and build the new `worktree-doctor` skill.

### Phase 3: Integration & Polish
Wire linting/type-checking, bump the plugin version, run full validation (lint, tests, skill validation, manual `uv run` smoke tests), and confirm worktree creation end-to-end.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### 1. Define shared conventions (write once, reuse in every script)
- Worktree directory name: `<repo>-<name>` where `<repo>` is derived from `.git/config` `[remote "origin"] url` basename (strip trailing `.git`), falling back to `basename(git rev-parse --show-toplevel)`. Do not double-prefix if `<name>` already starts with `<repo>-`.
- Worktree path: `<repo_root>/.claude/worktrees/<repo>-<name>/`.
- Branch name: `worktree-<name>`.
- Protected branches constant: `main master develop staging production`.
- Base ref: branch from `origin/HEAD` when available, else local `HEAD` (mirror the doc's `worktree.baseRef` "fresh" default; mention `head` override).

### 2. Build `git-worktree` script (TDD) — the template skill
- Write `scripts/tests/conftest.py` (copy the `fetch-diff` pattern: insert sibling `scripts/` on `sys.path`).
- Write failing tests in `scripts/tests/test_git_worktree.py` for the pure functions first:
  - `derive_repo_name(git_config_text, toplevel)` — origin URL basename, `.git` stripped, ssh + https forms, fallback to toplevel name.
  - `build_worktree_dirname(repo, name)` — prefixes `repo-`, no double-prefix.
  - `build_branch_name(name)` → `worktree-<name>`.
  - `validate_name(name)` — allowed charset `^[a-zA-Z0-9/_-]+$`, rejects empty/invalid.
  - `gitignore_has_worktrees(gitignore_text)` — detects `.claude/worktrees/`.
  - `parse_worktreeinclude(text)` — strips comments/blanks, returns patterns.
  - `match_worktreeinclude(patterns, gitignored_files)` — returns files both matched (`.gitignore` glob semantics, e.g. `fnmatch`/`pathspec`) and gitignored.
- Implement `scripts/git_worktree.py` to pass tests. PEP 723 header; pure functions above + thin IO layer:
  - ensure `.claude/worktrees/` in `.gitignore` (suggest/append + report);
  - `git worktree add <path> -b worktree-<name>` from the base ref;
  - replicate `.worktreeinclude`: copy matched gitignored files into the worktree (this is the step native `git worktree add` skips);
  - if `.envrc` was copied, run `direnv allow <worktree>` (guard if `direnv` absent). Note `.envrc` is a Claude protected path: under `default`/`acceptEdits` the copy/write prompts, so the report should call out when an `.envrc` copy was skipped/declined rather than failing silently;
  - print a final report (path, branch, copied files, next-step pointer to language setup reference, and the headless invocation hint from "Running unattended").
- Keep all language/dependency setup OUT of the script — it prints which `references/setup-<lang>.md` to follow.

### 3. Author `git-worktree` references (progressive disclosure)
- `references/setup-python.md` — `uv sync --all-extras` for isolation; copy `.env`/`.envrc` then `direnv allow .`; background verify with `uv run pytest` + `basedpyright`/`ty`. **(First-class, matches this repo.)**
- `references/setup-node.md` — lockfile-detected `npm`/`pnpm`/`yarn install` (preserve prior behavior incl. optional `node_modules` symlink with `--isolated` escape hatch); `tsc --noEmit`; `vitest`.
- `references/setup-rust.md` — `cargo build`/`cargo test`.
- `references/setup-go.md` — `go mod download`; `go build`/`go test`.
- `references/setup-generic.md` — unknown project: copy env files, no dependency assumptions.
- `references/worktreeinclude.md` — what `.worktreeinclude` is, `.gitignore` syntax, why manual worktrees need the script's copy step, common entries (`.env`, `.env.local`, `.envrc`, `**/.claude/settings.local.json`). Link to https://code.claude.com/docs/en/worktrees.
- `references/database-branching.md` — optional Neon/PlanetScale/Postgres branch suggestions (moved out of the body; loaded only if a provider is detected).
- Follow `.claude/rules/skill-development.md`; **never use `` !`...` `` patterns in any `SKILL.md`** (GitHub #12781) — use `$ command` notation; code examples that must show `!` live in reference files.

### 4. Rewrite `git-worktree/SKILL.md` (language-agnostic, <500 lines)
- Keep frontmatter shape (`name`, `description` with concrete "Use when…", `argument-hint: "<name> [--from <base>]"`, `effort: medium`, `disable-model-invocation: true`).
- Body: invoke `uv run "${CLAUDE_SKILL_DIR}/scripts/git_worktree.py" <name> [--from <base>]`; then detect project type and read the matching `references/setup-<lang>.md`; link DB branching + worktreeinclude references; keep the companion-skill cross-links.

### 5. Build `git-worktree-status` script + references + SKILL.md (TDD)
- Pure functions: `in_worktree(git_common_dir)`; `parse_log_status(log_text)` → generic `PASS`/`FAIL`/`RUNNING`/`NOT_RUN` from `.worktree-logs/*.log` using language-neutral markers; report formatter.
- Language-specific log/verify commands live in the `git-worktree` `references/setup-<lang>.md`; status SKILL.md links to them via `../git-worktree/references/...`.
- Rewrite `SKILL.md` to call the script.

### 6. Build `git-worktree-clean` script + SKILL.md (TDD)
- Pure functions: `parse_worktree_list_porcelain(text)` → list of `{path, branch, head}`; `classify_worktree(branch, is_merged, protected)` → `merged|unmerged|protected`; report formatter; disk-usage helper that is language-neutral (no hardcoded `node_modules` exclude — derive ignored dirs generically or document the exclude in references).
- IO: `git worktree list --porcelain`, `git merge-base --is-ancestor`, `git worktree remove`, branch deletion, `git worktree prune`. Honor `--dry-run`, `--all`, `--force`.
- Rewrite `SKILL.md`.

### 7. Build `git-worktree-remove` script + SKILL.md (TDD)
- Pure functions: `resolve_target(name_or_path, worktrees)`; `is_protected(branch, protected)`; `deletion_flag(merged)` → `-d`/`-D`.
- IO: safety checks (protected branch block, uncommitted-changes warning via `git status --porcelain`, merge-status check), `git worktree remove [--force]`, local/remote branch deletion (confirmed), `git worktree prune`. Honor `--force`, `--keep-branch`, `--keep-remote`.
- Rewrite `SKILL.md`.

### 8. Create `worktree-doctor` skill (TDD)
- New skill dir `plugins/boss-dev/agent-harness/skills/worktree-doctor/`.
- `scripts/worktree_doctor.py` pure functions: `scan_gitignored_candidates(gitignored_files, candidate_patterns)` (env/secret/local-config patterns: `.env*`, `.envrc`, `*.local`, `secrets*`, etc.); `detect_project_types(repo_files)` (`pyproject.toml`→python, `package.json`→node, `Cargo.toml`→rust, `go.mod`→go); `build_worktreeinclude_suggestion(candidates)`; reuse `gitignore_has_worktrees`.
- Behavior: analyze repo, print a suggested `.worktreeinclude` and whether `.claude/worktrees/` is gitignored; **suggest by default**, with an opt-in `--write` flag to create the file.
- `references/worktreeinclude-patterns.md` — catalog of candidate patterns + rationale.
- `SKILL.md` — concrete triggers ("when setting up worktrees in a new repo", "before first `/git-worktree`"), invokes the script, model-invocable (omit `disable-model-invocation` or set false so Claude can suggest it).
- Tests in `scripts/tests/`.

### 9. Wire linting & type-checking
- Add to `devtools/lint.py` `TYPE_CHECK_PATHS`: `git-worktree/scripts/git_worktree.py`, `git-worktree-clean/scripts/git_worktree_clean.py`, `git-worktree-remove/scripts/git_worktree_remove.py`, `git-worktree-status/scripts/git_worktree_status.py`, `worktree-doctor/scripts/worktree_doctor.py` (using the `_AGENT_HARNESS_SKILLS` prefix).
- Confirm `pyrightconfig.json` already excludes `plugins/**/scripts/tests/**` (it does) and ruff `per-file-ignores` covers `plugins/boss-dev/agent-harness/**` (it does).

### 10. Version bump
- Use the `version-bump-reviewer` skill conventions. New skill + new feature-bearing scripts = **minor** bump: `0.6.1` → `0.7.0` in both `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json` and the `agent-harness` entry of `.claude-plugin/marketplace.json` (keep them in parity).

### 11. Validate (final step)
- Run `make lint`, `make test`, the skill validator, and manual `uv run` smoke tests; create a real worktree end-to-end and confirm placement/branch/.env copy. See Validation Commands.

## Testing Strategy

- **TDD per script**: write `scripts/tests/test_<name>.py` first, watch it fail, then implement. Cover pure functions thoroughly (repo-name parsing incl. ssh/https/`.git`; no-double-prefix; `.worktreeinclude` match incl. "matched but not gitignored ⇒ skip"; porcelain parsing incl. main-worktree skip + detached head; merge classification incl. protected branches; status log parsing for each state).
- **Import pattern**: each `conftest.py` inserts the sibling `scripts/` dir on `sys.path` (copy `fetch-diff`); tests import the script module directly. `pyproject.toml` already sets `--import-mode=importlib` and `testpaths=["tests","plugins"]`.
- **IO isolation**: keep `git`/filesystem/`direnv` side effects in thin wrappers; unit-test pure logic with fixture strings (sample `.git/config`, `git worktree list --porcelain` output, `.worktreeinclude`, `.gitignore`). Use `tmp_path` for the few filesystem-copy tests.
- **Edge cases**: no remote configured (repo-name fallback); name already repo-prefixed; missing `.worktreeinclude`; `direnv` not installed; protected/unmerged branch removal; running from main repo vs inside a worktree (status); repo with multiple project types (doctor).

## Acceptance Criteria

- Each of the four existing skills has `scripts/<name>.py` (PEP 723, `uv run`) plus `scripts/tests/` with passing tests written test-first.
- New `worktree-doctor` skill exists with script + tests + reference and suggests a `.worktreeinclude`.
- Worktrees are created at `.claude/worktrees/<repo>-<name>/` (repo prefix from `.git/config`, no double-prefix) on branch `worktree-<name>`; `.worktreeinclude`-matched gitignored files are copied; `.envrc` triggers `direnv allow`.
- Skill bodies contain no language-specific commands inline; language setup (Python/uv first-class, plus Node/Rust/Go/generic) lives in `references/` and is referenced for on-demand loading; every `SKILL.md` is under 500 lines and uses `$ command` notation (no `` !`...` ``).
- `.claude/worktrees/` confirmed in `.gitignore`; skills suggest adding it when absent.
- `make lint` passes (new scripts in `TYPE_CHECK_PATHS`); `make test` passes; skill validator reports no progressive-disclosure warning for these skills.
- `agent-harness` version is `0.7.0` in both `plugin.json` and `marketplace.json`.

## Validation Commands
Execute these to validate the task is complete:

- `make lint` — codespell + ruff (fix/format) + basedpyright on the new scripts must pass clean.
- `make test` — full pytest suite passes.
- `uv run pytest -s plugins/boss-dev/agent-harness/skills/git-worktree/scripts/tests/` — worktree script tests (repeat per skill dir).
- `uv run python scripts/skill_validation.py` (or `make` target if defined) — confirm no SKILL.md violations / progressive-disclosure warnings for the refactored skills.
- `uv run "plugins/boss-dev/agent-harness/skills/worktree-doctor/scripts/worktree_doctor.py"` — prints a sane `.worktreeinclude` suggestion for this repo.
- `uv run "plugins/boss-dev/agent-harness/skills/git-worktree/scripts/git_worktree.py" doctor-smoke-test` then `git worktree list` — confirm `.claude/worktrees/boss-skills-doctor-smoke-test/` on branch `worktree-doctor-smoke-test`; if a `.worktreeinclude` and matching gitignored files exist, confirm they are copied; then `git worktree remove` to clean up.
- `python -m py_compile` is implicit via `uv run`; ensure each script runs `--help` without error.

## Running Unattended (headless / autonomous agents)

When a worktree is driven by an autonomous agent (CI, background session, or `claude -p`), two interactive gates must be cleared. They are independent — clearing one does not clear the other.

1. **Workspace trust dialog** (first-time `--worktree` in a directory):
   - Headless: `claude -p --worktree <name> "<task>"` skips the trust check entirely.
   - Interactive: run `claude` once at the repo root and accept trust; it is saved per-directory, so later `--worktree` calls reuse it. (Starting in `$HOME` is session-only and cannot be persisted — start from a project subdir.)
2. **Permission prompts** (edits / commands) — set a looser mode at startup or as a default:
   - One-off, fully unattended (isolated container/VM only): `claude -p --permission-mode bypassPermissions "<task>"` (or the equivalent `--dangerously-skip-permissions`). Refuses to start under root/sudo outside a recognized sandbox; offers no prompt-injection protection.
   - Locked-down CI: `claude -p --permission-mode dontAsk "<task>"` — only `permissions.allow` rules and read-only Bash run; everything else is auto-denied.
   - Background-checked autonomy: `--permission-mode auto` (needs Opus 4.6+/Sonnet 4.6+; `defaultMode: "auto"` must live in `~/.claude/settings.json`, not project/local settings).
   - Persisted default: `{ "permissions": { "defaultMode": "acceptEdits" } }` in `.claude/settings.json`.

Implications for these skills:
- The `git-worktree` skill should surface the headless recipe in its report/docs so users can re-enter the worktree non-interactively (e.g. `claude -p --permission-mode acceptEdits` from inside the new worktree).
- Because `.claude/worktrees` is exempt from protected paths, worktree creation/copy under that path runs cleanly even in `default` mode — except the `.envrc` copy, which is a protected file and only silent under `auto`/`bypassPermissions` (see Key doc facts).
- For a worktree-spawning **subagent** (`isolation: worktree`) there is no separate trust dialog, and a `permissionMode` in subagent frontmatter is **ignored** when the parent session runs in `auto` mode.

## Notes

- Script filenames use underscores (`git_worktree.py`) while skill directories stay hyphenated (`git-worktree/`) — required for Python importability and matches the existing `fetch_diff.py` convention. The user's "same name as the skill" intent is preserved modulo this necessary substitution.
- `.worktreeinclude` copying must be done by the script because manual `git worktree add` does not process it (only Claude's native `--worktree`/`EnterWorktree`/subagent worktrees do). This is the central reason the script exists rather than deferring to native worktree creation.
- Possible future enhancement (out of scope unless requested): a `WorktreeCreate`/`WorktreeRemove` hook (https://code.claude.com/docs/en/hooks) so Claude's native `--worktree` flag also applies the repo-prefix convention.
- For `.worktreeinclude` glob matching, prefer `pathspec` (gitignore-accurate) or stdlib `fnmatch` if avoiding a dependency; add via PEP 723 `dependencies` if used.
- If unsure about any worktree behavior, naming, base ref, or `.worktreeinclude` semantics during implementation, re-read the doc URLs listed in **Context**.

### As-built deviations from this plan

- **`pathspec` added to `pyproject.toml` dev deps (deviates from "no pyproject change").** `git_worktree.py` uses `pathspec` (chosen over stdlib `fnmatch` for gitignore-accurate `.worktreeinclude` matching). The scripts declare it via PEP 723 for standalone `uv run`, but the **tests import the script module** and **basedpyright must resolve the import**, so `pathspec>=0.12.1` was added to the `[dependency-groups] dev` list. This is a test/type-check-time need (the `boss-skills` package itself never imports `pathspec`), so `dev` is the correct home rather than `[project] dependencies`.
- **Version bumped `0.7.0` → `0.8.0`, not `0.6.1` → `0.7.0`.** `0.7.0` was already published by the unrelated `unicode-hygiene` work before this refactor began, so this minor bump (new skill + new feature-bearing scripts) targets `0.8.0` in both `plugin.json` and `marketplace.json`.
