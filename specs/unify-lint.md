# Plan: Unify the lint toolchain (deterministic, enforced formatting across make / pre-commit / CI)

## Context

Auditing `.pre-commit-config.yaml` against `pyproject.toml`, `.rumdl.toml`, `devtools/lint.py`,
and the `Makefile` revealed that a file's formatting can differ depending on which tool last
touched it, and that CI does not actually *enforce* formatting — it silently auto-fixes in the
runner and passes. Three entry points (`make lint`, `pre-commit`, the GitHub Actions "Run
linting" step) disagree about what runs and whether it mutates or enforces. The result is
working-tree churn ("why did `make lint` just reformat files I didn't touch?") and unformatted
code merging green.

This spec makes the lint toolchain deterministic and enforced: the same formatters run the same
way regardless of entry point, CI fails on unformatted/misspelled code instead of silently
fixing it, and markdown lint scope is mirrored between its two entry points.

## Objective

When complete:

- `devtools/lint.py` supports a `--check` mode that is report-only (no file mutation) and exits
  non-zero on any formatting / lint / spelling violation. The default (no flag) keeps today's
  local auto-fix behavior.
- The GitHub Actions "Run linting" step runs `--check`, so CI enforces rather than mutates.
- `pre-commit` runs the same `ruff` (check + format) and `codespell` as `make lint`, scoped to
  the same paths, pinned to the same versions — so committing and `make lint` cannot disagree on
  `.py`.
- The pre-commit `rumdl` hook's `files:` regex mirrors `.rumdl.toml` `include`, so `make
  markdown-lint` and pre-commit flag the same markdown set.
- Low-priority hardening: `trailing-whitespace` stops eating markdown hard-breaks; the
  unicode-hygiene hook's `files:` regex mirrors the validator's `DEFAULT_TARGETS`.

## Problem Statement

1. **CI mutates-and-passes; never enforces.** `devtools/lint.py:30-44` runs
   `codespell --write-changes`, `ruff check --fix`, and `ruff format` (no `--check`), then derives
   its exit code only from each tool's status (`run()` counts a non-zero subprocess as one error).
   `ruff format` always exits 0; `ruff check --fix` exits 0 once it auto-fixes. The CI "Run
   linting" step applies fixes to the ephemeral runner and discards them — the committed tree
   stays unformatted and CI is green. (codespell still exits non-zero on a real typo, so spelling
   is effectively enforced; pure `ruff format` reformatting is not.)
2. **`ruff` + `codespell` are absent from `.pre-commit-config.yaml`.** Pre-commit only runs
   whitespace / EOF / rumdl / unicode hooks. So `.py` formatting state depends on whether a human
   ran `make lint`; committing via pre-commit alone never formats Python.
3. **rumdl scope divergence.** `make markdown-lint` / `markdown-fix` run `rumdl check/fmt .`
   governed by `.rumdl.toml` `include` (which lists `docs/plugins/*.md`). The pre-commit rumdl
   hook's `files:` regex omits `docs/plugins/`, so those files are fixed by `make markdown-fix`
   but never checked at commit time. (rumdl ignores `include` for explicitly-passed paths —
   verified — so the regex is the only commit-time scope and must mirror `include`.)
4. **Low severity.** `trailing-whitespace` has no `--markdown-linebreak-ext`; it strips trailing
   spaces unconditionally, including markdown hard-breaks and inside Python multiline strings that
   `ruff format` (preview) preserves.

## Solution Approach

Single source per concern, and a mutate-vs-enforce split keyed on entry point:

- **Formatter/linter config** lives in `pyproject.toml` (`[tool.ruff]`, `[tool.codespell]`) —
  unchanged. Both `make lint` and the new pre-commit hooks read it.
- **`lint.py`** keeps auto-fix as the local-dev default and gains `--check` (report-only,
  enforcing) for CI. One script, two modes — no second tool to drift.
- **pre-commit** gains `ruff-check`, `ruff-format`, and `codespell`, scoped with `files:` to the
  exact `SRC_PATHS` (`devtools`, `scripts`, `plugins`) that `lint.py` uses, so pre-commit and
  `make lint` cover the same set and cannot disagree (neither touches `tests/`). basedpyright is
  intentionally NOT added to pre-commit: it is report-only (no mutation → no flip-flop) and slow;
  it runs in `make lint` and in CI (`--check`).
- **rumdl** scope is kept in sync by mirroring `.rumdl.toml` `include` in the pre-commit `files:`
  regex (rumdl ignores `include` for explicit paths, so the regex is load-bearing and must not be
  dropped).

## Relevant Files

To read / modify:

- `devtools/lint.py` — add `argparse` `--check`; branch each tool's flags on the mode; keep the
  `run()` error-counting exit model. Mirror repo conventions (`scripts/verify-structure.py`
  argparse style).
- `.github/workflows/ci.yml` — change the "Run linting" step command to add `--check`.
- `.pre-commit-config.yaml` — add the `astral-sh/ruff-pre-commit` repo (`ruff-check` +
  `ruff-format`) and the `codespell-project/codespell` repo, scoped with `files:`; broaden the
  rumdl `files:` regex to mirror `.rumdl.toml include`; add `args: [--markdown-linebreak-ext=md]`
  to `trailing-whitespace`; tighten the `validate-unicode-hygiene` `files:` regex to mirror
  `DEFAULT_TARGETS`.
- `Makefile` — optional convenience target `lint-check: uv run python devtools/lint.py --check`.

Reference (unchanged): `pyproject.toml` `[tool.ruff]` / `[tool.ruff.lint.per-file-ignores]` /
`[tool.codespell]`; `.rumdl.toml` `include`; `scripts/validate-unicode-hygiene.py` `DEFAULT_TARGETS`.

Pinned versions (from `uv.lock`): ruff `0.14.10`, codespell `2.4.1`.

### New Files

None — this is a config + one script-flag change (plus an optional Makefile target). No new files.

## Implementation Phases

### Phase 1: Local enforce mode
Give `devtools/lint.py` a report-only `--check` mode while keeping today's auto-fix default, so
one script serves both local-dev (fix) and CI (enforce) without a second tool to drift.

### Phase 2: Wire enforcement + parity
Point CI at `--check` so it enforces; add ruff + codespell to pre-commit scoped to `lint.py`'s
paths/versions so committing and `make lint` agree on `.py`; broaden the rumdl `files:` regex to
mirror `.rumdl.toml include`.

### Phase 3: Hardening + validation
Apply the low-priority whitespace/unicode-regex hardening, then run the full end-to-end checks to
prove enforce-vs-fix behaves per entry point and no two tools fight over a file.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### 1. Add `--check` mode to `devtools/lint.py` (Phase 1)
- Parse args with `argparse`; add `--check` (store_true). Keep `main()` returning `errcount` and
  the `exit(main())` contract.
- When `--check` is set, run the report-only variants (no mutation, non-zero on violation):
  - `codespell` **without** `--write-changes`
  - `ruff check` **without** `--fix`
  - `ruff format --check`
  - `basedpyright --stats` (already report-only; unchanged)
- When not set, keep today's mutating variants (`codespell --write-changes`, `ruff check --fix`,
  `ruff format`). Build each command list conditionally on the flag.

### 2. Make CI enforce (Phase 2)
- In `.github/workflows/ci.yml`, change the "Run linting" step to
  `run: uv run python devtools/lint.py --check`. (Keep its existing `if:` / placement.)

### 3. Add ruff + codespell to pre-commit, scoped + pinned (Phase 2)
- Add to `.pre-commit-config.yaml`:
  ```yaml
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.14.10
    hooks:
      - id: ruff-check
        args: [--fix]
        files: ^(devtools|scripts|plugins)/.*\.py$
      - id: ruff-format
        files: ^(devtools|scripts|plugins)/.*\.py$
  - repo: https://github.com/codespell-project/codespell
    rev: v2.4.1
    hooks:
      - id: codespell
        additional_dependencies: ["tomli"]
        files: ^(devtools|scripts|plugins|README\.md)
  ```
  The `files:` scopes mirror `lint.py` `SRC_PATHS` (+ `README.md` for codespell, matching
  `DOC_PATHS`) so pre-commit and `make lint` cover the identical set. codespell reads its
  `ignore-words-list` from `[tool.codespell]` in `pyproject.toml`. List `ruff-check` before
  `ruff-format`. Confirm the hook ids `ruff-check`/`ruff-format` resolve at the pinned rev
  (`uvx pre-commit run ruff-check --all-files` errors clearly if an id is wrong).

### 4. Broaden the pre-commit rumdl scope to mirror `.rumdl.toml` (Phase 2)
- Do **not** drop the `files:` regex (rumdl ignores `include` for explicit paths — verified — so
  dropping it makes the hook lint ALL staged markdown, regressing the inclusion policy).
- Add `plugins` to the `docs/(...)` alternation so the regex covers the `docs/plugins/*.md` files
  that `.rumdl.toml include` lists but the current regex omits:
  ```yaml
  files: ^(README\.md|plugins/[^/]+/README\.md|plugins/[^/]+/[^/]+/README\.md|docs/(architecture|checklists|plugins)/[^/]+\.md)$
  ```

### 5. Low-priority hardening (Phase 3)
- Add `args: [--markdown-linebreak-ext=md]` to the `trailing-whitespace` hook.
- Tighten the `validate-unicode-hygiene` hook `files:` regex to full parity with the validator's
  `DEFAULT_TARGETS` (one level under `agents/`, `commands/`, `.claude/commands/`):
  ```yaml
  files: ^(plugins/.+/(SKILL\.md|agents/[^/]+\.md|commands/[^/]+\.md)|plugins/.+/\.claude-plugin/plugin\.json|\.claude-plugin/marketplace\.json|\.claude/skills/.+/SKILL\.md|\.claude/commands/[^/]+\.md)$
  ```
  (Read-only scanner; this is parity with the script's globs, not a correctness fix.)

### 6. Validate end-to-end (Phase 3)
- Run the validation commands below; confirm enforce-vs-fix behaves per mode and that no entry
  point reformats a file another one left alone.

## Testing Strategy

- **Enforce mode:** on a scratch branch, introduce a mis-formatted `.py` (stray spaces / bad
  import order) and a `docs/plugins/*.md` lint violation. Confirm `uv run python devtools/lint.py
  --check` exits non-zero **without** modifying files, and the CI step would go red. Revert.
- **Parity:** `make lint` (auto-fix) then `uvx pre-commit run ruff-format --all-files` on the same
  tree produces zero further changes (no flip-flop). Same for `ruff-check`.
- **rumdl scope:** `make markdown-lint` and `uvx pre-commit run rumdl --all-files` flag the same
  `docs/plugins/*.md` file.
- **Scope:** confirm pre-commit ruff does **not** touch `tests/` (matches `lint.py`), so no new
  divergence is introduced.

## Acceptance Criteria

- `uv run python devtools/lint.py` (default) still auto-fixes locally; `--check` is report-only and
  exits non-zero on any violation, leaving the tree unmodified (`git diff --exit-code` clean).
- CI "Run linting" runs `--check` and fails on unformatted/misspelled committed code.
- `pre-commit` runs ruff (check+format) and codespell on the same paths/versions as `make lint`;
  after `uvx pre-commit run --all-files`, `git diff --exit-code` is clean.
- The pre-commit rumdl `files:` regex mirrors `.rumdl.toml include` (covers `docs/plugins`);
  pre-commit and `make markdown-lint` flag the same files.
- `trailing-whitespace` carries `--markdown-linebreak-ext=md`; the unicode-hygiene `files:` regex
  mirrors `DEFAULT_TARGETS`.

## Validation Commands

- `uv run python devtools/lint.py --check` — report-only; exit 0 on a clean tree, non-zero on a
  planted violation; `git diff --exit-code` clean afterward (no mutation).
- `uv run python devtools/lint.py` — still auto-fixes locally.
- `uvx pre-commit run ruff-check ruff-format codespell --all-files` — pass on a clean tree.
- `uvx pre-commit run rumdl --all-files` and `make markdown-lint` — flag the same files.
- `uvx pre-commit run --all-files && git diff --exit-code tests/fixtures/unicode-hygiene/` —
  fixtures still byte-stable.

## Notes

- **Version lockstep.** Pin `ruff-pre-commit` `rev` to the ruff version `uv.lock` resolves
  (`0.14.10` today). Add a Renovate `packageRule` grouping the `astral-sh/ruff-pre-commit`
  pre-commit update with the `ruff` PyPI dependency so they bump together; otherwise Renovate can
  advance one and reintroduce a pre-commit-vs-`make lint` ruff mismatch.
- `codespell`'s `additional_dependencies: ["tomli"]` is only needed if the hook's env Python is
  <3.11 (3.11+ has stdlib `tomllib`); harmless to keep for reproducibility.
- This is config + one script-flag change; no production/plugin behavior changes. `make ci` (tests
  only) is unaffected; enforcement lives in the GitHub Actions "Run linting" step.
- `tests/` remains outside ruff in both entry points by design (scoped `files:`), matching today's
  `lint.py` `SRC_PATHS`.
