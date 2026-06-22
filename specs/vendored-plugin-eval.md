# Plan: Vendor the patched plugin-eval into `scripts/plugin_eval/`

> Self-contained spec. Authored to be executed by a fresh agent with **zero prior
> conversation context**. Read top to bottom, then work the phases in order.

## Task Description

Copy the locally-patched `plugin-eval` package (currently an **external** fork at
`/Users/bossjones/dev/wshobson/plugin-eval-apikey`, selected via `PLUGIN_EVAL_SOURCE` in
`.env`) **into this repo** at `scripts/plugin_eval/`, and repoint the eval tooling at that
vendored copy so the repo no longer depends on an out-of-tree directory. Add a credited
`README.md`, preserve the upstream `LICENSE`, and keep the patch minimal/clearly marked so a
future upstream PR to `wshobson/agents` is a clean extract.

Task type: **refactor / chore** (vendor an external dependency). Complexity: **medium**.

## Objective

When complete: `make eval-skill … AUTH=api-key` and `/skill-evals --auth api-key` run the LLM
judge from the **in-repo** `scripts/plugin_eval/` with **no** `PLUGIN_EVAL_SOURCE` override and
**no** reference to the external fork or the upstream git URL as a runtime default; lint/test
stay green (vendored tree excluded from tooling); and the package's own tests pass, proving the
`--auth api-key` patch is intact.

## Problem Statement

A real upstream gap was fixed recently: `plugin-eval`'s LLM judge documents `--auth api-key`
but never wired it up (it only called `claude-agent-sdk`, which returns empty in a subprocess →
silent static-only scoring). The fix lives in a **patched fork outside the repo**
(`/Users/bossjones/dev/wshobson/plugin-eval-apikey`), reached via
`PLUGIN_EVAL_SOURCE='plugin-eval[llm,api] @ file://…'` in the gitignored `.env`. That makes the
judge work **only on this machine, only while that directory exists** — if it is deleted/moved,
evals silently revert to static-only. Vendoring removes the hidden external dependency and makes
the fix reproducible and reviewable in-repo.

## Solution Approach

Vendor the buildable Python package (not the Claude-plugin cruft) into `scripts/plugin_eval/`,
change `scripts/eval-skills.py`'s `DEFAULT_SOURCE` to a **repo-relative `file://` URI** computed
from `REPO_ROOT`, ensure the `[llm,api]` extras are requested (so the anthropic SDK installs for
the api-key path), and exclude the vendored tree from ruff/basedpyright/codespell/pytest. The
`uvx --from <source>` mechanism is unchanged — only the source string moves from a git URL to a
local path. Keep `PLUGIN_EVAL_SOURCE` as an override escape-hatch (now overriding a local
default). Update the prose that claims "nothing is vendored." Preserve upstreamability by keeping
the vendored `pyproject.toml` identical to upstream and putting the "install both extras"
decision in **our** wrapper.

## Relevant Files

**Vendor source (external, read-only):** `/Users/bossjones/dev/wshobson/plugin-eval-apikey/` —
the patched fork. Copy its `src/plugin_eval/`, `pyproject.toml`, `README.md`, `tests/`. The patch
is already present: `src/plugin_eval/layers/judge.py` has `_query_via_api()` + the
`auth == "api-key"` branch in `query_llm()`; `src/plugin_eval/engine.py` sets `model_usage` on
the `PluginEvalResult`.

**Runtime wrapper (must change):** `scripts/eval-skills.py`
- `DEFAULT_SOURCE` (the git URL) — repoint to the vendored `file://` URI.
- `REPO_ROOT = Path(__file__).resolve().parent.parent` — already correct; reorder so it's
  defined *before* `DEFAULT_SOURCE`.
- `resolve_source(base, needs_llm)` — change the extras from `[llm]` to `[llm,api]`.
- module docstring + the `PLUGIN_EVAL_SOURCE` escape-hatch comment — update wording.

**Tooling config (exclude the vendored tree):**
- `pyproject.toml` — `[tool.ruff] exclude`, `[tool.codespell] skip`, optional
  `[tool.pytest.ini_options] norecursedirs`, optional `[tool.uv] exclude`.
- `pyrightconfig.json` — `exclude` array.
- `devtools/lint.py` — no change needed (it passes `["devtools","scripts","plugins"]` to tools
  that read the above config); confirm only.

**Prose to repoint (grep-driven, "nothing is vendored" / upstream URL):**
`.claude/skills/skill-evals/SKILL.md`, `.claude/skills/skill-evals/references/plugin-eval.md`,
`.claude/skills/version-bump-reviewer/SKILL.md` (inline `SRC="${PLUGIN_EVAL_SOURCE:-git+…}"`),
`docs/eval-skills.md`, `docs/scripts.md`, `README.md`. Keep `PLUGIN_EVAL_SOURCE` override docs.

**Local-only (manual, not committed):** `.env` — remove the `PLUGIN_EVAL_SOURCE` line so the new
vendored `DEFAULT_SOURCE` is used. The external fork dir can be deleted after verification.

### New Files
- `scripts/plugin_eval/` — the vendored package: `src/plugin_eval/**`, `pyproject.toml`,
  `tests/**`, `README.md` (augmented with credit), `LICENSE` (from upstream).
- `scripts/plugin_eval/VENDORING.md` (or a clearly-marked section in `README.md`) — credit +
  the exact local patch + "temporary pending upstream PR."

## Implementation Phases

### Phase 1: Foundation — vendor the package
Copy the package files in; trim the cruft; add credit + license; confirm the patch survives.

### Phase 2: Core — repoint the runtime
Change `eval-skills.py` `DEFAULT_SOURCE` to the vendored `file://` URI and `resolve_source` to
`[llm,api]`; remove the `.env` override.

### Phase 3: Integration & Polish — exclusions, docs, verify
Exclude the vendored tree from lint/type-check/spellcheck/pytest; update "nothing is vendored"
prose; run the full verification matrix; version-bump the two edited SKILL.md files.

## Step by Step Tasks
IMPORTANT: Execute every step in order, top to bottom.

### 1. Vendor the package files
- Create `scripts/plugin_eval/`. Copy from `/Users/bossjones/dev/wshobson/plugin-eval-apikey/`:
  `src/plugin_eval/` (whole tree), `pyproject.toml`, `README.md`, `tests/`.
- **Do NOT copy:** `.claude-plugin/`, `.codex-plugin/`, `.venv/`, `.pytest_cache/`, `agents/`,
  `commands/`, `skills/`, the plugin-level `scripts/`, `.git/`, `__pycache__/`, `uv.lock`
  (unused by `uvx --from`; drop to keep the surface lean).
- Verify the patch is present after copy:
  - `grep -n "_query_via_api\|auth == \"api-key\"" scripts/plugin_eval/src/plugin_eval/layers/judge.py`
  - `grep -n "model_usage" scripts/plugin_eval/src/plugin_eval/engine.py`

### 2. Add license + credit
- Obtain the upstream license (the fork lacks a root `LICENSE`; `pyproject.toml` has no `license`
  field). Copy `/Users/bossjones/dev/wshobson/agents/LICENSE` into `scripts/plugin_eval/LICENSE`
  **after confirming it is MIT** (the agent-harness plugin.json declares MIT; verify the
  `wshobson/agents` root LICENSE text). If it is not MIT or is absent upstream, stop and surface
  before committing — do not vendor without a clear license.
- Write `scripts/plugin_eval/README.md` (augment the upstream README with a top section, or add
  `scripts/plugin_eval/VENDORING.md`) stating: this is a **vendored, locally-patched** copy of
  `wshobson/agents` `plugins/plugin-eval`; the upstream URL
  (`https://github.com/wshobson/agents/tree/main/plugins/plugin-eval`); the ref/date vendored;
  MIT license (see `LICENSE`); the **local patch** = wire `--auth api-key` to the `anthropic`
  SDK (`judge.py: _query_via_api` + `query_llm` dispatch) and surface real token usage
  (`engine.py: model_usage`); and that this vendoring is **temporary, pending an upstream PR**.
- Keep the patched regions in `judge.py`/`engine.py` clearly commented (they already carry
  explanatory comments) so the future PR is a clean cherry-pick.

### 3. Repoint `DEFAULT_SOURCE` in `scripts/eval-skills.py`
- Reorder so `REPO_ROOT` is defined before `DEFAULT_SOURCE`, then:
  ```python
  REPO_ROOT = Path(__file__).resolve().parent.parent
  # Vendored, locally-patched plugin-eval (see scripts/plugin_eval/README.md).
  DEFAULT_SOURCE = (REPO_ROOT / "scripts" / "plugin_eval").as_uri()  # file:///…/scripts/plugin_eval
  ```
- In `resolve_source()`, change the extras so the api-key backend's `anthropic` SDK installs:
  ```python
  return f"plugin-eval[llm,api] @ {base}"   # was [llm]
  ```
  (Keep the `if base.startswith("plugin-eval"): return base` short-circuit so a user-supplied
  full PEP 508 `PLUGIN_EVAL_SOURCE` is still honored verbatim.)
- Update the module docstring (the "pulled on demand … nothing is vendored" lines) and the
  `PLUGIN_EVAL_SOURCE` escape-hatch comment to describe a **local vendored default** that
  `PLUGIN_EVAL_SOURCE` can still override (e.g. to test an upstream revision).

### 4. Remove the `.env` override (local, manual)
- Delete the `PLUGIN_EVAL_SOURCE='…plugin-eval-apikey'` line from `.env` (gitignored) so runs
  fall back to the new vendored `DEFAULT_SOURCE`. (If kept, it would point at the soon-deleted
  fork.)

### 5. Exclude the vendored tree from tooling
- `pyproject.toml`:
  - `[tool.ruff]`: `exclude = [".claude/", "scripts/plugin_eval/"]` and add `force-exclude = true`
    (lint.py passes `scripts` explicitly; force-exclude guarantees the subdir is skipped).
  - `[tool.codespell]`: add `skip = "scripts/plugin_eval/"`.
  - `[tool.pytest.ini_options]`: add `norecursedirs = ["scripts/plugin_eval"]` (belt-and-suspenders;
    `testpaths = ["tests", "plugins"]` already keeps `make test` out of it).
  - `[tool.uv]`: optionally add `exclude = ["scripts/plugin_eval"]` to document it is not a
    workspace member.
- `pyrightconfig.json`: add `"scripts/plugin_eval/**"` to the `exclude` array.
- Confirm `make markdown-lint` and `make link-check` do not choke on the vendored
  `README.md`/`tests`; if they scan it, exclude `scripts/plugin_eval/` in their config too.

### 6. Repoint the "nothing is vendored" prose
- Grep for every reference and update wording (keep the `PLUGIN_EVAL_SOURCE` override docs;
  change runtime-default claims):
  ```bash
  grep -rn "nothing is vendored\|not vendored\|pulled on demand\|git+https://github.com/wshobson/agents" \
    scripts/eval-skills.py .claude/skills/skill-evals docs README.md
  grep -rn "PLUGIN_EVAL_SOURCE:-git" .claude/skills/version-bump-reviewer/SKILL.md
  ```
- Files to edit: `.claude/skills/skill-evals/SKILL.md` (intro), `.../references/plugin-eval.md`,
  `.claude/skills/version-bump-reviewer/SKILL.md` (the inline `SRC=` default → vendored path),
  `docs/eval-skills.md`, `docs/scripts.md`, `README.md`. Leave links to the upstream repo as
  attribution; only change statements that say the package is fetched/never vendored.

### 7. Self-test the vendored package (prove the patch survives)
- `uv run --project scripts/plugin_eval --extra dev --extra llm --extra api -m pytest scripts/plugin_eval/tests -q`
  → expect all tests green (28 at vendoring time). This creates `scripts/plugin_eval/.venv`;
  confirm `.venv` is gitignored (the repo's `.gitignore` should already cover `.venv`/`**/.venv`;
  add if not). Optionally add a `make eval-selftest` target wrapping this command.

### 8. End-to-end verify the judge runs from the vendored copy
- With **no** `PLUGIN_EVAL_SOURCE` in `.env`, run:
  `make eval-skill SKILL=plugins/boss-dev/agent-harness/skills/add-review-comment DEPTH=standard AUTH=api-key`
  → the report must contain a populated `## Model Usage` table (judge ran), **not** "No model
  usage (static-only evaluation)".
- `make eval` (quick/static across all skills) → confirms the non-llm `file://` source path also
  resolves (table prints scores, no errors).

### 9. Lint, test, and grep-clean
- `make lint` → green; confirm it did **not** scan `scripts/plugin_eval/`.
- `make test` → green (e.g. 766 passed); confirm the vendored `tests/` were **not** discovered.
- `grep -rn "git+https://github.com/wshobson/agents" scripts/eval-skills.py Makefile` → no
  **runtime default** remains (override examples in prose/docs are fine).
- `grep -rn "plugin-eval-apikey" . --exclude-dir=.git` → zero hits (no external-fork reference).

### 10. Version-bump and commit
- Editing `.claude/skills/skill-evals/SKILL.md` and `.claude/skills/version-bump-reviewer/SKILL.md`
  (repo-internal skills) triggers the version-bump hook → bump each skill's frontmatter
  `metadata.version` (prose/source-pointer change = patch tier). `scripts/eval-skills.py`,
  `Makefile`, `docs/**`, `pyproject.toml`, and the new `scripts/plugin_eval/**` are not versioned
  artifacts. Run the `version-bump-reviewer` skill; commit with conventional messages and the
  `(vX.Y.Z)` anchor. Nothing pushed unless asked.

### 11. Cleanup (manual, outside the repo)
- After verification, delete the external fork `/Users/bossjones/dev/wshobson/plugin-eval-apikey`.
- Update the memory note `plugin-eval-judge-apikey-fix.md` to point at `scripts/plugin_eval/`
  instead of the external fork + `.env` override.

## Testing Strategy
- **Patch-survival unit tests:** run the vendored package's own suite (Step 7) — covers
  `judge.py`/`engine.py` behavior, including the auth dispatch, without network/API key.
- **End-to-end judge:** Step 8 confirms the api-key backend actually reaches the Anthropic API
  and populates `model_usage` through the normal `make eval-skill` flow, sourced from the
  vendored copy (no override).
- **Quick/static path:** `make eval` exercises the `needs_llm=False` branch (bare `file://`
  source) to ensure both source forms resolve.
- **Tooling isolation:** `make lint` + `make test` confirm the vendored third-party tree is fully
  excluded and does not break the repo's gates.
- **Edge cases to watch:** `file://` URI with extras (`plugin-eval[llm,api] @ file://…`) must be a
  valid PEP 508 spec (verified working previously); a repo path containing spaces is handled by
  `.as_uri()`; the nested `scripts/plugin_eval/pyproject.toml` must not be adopted as a uv
  workspace member (no `[tool.uv.workspace]` exists — confirm); `force-exclude` matters because
  lint.py passes `scripts` explicitly.

## Acceptance Criteria
- `scripts/plugin_eval/` contains the buildable package (`src/`, `pyproject.toml`, `tests/`,
  `README.md` with credit, `LICENSE`) and **none** of the Claude-plugin cruft or `.venv`.
- The `--auth api-key` patch is present and the vendored test suite passes.
- `make eval-skill … AUTH=api-key` produces a judge-active report (populated `## Model Usage`)
  with `PLUGIN_EVAL_SOURCE` unset.
- `make lint` and `make test` are green; the vendored tree is excluded from both.
- No runtime default or `.env`/code reference points at the upstream git URL or the external fork
  (`grep` clean); `PLUGIN_EVAL_SOURCE` still works as an optional override.
- `README.md`/`VENDORING.md` credits `wshobson/agents`, states MIT license, and documents the
  patch for a future upstream PR.
- The two edited SKILL.md files are version-bumped; nothing pushed.

## Validation Commands
```bash
# patch present
grep -n "_query_via_api" scripts/plugin_eval/src/plugin_eval/layers/judge.py
grep -n "model_usage=" scripts/plugin_eval/src/plugin_eval/engine.py
# vendored package self-test (28 tests)
uv run --project scripts/plugin_eval --extra dev --extra llm --extra api -m pytest scripts/plugin_eval/tests -q
# judge runs from the vendored copy, no override (expect a "## Model Usage" table)
make eval-skill SKILL=plugins/boss-dev/agent-harness/skills/add-review-comment DEPTH=standard AUTH=api-key
# quick/static path resolves
make eval
# repo gates green + vendored tree excluded
make lint
make test
# no external/upstream runtime references remain
grep -rn "git+https://github.com/wshobson/agents" scripts/eval-skills.py Makefile
grep -rn "plugin-eval-apikey" . --exclude-dir=.git
```

## Notes
- **Upstreamability is a first-class goal:** keep the vendored `pyproject.toml` identical to
  upstream (separate `llm`/`api` extras) and put the "request both extras" decision in our
  `resolve_source` (`[llm,api]`). That way the future PR to `wshobson/agents` is just the
  `judge.py` + `engine.py` diff.
- **Why `file://` + extras and not a bare path:** `plugin-eval[llm,api] @ <X>` is a PEP 508 direct
  reference and `<X>` must be a URL; `Path.as_uri()` yields `file:///…`, which `uvx --from`
  accepts (verified previously). A bare filesystem path only works without the `[extras]` form.
- **No new repo dependencies** (`uv add` not needed) — the vendored package's deps are resolved by
  `uvx` into its own ephemeral env, exactly as today.
- **First run after vendoring** rebuilds the local package and downloads its deps
  (claude-agent-sdk, anthropic, pydantic, …); subsequent runs hit the uv cache.
