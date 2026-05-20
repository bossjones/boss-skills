# Plan: Port PR-Review and Git-Worktree Skills into the `agent-harness` Plugin

## Task Description

Port ten skills from two external sources into the `agent-harness` plugin of the
boss-skills repository, under `plugins/boss-dev/agent-harness/skills/`:

**From `/Users/bossjones/dev/mlflow/.claude/skills/` (4 skills):**

- `fetch-diff` — fetch a PR diff with line numbers and auto-generated-file masking
- `fetch-unresolved-comments` — fetch unresolved PR review threads via the GitHub GraphQL API
- `pr-review` — review a PR and emit a schema-validated local review payload
- `add-review-comment` — post a single inline review comment to a PR

**From `/Users/bossjones/dev/FlorianBruniaux/claude-code-ultimate-guide/examples/skills/` (6 skills):**

- `git-worktree` — create isolated git worktrees for feature development
- `git-worktree-clean` — batch-clean stale/merged worktrees
- `git-worktree-remove` — safely remove a single worktree with branch cleanup
- `git-worktree-status` — report background verification status for a worktree
- `release-notes-generator` — model-invocable release-notes skill with `assets/` + `references/`
- `release-notes` — command-style release-notes skill (`$ARGUMENTS`-driven)

The task includes an explicit evaluation: **port the mlflow `src/skills` Python
package as-is vs. port it a different way.** That evaluation is resolved in the
*Solution Approach* below.

## Objective

When this plan is complete, the `agent-harness` plugin ships a `skills/`
directory containing ten self-contained, distributable skills. Each skill:

- Lives at `plugins/boss-dev/agent-harness/skills/<name>/SKILL.md` and is
  auto-discovered by Claude Code.
- Has **no dependency on the mlflow repo layout** or on a repo-level `uv`
  workspace — it works after `/plugin install agent-harness@boss-skills`.
- Passes `scripts/skill_validation.py`, `scripts/verify-structure.py`,
  `make lint`, `make markdown-lint`, and `make test`.
- Carries any executable logic as **PEP 723 standalone scripts** matching the
  repo's documented convention.

The `agent-harness` plugin manifest and the marketplace entry are version-bumped
and kept in sync, and the plugin README is updated to list the new skills.

## Problem Statement

The `agent-harness` plugin currently has empty scaffolding — its README says
"Skills will live in `skills/<skill-name>/SKILL.md`" but no `skills/` directory
exists. Two mature skill collections already exist elsewhere on disk and solve
real agentic-dev workflows (PR review, worktree lifecycle, release notes), but
they cannot be used by the boss-skills marketplace as-is:

1. **The mlflow skills depend on a `uv` workspace package.** All four mlflow
   skills invoke `uv run --package skills skills <command>`. The `--package
   skills` flag resolves a `uv` *workspace member* declared in mlflow's repo.
   The package source is `/Users/bossjones/dev/mlflow/.claude/skills/src/skills/`
   with its own `pyproject.toml` (`name = "skills"`, `[project.scripts]`). This
   only works *inside the mlflow checkout*. A plugin installed into another
   user's `~/.claude/plugins/` has no such workspace member, so every invocation
   would fail with "package `skills` not found".

2. **The mlflow code is mlflow-specific in places.** `fetch_diff.py` hardcodes
   `mlflow/protos` auto-generated-file detection; `pr-review/SKILL.md` references
   `.github/instructions/code-review.instructions.md` and `.claude/rules/`;
   `validate_review.py` computes its schema path via `Path(__file__).parents[3]`,
   which is tightly coupled to the `.claude/skills/src/skills/commands/` layout.

3. **The ultimate-guide skills use command-only frontmatter.** They rely on
   `effort`, `disable-model-invocation`, `argument-hint`, and `$ARGUMENTS`, and
   cross-link each other with `./git-worktree.md`-style relative links that
   assume a flat directory. They need light normalization for the
   one-directory-per-skill layout boss-skills uses.

4. **boss-skills has its own validation gate.** `scripts/skill_validation.py`
   enforces name/description/structure rules (16 checks), `name` must match the
   directory, and the GitHub #12781 backtick-bang parser bug is checked. Ported
   skills must pass these.

5. **boss-skills runs a `plugin-eval` quality gate.** `make eval-ci` scores
   every `plugins/**/SKILL.md` and fails the build for any skill below
   `EVAL_THRESHOLD` (57); CI runs it at static depth on Python 3.13. Porting
   ten skills into `plugins/` adds them to that discovered set — each must
   clear the threshold, and the Makefile's baseline comment must be refreshed.

## Solution Approach

### Evaluation: porting the `src/skills` package — three options

The mlflow `src/skills` package (≈10 files) has this dependency surface:

| Skill | Needs from `src/skills` | Third-party deps |
|-------|------------------------|------------------|
| `fetch-diff` | `commands/fetch_diff.py`, `github/{client,types,utils}.py`, `cli.py` | `aiohttp`, `pydantic` |
| `fetch-unresolved-comments` | `commands/fetch_unresolved_comments.py`, `github/*` | `aiohttp`, `pydantic` |
| `pr-review` | `commands/validate_review.py` + `review-payload.schema.json` | `jsonschema` |
| `add-review-comment` | **nothing** — pure `gh api` bash | none |

Note `src/skills/commands/fetch_logs.py` powers a fifth skill (`analyze-ci`) that
is **out of scope** and will not be ported.

**Option A — Port `src/skills` verbatim as a `uv` workspace package.**
Copy `.claude/skills/src/skills/` + its `pyproject.toml` into the repo and
register it as a `uv` workspace member in the boss-skills root `pyproject.toml`.
*Rejected.* This makes the skills work only inside the boss-skills checkout, not
after `/plugin install`. Plugins are copied to `~/.claude/plugins/` standalone;
a workspace dependency cannot follow them. It also pollutes the boss-skills root
project with an unrelated package and ships `fetch_logs.py` we do not want.

**Option C — Vendor `src/skills` as a shared in-plugin module.**
Place a trimmed `skills` package under a non-skill directory (e.g.
`plugins/boss-dev/agent-harness/skills/_shared/`) and have each PEP 723 script
manipulate `sys.path` to import it. *Rejected as default.* It works and removes
duplication, but adds `sys.path` fragility, an import surface that the repo's
`skill_validation.py`/`verify-structure.py` do not expect, and a directory that
looks like a skill but is not. The shared code is small enough that the
duplication Option B incurs is cheaper than this indirection.

**Option B — Convert each command into a self-contained PEP 723 script
(RECOMMENDED).**
Drop the `uv` workspace package entirely. For each skill that needs executable
logic, ship a single standalone script under the skill's own `scripts/`
directory with PEP 723 inline metadata. The trimmed GitHub client logic
(`GitHubClient` async methods actually used: `get_pr`, `get_pr_diff`,
`get_compare_diff`, `graphql`; plus `parse_pr_url`, `get_github_token`, and the
small pydantic models) is **inlined into each of the two scripts that need it**
(`fetch_diff.py`, `fetch_unresolved_comments.py`).

This is the recommended approach because:

- **Distributable.** A PEP 723 script is fully self-contained; `uv run` resolves
  its inline dependencies on demand. It works identically inside boss-skills and
  after `/plugin install` into any project.
- **Matches house style.** `CLAUDE.md` explicitly documents PEP 723 standalone
  scripts, and existing skills already follow it — `twitter-media-downloader`
  ships `scripts/download.py` + `scripts/tests/`, `proxmox-infra` ships
  `tools/*.py` invoked via `uv run "${CLAUDE_SKILL_DIR}/..."`.
- **No mlflow coupling.** Each script owns its dependencies and its schema path;
  nothing reaches outside the skill directory.
- **Small, stable duplication.** The shared GitHub client subset is ≈90 lines.
  Two copies of stable, rarely-changing HTTP plumbing is an acceptable trade
  against the `sys.path` indirection of Option C.

The relevant GitHub client subset to inline is small — the four async methods
above plus token discovery (`GH_TOKEN` env or `gh auth token`) and PR-URL
parsing. The `aiohttp` async client is ported as-is for fidelity with proven
mlflow code; an optional later simplification to synchronous `urllib` (dropping
the `aiohttp` dependency) is noted in *Notes* but is **not** part of this plan.

### Invocation convention

mlflow skills call `uv run --package skills skills fetch-diff <url>`. After
porting, scripts are invoked with the absolute, install-safe form already used
by `proxmox-infra`:

```bash
uv run "${CLAUDE_SKILL_DIR}/scripts/fetch_diff.py" <pr_url> [--files <pattern> ...]
```

### Skill normalization rules (applied to all ten)

- `name` in frontmatter MUST equal the skill directory name (validator Rule 3).
- Rewrite cross-skill links from the ultimate-guide flat form
  `./git-worktree.md` to the directory form `../git-worktree/SKILL.md`.
- `pr-review` cross-references `fetch-diff` — update its link to
  `../fetch-diff/SKILL.md` (both live in the same plugin after porting).
- Remove mlflow-specific path references from `pr-review/SKILL.md`
  (`.github/instructions/code-review.instructions.md`, `.claude/rules/`); the
  severity table is already self-contained in the body, and the style-guide step
  becomes "consult the target repo's `CLAUDE.md` and any `.claude/rules/` if
  present."
- Generalize `is_autogenerated_file()` in `fetch_diff.py`: drop the
  `mlflow/protos` branch; keep the generic lock-file names (`uv.lock`,
  `yarn.lock`, `package-lock.json`) and the generic "Generated by the protocol
  buffer compiler" Java-header check.
- `extract_stacked_pr_base_sha()` keys off a literal "Stacked PR" section in PR
  bodies. It is harmless in non-mlflow repos (it simply returns `None`); keep it
  but add a docstring note that it is an mlflow-flavored convention.
- Preserve scoped `Bash(...)` entries in `allowed-tools` where mlflow used them
  (they encode least-privilege intent). The repo validator emits only
  WARNING-level findings for these, which `make` tolerates in non-strict mode;
  Step 9 optionally hardens the validator to recognize them.

### Validation & eval feedback loop

Two fast, fully offline gates form the feedback loop applied to every ported
skill. Both are instant and need no LLM — the "fastest validation possible":

1. **Structural validation — `scripts/skill_validation.py`** (see
   `docs/skill-validation.md`). Deterministic, offline. Checks the 17 rule IDs:
   `name` matches its directory, `description` has a trigger phrase and no
   vague filler, frontmatter parses, no backtick-bang #12781, body has
   instructions and an example. ERROR findings fail; `--strict` also fails on
   WARNINGs.
2. **Quality score — `scripts/eval-skills.py` at the `static` layer** (see
   `docs/eval-skills.md`). The default layer: instant, free, offline, no LLM.
   Runs `plugin-eval` and prints a composite score, badge, and anti-pattern
   count per skill. `make eval` reports; `make eval-ci` gates at
   `EVAL_THRESHOLD` (currently 57).

**Per-skill loop** — for each of the ten skills, after writing its `SKILL.md`:

1. `uv run scripts/skill_validation.py <skill-dir> --strict` — fix every
   ERROR; triage each WARNING (fix it, or note why it is accepted).
2. `uv run scripts/eval-skills.py --skill <skill-dir>` — read the static
   score, badge, and anti-pattern count.
3. Revise the `SKILL.md` and repeat until validation is ERROR-clean and the
   static score is at or above `EVAL_THRESHOLD` (57).

`eval-skills.py` discovers skills by globbing `plugins/**/SKILL.md`, so the ten
new skills join the scored set automatically the moment their `SKILL.md` lands.
CI runs `make eval-ci` (static depth, Python 3.13) — **every ported skill must
clear `EVAL_THRESHOLD` at static depth or the build breaks.** The per-skill
loop exists to guarantee that before a skill is considered done.

The deeper, LLM-backed layers (`llm-judge`, `monte-carlo`, `all`, `make
eval-skill`, and `plugin-eval certify`) are deliberately **out of scope** here.
They belong to a future "enhance-a-skill" subagent or slash command that will
wrap a richer, judged feedback loop; this plan keeps the cycle to the fastest
offline layers only.

## Relevant Files

Use these files to complete the task:

**Source — mlflow skills (read, do not modify):**

- `/Users/bossjones/dev/mlflow/.claude/skills/fetch-diff/SKILL.md` — source SKILL.md
- `/Users/bossjones/dev/mlflow/.claude/skills/fetch-unresolved-comments/SKILL.md`
- `/Users/bossjones/dev/mlflow/.claude/skills/pr-review/SKILL.md`
- `/Users/bossjones/dev/mlflow/.claude/skills/pr-review/review-payload.schema.json` — copy verbatim
- `/Users/bossjones/dev/mlflow/.claude/skills/add-review-comment/SKILL.md`
- `/Users/bossjones/dev/mlflow/.claude/skills/src/skills/commands/fetch_diff.py` — logic to inline
- `/Users/bossjones/dev/mlflow/.claude/skills/src/skills/commands/fetch_unresolved_comments.py` — logic to inline
- `/Users/bossjones/dev/mlflow/.claude/skills/src/skills/commands/validate_review.py` — logic to inline
- `/Users/bossjones/dev/mlflow/.claude/skills/src/skills/github/{client,types,utils}.py` — trimmed client to inline

**Source — ultimate-guide skills (read, do not modify):**

- `/Users/bossjones/dev/FlorianBruniaux/claude-code-ultimate-guide/examples/skills/git-worktree/SKILL.md`
- `/Users/bossjones/dev/FlorianBruniaux/claude-code-ultimate-guide/examples/skills/git-worktree-clean/SKILL.md`
- `/Users/bossjones/dev/FlorianBruniaux/claude-code-ultimate-guide/examples/skills/git-worktree-remove/SKILL.md`
- `/Users/bossjones/dev/FlorianBruniaux/claude-code-ultimate-guide/examples/skills/git-worktree-status/SKILL.md`
- `/Users/bossjones/dev/FlorianBruniaux/claude-code-ultimate-guide/examples/skills/release-notes/SKILL.md`
- `/Users/bossjones/dev/FlorianBruniaux/claude-code-ultimate-guide/examples/skills/release-notes-generator/` — full tree (`SKILL.md`, `assets/`, `references/`)

**Repo files to read for conventions:**

- `plugins/social-media/twitter-tools/skills/twitter-media-downloader/` — reference for `scripts/` + `scripts/tests/` layout
- `plugins/boss-homelab/proxmox-infra/skills/proxmox-infrastructure/SKILL.md` — reference for `${CLAUDE_SKILL_DIR}` invocation
- `scripts/skill_validation.py` — the 16-rule skill validator (gate)
- `scripts/verify-structure.py` — marketplace/plugin manifest validator (gate)
- `devtools/lint.py` — lints `devtools`, `scripts`, `plugins` with ruff; type-checks only `devtools`, `scripts`
- `CLAUDE.md` — PEP 723 + code-standards reference
- `docs/skill-validation.md` — criteria reference for `scripts/skill_validation.py`
  (the 17 rule IDs, severities, frontmatter short-circuit, worked pass/fail example)
- `docs/eval-skills.md` — reference for `scripts/eval-skills.py` / `plugin-eval`
  (layers, thresholds, skill discovery, Makefile + CI integration)
- `scripts/eval-skills.py` — the `plugin-eval` quality-gate wrapper
- `Makefile` — `eval`, `eval-ci`, `eval-skill` targets and `EVAL_THRESHOLD`
- `.github/workflows/ci.yml` — runs `make eval-ci` at static depth, Python 3.13

**Repo files to modify:**

- `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json` — version bump `0.1.0` → `0.2.0`
- `.claude-plugin/marketplace.json` — sync `agent-harness` entry `version` to `0.2.0`
- `plugins/boss-dev/agent-harness/README.md` — replace "Skills — _Coming soon._" with the skill list
- `scripts/skill_validation.py` — optional Step 9 hardening for scoped `allowed-tools`
- `Makefile` — re-baseline `EVAL_THRESHOLD` and its baseline comment after the
  ten skills are ported (Step 11)

### New Files

```
plugins/boss-dev/agent-harness/skills/
├── fetch-diff/
│   ├── SKILL.md
│   └── scripts/
│       ├── fetch_diff.py                       # PEP 723: aiohttp, pydantic
│       └── tests/test_fetch_diff.py
├── fetch-unresolved-comments/
│   ├── SKILL.md
│   └── scripts/
│       ├── fetch_unresolved_comments.py        # PEP 723: aiohttp, pydantic
│       └── tests/test_fetch_unresolved_comments.py
├── pr-review/
│   ├── SKILL.md
│   ├── review-payload.schema.json              # copied verbatim from mlflow
│   └── scripts/
│       ├── validate_review.py                  # PEP 723: jsonschema
│       └── tests/test_validate_review.py
├── add-review-comment/
│   └── SKILL.md                                # pure gh-api bash, no script
├── git-worktree/
│   └── SKILL.md
├── git-worktree-clean/
│   └── SKILL.md
├── git-worktree-remove/
│   └── SKILL.md
├── git-worktree-status/
│   └── SKILL.md
├── release-notes-generator/
│   ├── SKILL.md
│   ├── assets/{README.md, changelog-template.md, slack-template.md}
│   └── references/{README.md, commit-categories.md, tech-to-product-mappings.md}
└── release-notes/
    └── SKILL.md
```

## Implementation Phases

### Phase 1: Foundation

Create the `skills/` directory tree under `agent-harness`, study the source
files in depth, and confirm the boss-skills validation gates so later phases
have a clear pass/fail target. Read `docs/skill-validation.md` and
`docs/eval-skills.md`, then run `make eval` and `skill_validation.py` once to
record the pre-port baseline (the three existing skills) — later steps measure
ported skills against it. Port the four "documentation-only" git-worktree
skills first — they are pure markdown and exercise the normalization rules
(cross-link rewrites, frontmatter) with no Python risk.

### Phase 2: Core Implementation

Port the two release-notes skills (markdown + `assets/` + `references/`), then
the four mlflow skills. The mlflow skills are the high-risk work: convert the
`src/skills` package into three PEP 723 scripts (`fetch_diff.py`,
`fetch_unresolved_comments.py`, `validate_review.py`) per Option B, inlining the
trimmed GitHub client, and rewrite each SKILL.md to the `${CLAUDE_SKILL_DIR}`
invocation form. Write tests alongside the scripts (TDD: the pure functions —
`filter_diff`, `is_autogenerated_file`, `format_comments`, schema validation —
get tests written before/with the port). Each ported skill passes through the
per-skill feedback loop (strict structural validation + static `plugin-eval`
score) before the next skill is started.

### Phase 3: Integration & Polish

Bump the `agent-harness` plugin version and sync the marketplace entry, update
the plugin README, run the full validation suite, and fix every error. Optionally
harden `skill_validation.py` for scoped `allowed-tools`. Re-baseline
`EVAL_THRESHOLD` across all thirteen skills and run `make eval-ci` as part of
the final gate.

## Step by Step Tasks

IMPORTANT: Execute every step in order, top to bottom.

### 1. Scaffold the skills directory and confirm gates

- Create `plugins/boss-dev/agent-harness/skills/` and the ten per-skill
  subdirectories listed in *New Files*.
- Run `uv run scripts/skill_validation.py plugins/boss-dev/agent-harness/skills`
  and `uv run scripts/verify-structure.py` once now to capture the baseline
  (expected: clean, since no SKILL.md exists yet) and confirm both scripts run.
- Re-read `scripts/skill_validation.py` rules so each ported SKILL.md is written
  to pass: `name` matches directory, description ≤1024 chars, no vague phrases
  ("when needed", "as appropriate"), no backtick-bang patterns inside fenced
  code blocks (#12781).
- Read `docs/skill-validation.md` and `docs/eval-skills.md` in full — they
  define the two feedback-loop gates and how a `SKILL.md` passes each.
- Run `make eval` now to record the pre-port static-score baseline for the
  three existing skills; this is the reference the ten ported skills are
  measured against.

### 2. Port the four git-worktree skills (markdown only)

- For each of `git-worktree`, `git-worktree-clean`, `git-worktree-remove`,
  `git-worktree-status`: copy the source `SKILL.md` into the new directory.
- Keep the existing frontmatter fields (`name`, `description`, `argument-hint`,
  `effort`, `disable-model-invocation`) — `skill_validation.py` does not reject
  unknown optional fields; it only checks `name`, `description`, `allowed-tools`,
  and `model`.
- Rewrite companion cross-links from the flat form to the directory form, e.g.
  `[`/git-worktree-status`](./git-worktree-status.md)` →
  `[`/git-worktree-status`](../git-worktree-status/SKILL.md)`.
- Verify each `description` is concrete and contains a trigger phrase
  ("Use when…"); tighten any that read as vague.
- Leave the `$ARGUMENTS` trailers as-is — these skills are command-style.
- Feedback loop: for each of the four skills, run
  `uv run scripts/skill_validation.py <skill-dir> --strict` then
  `uv run scripts/eval-skills.py --skill <skill-dir>`; revise the `SKILL.md`
  until it is ERROR-clean and its static score is ≥ `EVAL_THRESHOLD` (see
  *Validation & eval feedback loop*).

### 3. Port the two release-notes skills

- Copy `release-notes/SKILL.md` into `skills/release-notes/SKILL.md`.
- Copy the full `release-notes-generator/` tree: `SKILL.md`, `assets/`
  (`README.md`, `changelog-template.md`, `slack-template.md`), and `references/`
  (`README.md`, `commit-categories.md`, `tech-to-product-mappings.md`).
- In `release-notes-generator/SKILL.md`, drop the dangling "Related Skills"
  entries that point at skills not in this repo (`github-actions-templates`,
  `changelog-generator`) or replace them with a note that they are external
  inspirations — otherwise `make link-check` / reviewers flag dead references.
- Confirm both `description` fields stay ≤1024 chars (the generator's is long —
  measure it).
- Feedback loop: for each of the two skills, run
  `uv run scripts/skill_validation.py <skill-dir> --strict` then
  `uv run scripts/eval-skills.py --skill <skill-dir>`; revise the `SKILL.md`
  until it is ERROR-clean and its static score is ≥ `EVAL_THRESHOLD` (see
  *Validation & eval feedback loop*).

### 4. Port `add-review-comment` (no script)

- Copy `add-review-comment/SKILL.md` verbatim — it is pure `gh api` bash with no
  package dependency.
- Verify the `allowed-tools` list. mlflow uses YAML-list form with scoped
  entries (`Bash(gh api:*)`, etc.); keep them. They produce only WARNING-level
  validator findings (see Step 9).
- Feedback loop: run
  `uv run scripts/skill_validation.py plugins/boss-dev/agent-harness/skills/add-review-comment --strict`
  then `uv run scripts/eval-skills.py --skill plugins/boss-dev/agent-harness/skills/add-review-comment`;
  revise the `SKILL.md` until it is ERROR-clean and its static score is ≥
  `EVAL_THRESHOLD` (see *Validation & eval feedback loop*).

### 5. Build the `fetch-diff` PEP 723 script

- Create `skills/fetch-diff/scripts/fetch_diff.py` with a PEP 723 header:

  ```python
  #!/usr/bin/env -S uv run --script --quiet
  # /// script
  # requires-python = ">=3.13"
  # dependencies = ["aiohttp", "pydantic"]
  # ///
  ```

- Inline the trimmed GitHub client: `parse_pr_url`, `get_github_token` (from
  `github/utils.py`), the `GitRef`/`PullRequest` pydantic models (from
  `github/types.py`), and a `GitHubClient` with only `__aenter__`/`__aexit__`,
  `_get_json`, `_get_text`, `get_pr`, `get_pr_diff`, `get_compare_diff` (from
  `github/client.py`). Use `typing.Self` (Python 3.13) instead of
  `typing_extensions.Self`.
- Inline the `fetch_diff` logic verbatim from `commands/fetch_diff.py`:
  `extract_stacked_pr_base_sha`, `filter_diff`, `is_autogenerated_file`,
  `fetch_diff`, and an `argparse`-based `main()` (replacing the `register`/`run`
  subparser wiring with a direct `argparse.ArgumentParser`).
- Generalize `is_autogenerated_file()`: remove the `mlflow/protos` branch; keep
  the lock-file and protobuf-Java-header checks.
- Keep code-standards compliance: `from __future__ import annotations`,
  `pathlib.Path`, absolute style, modern typing (`str | None`, `list[str]`),
  100-char lines, `# ruff: noqa: T201` for the intentional `print`.

### 6. Build the `fetch-unresolved-comments` PEP 723 script

- Create `skills/fetch-unresolved-comments/scripts/fetch_unresolved_comments.py`
  with the same PEP 723 header (`aiohttp`, `pydantic`).
- Inline the trimmed GitHub client subset it needs: `parse_pr_url`,
  `get_github_token`, the `GitHubClient.graphql` method, and the `ReviewComment`
  / `ReviewThread` pydantic models (from `github/types.py`).
- Inline the `fetch_unresolved_comments` logic verbatim from
  `commands/fetch_unresolved_comments.py`: `REVIEW_THREADS_QUERY`,
  `format_comments`, `UnresolvedCommentsResult`, and an `argparse` `main()`.

### 7. Build the `pr-review` skill (script + schema + SKILL.md)

- Copy `review-payload.schema.json` verbatim into `skills/pr-review/`.
- Create `skills/pr-review/scripts/validate_review.py` with a PEP 723 header
  (`requires-python = ">=3.13"`, `dependencies = ["jsonschema"]`).
- Inline the `validate_review.py` logic, but change the schema-path default from
  `Path(__file__).parents[3] / "pr-review" / "review-payload.schema.json"` to
  `Path(__file__).resolve().parent.parent / "review-payload.schema.json"` (the
  sibling of `scripts/`). Keep `--schema` as an override.
- Port `pr-review/SKILL.md`:
  - Update the `fetch-diff` cross-link to `../fetch-diff/SKILL.md`.
  - Replace the `validate-review` invocation
    `uv run --package skills skills validate-review /tmp/review-payload.json`
    with `uv run "${CLAUDE_SKILL_DIR}/scripts/validate_review.py" /tmp/review-payload.json`.
  - Replace the `Edit(//tmp/review-payload.json)` and other `allowed-tools` with
    forms valid for this repo; keep `Skill` (needed to invoke `fetch-diff`) and
    note it triggers a WARNING until Step 9.
  - Remove mlflow-only path references (`.github/instructions/…`,
    `.claude/rules/`); reword the style-guide bullet to be repo-agnostic.
  - Keep `disable-model-invocation: true`, `argument-hint`, `arguments`.
- Feedback loop: run
  `uv run scripts/skill_validation.py plugins/boss-dev/agent-harness/skills/pr-review --strict`
  then `uv run scripts/eval-skills.py --skill plugins/boss-dev/agent-harness/skills/pr-review`;
  revise the `SKILL.md` until it is ERROR-clean and its static score is ≥
  `EVAL_THRESHOLD` (see *Validation & eval feedback loop*).

### 8. Rewrite the mlflow SKILL.md invocations

- In `fetch-diff/SKILL.md` and `fetch-unresolved-comments/SKILL.md`, replace
  every `uv run --package skills skills <cmd>` example with
  `uv run "${CLAUDE_SKILL_DIR}/scripts/<script>.py"`.
- Update `allowed-tools` accordingly (e.g.
  `Bash(uv run:*)` or bare `Bash` — see Step 9 for the WARNING trade-off).
- Keep the rich "Output Example" / "Example Output" sections; verify no
  fenced code block contains a backtick-bang pattern (#12781).
- Feedback loop: for `fetch-diff` and `fetch-unresolved-comments`, run
  `uv run scripts/skill_validation.py <skill-dir> --strict` then
  `uv run scripts/eval-skills.py --skill <skill-dir>`; revise the `SKILL.md`
  until it is ERROR-clean and its static score is ≥ `EVAL_THRESHOLD` (see
  *Validation & eval feedback loop*).

### 9. (Optional) Harden the skill validator for scoped tools

- `scripts/skill_validation.py::check_optional_fields` stringifies
  `allowed-tools` with `str(allowed).split(",")`, which mishandles YAML-list
  frontmatter and flags scoped `Bash(...)` / `Skill` entries as unknown tools.
- Optionally update it to: (a) accept list-form `allowed-tools`, (b) strip a
  trailing `(...)` scope before the `KNOWN_TOOLS` check, and (c) add `Skill` to
  `KNOWN_TOOLS`.
- If this step is skipped, the ported skills still pass `make` because these are
  WARNING-level (non-strict mode); document the decision in the PR.

### 10. Update plugin manifest, marketplace, and README

- Bump `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json` `version`
  from `0.1.0` to `0.2.0` (minor — additive new skills).
- Sync the `agent-harness` entry `version` in `.claude-plugin/marketplace.json`
  to `0.2.0` so the manifest and registry match.
- Replace the "### Skills — _Coming soon._" block in
  `plugins/boss-dev/agent-harness/README.md` with a list of the ten shipped
  skills and a one-line description each.
- Consider running the repo's `version-bump-reviewer` skill to confirm the bump
  tier and produce the conventional commit.

### 11. Re-baseline the eval quality gate

- Run `make eval` to score all thirteen skills (the three originals plus the
  ten ported) at static depth and record each score.
- Update the baseline comment block above `EVAL_THRESHOLD` in the `Makefile`:
  refresh the date to the port date and list the new minimum.
- Set `EVAL_THRESHOLD` to `min(all 13 static scores) - 5`, BUT never lower it
  below the current 57 — re-baselining may *raise* the floor when every skill
  clears a higher mark; it must not be lowered to accommodate a weak port. If a
  ported skill scores below 57 at static depth, fix the skill (loop back to its
  port step), do not weaken the gate.
- Run `make eval-ci` and confirm it exits 0 with all thirteen skills passing.

### 12. Validate, test, and fix

- Run the full validation suite (see *Validation Commands*).
- Fix every error and address warnings until `skill_validation.py`,
  `verify-structure.py`, `make lint`, `make markdown-lint`, `make eval-ci`, and
  `make test` all pass.
- Smoke-test each PEP 723 script with `--help` to confirm `uv` resolves the
  inline dependencies and `argparse` wiring is correct.

## Testing Strategy

Follow TDD for the Python scripts — the pure, side-effect-free functions are
where bugs hide, and they are cheaply testable without network access. Place
tests under each skill's `scripts/tests/test_*.py`, mirroring
`twitter-media-downloader/scripts/tests/`. Tests run via `make test`
(`uv run pytest`).

**`fetch-diff/scripts/tests/test_fetch_diff.py`:**

- `filter_diff` — line-number annotation: `-` lines get the left number only,
  `+` lines the right number only, context lines both; blank line inserted
  between files.
- `filter_diff` with `file_patterns` — only matching files survive; non-matching
  `diff --git` blocks are dropped.
- `is_autogenerated_file` — `uv.lock` / `yarn.lock` / `package-lock.json` →
  `True`; an ordinary `.py` file → `False`; confirm the removed `mlflow/protos`
  branch is gone (a `foo/protos/x.py` path → `False`).
- `extract_stacked_pr_base_sha` — returns the base SHA for a body with a bold
  `[**branch**]` stacked entry; returns `None` when "Stacked PR" is absent.
- Masked-file rendering — auto-generated and deleted files show the mask message
  and suppress hunk content.

**`fetch-unresolved-comments/scripts/tests/test_fetch_unresolved_comments.py`:**

- `format_comments` — resolved threads are excluded; unresolved threads are
  grouped `by_file`; `total` counts every comment across kept threads; a thread
  with no comments or no path is skipped. Drive it with a hand-built GraphQL
  response dict (no network).

**`pr-review/scripts/tests/test_validate_review.py`:**

- A minimal valid `APPROVE` payload (empty `comments`, body ending with the
  `🤖 Generated with Claude` footer) passes.
- A `COMMENT` payload with one well-formed inline comment passes.
- Failure cases each raise/exit non-zero: missing footer; comment `body` lacking
  a severity prefix; `event` not in the enum; `APPROVE` with a `🔴 CRITICAL`
  comment; `start_line` without `start_side`.
- The default schema path resolves to the sibling `review-payload.schema.json`.

**Edge cases to cover:** empty diff input to `filter_diff`; a PR body of `None`
in `extract_stacked_pr_base_sha`; a GraphQL response with zero review threads.

Network-dependent code paths (`GitHubClient` HTTP/GraphQL calls,
`get_github_token`'s `gh` subprocess) are **not** unit-tested — they are thin
wrappers over `aiohttp`/`subprocess`. Coverage of those is the `--help`
smoke-test plus a manual run against a real public PR during review.

### Skill-quality validation (the feedback loop)

Beyond pytest, every ported skill is validated through the two-gate loop in
*Validation & eval feedback loop*: strict `skill_validation.py` plus static
`eval-skills.py --skill`. It is run per skill during porting and re-run as a
whole-repo gate (`make eval-ci`) in Step 12. This is structural/quality
validation, not unit testing — kept to the fastest offline layers only.

## Acceptance Criteria

- `plugins/boss-dev/agent-harness/skills/` contains all ten skill directories,
  each with a `SKILL.md` whose `name` equals its directory name.
- No ported file references the mlflow repo layout, the `uv` `skills` workspace
  package, or `uv run --package skills`.
- `fetch_diff.py`, `fetch_unresolved_comments.py`, and `validate_review.py` each
  carry a valid PEP 723 header and run standalone via
  `uv run "${CLAUDE_SKILL_DIR}/scripts/<script>.py" --help`.
- `pr-review/review-payload.schema.json` exists and `validate_review.py` resolves
  it as the default schema with no `--schema` argument.
- `uv run scripts/skill_validation.py plugins/boss-dev/agent-harness/skills`
  reports zero ERROR-level findings; under `--strict` every remaining WARNING is
  either fixed or explicitly documented in the PR.
- `uv run scripts/verify-structure.py` passes (marketplace + manifests valid).
- `make lint`, `make markdown-lint`, and `make test` all pass with zero errors.
- `make eval-ci` exits 0 — every skill under `plugins/**` (the three originals
  plus the ten ported) scores at or above `EVAL_THRESHOLD` at static depth.
- The `Makefile` `EVAL_THRESHOLD` value and baseline comment reflect the
  post-port static-score baseline across all thirteen skills, and the threshold
  is not lower than 57.
- All new tests pass and meaningfully exercise `filter_diff`,
  `is_autogenerated_file`, `extract_stacked_pr_base_sha`, `format_comments`, and
  `validate_review`.
- `agent-harness` `plugin.json` and the marketplace entry both read `version`
  `0.2.0`.
- `agent-harness/README.md` lists the ten new skills under "Skills".

## Validation Commands

Execute these commands from the repo root to validate the task is complete:

- `uv run scripts/skill_validation.py plugins/boss-dev/agent-harness/skills` —
  validate all ten SKILL.md files against the 16-rule standard (zero errors)
- `uv run scripts/skill_validation.py plugins/boss-dev/agent-harness/skills --strict` —
  strict structural pass (warnings surfaced as the authoring feedback signal)
- `uv run scripts/eval-skills.py --skill plugins/boss-dev/agent-harness/skills/<name>` —
  static `plugin-eval` score for one skill (the per-skill loop command)
- `make eval` — score all thirteen skills at static depth (report only)
- `make eval-ci` — quality gate; every skill must score ≥ `EVAL_THRESHOLD`
- `uv run scripts/verify-structure.py` — validate marketplace.json + plugin
  manifests after the version bump
- `uv run python -m py_compile plugins/boss-dev/agent-harness/skills/fetch-diff/scripts/fetch_diff.py plugins/boss-dev/agent-harness/skills/fetch-unresolved-comments/scripts/fetch_unresolved_comments.py plugins/boss-dev/agent-harness/skills/pr-review/scripts/validate_review.py` —
  confirm the PEP 723 scripts compile
- `uv run "$PWD/plugins/boss-dev/agent-harness/skills/fetch-diff/scripts/fetch_diff.py" --help` —
  confirm `uv` resolves inline deps and argparse wiring (repeat for the other two scripts)
- `make lint` — ruff check/format + codespell across `devtools`, `scripts`, `plugins`
- `make markdown-lint` — lint all new SKILL.md and reference markdown
- `make link-check` — confirm no dead cross-skill links
- `make test` — run the pytest suite including the new `scripts/tests/`
- `python -c "import json,pathlib; [json.loads(pathlib.Path(p).read_text()) for p in ['plugins/boss-dev/agent-harness/.claude-plugin/plugin.json','.claude-plugin/marketplace.json','plugins/boss-dev/agent-harness/skills/pr-review/review-payload.schema.json']]" && echo JSON_OK` —
  confirm modified/new JSON files parse

## Notes

- **Scope boundary:** the mlflow `analyze-ci` skill and its backing
  `src/skills/commands/fetch_logs.py` are intentionally **not** ported. If they
  are wanted later, the same Option B pattern applies (a `fetch_logs.py` PEP 723
  script under an `analyze-ci/scripts/` directory).
- **`release-notes` vs `release-notes-generator` overlap:** both skills cover
  the same workflow — `release-notes` is command-style (`$ARGUMENTS`,
  `disable-model-invocation`) and `release-notes-generator` is model-invocable
  with `assets/`/`references/`. The task explicitly requests both, so both are
  ported, but they are near-duplicates. Recommendation: after porting, keep
  `release-notes-generator` as the canonical skill and either delete
  `release-notes` or repurpose it as a thin command wrapper, to avoid two skills
  competing for the same trigger. Flag this for the user before merge.
- **`aiohttp` dependency:** the ported scripts keep the async `aiohttp` client
  for fidelity with proven mlflow code. A future simplification could replace it
  with synchronous `urllib.request`, dropping `aiohttp` from the PEP 723
  dependency list (each script makes only one or two sequential HTTP calls, so
  async buys nothing). This is **out of scope** for this plan.
- **No `uv add` needed.** All Python dependencies (`aiohttp`, `pydantic`,
  `jsonschema`) are declared inline via PEP 723 in the skill scripts and
  resolved on demand by `uv run`; the boss-skills root `pyproject.toml` is not
  touched.
- **Type-checking gap:** `devtools/lint.py` type-checks only `devtools` and
  `scripts`, not `plugins`. The new skill scripts are ruff-checked but not
  basedpyright-checked by default. Either add the skill `scripts/` paths to
  `TYPE_CHECK_PATHS` in `devtools/lint.py`, or accept the gap — the scripts are
  small and fully annotated. Decide during Phase 3.
- **Audit protocol:** per `.claude/rules/audit-protocol.md`, if any audit agent
  is invoked on the ported skills, pass only the file path with no context about
  what was just changed.
- **Source provenance:** the ultimate-guide skills are MIT-licensed examples
  from `FlorianBruniaux/claude-code-ultimate-guide`; the mlflow skills come from
  the Apache-2.0 mlflow repo. Add a one-line attribution comment to each ported
  SKILL.md (or to the plugin README) noting the upstream source.
- **Future "enhance-a-skill" workflow.** The deeper feedback loop —
  `eval-skills.py --layer llm-judge` / `monte-carlo`, `make eval-skill`
  (standard depth via Claude Code Max), and `plugin-eval certify` — is
  intentionally not used in this plan. It is reserved for a future subagent or
  slash command that iteratively "enhances" a skill against a judged rubric.
  This plan keeps the cycle to the fastest offline layers — static
  `plugin-eval` plus `skill_validation.py`.
- **Do not weaken the eval gate.** `static` depth is largely structural, so the
  mature mlflow and ultimate-guide skills should clear `EVAL_THRESHOLD` (57)
  comfortably. If one does not after revision, surface it to the user — do not
  lower `EVAL_THRESHOLD` to make CI pass.
- **Validator hardening vs. the strict loop:** Step 9's `skill_validation.py`
  hardening interacts with the `--strict` half of the feedback loop — scoped
  `Bash(...)` and `Skill` entries in `allowed-tools` produce WARNINGs under
  `--strict`. Either land Step 9 or document each accepted warning in the PR.
