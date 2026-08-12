# Plan: Namespace harness artifacts to the plugin's source repo, not the working repo

> **How to execute this spec:** `/agent-harness:build specs/hooks-namespaced-to-plugin-repo.md`
>
> Work the **Step by Step Tasks** in order, committing at each numbered step. Test-first: each
> step's test file is written and failing before the module it covers.
>
> Amends [`specs/hooks-improved.md`](hooks-improved.md) — that spec is already implemented
> (v0.30.2); this one changes only how the runtime root is *named*. Step 6 updates its
> path-resolution contract so the two documents cannot disagree.

---

## Context

`specs/hooks-improved.md` is **already implemented** (agent-harness v0.30.2). Its path contract
derives the runtime root from the *project you happen to be working in*:

```python
# hooks/utils/harness_paths.py:62
return resolved_project_dir / f".{slug(resolved_project_dir.name)}"
```

So every repo you touch grows a differently-named dot-dir — `~/dev/foo/.foo/`,
`~/dev/bar/.bar/` — and a git worktree named `boss-skills-auth` gets its own `.boss-skills-auth/`.
Nothing is namespaced to the thing that actually *owns* those files: the agent-harness plugin,
which ships from the `boss-skills` marketplace repo.

**Intended outcome:** the dot-dir name comes from the plugin's own source repo, so it is
`.boss-skills/` in every project, every worktree, every machine — while staying **project-local**
(artifacts sit beside the work that produced them) and **backport-safe** (the identical bytes
copied into `aif-skills` produce `.aif-skills/`, so the portability grep still passes).

Decisions taken with the user:

| Question | Decision |
| --- | --- |
| Location | Per-project: `$CLAUDE_PROJECT_DIR/.boss-skills/{logs,data,cache}`. Only the **name** changes. |
| Derivation | Walk `Path(__file__)` ancestors to the first dir containing `.claude-plugin/marketplace.json`; use its slugged basename. No env var — status lines and standalone skill scripts don't reliably get `CLAUDE_PLUGIN_ROOT`. |
| Legacy `.{repo-name}/` dirs | Report only. `harness-doctor` lists them as "safe to delete after review". Never move, never delete, no read-fallback. |

Both anchors verified on this machine:

```text
/Users/bossjones/dev/bossjones/boss-skills/.claude-plugin/marketplace.json    # dev checkout
~/.claude/plugins/marketplaces/boss-skills/.claude-plugin/marketplace.json    # installed copy
```

The plugin's own `.claude-plugin/` holds `plugin.json` but **not** `marketplace.json`, so the walk
cannot stop early on it. That is the whole trick — checking for the *marketplace* manifest is what
makes "the plugins repo" a precise, testable anchor.

---

## Objective

1. `resolve_harness_root()` derives `<project>/.{plugin-repo-slug}/` instead of
   `<project>/.{project-slug}/`. Override precedence (`CLAUDE_HARNESS_DIR` → plugin option
   `HARNESS_DIR` → derived), the `CLAUDE_HOOKS_LOG_DIR` narrow logs-only override, and the
   `project_dir=` explicit-anchor argument all keep their current semantics.
2. The derivation lives in exactly **one** stdlib-only module that hooks, status lines,
   `harness-doctor`, and `setup-agent-harness` all share — no second copy of the walk.
3. `setup_harness.py`'s managed `.gitignore` block writes the plugin-namespaced dir.
4. `harness-doctor` reports the resolved namespace, where it came from, and any legacy
   `.{project-slug}/` it finds.
5. No plugin `.py` file contains the literal `boss-skills` (existing portability constraint holds).
6. Docs, `plugin.json` userConfig text, `specs/hooks-improved.md`, and the version are consistent.

---

## Problem Statement

The root name answers the wrong question. It says "which repo am I standing in", when the files
belong to "which plugin wrote these". Three concrete consequences:

- **Scatter.** Working across ten repos produces ten differently-named dot-dirs. There is no single
  name to `.gitignore` globally, no single name to `find`, and no single name to explain in docs.
- **Worktrees fragment.** A worktree at `.claude/worktrees/boss-skills-auth` gets `.boss-skills-auth/`,
  so the same project's artifacts split by branch for no reason anyone asked for.
- **Docs cannot name the thing.** Every doc says `.{repo-slug}/`, a placeholder the reader has to
  resolve mentally, instead of a name they can copy.

---

## Solution Approach

One new ~30-line module, one changed line of derivation, and a fan-out of consumers/docs.

### New: `hooks/utils/plugin_namespace.py`

Deliberately **stdlib-only with no intra-package imports** (same shape as `utils/preflight.py`).
That matters: `harness_paths.py` does `from utils.config import _option`, which forces standalone
loaders (`harness_doctor._harness_root()`) to build a fake `utils` package before they can import
it. A dependency-free module can be loaded by any script with a plain
`importlib.util.spec_from_file_location`, which is what keeps the single-source-of-truth promise
cheap enough that nobody re-copies the walk.

```python
DEFAULT_NAMESPACE = "agent-harness"

def slug(value: str) -> str: ...            # moved here from harness_paths (single definition)

def namespace_from(start: Path) -> tuple[str, Path | None]:
    """Pure: nearest ancestor of `start` holding a marketplace manifest → (slug, that dir)."""
    for ancestor in start.resolve().parents:
        if (ancestor / ".claude-plugin" / "marketplace.json").is_file():
            return slug(ancestor.name), ancestor
    return DEFAULT_NAMESPACE, None

@lru_cache(maxsize=1)
def plugin_namespace() -> str:
    return namespace_from(Path(__file__))[0]
```

Splitting the pure walk (`namespace_from`) from the cached `__file__`-bound wrapper is what makes
this unit-testable against synthetic trees in `tmp_path` — no monkeypatching of `__file__`, no
cache-clearing gymnastics.

`harness_paths.slug()` is **re-exported** from here rather than duplicated, so the existing
`slug()` edge-case tests keep passing unchanged and there is still exactly one implementation.

### Changed: `hooks/utils/harness_paths.py`

```diff
-    return resolved_project_dir / f".{slug(resolved_project_dir.name)}"
+    return resolved_project_dir / f".{plugin_namespace()}"
```

and the unresolvable-project branch (`harness_paths.py:59-60`) returns the *same relative* name
(`Path(f".{plugin_namespace()}")`) instead of the divergent `DEFAULT_HARNESS_DIR` literal — one
name, one place, no branch that can drift. `DEFAULT_HARNESS_DIR` collapses into
`plugin_namespace.DEFAULT_NAMESPACE`, preserving the "default string appears exactly once"
acceptance criterion from the original spec.

### Hot-path cost

Status lines re-run on every assistant message. The walk is ~6–8 `is_file()` stats, `lru_cache`d
per process, and does no `mkdir` — well inside the budget the original spec set for the status-line
path. Measure it anyway (step 7) rather than assuming.

---

## Relevant Files

### New files

- `plugins/boss-dev/agent-harness/hooks/utils/plugin_namespace.py` — the walk, `slug()`,
  `DEFAULT_NAMESPACE`. PEP 723, `requires-python = ">=3.11"`, `dependencies = []`.
- `plugins/boss-dev/agent-harness/hooks/tests/test_plugin_namespace.py`.

### Files to modify

- `hooks/utils/harness_paths.py:11,16-19,59-62` — import the namespace, re-export `slug`, replace
  both derivation branches, drop the local `_NON_ALPHANUMERIC` / `DEFAULT_HARNESS_DIR`.
- `hooks/tests/test_harness_paths.py:73-90` — the two tests that assert `.my-project` and
  `Path(DEFAULT_HARNESS_DIR)`.
- `skills/setup-agent-harness/scripts/setup_harness.py:140-150` — delete `harness_slug`; have
  `gitignore_patterns()` return `f".{plugin_namespace()}/"` via the existing importlib loader
  (~`:357`), matching `harness_doctor._load_hook_module()`.
- `skills/setup-agent-harness/scripts/tests/test_setup_harness.py:15,31-35` — `patterns[0]` is now
  namespace-derived, not `tmp_path.name`-derived.
- `skills/setup-agent-harness/SKILL.md:3,18-21` — the `description` says "repository-derived harness
  runtime root"; it is now plugin-derived. Edit it deliberately — the description is the triggering
  surface.
- `skills/harness-doctor/scripts/harness_doctor.py:98-101,155-161` — add the resolved namespace and
  its source dir to the report, and add legacy `.{slug(repo_root.name)}/` to `stale_artifacts`
  (only when it exists and differs from the resolved root), alongside the existing `logs/` and
  `.claude/data/` entries. The doctor **reports; it never deletes.**
- `skills/harness-doctor/scripts/tests/test_harness_doctor.py` + `SKILL.md` — cover the new field.
- `.claude-plugin/plugin.json:5,44` — version bump and the `HARNESS_DIR` description
  ("project-derived `.{repo-slug}`" → plugin-derived).
- `.claude-plugin/marketplace.json` (repo root) — matching version entry; must stay at parity.
- `.gitignore:274` — `.boss-skills/` is already present; add a comment noting it is now
  plugin-namespaced (identical value here, different meaning), so nobody "fixes" it later.
- `specs/hooks-improved.md:126-160` — update the path-resolution contract and the
  `slug(basename($CLAUDE_PROJECT_DIR))` narrative so the spec matches shipped behavior.

### Docs carrying the `.{repo-slug}` placeholder

Replace with `.{plugin-repo}` plus one worked example:

`plugins/boss-dev/agent-harness/docs/hooks.md:83,89-94,147` ·
`plugins/boss-dev/agent-harness/docs/getting-started.md:78,148,159` ·
`plugins/boss-dev/agent-harness/docs/commands.md:355` ·
`plugins/boss-dev/agent-harness/docs/status-lines.md:138` ·
`plugins/boss-dev/agent-harness/README.md:201` ·
`plugins/boss-dev/agent-harness/commands/update_status_line.md:2,20,32` ·
`docs/plugins/agent-harness.md:216,224` · `docs/tutorials/agent-harness/README.md:91` ·
`CLAUDE.md:67` · root `README.md:79`

Keep the placeholder abstract in shipped markdown (`.{plugin-repo}/`) with "in this repo,
`.boss-skills/`" as the example — a hardcoded `.boss-skills` in docs is wrong the moment the tree
is copied to `aif-skills`.

---

## Step by Step Tasks

Execute in order. Commit per numbered step. Test-first: the test file is written and failing before
the module it covers.

### 1. Write `hooks/tests/test_plugin_namespace.py` (red)

Against synthetic `tmp_path` trees, exercising `namespace_from()` only:

- An ancestor holding `.claude-plugin/marketplace.json` wins → its slugged basename.
- An intermediate ancestor holding `.claude-plugin/plugin.json` **without** `marketplace.json` is
  skipped. This is the real plugin-dir case; if it ever stops being skipped, the namespace silently
  becomes `agent-harness` everywhere.
- Nested marketplaces → the **nearest** ancestor wins.
- No manifest anywhere → `("agent-harness", None)`.
- Name slugging reuses the existing table (`My Repo (v2)` → `my-repo-v2`, `---` → `agent-harness`).
- One live assertion: `plugin_namespace() == slug(<the repo root this file lives in>.name)`,
  computed from `Path(__file__)` — **no `boss-skills` literal**, so it also passes in a fork.

### 2. Implement `hooks/utils/plugin_namespace.py` (green)

Per [`.claude/rules/python-scripts.md`](../.claude/rules/python-scripts.md) and
[`CLAUDE.md`](../CLAUDE.md): PEP 723 header, `requires-python = ">=3.11"`, `dependencies = []`,
`from __future__ import annotations`, full annotations, `pathlib.Path`. Stdlib only; **no**
`from utils.… import` — that is load-bearing for the standalone loaders.

### 3. Update `test_harness_paths.py` (red), then `harness_paths.py` (green)

New and changed assertions:

- Two different project dirs (`tmp/foo`, `tmp/bar`) → **same** dot-dir name, different parents.
  This is the whole point of the change; it deserves a named test.
- `test_derivation_uses_project_environment_not_current_working_directory` keeps asserting the
  *location* comes from `$CLAUDE_PROJECT_DIR` (not `os.getcwd()`) but no longer asserts
  `.my-project`.
- Unresolvable project dir → relative `Path(f".{plugin_namespace()}")`.
- Unchanged and must stay green: `CLAUDE_HARNESS_DIR` > plugin option > derived; `project_dir=`
  beats `CLAUDE_PROJECT_DIR`; `CLAUDE_HOOKS_LOG_DIR` moves **only** `logs_root()`; all resolvers
  stay side-effect free (`assert not root.exists()`); path-traversal guards on session/agent ids.

Then make the two-line change in `harness_paths.py` and delete its now-duplicated
`slug` / `_NON_ALPHANUMERIC` / `DEFAULT_HARNESS_DIR` in favour of the re-export.

### 4. Point `setup_harness.py` at the shared namespace

- `gitignore_patterns()` → `f".{plugin_namespace()}/"`; delete `harness_slug` and its now-dead
  `_NON_ALPHANUMERIC`.
- Load `plugin_namespace.py` by path with the loader already in the file (~`:357`); no `utils`
  package shim is needed, because the module has no intra-package imports.
- Update `test_setup_harness.py:15,31-35`. The managed block is delimited
  (`MANAGED_BLOCK_START` / `END`), so a re-run in a repo that already has `.{old-name}/`
  **rewrites the block in place** — verify that path with a test rather than assuming it. The stale
  `.{old-name}/` line disappears from the managed block; the directory itself is left alone.

### 5. Teach `harness-doctor` about the namespace and the legacy dir

- Report `namespace`, `namespace_source` (the dir holding `marketplace.json`, or `null` for the
  fallback), and the resolved root with its `logs/` / `data/` / `cache/` sizes.
- Add `legacy_project_root` to `stale_artifacts`: `repo_root / f".{slug(repo_root.name)}"`, emitted
  only when it exists **and** differs from the resolved root, with the existing "safe to delete
  after review" advice string.
- Extend `test_harness_doctor.py`; update `SKILL.md`. Never use `` ! ``-backtick patterns in a
  `SKILL.md` — see the parser bug
  ([GitHub #12781](https://github.com/anthropics/claude-code/issues/12781)) noted in `CLAUDE.md`.

### 6. Docs, spec, and config text

- Replace every `.{repo-slug}` occurrence listed under **Relevant Files** with `.{plugin-repo}`
  plus a worked example, and restate the resolution order in `docs/hooks.md:89-94`.
- `plugin.json:44` `HARNESS_DIR` description.
- `.gitignore:274` comment.
- `specs/hooks-improved.md` — rewrite the path-resolution contract so it no longer documents
  project-basename derivation.

### 7. Measure the status-line cost, then bump the version

- Time `plugin_namespace()` cold (`python -X importtime`, or a `timeit` loop over `namespace_from`)
  from a status-line-like invocation. Record the number in `docs/hooks.md`. If it is not trivially
  small, say so rather than shipping quietly.
- Run the [`version-bump-reviewer`](../.claude/skills/version-bump-reviewer/SKILL.md) skill.
  Expected **minor** → `0.31.0` (behavior change to the artifact path in a pre-1.0 plugin). It must
  bump `plugin.json:5` **and** the `agent-harness` entry in the root `.claude-plugin/marketplace.json`
  — they are at parity today and must stay there.

### 8. Validate

Run everything under **Validation Commands**, then the live check under **Verification**.

---

## Testing Strategy

Three layers, matching the suite that already exists:

- **Unit (pure).** `namespace_from()` against synthetic trees; `harness_paths` precedence branches;
  the same-name-across-two-projects invariant; the logs-only override divergence.
- **Contract.** `setup_harness.gitignore_patterns()` returns the namespaced entry; the managed
  block rewrites in place over a stale one.
- **End-to-end.** The existing `hooks/tests/` sweep must still produce
  `<root>/logs/<session>/<Event>.jsonl` and create **no** `logs/`, no `.claude/data/`, and no
  `.{project-name}/` directory in the tmp project.

Named edge cases:

- Plugin tree with no `marketplace.json` above it (vendored into `.claude/hooks/` of a foreign
  repo) → `.agent-harness/`, no crash.
- `CLAUDE_HARNESS_DIR` / plugin-option `HARNESS_DIR` set → still wins over the namespace.
- `project_dir=` explicit argument (the status-line path) → still wins over `CLAUDE_PROJECT_DIR`.
- Marketplace dir with an awkward name (`My Repo (v2)`) → `.my-repo-v2/`.
- Git worktree under `.claude/worktrees/boss-skills-auth` → root is `<worktree>/.boss-skills/`,
  **not** `.boss-skills-auth/`. This is a concrete regression the old derivation had; pin it.

---

## Acceptance Criteria

1. In any project, the resolved root is `<project>/.{plugin-repo-slug}/` — an identical name across
   projects, worktrees, and machines.
2. The derivation exists in exactly one module: `harness_slug` is gone from `setup_harness.py`, and
   no non-test plugin file derives a root from a project name.
3. `grep -rn 'boss-skills' plugins/boss-dev/agent-harness/ --include='*.py' | grep -v '/tests/'`
   returns nothing beyond the pre-existing, documented `or "boss-skills"` fallback in
   `setup_harness._plugin_id()`.
4. Override precedence, the narrow `CLAUDE_HOOKS_LOG_DIR` scope, the `project_dir=` anchor, and the
   traversal guards are unchanged (their tests pass untouched except for the two name assertions).
5. `setup_harness apply --gitignore` writes `.{plugin-repo}/` and rewrites an existing managed block
   in place.
6. `harness-doctor` reports the namespace, its source, and any legacy `.{project-slug}/`; it deletes
   nothing.
7. No legacy directory is moved, deleted, or read from.
8. `make lint`, `make test`, `make test-agent-harness`, `make verify-structure`,
   `make markdown-lint` pass with zero warnings.
9. `plugin.json` and `marketplace.json` versions are bumped and identical.
10. No shipped `.md` still says the root is derived from the project or repository name.

---

## Validation Commands

```bash
# Full gate — CLAUDE.md requires zero warnings
make lint
make test
make test-agent-harness
make verify-structure
make markdown-lint

# Focused suites
uv run pytest -s plugins/boss-dev/agent-harness/hooks/tests/
uv run pytest -s plugins/boss-dev/agent-harness/skills/harness-doctor/scripts/tests/
uv run pytest -s plugins/boss-dev/agent-harness/skills/setup-agent-harness/scripts/tests/

# The namespace resolves from this checkout (must print: boss-skills)
uv run python - <<'PY'
import importlib.util, pathlib
p = pathlib.Path("plugins/boss-dev/agent-harness/hooks/utils/plugin_namespace.py")
spec = importlib.util.spec_from_file_location("pn", p)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
print(m.plugin_namespace())
PY

# Backport portability (must print nothing)
grep -rn 'boss-skills' plugins/boss-dev/agent-harness/ --include='*.py' \
  | grep -v '/tests/' | grep -v 'or "boss-skills"'

# Nobody derives the LIVE root from a project name any more (must print nothing).
# harness_doctor._legacy_project_root() is excluded by content: it deliberately
# reconstructs the old repository-named root so the doctor can report it as stale.
# Excluded by content, not by file, so any *other* project-name derivation in that
# file still fails the check.
grep -rn 'slug(.*\.name)\|harness_slug' plugins/boss-dev/agent-harness/ --include='*.py' \
  | grep -v '/tests/' | grep -v plugin_namespace.py \
  | grep -v 'repo_root / f".{slug(repo_root.name)}"'

# No stale placeholder left in shipped docs (must print nothing)
grep -rn 'repo-slug' plugins/ docs/ CLAUDE.md README.md

# Version parity (the two values must match)
jq -r .version plugins/boss-dev/agent-harness/.claude-plugin/plugin.json
jq -r '.plugins[] | select(.name=="agent-harness") | .version' .claude-plugin/marketplace.json
```

---

## Verification (live)

`agent-harness@boss-skills` is the globally enabled plugin on this machine
(`~/.claude/settings.json:29`), installed at
`~/.claude/plugins/marketplaces/boss-skills/plugins/boss-dev/agent-harness` — so the installed copy
must be refreshed (or reinstalled from this checkout) before the live check, or it exercises the old
code and passes for the wrong reason.

1. In **a repo that is not boss-skills** (for example `~/dev/mlflow`), start
   `claude --debug-file /tmp/cc-hooks.log`, issue a prompt, let it call a tool, then stop.
2. `ls -d ~/dev/mlflow/.boss-skills/logs/*/` → exists; `ls -d ~/dev/mlflow/.mlflow` → absent.
3. `jq -r .hook_event_type ~/dev/mlflow/.boss-skills/logs/*/*.jsonl | sort | uniq -c`.
4. Status-line round-trip (three processes, the most likely thing to half-work): run
   `/update_status_line` to set a key, confirm it lands in
   `.boss-skills/data/sessions/<session_id>.json` **and** renders.
5. In a boss-skills **worktree**, confirm the root is `.boss-skills/`, not `.boss-skills-<branch>/`.
6. `make doctor` → reports the namespace, its source path, and any legacy `.{project-slug}/`.

If anything fails, use `superpowers:systematic-debugging`; `--debug-file` shows which hook matched
and its exit code.

---

## Notes

- No new dependencies; stdlib only. `log_event.py` runs on every event, so the added import must
  stay cold-start cheap — that is why `plugin_namespace.py` imports nothing beyond `functools`,
  `pathlib`, and `re`.
- The fail-open rule is untouched: every hook still exits 0 on every error path.
- Out of scope: migrating or deleting legacy dirs, changing where `logs` / `data` / `cache` sit
  relative to the root, and the worktree skills' separate `.worktree-logs/` mechanism.
