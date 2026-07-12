# Plan: Convert `.claude/` into symlinks over `plugins/` (run-symlink-sync)

## Context

`boss-skills` ships its skills/commands/agents/hooks/output-styles/status_lines from
`plugins/<category>/<plugin>/` to a marketplace, but the repo's own `.claude/` dev
environment historically kept **separate copies** of that content. Those copies drift
silently, so working in this repo no longer exercises the exact bytes marketplace users
install. `scripts/symlink_plugins.py` exists to make `plugins/` the single source of
truth by replacing the `.claude/` copies with **relative symlinks** into the matching
plugin components (real files are backed up + recorded in a restore manifest first).

Commit `48fa00b` added a `--diff` flag to that script. Running `--diff` locally surfaced
the exact content drift, and PR [#49](https://github.com/bossjones/boss-skills/pull/49)
(which introduced `--diff`) is still **open with three unresolved review comments**. This
plan (a) resolves the PR #49 feedback so the tooling is trustworthy, (b) records the
porting analysis that answers "do we lose anything by overwriting?", and (c) runs the
symlink conversion, phased by component.

## Objective

Every `.claude/{skills,commands,agents,hooks,output-styles,status_lines}` item that has a
`plugins/` source becomes a **relative symlink** into that source, with:
- PR #49's markup-crash bug and two CLAUDE.md test violations fixed first;
- the two locally-divergent files (`build.md`, active `status_line_v10.py`) handled by
  explicit, recorded overwrite decisions (both recoverable);
- a clean `--check` (exit 0, no drift/broken links) and green `pytest`/`make lint` afterward;
- full reversibility via `scripts/symlink_plugins.py --restore` and git history.

## Problem Statement

Two coupled problems:

1. **The tool isn't merge-clean.** `--diff` renders raw file content through Rich with
   `markup=True`, so any `[bracket]` in a diffed file (Markdown links, `[tool.ruff]` TOML
   headers, frontmatter) either silently distorts output or crashes the whole run with
   `rich.errors.MarkupError`. Two test helpers also violate the repo's own CLAUDE.md
   ("full type annotations", "pathlib over os.path").

2. **Overwriting `.claude/` might lose local work.** Before replacing ~44 real files with
   symlinks we must know whether any `.claude/` copy holds a fix/behavior not present in
   its `plugins/` source. The `--diff` + git-history analysis below answers this.

## Solution Approach

Fix PR #49 first (three small, mechanical edits) so `--diff` is crash-safe and the branch
can merge. Then run `symlink_plugins.py` **per component** — skills → commands → agents →
hooks → output-styles → status_lines — verifying with `--check --diff` between each phase.
The script already backs up every replaced real file to `.backups/symlink-plugins/<ts>/`
with a `manifest.json`, and `--restore` undoes the latest run; combined with git tracking
of `.claude/` (117 files), the conversion is fully reversible. No manual porting is
required (see Findings) — the two divergent files (`build.md`, `status_line_v10.py`) are
intentionally allowed to be overwritten per the user's decisions.

## Findings: drift analysis (the porting question, answered)

**Bottom line: no logic should be ported FROM `.claude/` INTO `plugins/`.** In every one of
the 44 drifted files, `plugins/` is equal-or-ahead. Two files hold a *local-only* variant
that `plugins/` intentionally omits — both are handled by "let it be overwritten" decisions
(recoverable), not ports.

Method (three independent passes, so a cosmetic touch in `plugins/` can't mask a real
`.claude/`-only feature):
1. **Content** — `COLUMNS=400 uv run scripts/symlink_plugins.py --diff` (diff direction is
   `--- .claude/` current → `+++ plugins/` source; `-` lines = `.claude/`-only content).
2. **Direction of truth** — `git log -1 --format=%ai` on each target vs its source.
3. **Feature extraction** — Python `tokenize` to canonicalize each `.py` pair (ignoring
   whitespace/quotes/line-reflow) and list identifiers + string literals present in
   `.claude/` but **absent** from `plugins/` — this is what catches genuinely dropped logic
   under ruff's multi-line→single-line reformatting.

**`plugins/` is canonical; `.claude/` is stale.**
- `.claude/hooks/*` were last touched **2026-04-28**; the `plugins/` copies were updated
  through **2026-06-09 / 2026-06-30 / 2026-07-03**. A June commit is literally titled
  *"feat(agent-harness): backport fixes + cosmetic/structural alignment (v0.4.1)"* — prior
  `.claude/` fixes were already pulled **into** `plugins/`.
- Spot-verified that the big refactors are `plugins/`-superset, not lossy:
  - `pre_tool_use.py` (139→240 lines): smarter `rm` guard (ignores `docker rm`/`git rm`/
    `--rm`) and *expanded* `.env` protection (`.envrc`, `.env.local`, `--env-file` handling).
  - `permission_request.py`: *tightened* the read-only-git allowlist (`git branch|tag` →
    bare-listing-only, so `git branch -D` isn't auto-allowed) and *added* a security block
    rejecting chained commands (`;`, `&&`, `|`, backticks, redirects).
  - `setup.py`, validators, `llm/*`, `tts/*`: pure ruff formatting + type modernization
    (`Optional`→`| None`, `IOError`→`OSError`). The shared TTS-selection helper is preserved
    in `notification/stop/subagent_start/subagent_stop.py` — only its docstring was reworded.

**Two local-only variants `plugins/` intentionally lacks (decisions, not ports):**

| File | What `.claude/` has that `plugins/` lacks | Why it's not a "port" | Decision |
|------|-------------------------------------------|-----------------------|----------|
| `.claude/commands/build.md` | A *different command*: "Build Command" (`model: opus`, `USER_PROMPT`, ty+ruff Stop hooks, free-form build) vs. plugins' "Build" (`PATH_TO_PLAN`, plan-executor, no hooks). | Same filename, different purpose — not drift of one file. | **Let it be overwritten.** `/build` becomes the plan-executor, loses its ty/ruff Stop hooks. Recoverable via git + backup + `--restore`. |
| `.claude/status_lines/status_line_v10.py` | **Adobe-discounted pricing** (`ADOBE_PRICING`, opus ≈ $4.50/$22.50). This is the **ACTIVE** status line (`settings.json:84`). Plugins ships **public list pricing** (`MODEL_PRICING`, opus $15/$75) + newer models (`opus-4-8`, `sonnet-4-6`) + clamping bug-fixes. | Porting Adobe pricing into a public marketplace plugin would leak internal pricing — wrong direction. | **Let it be overwritten.** Live cost readout switches to list prices (opus ~3.3× higher). Adobe variant recoverable via git + backup + `--restore`. |

Because **both** divergences are "overwrite," the sync runs straight through with **no
exclusions** — default `backup+replace` behavior handles them, and both originals land in
the backup `manifest.json` + git history. (If a "preserve" decision is ever wanted, the
mechanism is: run the component, then `git checkout -- <path>` or restore that one file from
the backup dir so it stays a real file — no `symlink_plugins.py` change required.)

**Command name collisions (informational, no action):** `commit-push-pr.md`, `debug-ci.md`,
and `fix-gh-pr-comments.md` are claimed by two plugins each; the script's deterministic
sort makes `plugins/boss-dev/agent-harness/…` the winner and reports the loser as
`conflict` (skipped, left untouched). Verify the intended plugin wins during Phase 2.

## Relevant Files

- `scripts/symlink_plugins.py` — the conversion tool. **Edit line 581** (`_print_diffs`)
  for the markup fix. Core entry points already in place: `plan_actions()`, `execute()`,
  `check()`, `restore()`, `diff_action()`.
- `tests/test_symlink_plugins.py` — **edit `_action_for` at line 364** (add return type)
  and **line 388** (swap `os.path.relpath` for pathlib); note line 92 also uses `os.path`.
- `.claude/` (117 git-tracked files) — the conversion target. Everything with a `plugins/`
  source becomes a symlink; orphans (no source) are left untouched.
- `plugins/*/*/.claude-plugin/plugin.json` — discovered plugin roots (source of truth).
- `.backups/symlink-plugins/<ts>/manifest.json` — generated backup + restore ledger.
- `CLAUDE.md` §Code Standards — the type-annotation / pathlib rules PR #49 flagged.

## Implementation Phases

### Phase 1: Foundation — resolve PR #49 feedback
Make `--diff` crash-safe and the branch merge-clean before relying on it.

### Phase 2: Core Implementation — phased symlink conversion
Run `symlink_plugins.py` per component, verifying between each.

### Phase 3: Integration & Polish — verify, commit, document
Final `--check` clean, tests green, commit, note the behavior changes.

## Step by Step Tasks

IMPORTANT: Execute every step in order, top to bottom. All work stays in the current
worktree (`adguard-home-ha-dns-spec-c455c8`).

### 1. Save this spec
- Write this document to `specs/run-symlink-sync.md` (the requested deliverable).

### 2. Fix PR #49 issue 1 — Rich markup crash (`scripts/symlink_plugins.py:581`)
- In `_print_diffs`, change `console.print(line, end="")` to
  `console.print(line, end="", markup=False, highlight=False)`.
- This makes raw diff content (brackets, TOML headers, frontmatter) render literally
  instead of being parsed as Rich markup.

### 3. Fix PR #49 issue 2 — missing return type (`tests/test_symlink_plugins.py:364`)
- Annotate `_action_for(...)` with its return type: `-> sp.Action`
  (e.g. `def _action_for(repo: Path, components: tuple[str, ...], kind: str) -> sp.Action:`).

### 4. Fix PR #49 issue 3 — `os.path` → pathlib (`tests/test_symlink_plugins.py:388`)
- Replace `os.path.relpath(other, start=link.parent)` with a pathlib approach:
  use `other.relative_to(link.parent, walk_up=True)` (Python 3.13 target per the script's
  `requires-python`).
- Also address the sibling `os.path.isabs` usage at line 92 (`Path(link).is_absolute()`)
  and drop `import os` if it becomes unused, to fully satisfy the CLAUDE.md rule.

### 5. Validate the tooling before using it
- `uv run python -m py_compile scripts/symlink_plugins.py`
- `make lint` (0 errors on the two edited files)
- `uv run pytest -s tests/test_symlink_plugins.py` (all pass)
- `COLUMNS=400 uv run scripts/symlink_plugins.py --diff` — runs without `MarkupError`.

### 6. Pre-flight dry run
- `uv run scripts/symlink_plugins.py --check --diff` — confirm the plan matches the
  Findings (25 skills `create`, commands with the 3 `conflict`s, etc.) and note the
  current backup state. Confirm `git status --porcelain` is unchanged before/after
  (dry run must not mutate).

### 7. Phase 2a — skills (lowest risk: all `create`)
- `uv run scripts/symlink_plugins.py --components skills`
- `uv run scripts/symlink_plugins.py --check --components skills` → exit 0.
- Spot-check: `.claude/skills/twitter-media-downloader/SKILL.md` resolves through the link.

### 8. Phase 2b — commands (has `backup+replace` incl. build.md, and 3 conflicts)
- `uv run scripts/symlink_plugins.py --components commands`
- Confirm `build.md` was backed up (appears in the new `manifest.json`) and now points at
  the plugins version — this is the intended behavior change.
- Confirm the 3 conflicts resolved to the intended `agent-harness` plugin (skipped losers
  left untouched). `--check --components commands` → exit 0.

### 9. Phase 2c–2f — agents, hooks, output-styles, status_lines
- Run each component in turn, `--check` after each:
  `--components agents`, then `hooks`, then `output-styles`, then `status_lines`.
- `hooks` is the largest (25 `backup+replace`); verify a nested leaf resolves, e.g.
  `.claude/hooks/utils/tts/tts_queue.py` and `.claude/hooks/validators/ruff_validator.py`.
- **`status_lines`:** `status_line_v10.py` is the ACTIVE status line (`settings.json:84`)
  and gets overwritten (Adobe → public list pricing) per decision. This is expected; confirm
  it appears in the backup `manifest.json`. `settings.json` still points at the same path —
  now a symlink — so no settings edit is needed. If you later want Adobe pricing back,
  `--restore` or `git checkout -- .claude/status_lines/status_line_v10.py`.

### 10. Phase 3 — full verification
- `uv run scripts/symlink_plugins.py --check` (all components) → exit 0, "No broken links
  or drift."
- Confirm a real edit to a plugin source is reflected through the `.claude/` symlink
  (edit-and-revert a source file, observe via the link).
- Re-run the repo suite: `make lint` and `make test` (or at least
  `uv run pytest -s tests/test_symlink_plugins.py`) stay green.

### 11. Commit
- Stage `scripts/symlink_plugins.py`, `tests/test_symlink_plugins.py`,
  `specs/run-symlink-sync.md`, the now-symlinked `.claude/*` entries, and
  `.backups/symlink-plugins/**` (manifest + backups).
- Conventional commit, e.g.
  `chore(symlink-plugins): sync .claude/ to plugin symlinks + fix PR #49 review`.
- Do **not** push or open a PR unless the user asks.

### 12. Final validation
- Run the Validation Commands below; confirm all pass.

## Testing Strategy

- **Unit:** existing `tests/test_symlink_plugins.py` (26 tests) must stay green after the
  PR #49 edits; the return-type + pathlib changes are covered by the current cases.
- **Tool behavior:** `--diff` must not raise on real repo content (regression for the
  markup bug) — assert by running `--diff` across the whole repo without error.
- **Idempotence:** a second `symlink_plugins.py` run reports "Already in sync — nothing to
  do." and `--check` exits 0.
- **Reversibility (rehearsal):** `--restore` returns the tree to real files and moves
  backups back (only rehearse if needed; the real run is committed).
- **Edge cases:** conflicts (dual-claimed commands) are skipped, orphans (no source) are
  never touched, nested leaves (`hooks/utils/...`, `agents/team/...`) recreate intermediate
  real dirs and link only the leaf.

## Acceptance Criteria

- `scripts/symlink_plugins.py:581` uses `markup=False, highlight=False`; `--diff` runs over
  the whole repo with no `MarkupError`.
- `_action_for` has a `-> sp.Action` return type; no `os.path` remains in
  `tests/test_symlink_plugins.py` (or `import os` removed).
- `uv run pytest -s tests/test_symlink_plugins.py` — all pass; `make lint` — 0 errors.
- Every `.claude/` item with a `plugins/` source is a relative symlink; orphans untouched.
- `uv run scripts/symlink_plugins.py --check` exits 0 ("No broken links or drift").
- `build.md` and `status_line_v10.py` overwrites are recorded in the backup `manifest.json`
  and reversible (git + `--restore`); no `.claude/`-only logic is lost or needs porting to `plugins/`.
- `specs/run-symlink-sync.md` exists with this content.
- No push/PR unless explicitly requested.

## Validation Commands

- `uv run python -m py_compile scripts/symlink_plugins.py` — script compiles.
- `make lint` — 0 lint/type errors on edited files.
- `uv run pytest -s tests/test_symlink_plugins.py` — unit tests pass.
- `COLUMNS=400 uv run scripts/symlink_plugins.py --diff` — no `MarkupError` on real content.
- `uv run scripts/symlink_plugins.py --check` — exit 0, no drift or broken links.
- `find .claude -type l | wc -l` — non-zero; managed items are symlinks.
- `git status --porcelain` after a `--check` run — unchanged (dry run is non-mutating).

## Notes

- **Reversibility is layered:** `.claude/` is git-tracked (117 files) *and* the script
  writes a timestamped backup + `manifest.json`; `--restore` consumes the latest manifest.
  Both overwrites are safe on both counts.
- **No new dependencies.** The script already declares `rich>=13.0.0` via PEP 723; the
  pathlib fix uses `Path.relative_to(..., walk_up=True)` (stdlib, 3.13).
- **`--copy` fallback** exists for symlink-hostile filesystems but is not needed here.
- **Scope boundary:** this plan does not re-home the standalone `/build` command or the
  Adobe-priced status line into a plugin (both chosen to be overwritten). If either is
  wanted long-term, a follow-up can add it under a plugin with a non-colliding name or a
  gitignored private file.
- **PR #49:** applying steps 2–4 here resolves its three review threads; the branch can
  then be updated/merged separately per the user's normal flow.
