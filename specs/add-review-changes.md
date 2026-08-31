# Plan: Port `review-changes` into the `agent-harness` plugin

> **Build step 0:** this document is also the deliverable the user asked for. Write it verbatim to
> `specs/add-review-changes.md` as the first action of `/agent-harness:build`. Plan mode restricted
> edits to the plan file, so it could not be created during planning. All relative links below are
> written to resolve from `specs/`, and files that do not exist yet are deliberately left as
> backticked paths rather than links, because `make link-check` (lychee) globs `**/*.md` and
> `exclude_path` does not exclude `specs/`.

## Task description

Port the `review-changes` skill from `top-marks` (a repo-local `.claude/skills/` skill) into the
[`agent-harness`](../plugins/boss-dev/agent-harness/) plugin, generalizing it so it produces useful,
quiet reviews in an arbitrary repository rather than only in the repo it was written for. Task type:
**feature**. Complexity: **complex** (12 files, ~1,150 lines of prose policy to rewrite, plus
registration across 6 more files).

## Objective

`agent-harness` ships a `review-changes` skill that, installed at user scope in any repository:

1. resolves a review scope and an annotated, citable patch without assuming a branch layout,
   a remote, a shell, or a language;
2. learns the repo's rules by discovery at the merge-base SHA, sharpened by an optional per-repo
   profile, and cites them by path;
3. fans out lenses, drops findings that cite non-citable lines, and strips false positives
   adversarially;
4. reports in chat, adds no sixth severity vocabulary, and produces **no findings at all** in a
   repo whose conventions it cannot establish.

## Context

`review-changes` is a multi-lens pre-commit review skill living at
`/Users/malcolm/dev/adobe-aifoundations/top-marks/.claude/skills/review-changes/` (11 files, 1,143
lines). It was vendored into `top-marks` from `director`, which adapted it from an Adobe DxE
pre-flight plugin. Its machinery is genuinely good and this repo has nothing like it:

- an **annotated patch** with a citable `[N]` line set per file,
- repo rules read **at the merge-base SHA** so a rule edit in your own diff cannot soften the
  review of that diff,
- a **deterministic validation gate** that drops any finding citing a non-citable line,
- a **two-axis finding schema** (`priority` = how bad, `confidence` = how sure) with a required
  `uncertainty_reason`,
- an **adversarial challenge pass** with a stable false-positive taxonomy.

The problem: it is a *repo-specific instantiation* of that machinery. Roughly 40% of its prose
encodes `top-marks` policy — Jira key prefixes, `notes/`/`research/`/`pillars/` placement rules, a
`decks/` AI-SLOP badge gate, `venv`-not-`uv`, `dp-*` console scripts, `mcp__ada-mcp-gateway__*`
tools, an `aip-repo-investigator` subagent, and emoji confidence tags. Dropped into an arbitrary
repo it would either cite rules that do not exist or invent findings.

The goal is to keep the machine, replace the policy with **runtime discovery plus an optional
per-repo profile**, and ship it in [`agent-harness`](../plugins/boss-dev/agent-harness/) — which is
installed at user scope, so "any repo" is the actual operating environment, not a nice-to-have.

## What the repo already has, and why this is still additive

Verified against every review-shaped capability in the tree:

| Existing | Path | Relationship |
|---|---|---|
| `review` (2-axis Standards/Spec, parallel subagents, merge-base diff) | [`.claude/skills/review/SKILL.md`](../.claude/skills/review/SKILL.md) | **Trigger collision.** Left untouched per decision; tracked as a GitHub issue (task 9). |
| `boss-security-review` (severity-graded report on changed code, fan-out) | [`plugins/boss-dev/agent-harness/skills/boss-security-review/`](../plugins/boss-dev/agent-harness/skills/boss-security-review/) | Owns the security-vulnerability lens. `review-changes` declares it out of scope and delegates. Its [`references/fanout.md`](../plugins/boss-dev/agent-harness/skills/boss-security-review/references/fanout.md) is the prior art for one-lens-per-subagent; its [`references/severity-model.md`](../plugins/boss-dev/agent-harness/skills/boss-security-review/references/severity-model.md) is the repo's most mature severity model. |
| `pr-review` (multi-dimension + severity gate + JSON payload) | [`plugins/boss-dev/agent-harness/skills/pr-review/`](../plugins/boss-dev/agent-harness/skills/pr-review/) | PR-number-scoped, remote, `disable-model-invocation: true` — no routing conflict. |
| `fetch-diff` (line-annotated PR diff, generated-file masking) | [`plugins/boss-dev/agent-harness/skills/fetch-diff/`](../plugins/boss-dev/agent-harness/skills/fetch-diff/) | Same idea, **remote-PR only**, different column format. Not reused; cross-linked. |
| `reviewer` agent (8-phase code review) | `plugins/boss-experimental/boss-experimental/agents/reviewer.md` | Closest analogue to the code lens, but lives in a **different plugin** — must not be a dependency. |
| `stop-slop`, `unicode-hygiene` | [`skills/stop-slop/`](../plugins/boss-dev/agent-harness/skills/stop-slop/), [`skills/unicode-hygiene/`](../plugins/boss-dev/agent-harness/skills/unicode-hygiene/) | Already-enforced concerns. The review must not re-flag them. |

**What is genuinely new** (grep-verified: zero hits for "adversarial" anywhere in the repo, no
structured finding schema, no mechanical diff-scope gate): the citable-line gate, the
`priority`+`confidence` observation contract, and the adversarial challenge pass. Those three
should lead the description.

**Severity vocabulary:** the repo already has five incompatible ones. Do **not** add a sixth. Use
`CRITICAL / HIGH / MEDIUM / LOW` for `priority` (it maps onto `boss-security-review`'s
`Critical/High/Medium/Low` minus `Info`) and cross-reference that severity model rather than
restating it.

## Target layout

```text
plugins/boss-dev/agent-harness/skills/review-changes/
├── SKILL.md
└── references/
    ├── observation-format.md      # the finding JSON, field by field
    ├── quality-gates.md           # the 8 pre-report checks every lens runs
    ├── challenge-criteria.md      # the FP taxonomy with stable ids
    ├── repo-profile.md            # NEW: rule discovery + the optional per-repo profile contract
    └── lenses/
        ├── claims.md
        ├── consistency.md
        ├── structure.md
        ├── cross-refs.md
        ├── placement.md
        ├── disclosure.md
        └── code.md
```

No `scripts/`, no `eval/` (both decided against for this PR). `plugin.json` needs **no** skill
entry — it declares `"skills": "./skills/"` and discovery is by directory scan.

## Relevant files

### New files

All twelve live under `plugins/boss-dev/agent-harness/skills/review-changes/`. Eleven are ports of
the corresponding source file; `references/repo-profile.md` is new to this port and is what makes
the skill portable — it is where rule discovery and the per-repo escape hatch are specified.

### Existing files to modify

- [`plugins/boss-dev/agent-harness/.claude-plugin/plugin.json`](../plugins/boss-dev/agent-harness/.claude-plugin/plugin.json)
  and [`.claude-plugin/marketplace.json`](../.claude-plugin/marketplace.json) — the version pair
  that `check_manifest_conflicts` compares; must move in lockstep.
- [`plugins/boss-dev/agent-harness/README.md`](../plugins/boss-dev/agent-harness/README.md) and
  [`docs/plugins/agent-harness.md`](../docs/plugins/agent-harness.md) — both carry a version token
  on a `>`-prefixed line in the first 8 lines that `check_doc_version_drift` reads, plus a
  hand-maintained skills count.
- [`plugins/boss-dev/agent-harness/docs/skills.md`](../plugins/boss-dev/agent-harness/docs/skills.md)
  — the authoritative three-layer skill index.

### Existing files to read, not modify

- [`plugins/boss-dev/agent-harness/skills/boss-security-review/SKILL.md`](../plugins/boss-dev/agent-harness/skills/boss-security-review/SKILL.md)
  — the proven pattern for a portable, user-scope-safe skill: a tiered `RULES_SOURCE` that prefers
  the target repo's own rules, falls back to bundled copies, then to a built-in checklist. **Rule 2
  is modelled directly on it.** Its
  [`references/fanout.md`](../plugins/boss-dev/agent-harness/skills/boss-security-review/references/fanout.md)
  is the existing one-lens-per-subagent contract, and
  [`references/severity-model.md`](../plugins/boss-dev/agent-harness/skills/boss-security-review/references/severity-model.md)
  is the severity model to cross-reference instead of restating.
- [`plugins/boss-dev/agent-harness/skills/harness-doctor/SKILL.md`](../plugins/boss-dev/agent-harness/skills/harness-doctor/SKILL.md)
  — the plugin's most complete frontmatter, and the `$ command` notation that avoids the parser bug.
- [`plugins/boss-dev/agent-harness/skills/fetch-diff/SKILL.md`](../plugins/boss-dev/agent-harness/skills/fetch-diff/SKILL.md)
  — the house style for a `## Reference Files` section (each entry with a *when to consult* clause)
  and a `## Related skills` chain.
- [`.claude/rules/skill-development.md`](../.claude/rules/skill-development.md) and
  [`.claude/rules/plugin-structure.md`](../.claude/rules/plugin-structure.md) — the binding
  authoring rules, including the `!`-backtick parser bug (GitHub #12781).
- [`.claude/rules/audit-protocol.md`](../.claude/rules/audit-protocol.md) — constrains how lens
  subagents may be briefed.

## The port: five genericization rules

These are the whole design. Every rewrite below is an application of one of them.

### Rule 1 — Discover rules, do not hardcode them

Replace the `notes/` / `research/` / `pillars/` / `decks/` table in Step 2 with discovery at
`$BASE_SHA`:

```bash
BASE_SHA=$(git merge-base "$BASE" HEAD 2>/dev/null || git rev-parse HEAD)

# Root-level rule files, whichever exist
for f in CLAUDE.md AGENTS.md AGENT.md CONTRIBUTING.md .github/copilot-instructions.md; do
  git show "$BASE_SHA:$f" 2>/dev/null
done
git ls-tree -r --name-only "$BASE_SHA" -- .cursor/rules .claude/rules 2>/dev/null

# Nested rules: for every directory in a changed file's ancestry
git show "$BASE_SHA:<dir>/CLAUDE.md"   # Claude Code's own nested-rules convention
git show "$BASE_SHA:<dir>/AGENTS.md"
git show "$BASE_SHA:<dir>/README.md"   # rules often live next to content
```

Dedupe symlinked rule files **by blob id**, not by a hardcoded fact:
`git rev-parse "$BASE_SHA:AGENT.md"` equal to `git rev-parse "$BASE_SHA:CLAUDE.md"` means one file,
read once. This generically replaces the `top-marks` note that `AGENT.md` is a symlink while
`AGENTS.md` is a real sibling — and it still catches the important case (two *distinct* rule files
that contradict each other).

Rule precedence survives verbatim: **the repo's own rules override everything and must be cited by
path; industry standards only where the repo is silent; the model's judgement is lowest.**

### Rule 2 — An optional per-repo profile is the escape hatch

The source skill's value came from repo-specific traps. Preserve that without hardcoding by
reading an optional `.claude/review-changes.md` from the target repo at `$BASE_SHA`. This mirrors
the proven three-tier `RULES_SOURCE` fallback in
[`boss-security-review`](../plugins/boss-dev/agent-harness/skills/boss-security-review/SKILL.md):
repo profile → discovered rule files → built-in generic lens content.

The new `references/repo-profile.md` documents the contract, all sections optional:

| Profile section | Overrides |
|---|---|
| `## Skip paths` | additions to the generic skip classification |
| `## Rule files` | extra rule paths to load at base SHA |
| `## Already enforced` | tools/CI gates whose findings are out of scope (gate 8) |
| `## Issue tracker` | key pattern and read-only lookup command |
| `## Index files` | which index/nav file a new file must appear in |
| `## Claim conventions` | a repo's source/confidence tagging contract |
| `## Downstream renders` | published copies that go stale on a canonical edit |
| `## Repo traps` | free-form, appended to every lens brief |

Say in the report whether a profile was found. Absent one, the skill still works — it is just
quieter, which is the correct failure mode.

### Rule 3 — Probe capabilities, never assume tools

Every named-tool dependency becomes conditional. Scout MCP tools, `gh`, and any issue-tracker MCP
are used **if present in the session**; otherwise fall back to `Grep`/`Glob` and **say in the
evidence which was used**. Delete the `aip-repo-investigator` dependency outright — a lens that
needs to verify a code claim dispatches a plain subagent instead. Never claim an index-backed
answer that was not obtained.

### Rule 4 — Derive "already someone else's job" from the repo's own config

Gate 8 stops naming `dp-harness-lint`/`black`/`flake8`/`mypy` and instead detects what the repo
actually enforces, in this order of authority:

1. [`.pre-commit-config.yaml`](../.pre-commit-config.yaml) and `lefthook.yml` — what blocks a commit
2. `.github/workflows/*` — what blocks a merge
3. tool config: `pyproject.toml`, `eslint.config.*`/`.eslintrc*`, `biome.json`, `.prettierrc*`,
   `rustfmt.toml`, `.golangci.yml`, `.rubocop.yml`, `.editorconfig`, `.markdownlint*`/`.rumdl.toml`
4. `Makefile` / `justfile` targets

Whatever those own is not a finding. Formatting, import order, line length, and markdown style are
never findings regardless.

### Rule 5 — Language-dispatch the code lens; keep the doc lenses universal

`top-marks` diffs are ~90% markdown, so the source `code.md` is a Python-CLI-plus-decks document.
Rewrite it around **universal defect classes** with a per-language dispatch table, and generalize
the `dp-*` rule into its actually-portable form:

> **The declared-entrypoints truth.** The commands that exist are the ones the repo declares —
> `[project.scripts]` in `pyproject.toml`, `bin`/`scripts` in `package.json`, `[[bin]]` in
> `Cargo.toml`, `Makefile`/`justfile` targets. A doc, script, or skill body naming any other
> command is a finding. Read the list; do not assume.

The six doc/meta lenses stay — they are portable — but `placement.md` becomes **strictly
rules-driven**: it reports only what it can cite to a discovered rule or a demonstrable convention
in the sibling files ("every other file in this directory is kebab-case"). With no governing rule
it reports nothing. That is the difference between a useful lens and a noise generator in an
unknown repo.

## Per-file rewrite specification

### `SKILL.md`

Keep the six-stage shape verbatim — it is the skill:

```text
scope the diff  ->  load repo rules AT BASE SHA  ->  dispatch N lenses in parallel
                ->  validate mechanically  ->  challenge (FP filter)  ->  report
```

Frontmatter (matching sibling conventions — `name` and `description` are the only keys
[`scripts/verify-structure.py`](../scripts/verify-structure.py) enforces):

```yaml
---
name: review-changes
description: >
  Multi-lens review of the changes in the current working tree - docs, specs, config, and code -
  before you commit, open a PR, or publish. [... concrete trigger phrasings ...] Use when asked to
  "review my changes", "review this before I push", "pre-flight check", or before committing a unit
  of work. [... the three differentiators ...]
argument-hint: "[staged | unstaged | full | <paths...>] (default: merge base with origin/HEAD -> working tree)"
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
  - Agent
---
```

Keep `description` under 1,024 characters (a `skill_validation.py` ERROR) and over 100 (full
plugin-eval length credit). Do **not** set `disable-model-invocation` — the point is that it fires
on "review my changes".

Rewrite map, section by section:

| Source section | Action |
|---|---|
| Provenance paragraph | Keep, compressed to two sentences. Reference the upstream repos in **backticks, not links** — they are private Adobe repos and a link would 404 under `make link-check` (`lychee.toml` accepts 200/401/403/405/429, and `include_verbatim = false` skips inline code). |
| Step 1 base resolution | Keep the remote-tracking-ref logic and its comment about why `--short` must not be stripped. **Harden** per the table below. |
| Step 1 annotated patch (awk) | Keep verbatim. Verified working on this platform (BSD `awk` 20200816): `[1]a [2]B2 [3]c [4]NEW [5]d [6]e`, with `\ No newline at end of file` correctly skipped. Both guards (`!inhunk{next}`, `/^\\/{next}`) are load-bearing — keep the paragraph explaining why. |
| Step 1 skip table | Replace with generic classification (below). |
| Step 1 size guard / full-file mode | Keep as-is. |
| Step 2 rule table | Replace per **Rule 1** + **Rule 2**. |
| Step 3 lens table | Keep the table and the model hints (`opus`/`sonnet` are valid subagent model overrides). Replace the "touches" column with generic globs and detected-language triggers. Keep the "verify each lens actually reported" paragraph — it guards a silent failure mode. |
| Step 3 Scout / `aip-repo-investigator` | Replace per **Rule 3**. |
| Step 3 accountability sections | Generalize: read the changed document's own `## Sources` / `## References` / `## Changelog` if it has them; the profile may name others. |
| Step 4 mechanical validation | **Keep verbatim**, including the merge rule on `(file, line, category)` (not `file:line` alone), the theme precedence chain `disclosure > claims > consistency > code > placement > cross-refs > structure`, and the warning that a zero drop count means the gate is not running. |
| Step 5 challenge | Keep as-is. |
| Step 6 report | Keep. Reinforce: findings **in chat only**, never write a findings file — that is what separates it from `boss-security-review`. |
| "When to run it" | Point at [`/agent-harness:commit-push-pr`](../plugins/boss-dev/agent-harness/commands/commit-push-pr.md) and generic "before you open a PR or publish". Drop `/wiki-publish` and `/jira-sync`. |
| "It complements, not replaces" | Replace per **Rule 4**. |

Step 1 hardening — the "works in any repo" surface, all cases verified against this tree:

| Case | Behaviour |
|---|---|
| Explicit base argument | Wins over all detection. |
| `origin/HEAD` unset | Try `origin/main`, `origin/master`, `origin/develop`, `origin/trunk`, then `upstream/*`. |
| No remote at all | Fall back to local `main`/`master`/`develop`/`trunk`. |
| Shallow clone, `merge-base` fails | Fall back to `HEAD` (uncommitted only) and **say so** in the scope line. |
| Already on the default branch | `merge-base == HEAD`, so the review covers staged + unstaged. Correct, but state it; offer `HEAD~1` or an explicit base if empty. |
| No commits yet | Review `git diff --staged` plus untracked. |
| Unresolvable base | Fail loudly. An unresolvable base exits 128 with **empty stdout**, indistinguishable from "no changes" — keep the source's explicit guard. |

**New: untracked files.** `git diff "$MB"` does **not** see untracked files — verified: a new
`untracked.md` produced empty output from `git diff HEAD --name-only` while `git status --porcelain`
showed `?? untracked.md`. For a "review before you commit" skill that is the single most important
file class to miss. Add:

```bash
git status --porcelain | awk '/^\?\? /{print substr($0,4)}'        # untracked candidates
git diff --no-index -- /dev/null <file> | awk '...'                # annotate as all-new
```

Verified to yield `@@ -0,0 +1 @@` / `[1] +x` through the same awk pipeline, so the citable-line set
stays uniform. Respect `.gitignore` (untracked-but-ignored files are not in scope unless tracked).

Generic skip classification, replacing the hardcoded table:

| Class | Detection |
|---|---|
| Binary | `git diff --numstat` prints `-` for added and deleted on binary files |
| Generated | `.gitattributes` `linguist-generated`, plus a portable list: `*.lock`, `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `uv.lock`, `poetry.lock`, `Cargo.lock`, `go.sum`, `*.min.js`, `*.map`, `*_pb2.py`, `*.generated.*` |
| Vendored / build | `node_modules/`, `vendor/`, `dist/`, `build/`, `target/`, `.venv/`, `venv/`, `__pycache__/`, `coverage/` |
| Profile-supplied | `## Skip paths` |

Mark skipped files `skipped` in coverage and drop any finding on them.

### `references/observation-format.md`

Keep the JSON schema and the two-axis explanation **verbatim** — this is the novel contribution.
Changes are cosmetic: replace the `top-marks` examples in the `priority` table (AI-SLOP badge, Jira
ticket filed) with portable ones, and generalize "`Read` and Scout show file line numbers" to "a
file read or a search result shows *file* line numbers; the patch shows the line number in the new
file *as annotated* — they diverge on any large file."

### `references/quality-gates.md`

All eight gates survive. Gate 2 gets **Rule 3**; gate 3 keeps the GitHub-anchor slug rules (they
are universal and computable) and drops Confluence / Jira / Copilot-frontmatter, replaced by "if
this repo renders somewhere else, the profile says so"; gate 4 gets **Rule 1**; gate 8 gets
**Rule 4**. The universal skip list at the bottom carries over unchanged.

### `references/challenge-criteria.md`

Keep criteria **1-12 with their ids verbatim**, including the kebab-case of 9-11. The rationale is
real: stable ids let rejection histograms join across the three systems running this taxonomy.
Genericize 13-16 rather than dropping them — all four describe portable failure modes:

| Id | Generalization |
|---|---|
| `fp_unresolvable_reference` | Drop the named Jira MCP tool; verify with whatever the profile or session provides. |
| `fp_wrong_document` | Keep — "right that something is missing, wrong about which document owns it" is repo-agnostic. |
| `fp_tool_enforced` | Resolve against the discovered toolchain (**Rule 4**). |
| `fp_draft_status` | Generalize the tag set to `DRAFT` / `WIP` / `TODO` / `RFC`, keeping the crucial carve-out: draft status never excuses a claim asserted as sourced that is not, or a broken anchor. |

### `references/lenses/*.md`

| Lens | Rewrite |
|---|---|
| `claims` | Keep counts (universal, highest-yield), links/URLs, attribution, status assertions, relative dates. Generalize issue keys to a profile-named pattern with a **read-only** lookup and an explicit "never write to the tracker". Delegate code claims to a subagent instead of grepping. Replace the emoji tag contract with "if the repo tags claims with a source/confidence convention, the profile names it." |
| `consistency` | Keep nearly whole — table-vs-prose, header-vs-body, decision-state conflict, ownership/scope conflict, terminology drift, numeric self-consistency, canonical-vs-downstream. Replace the `CLAUDE.md`-vs-`AGENTS.md` specifics with the generic "two rule files restating the same conventions", using the blob-id check from **Rule 1**. |
| `structure` | Keep whole — anchor slug computation, heading sequence, table shape, new-doc shape. Make the changelog check **conditional** on a detected convention (a root `CHANGELOG.md`, or a per-document `## Changelog` if the rules require one). Keep the priority-by-cause judgement: the diff broke it, report; pre-existing, do not. |
| `cross-refs` | Keep relative-link resolution and rename/inbound-link checking. Replace the fixed index table with detection: the nearest `README.md`, a docs-site nav (`mkdocs.yml`, `SUMMARY.md`, `docusaurus.config.*`, `_sidebar.md`), or a profile-named index. Keep the "reference cited by bare filename resolves from nowhere" trap — it is exactly the failure this port must avoid. |
| `placement` | **Largest rewrite.** Delete rules 1-7 and the folder contract. Becomes strictly rules-driven per **Rule 5**: cite a discovered rule or a demonstrable sibling convention, or report nothing. Keep two universal checks: a committed file that `.gitignore` excludes (it had to be force-added), and a filename shape inconsistent with every sibling. |
| `disclosure` | Keep the whole surface — credentials, weakened guards, un-redacted transcript content, audience mismatch, PII, prompt injection, outbound writes. Two changes: calibrate visibility by probing (`gh repo view --json visibility` when available, else assume private and **do not manufacture leaks**), and state that vulnerability review is out of scope, delegating to [`boss-security-review`](../plugins/boss-dev/agent-harness/skills/boss-security-review/SKILL.md). |
| `code` | **Full rewrite** per **Rule 5.** Universal classes: swallowed errors; a change to a documented CLI/API/exit-code contract that CI gates on; new behaviour with no test; output pollution on a machine-readable path; mutable default arguments, string-concatenated paths, missing file encoding; a CI step whose failure is swallowed (`continue-on-error` on a gate, or a trailing or-true); a gate on a command whose exit code is meaningless. Plus the declared-entrypoints truth, a per-language dispatch table (Python / TS-JS / Go / Rust / Shell) naming what to check and which tool already owns style, and a short section on skill/agent definitions (description quality, `allowed-tools` gaps, unresolvable reference paths) since this plugin's users author those. Delete the AI-SLOP gate and the `venv`-not-`uv` rule. |

### Untainted-lens-dispatch constraint

[`.claude/rules/audit-protocol.md`](../.claude/rules/audit-protocol.md) bans hinting at what an
audit agent should find. Encode the distinction explicitly in Step 3: a lens brief carries **data**
(annotated patches, changed-file list, citable-line set, compiled rules, branch name, absolute
reference paths) and never **expectations** — no hypothesis about what is wrong, no mention of what
was just fixed, no "verify that X".

## Registration, docs, and version bump

Adding a skill is a **minor** bump: `0.31.3` -> `0.32.0`. It must land in **four** places or
`verify-structure.py`'s `check_manifest_conflicts` and `check_doc_version_drift` warn (and fail
under `--strict`):

| File | Edit |
|---|---|
| [`plugins/boss-dev/agent-harness/.claude-plugin/plugin.json`](../plugins/boss-dev/agent-harness/.claude-plugin/plugin.json) | `"version"` line 5: `0.31.3` -> `0.32.0` |
| [`.claude-plugin/marketplace.json`](../.claude-plugin/marketplace.json) | `agent-harness` entry `"version"` line 42, same tier. Leave top-level `metadata.version` (`0.2.0`) alone. |
| [`plugins/boss-dev/agent-harness/README.md`](../plugins/boss-dev/agent-harness/README.md) | line 3 `**v0.31.3**`; line 380 `Plugin version **v0.31.3**`; line 22 skills count `20` -> `22` (already drifted, 21 dirs on disk today) |
| [`docs/plugins/agent-harness.md`](../docs/plugins/agent-harness.md) | line 3 `v0.31.3`; line 22 `Skills` count `14` -> `22` |

Documentation, in the plugin's established shapes:

- [`plugins/boss-dev/agent-harness/docs/skills.md`](../plugins/boss-dev/agent-harness/docs/skills.md)
  — the authoritative index, three layers to update: a **Table of Contents** entry, an **At a
  glance** row (`\| Skill \| Invocation \| When to use \| Needs \|`), and a per-skill
  `### \`review-changes\`` section following the fixed bullet schema (blockquote one-liner,
  `**Invocation:**` / `**When to use:**` / `**What it does:**` / `**Example:**` / `**Source:**`).
  Add it under a new `## Change review` family heading — it is not PR-scoped, so it does not belong
  in the existing `## PR review workflow` family. Add `git` (required) and `gh` (optional) to
  `## Dependencies`.
- `plugins/boss-dev/agent-harness/README.md` — a new family table row under `## Skills`.
- The `.claude/skills/review-changes` mirror symlink is created by
  `uv run scripts/symlink_plugins.py`; `make symlink-plugins-check` verifies it.

Commit format per [`version-bump-reviewer`](../.claude/skills/version-bump-reviewer/SKILL.md) —
the trailing version tag is the grep anchor for the changelog generator:

```text
feat(review-changes): introduce multi-lens working-tree review skill (v0.32.0)
```

[`CHANGELOG.md`](../CHANGELOG.md) is git-cliff-generated; do not hand-edit it.

## Gates this must pass

The blocking CI job is [`.github/workflows/ci.yml`](../.github/workflows/ci.yml). There is **no**
markdown-lint, link-check, or verify-structure job in CI — those run via pre-commit and `make`.

| Gate | Where | Relevance |
|---|---|---|
| `make eval-ci` (plugin-eval static, threshold **57**) | CI | **The gate that will actually fail.** Auto-discovers every `SKILL.md` under `plugins/`; no opt-out. |
| `uv run scripts/validate-unicode-hygiene.py` | CI + pre-commit | BLOCKER class only: tag chars U+E0000-U+E007F and bidi overrides. **Em-dashes, arrows, and emoji are explicitly not flagged**, so no ASCII-ification is required. (`stop-slop` advises against em-dashes as style, not as a gate.) |
| `make ci` (pytest) | CI | No new tests needed — no scripts are shipped. |
| `uv run python devtools/lint.py` | CI | `codespell` runs over `plugins/`, so spelling in the new markdown is checked. |
| `rumdl` per [`.rumdl.toml`](../.rumdl.toml) | pre-commit | `include` covers `plugins/*/*/skills/*/SKILL.md` automatically. MD013 (line length), MD040 (fence language), MD041 (H1 first), MD014, MD033, MD046, MD048, MD036 are **disabled**. Still active and relevant: **MD057** (relative links must resolve on disk), **MD051** (`#anchor` must match a real heading), **MD034** (no bare URLs), **MD059** (no "here"/"click here" link text), MD009, MD012, MD031/032/058. |
| `make link-check` (lychee) | local | Accepts 200/401/403/405/429 — **not 404**. `include_verbatim = false` means links inside code fences and inline code are skipped, which is why the private upstream repos go in backticks. |
| `make verify-structure` | local | Requires `skills/<name>/SKILL.md` with parseable frontmatter and non-empty `name` + `description`. |

Plugin-eval scoring levers, from
`scripts/plugin_eval/src/plugin_eval/layers/static.py` — weights `frontmatter_quality` 0.32,
`orchestration_wiring` 0.23, `progressive_disclosure` 0.14, `structural_completeness` 0.10,
`token_efficiency` 0.09, `ecosystem_coherence` 0.06, `harness_portability` 0.06, and
`final_score = raw * max(0.5, 1 - 0.05 * anti_pattern_count)`:

- **Two traps to actively avoid.** `ORPHAN_REFERENCE`: every `(references/...)` link must resolve.
  `DEAD_CROSS_REF`: cross-refs are extracted as `(?:skill|skills)/([a-z0-9-]+)` and resolved
  against *this plugin's* `skills/` dir — so writing `.claude/skills/review/SKILL.md` in the body
  matches `skills/review` and is looked up as `agent-harness/skills/review`, which does not exist:
  a false-positive dead cross-ref costing 5%. **Never write a `skills/<name>` path in SKILL.md
  unless `<name>` is an agent-harness sibling.**
- The source is already well-positioned: **317 lines** (200-600 is the `progressive_disclosure`
  sweet spot), **12 H2/H3** (>=6), **6 code blocks** (>=5), **23 table lines** (>=1 table), and only
  **4** MUST/ALWAYS/NEVER tokens (`OVER_CONSTRAINED` fires above 15).
- Two easy wins: the source uses **one** fence language (`bash`) where >=3 distinct languages earn
  full `structural_completeness` credit — add `text` and `json` fences. And add **Examples** and
  **Troubleshooting** sections, both of which score.
- `ecosystem_coherence` credits the words "related" / "see also" / "companion" — the `## Related
  skills` section earns this and is the right place for the `boss-security-review` /
  `pr-review` / `fetch-diff` cross-links.
- `harness_portability` penalizes CamelCase tool names in backticks and prose like "use the Read
  tool". Reword: "dispatch one **subagent** per lens", "a file read shows file line numbers".

## Step by step tasks

Execute in order.

### 1. Write the spec

- Write this document verbatim to `specs/add-review-changes.md`.

### 2. Create the skill directory and copy the raw source

- `mkdir -p plugins/boss-dev/agent-harness/skills/review-changes/references/lenses`
- Copy all 11 source files across unmodified as the starting point, so every edit below is a
  reviewable diff rather than a fresh authoring pass.

### 3. Rewrite `SKILL.md`

- Apply the frontmatter block and the section-by-section rewrite map.
- Apply the Step 1 hardening table (base resolution) and the untracked-file handling.
- Apply the generic skip classification.
- Apply Rules 1-4 to Steps 2, 3, and the closing "complements" section.
- Add the untainted-dispatch constraint to Step 3.
- Add `## Examples`, `## Troubleshooting`, `## Reference Files`, and `## Related skills`.
- Verify: `<= 1024` char description, `< 15` MUST/ALWAYS/NEVER, `>= 3` fence languages, no
  `skills/<name>` path that is not an agent-harness sibling.

### 4. Rewrite the three shared references

- `observation-format.md` — schema verbatim, portable examples.
- `quality-gates.md` — gates 2, 3, 4, 8 per Rules 1, 3, 4.
- `challenge-criteria.md` — ids 1-12 verbatim, 13-16 generalized.

### 5. Write `references/repo-profile.md`

- Document rule discovery (Rule 1) and the eight optional profile sections (Rule 2), with a
  worked example profile.

### 6. Rewrite the seven lenses

- Per the lens table. `placement.md` and `code.md` are near-total rewrites; the other five are
  targeted edits.
- Each lens must still open by pointing at `quality-gates.md` and `observation-format.md`, and
  must state that those paths arrive as absolute paths in its brief.

### 7. Register and document

- `docs/skills.md`: TOC entry, At-a-glance row, `### \`review-changes\`` section under a new
  `## Change review` heading, `## Dependencies` additions.
- `plugins/boss-dev/agent-harness/README.md`: family table row; skills count `20` -> `22`.
- `uv run scripts/symlink_plugins.py` to create the `.claude/skills/review-changes` mirror.

### 8. Version bump

- `0.31.3` -> `0.32.0` across all four files in the registration table.

### 9. File the trigger-collision issue

`review` is being left untouched by decision, so record the conflict. The active `gh` account is
`malcolm_adobe`; switch first:

```bash
gh auth switch --hostname github.com --user bossjones
gh issue create --repo bossjones/boss-skills \
  --title "review-changes and .claude/skills/review compete for the same trigger surface" \
  --label enhancement --label needs-triage
gh auth switch --hostname github.com --user malcolm_adobe   # restore
```

Issue body should record: both descriptions verbatim; that `review`'s "review a branch, a PR,
work-in-progress changes, or asks to review since X" is the overlapping phrasing; the real
differentiators (7 lenses vs 2 axes; citable-line gate; JSON observation contract; adversarial
pass; severity+confidence gating vs none); that `review` is repo-internal, unversioned, and depends
on `docs/agents/issue-tracker.md` so it would not survive a user-scope install; and the two options
considered (narrow `review`'s description, or retire it and port its Spec-vs-implementation axis
into a lens).

### 10. Validate

- Run every command in the Verification section and fix what it reports.

### 11. Ship

- Commit as `feat(review-changes): introduce multi-lens working-tree review skill (v0.32.0)`, then
  open the PR via [`/agent-harness:commit-push-pr`](../plugins/boss-dev/agent-harness/commands/commit-push-pr.md).

## Acceptance criteria

1. `plugins/boss-dev/agent-harness/skills/review-changes/` contains `SKILL.md` plus the eleven
   reference files, and nothing else.
2. Zero occurrences in any ported file of: `AIP-`, `DEVPLT-`, `dp-`, `ada-mcp-gateway`,
   `aip-repo-investigator`, `harness-lint`, `AI-SLOP`, `notes/`, `pillars/`, `decks/`, `venv/bin`,
   or the confidence-tag emoji. Grep for each.
3. Every named external tool (`gh`, Scout MCP tools, any tracker MCP) is used conditionally, with a
   documented `Grep`/`Glob` fallback and a requirement to state which was used.
4. `SKILL.md` description is 100-1,024 characters, contains a `Use when` trigger clause, and names
   the three differentiators (citable-line gate, two-axis observation contract, adversarial pass).
5. `SKILL.md` contains no `skills/<name>` path unless `<name>` is an agent-harness sibling
   (`DEAD_CROSS_REF` avoidance), and every `(references/...)` link resolves
   (`ORPHAN_REFERENCE` avoidance).
6. `SKILL.md` has >= 3 distinct fence languages, >= 6 H2/H3 headings, >= 5 code blocks, >= 1 table,
   an Examples section, a Troubleshooting section, a `## Related skills` section, and < 15
   MUST/ALWAYS/NEVER tokens.
7. The challenge criteria retain ids 1-12 verbatim, including the kebab-case of 9-11.
8. Version is `0.32.0` in all four files, and `make verify-structure-strict` reports no manifest
   or doc-version-drift warnings.
9. `make eval-ci` passes (every skill >= 57), and the new skill's own score is recorded in the PR
   body from `make eval-skill`.
10. A tracking issue exists on `bossjones/boss-skills` for the `review` trigger collision, and
    `.claude/skills/review/` is unmodified.
11. Running the skill in a repository with no `CLAUDE.md`, no `AGENTS.md`, and no profile produces
    a scope line, a "no profile found" note, and either citable findings or a plain "no findings" —
    never an invented convention.

## Verification

Mechanical gates, in the order they will fail:

```bash
make verify-structure-strict     # frontmatter, manifest parity, doc version drift
uv run scripts/validate-unicode-hygiene.py
uv run rumdl check .             # MD057 relative links, MD051 anchors, MD034, MD059
make lint                        # codespell over plugins/
make eval-skill SKILL=plugins/boss-dev/agent-harness/skills/review-changes
make eval-ci                     # the CI gate: every skill >= 57
make link-check                  # lychee; confirm no 404 from the provenance references
make symlink-plugins-check
make ci                          # pytest
```

Then prove the skill actually works, in this repo and in a foreign one:

1. **Docs-only diff, this repo.** On a scratch branch, introduce a deliberate stale count and a
   broken relative link in a markdown file, then invoke the skill. Expect the `claims` and
   `cross-refs` lenses to fire, a non-zero validation drop count on the first run, and no findings
   on skipped files.
2. **Code diff, this repo.** Edit a hook or script under
   [`plugins/boss-dev/agent-harness/hooks/`](../plugins/boss-dev/agent-harness/hooks/) with a
   swallowed exception. Expect the `code` lens to fire and to **not** report anything
   `.pre-commit-config.yaml` or `devtools/lint.py` already owns (Rule 4 working).
3. **Untracked file.** Create a new untracked markdown file with a false claim and confirm it is
   reviewed — this is the case `git diff "$MB"` misses and the reason for the `--no-index` path.
4. **Foreign repo, no `CLAUDE.md`, no profile.** Run it in a repo with none of this repo's
   conventions (a plain TypeScript or Rust checkout). Expect: it resolves a base, states the scope,
   reports that no profile was found, and either produces citable findings or says "no findings"
   plainly. **A repo with no rules must produce a quiet review, not an invented one** — that is the
   pass condition for the whole port.
5. **Degenerate git states.** Confirm graceful behaviour with no remote, on the default branch, and
   in a `.worktrees/` checkout (this repo has live worktrees to test against).

## Notes

- **No new dependencies.** No `uv add`, no scripts, no tests. `git` is required; `gh` and Scout MCP
  tools are optional and probed.
- **Deliberately not reused.** `fetch-diff` is remote-PR-only with a different column format;
  extending it would change a contract four other skills depend on. The `boss-experimental`
  `reviewer` agent is in a **different plugin** and cannot be a dependency of a user-scope
  `agent-harness` install. Both are cross-linked instead.
- **Deferred by decision.** No `eval/` suite this PR (only `harness-doctor` has one, and
  `claude-config-validation` Check #22 is explicitly opt-in; the user will scaffold it separately).
  No PEP 723 scripts — the awk annotator stays, verified on BSD `awk` 20200816.
- **Known residual risk from the pure-markdown choice.** The Step 4 validation gate is model-
  executed, so it is only as reliable as the model's discipline. The mitigation is the source's own
  and it is kept prominently: report the drop count per lens, and treat a zero drop count on a
  large diff as evidence the gate did not run.
- **A known awk limitation to leave alone.** The hunk-header parse `split($3,a,",")` is correct for
  normal diffs including single-line hunks (`@@ -1 +1 @@` parses to `ln=0`, verified) but would
  misparse a combined merge diff (`@@@ ... @@@`). The skill never diffs a merge, so this is
  documented rather than fixed.
- **Eval report path**, if one is generated later: `docs/evals/agent-harness/review-changes.md`,
  never inside the skill directory, plus a bullet in
  [`docs/evals/README.md`](../docs/evals/README.md).
