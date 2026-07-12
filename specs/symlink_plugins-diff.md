# Plan: `--diff` flag for `scripts/symlink_plugins.py`

## Context

`scripts/symlink_plugins.py` mirrors plugin components (`plugins/<category>/<plugin>/{skills,commands,agents,hooks,output-styles,status_lines}/`)
into `.claude/` as relative symlinks (see `specs/symlink-plugins.md` for the
original design). Its planner (`plan_actions`) already *classifies* drift:

- `BACKUP_REPLACE` — a real (non-symlink) file/dir occupies a `.claude/` slot
  that a plugin also claims. It will be backed up and replaced on the next
  non-dry-run invocation.
- `REPOINT` — an existing symlink in that slot points at the wrong source
  (stale/incorrect).

`--check` reports *that* these exist (counts, non-zero exit) but never shows
*what* actually differs. Before a real file gets moved into `.backups/` and
overwritten by a symlink, or before a stale symlink gets repointed, a
contributor has no way to see the actual content delta without doing it by
hand (`diff -u` against a path they'd have to resolve themselves). `--diff`
closes that gap: it prints the real content differences for exactly the two
drifted kinds, reusing the existing planner unchanged.

## Objective

`scripts/symlink_plugins.py --diff` prints unified-diff-style output showing
how each `BACKUP_REPLACE`/`REPOINT` target currently differs from its plugin
source — without mutating anything. `--diff` composes with `--check` (its
pass/fail exit code stays authoritative); used alone, `--diff` is purely
informational and always exits `0`.

## Problem Statement

Drift is detected but invisible. A contributor deciding whether a
`BACKUP_REPLACE` is "just formatting" or "someone's uncommitted local edit
about to be silently backed up" currently has to manually resolve the plugin
source path and run `diff` themselves. `REPOINT` has the same problem in
reverse — you know a symlink is wrong, but not what you'd be gaining by fixing it.

## Solution Approach

Add a small set of pure, independently testable diff helpers to
`scripts/symlink_plugins.py`, and wire them into the *existing* `check()`
function rather than a parallel code path — `--diff` reuses `plan_actions`'s
classification unchanged, it just renders content for the two drifted kinds.
No new dependency: `difflib` is stdlib.

**New functions** (added near the existing `_classify`/`_iter_sources`
helpers; public functions unprefixed like `plan_actions`/`execute`, private
helpers prefixed like `_classify`/`_display`, matching existing convention):

```python
def _list_files(root: Path) -> dict[str, Path]:
    """rel-POSIX-path -> abs Path for every non-ignored file under root.

    Standalone helper reusing the existing _is_ignored() filter. Does NOT
    refactor _iter_sources — a separate implementation avoids touching
    already-tested shared planning code for an unrelated feature. Returns {}
    if root isn't a directory (degrade, not crash).
    """


def _read_text_or_none(path: Path) -> list[str] | None:
    """UTF-8 lines (splitlines(keepends=True)); None if binary/missing/undecodable.

    Binary heuristic: a NUL byte anywhere, or a UnicodeDecodeError. Matches
    git/diffutils' own heuristic.
    """


def diff_files(source: Path, target: Path) -> list[str]:
    """Unified diff lines, target's current content -> source's content.

    [] if identical. Binary fallback: raw read_bytes() equality check, so
    identical binaries never falsely report "differ"; a single explanatory
    line ("binary files differ") if binary and different.
    """


DIR_ONLY_IN_SOURCE = "only-in-source"
DIR_ONLY_IN_TARGET = "only-in-target"
DIR_DIFFERS = "differs"


@dataclass(frozen=True)
class DirDiffEntry:
    """One relative path's comparison result inside a recursive dir diff."""

    rel_path: str
    status: str  # DIR_ONLY_IN_SOURCE | DIR_ONLY_IN_TARGET | DIR_DIFFERS
    diff: list[str] = field(default_factory=list)  # only for DIR_DIFFERS


def diff_dirs(source: Path, target: Path) -> list[DirDiffEntry]:
    """Recursive dir comparison (skills dir-level case; also any
    BACKUP_REPLACE/REPOINT where source or target is a directory).

    Uses _list_files on both sides. Identical common files are omitted
    entirely from the result.
    """


def diff_action(action: Action) -> list[str]:
    """Renderable diff lines for one action; [] when there's nothing to show.

    - SKIP / CREATE / CONFLICT / ORPHAN_LEFT / source is None -> [] (nothing
      to compute, or explicitly out of scope: SKIP is already the correct
      symlink, CREATE has no existing target, CONFLICT/ORPHAN_LEFT don't have
      an assigned-source-vs-target divergence in this sense).
    - target doesn't exist/resolve (broken REPOINT symlink) -> one
      explanatory line, not a crash.
    - source/target kind mismatch (one's a dir, other's a file) -> one
      explanatory line instead of a misleading all-only-in-source dir diff.
    - otherwise dispatches to diff_dirs (flattened into lines with a
      per-entry header) or diff_files.
    """


def _print_diffs(actions: list[Action]) -> None:
    """console.print() wrapper: one header per action with a non-empty diff
    (_display(target) <- _display(source)), then the diff body. All actual
    comparison logic above stays plain list[str]/dataclasses with no rich
    markup, so it's unit-testable without capturing stdout.
    """
```

`check()` gains a keyword-only flag and calls `_print_diffs` right after the
existing `_print_plan(actions)` call:

```python
def check(
    repo_root: Path, actions: list[Action], components: tuple[str, ...], *, show_diff: bool = False
) -> int:
    _print_plan(actions)
    if show_diff:
        _print_diffs(actions)
    ...  # unchanged: broken-link scan, REPOINT-as-drift, exit code
```

**CLI wiring in `main()`:**

```python
parser.add_argument(
    "--diff", action="store_true",
    help="show content diffs for backup+replace/repoint actions (dry run; "
         "pair with --check to also gate the exit code on drift)",
)
...
if args.check or args.diff:
    exit_code = check(repo_root, actions, components, show_diff=args.diff)
    return exit_code if args.check else 0
```

This replaces the current `if args.check: return check(...)` line. No other
branch changes:

- `--diff` alone → dry run, `--diff`'s own exit code forced to `0`
  (informational; safe to run interactively without breaking a caller that
  greps exit codes).
- `--diff --check` → `--check`'s existing pass/fail semantics apply unchanged;
  diff output is additive.
- `--diff --restore` → behaves as `--restore` alone (the `--restore` branch
  short-circuits at the very top of `main()`, before `--check`/`--diff` are
  even read — pre-existing precedent, not a new special case).

## Relevant Files

- `scripts/symlink_plugins.py` — implementation target. Reuses `Action`,
  `plan_actions`, `_is_ignored`, `_display`, `console`, and the `check()`
  function this plugs into.
- `tests/test_symlink_plugins.py` — existing test patterns to match: module
  loaded via `importlib.util.spec_from_file_location` as `sp`; builders
  `_plugin_root`, `_write`, `_skill`, `_run`, `_kinds`; CLI-level assertions
  via `sp.main([...])` (see `test_check_broken_link_exits_nonzero`,
  `test_check_consistent_exits_zero` for the pattern to mirror).
- `specs/symlink-plugins.md` — original spec this one extends; same
  shape/voice.
- `Makefile` (~lines 202–215) — existing `symlink-plugins` /
  `symlink-plugins-check` / `unlink-plugins` targets. No new Make target is
  required for v1 (`--diff` is a flag a contributor passes ad hoc:
  `uv run scripts/symlink_plugins.py --check --diff`); see Notes for the
  optional follow-up.

## Step by Step Tasks

IMPORTANT: Execute every step in order, top to bottom (TDD: tests before
implementation within each step).

### 1. Write failing tests for file-level diffing
- Add to `tests/test_symlink_plugins.py`:
  - `test_diff_files_identical_returns_empty` — two files with identical text
    content → `sp.diff_files(...) == []`.
  - `test_diff_files_text_returns_unified_diff` — differing text content →
    result contains the expected `+`/`-` changed lines.
  - `test_diff_files_binary_reports_binary_differ` — two files each containing
    a NUL byte, differing content → a single "binary files differ"-style
    entry, no exception, no raw byte dump.
  - `test_diff_files_binary_identical_bytes_returns_empty` — identical
    NUL-containing content on both sides → `[]` (proves the byte-equality
    fallback avoids a false "differ").
- Run `uv run pytest -s tests/test_symlink_plugins.py -k diff_files` — confirm
  all four fail with `AttributeError` (function doesn't exist yet).

### 2. Implement `_read_text_or_none` and `diff_files`
- Add both functions per the signatures above.
- Re-run the step-1 tests until green.

### 3. Write failing tests for directory-level diffing
- `test_list_files_ignores_build_junk` — a directory containing
  `__pycache__/`, a `.pyc` file, and `.DS_Store` alongside real files → the
  junk is excluded from `sp._list_files(...)`.
- `test_diff_dirs_reports_only_in_source_only_in_target_and_differs` — a
  source/target directory pair with one source-only file, one target-only
  file, and one common-but-differing file → exactly three `DirDiffEntry` rows
  with the correct `status`, and a non-empty `diff` only on the differing one.

### 4. Implement `_list_files`, `DirDiffEntry`, and `diff_dirs`
- Add per the signatures above.
- Re-run the step-3 tests until green.
- Run the **full existing suite** (`uv run pytest -s tests/test_symlink_plugins.py`)
  to confirm `_list_files` (a new, separate implementation) hasn't
  accidentally diverged from or interfered with `_iter_sources`'s existing
  ignore-rule behavior.

### 5. Write failing tests for the `diff_action` dispatcher
- `test_diff_action_backup_replace_dir_shows_skill_drift` — a real (non-symlink)
  `.claude/skills/<name>/` directory whose `SKILL.md` content differs from the
  plugin source's (classified `BACKUP_REPLACE` by the existing planner) →
  `diff_action` reports the differing file.
- `test_diff_action_repoint_shows_current_vs_correct_source` — an existing
  symlink pointing at a *different* (wrong) plugin source (classified
  `REPOINT`) → `diff_action` diffs the currently-resolved content against the
  correct source's content.
- `test_diff_action_repoint_broken_symlink_reports_broken_message` — a symlink
  pointing at a path that no longer exists → `diff_action` returns the
  explanatory "broken" message rather than raising.
- `test_diff_action_skip_and_create_return_empty` — a `SKIP` action (already
  the correct symlink) and a `CREATE` action (no target yet) both → `[]`.
- `test_diff_action_conflict_and_orphan_return_empty` — a `CONFLICT` action
  and an `ORPHAN_LEFT` action both → `[]`.
- `test_diff_action_type_mismatch_reports_note` — a plugin skill (directory
  source) whose `.claude/` slot is occupied by a plain file → an explicit
  type-mismatch line, not a misleading dir diff.

### 6. Implement `diff_action`
- Add per the signature above, covering every branch exercised in step 5.
- Re-run the step-5 tests until green.

### 7. Write failing tests for CLI wiring
- `test_main_diff_alone_exits_zero_and_does_not_mutate` — stage a
  `BACKUP_REPLACE` scenario; `sp.main(["--diff", "--repo-root", str(tmp_path)])`
  returns `0`; confirm the real file on disk is untouched afterward (still a
  real file, not backed up or symlinked).
- `test_main_diff_with_check_preserves_check_exit_code` — same broken-link
  scenario as the existing `test_check_broken_link_exits_nonzero`, invoked as
  `sp.main(["--diff", "--check", ...])` → exit code `1`.

### 8. Wire `--diff` into `check()` and `main()`
- Add `show_diff` keyword to `check()`, call `_print_diffs` after
  `_print_plan`.
- Add the `--diff` argparse flag and the `if args.check or args.diff: ...`
  branch in `main()`, replacing the current `if args.check: return check(...)`
  line.
- Re-run the step-7 tests until green.

### 9. Validate
- Run the full validation commands below; confirm `make lint` and the entire
  `tests/test_symlink_plugins.py` suite (old + new) pass; manually run
  `uv run scripts/symlink_plugins.py --check --diff` against the real repo and
  confirm it exits `0` (or shows real, sensible drift) without mutating
  anything (`git status --porcelain` unchanged).

## Testing Strategy

Load the script per repo convention (`importlib.util.spec_from_file_location`,
already done at the top of `tests/test_symlink_plugins.py` as `sp`). Every new
test targets a distinct branch — no trivial tests:

- Text identity, text divergence, binary divergence, binary identity (proves
  the byte-equality fallback, not just "doesn't crash on binary").
- Ignore-rule reuse in `_list_files` (build junk excluded).
- Directory diff's three statuses (only-in-source / only-in-target / differs).
- Each `diff_action` kind: the two drifted kinds render content; the four
  non-drifted kinds (`SKIP`, `CREATE`, `CONFLICT`, `ORPHAN_LEFT`) render
  nothing; the two degrade paths (broken symlink, kind mismatch) render an
  explanatory note instead of crashing or misleading output.
- Both CLI compositions: `--diff` alone (exit forced to `0`, no mutation) and
  `--diff --check` together (exit code stays `--check`'s).

## Acceptance Criteria

- `scripts/symlink_plugins.py --diff` prints content diffs for every
  `BACKUP_REPLACE`/`REPOINT` action and never mutates the filesystem.
- `--diff` alone always exits `0`; `--diff --check` preserves `--check`'s
  existing pass/fail exit code.
- `SKIP`/`CREATE`/`CONFLICT`/`ORPHAN_LEFT` actions produce no diff output.
- A broken symlink target or a directory/file kind mismatch produces a clear
  explanatory line instead of a crash or misleading diff.
- All 14 new tests plus the full pre-existing `tests/test_symlink_plugins.py`
  suite pass; `make lint` is clean on `scripts/symlink_plugins.py`.

## Validation Commands

- `uv run python -m py_compile scripts/symlink_plugins.py` — script compiles.
- `make lint` — ruff + basedpyright clean on the modified script.
- `uv run pytest -s tests/test_symlink_plugins.py` — full suite (old + new) passes.
- `uv run scripts/symlink_plugins.py --check --diff` — runs against the real
  repo; exits `0` on a clean checkout; `git status --porcelain` unchanged
  afterward (no mutation).

## Notes

- No new dependency: `difflib` is stdlib; do not touch the PEP-723
  `dependencies = [...]` block.
- Ruff's `TRY` rule is selected in `pyproject.toml` — keep new `except` bodies
  minimal (single return/assignment), matching `_classify`'s existing
  `try: os.readlink(...) except OSError: return REPOINT` pattern.
- `basedpyright` strict mode: `Action.source` is `Path | None` — every new
  function must narrow it (`if action.source is None: return []`) before use,
  same as `execute()` already does.
- `DirDiffEntry.diff` must use `field(default_factory=list)`, not a bare `= []`
  default.
- `_display()` reads the module-level `REPO_ROOT` global, not the `repo_root`
  parameter threaded through the rest of the script (pre-existing quirk,
  already relied on by `_print_plan`/`check`). Under `tmp_path`-based tests
  `_display()` falls back to absolute paths — new tests should assert on diff
  *content* (`+`/`-` lines, `DIR_ONLY_IN_SOURCE`/`DIR_ONLY_IN_TARGET`
  statuses), not on repo-relative display strings.
- Keep all new comparison code on the `Path` side (`read_bytes`, `rglob`,
  `relative_to`) — it never needs raw symlink-target strings, unlike the
  existing `os.path.relpath`/`os.readlink` calls used specifically for
  symlink-string calculation elsewhere in the script.
- **Optional follow-up (not required for v1):** wire a `--diff`-aware variant
  into the `symlink-plugins-check` Make target (e.g. `symlink-plugins-diff`)
  if contributors want it in their everyday workflow — flagged here, not
  implemented, since the plain flag combo (`--check --diff`) already covers
  the use case without a Makefile change.
