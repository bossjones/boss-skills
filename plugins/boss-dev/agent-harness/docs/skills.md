# Skills Reference

Skills live under `skills/<skill-name>/SKILL.md`, auto-discovered on `/plugin install`. Skills are
**model-invoked** capabilities — Claude activates them automatically when a task matches — except
where a skill sets `disable-model-invocation: true`, in which case you trigger it explicitly (ask
for it by name, e.g. "use the git-worktree skill", or `/agent-harness:<name>`).

## Table of Contents

- [At a glance](#at-a-glance)
- [PR review workflow](#pr-review-workflow)
  - [`fetch-diff`](#fetch-diff)
  - [`fetch-unresolved-comments`](#fetch-unresolved-comments)
  - [`pr-review`](#pr-review)
  - [`add-review-comment`](#add-review-comment)
- [Git worktree lifecycle](#git-worktree-lifecycle)
  - [`git-worktree`](#git-worktree)
  - [`git-worktree-status`](#git-worktree-status)
  - [`git-worktree-clean`](#git-worktree-clean)
  - [`git-worktree-remove`](#git-worktree-remove)
  - [`worktree-doctor`](#worktree-doctor)
- [Release notes](#release-notes)
  - [`release-notes-generator`](#release-notes-generator)
- [Content & supply-chain hygiene](#content--supply-chain-hygiene)
  - [`stop-slop`](#stop-slop)
  - [`unicode-hygiene`](#unicode-hygiene)
- [Machine setup](#machine-setup)
  - [`setup-second-brain`](#setup-second-brain)
- [Type checking](#type-checking)
  - [`pyrefly-typing`](#pyrefly-typing)
- [cmux orchestration](#cmux-orchestration)
  - [`boss-cmux`](#boss-cmux)
  - [`boss-cmux-team`](#boss-cmux-team)
- [Security review](#security-review)
  - [`boss-security-review`](#boss-security-review)
- [Dependencies](#dependencies)

## At a glance

| Skill | Invocation | When to use | Needs |
| --- | --- | --- | --- |
| [`fetch-diff`](#fetch-diff) | model-invoked | Get a PR diff with line numbers for review | `uv`, `gh`/`GH_TOKEN` |
| [`fetch-unresolved-comments`](#fetch-unresolved-comments) | model-invoked | Get only open PR review threads | `uv`, `gh` |
| [`pr-review`](#pr-review) | explicit | Full PR review → local payload (no posting) | `uv`, `gh` |
| [`add-review-comment`](#add-review-comment) | model-invoked | Post one inline comment to a PR line | `gh` |
| [`git-worktree`](#git-worktree) | explicit | Start a feature in an isolated worktree | `git` 2.5+ |
| [`git-worktree-status`](#git-worktree-status) | explicit | Non-blocking worktree health check | `git` |
| [`git-worktree-clean`](#git-worktree-clean) | explicit | Batch-clean stale/merged worktrees | `git` |
| [`git-worktree-remove`](#git-worktree-remove) | explicit | Safely remove one worktree | `git` |
| [`worktree-doctor`](#worktree-doctor) | model-invoked | Suggest a `.worktreeinclude` so worktrees inherit local files | `uv`, `git` |
| [`release-notes-generator`](#release-notes-generator) | model-invoked | Draft changelog/PR/Slack notes | `git`, `gh` |
| [`stop-slop`](#stop-slop) | model-invoked | Strip AI writing patterns from prose | — |
| [`unicode-hygiene`](#unicode-hygiene) | model-invoked | Scan files for invisible / spoofed Unicode | `uv` |
| [`setup-second-brain`](#setup-second-brain) | explicit | Install/configure obsidian-wiki + optional QMD semantic search | `uv`, `node`≥22 for QMD |
| [`pyrefly-typing`](#pyrefly-typing) | explicit | Adopt Pyrefly into a *target* repo as a non-blocking typing feedback loop | `uv` |
| [`boss-security-review`](#boss-security-review) | model-invoked | Security-review changed code (or a path/whole repo) → severity-graded report | `git` |
| [`boss-cmux`](#boss-cmux) | model-invoked | Drive cmux windows/workspaces/panes/surfaces from natural language | cmux (macOS) |
| [`boss-cmux-team`](#boss-cmux-team) | model-invoked | Spawn/orient/drive a config-driven multi-agent team in cmux | `uv`, cmux (macOS) |

> **Adapted from:** the PR-review skills are adapted from
> [mlflow](https://github.com/mlflow/mlflow) (Apache-2.0); the worktree and release-notes skills are
> adapted from
> [claude-code-ultimate-guide](https://github.com/FlorianBruniaux/claude-code-ultimate-guide) (MIT).

---

## PR review workflow

A composable set for reviewing PRs: pull the diff, focus on open threads, produce a structured
review, and post individual comments. See [workflows.md](./workflows.md#pr-review-loop) for how they
chain with [`fix-gh-pr-comments`](./commands.md#fix-gh-pr-comments).

### `fetch-diff`

> Fetch a GitHub PR diff with old/new line numbers and auto-generated-file masking.

- **When to use:** You need a PR's diff annotated with line numbers to place inline review comments,
  or want it filtered to specific file globs.
- **What it does:** Runs a self-contained PEP 723 script that fetches the diff, annotates each line
  with old/new numbers, and masks auto-generated files (lock files, generated protobuf) so review
  focuses on hand-written changes. The token is auto-detected from `GH_TOKEN` or `gh auth token`.
- **Example:**

  ```bash
  uv run "${CLAUDE_SKILL_DIR}/scripts/fetch_diff.py" https://github.com/owner/repo/pull/123
  uv run "${CLAUDE_SKILL_DIR}/scripts/fetch_diff.py" https://github.com/owner/repo/pull/123 --files '*.py'
  ```

- **Source:** [`skills/fetch-diff/SKILL.md`](../skills/fetch-diff/SKILL.md) ·
  script [`scripts/fetch_diff.py`](../skills/fetch-diff/scripts/fetch_diff.py)

### `fetch-unresolved-comments`

> Fetch only the unresolved PR review threads via the GitHub GraphQL API, grouped by file.

- **When to use:** Before addressing reviewer feedback, when you want just the open threads and not
  already-resolved noise.
- **What it does:** Resolves the PR URL (from `PR_NUMBER` + `GITHUB_REPOSITORY`, or `gh pr view`),
  then queries GraphQL and returns JSON with a `total` count and a `by_file` map of unresolved
  threads (thread id, line, diff hunk, and each comment's author/body/timestamp).
- **Example:**

  ```bash
  uv run "${CLAUDE_SKILL_DIR}/scripts/fetch_unresolved_comments.py" https://github.com/owner/repo/pull/123
  ```

- **Source:** [`SKILL.md`](../skills/fetch-unresolved-comments/SKILL.md) · script
  [`fetch_unresolved_comments.py`](../skills/fetch-unresolved-comments/scripts/fetch_unresolved_comments.py)

### `pr-review`

> Review a PR and emit a schema-validated local review payload — inline comments plus a decision.

- **Invocation:** explicit (`disable-model-invocation: true`).
  `/agent-harness:pr-review <owner_repo> <pr_number> [extra_context]`
- **When to use:** Asked to review a PR or audit changes and produce review comments **without
  posting** them — for example to inspect before deciding to submit.
- **What it does:** Gathers context (diff via `fetch-diff`, existing threads, PR body), analyzes for
  correctness/security/edge cases/efficiency/readability/test-coverage, classifies findings
  (CRITICAL/MODERATE/NIT), and writes a payload to `/tmp/review-payload.json` validated against
  [`review-payload.schema.json`](../skills/pr-review/review-payload.schema.json). The PR is inspected
  as the merge result (`refs/pull/<pr>/merge`); every payload ends with a `🤖 Generated with Claude`
  line.
- **Example:**

  ```text
  /agent-harness:pr-review octocat/hello-world 42
  ```

- **Source:** [`skills/pr-review/SKILL.md`](../skills/pr-review/SKILL.md) ·
  validator [`scripts/validate_review.py`](../skills/pr-review/scripts/validate_review.py)

### `add-review-comment`

> Post a single inline review comment to a specific PR line or line range.

- **When to use:** You have one finding and want it anchored to an exact line, a multi-line range, or
  delivered as a one-click `suggestion` block. For a whole-PR review, use [`pr-review`](#pr-review).
- **What it does:** Invokes `fetch-diff` to confirm the line is in a diff hunk, then POSTs to
  `repos/{owner}/{repo}/pulls/{pr}/comments` via `gh api` with `path`, `line`, `side` (RIGHT for
  added/modified, LEFT for deleted), optional `start_line`/`start_side` for ranges, and `commit_id`.
  Comments end with `🤖 Generated with Claude`.
- **Source:** [`skills/add-review-comment/SKILL.md`](../skills/add-review-comment/SKILL.md)

---

## Git worktree lifecycle

Skills that cover the full lifecycle of isolated worktrees. The four `git-worktree*` skills set
`disable-model-invocation: true`, so invoke them explicitly; `worktree-doctor` is model-invoked.
Walkthrough in [workflows.md](./workflows.md#worktree-lifecycle).

### `git-worktree`

> Create an isolated worktree for feature development without switching branches.

- **Arguments:** `<branch_name> [--from <base>]`. Flags: `--fast` (skip install/tests),
  `--isolated` (fresh deps), `--skip-install`.
- **When to use:** Starting a new feature, fix, or experiment that needs its own working directory.
- **What it does:** Validates and conventionally prefixes the branch name (`feat/`, `fix/`, …),
  creates the worktree under `.worktrees/`, symlinks dependencies to avoid duplicate `node_modules`,
  detects a database provider and suggests branch-isolation commands, installs deps, and kicks off
  background verification (type-check, tests, build). Copies files that are both gitignored and
  listed in `.worktreeinclude` — see [`worktree-doctor`](#worktree-doctor) to generate that file.
- **Example:**

  ```text
  /agent-harness:git-worktree add-rate-limiter --from main
  ```

- **Source:** [`skills/git-worktree/SKILL.md`](../skills/git-worktree/SKILL.md)

### `git-worktree-status`

> Non-blocking report on the background verification jobs for a worktree.

- **When to use:** From inside a worktree, to check type-check/test/build results without blocking.
- **What it does:** Reads `.worktree-logs/`, reports per-check PASS/FAIL/RUNNING/NOT_RUN, commits
  ahead, disk usage, and log locations.
- **Source:** [`skills/git-worktree-status/SKILL.md`](../skills/git-worktree-status/SKILL.md)

### `git-worktree-clean`

> Batch-clean stale worktrees with merged-branch detection and a disk-usage report.

- **Arguments / flags:** `[--dry-run]`, `--all`, `--force`.
- **When to use:** Feature worktrees have accumulated and you want to reclaim space safely.
- **What it does:** Classifies worktrees (merged / unmerged / protected), auto-removes merged ones,
  reviews unmerged interactively, never touches protected branches (main, master, develop, staging,
  production), and reports reclaimed space plus any DB-branch cleanup commands.
- **Source:** [`skills/git-worktree-clean/SKILL.md`](../skills/git-worktree-clean/SKILL.md)

### `git-worktree-remove`

> Safely remove one worktree with branch cleanup and safety checks.

- **Arguments / flags:** `<worktree_name>`; `--force`, `--keep-branch`, `--keep-remote`.
- **When to use:** You're done with a single feature worktree and want it (and its branches) gone.
- **What it does:** Protects main/develop, warns on uncommitted changes and unmerged branches
  (requiring `-D`/`--force`), removes the worktree, optionally deletes local/remote branches, prunes
  references, and reminds you about leftover DB branches.
- **Source:** [`skills/git-worktree-remove/SKILL.md`](../skills/git-worktree-remove/SKILL.md)

### `worktree-doctor`

> Analyze a repo and suggest a `.worktreeinclude` so worktrees inherit env, secret, and local-config
> files.

- **Arguments:** `[--write]`. Allowed tools: `Bash(uv run:*)`, `Bash(git rev-parse:*)`,
  `Bash(git ls-files:*)`.
- **When to use:** Setting up worktrees in a new repo before the first `/git-worktree`, or when a
  worktree is missing its `.env` / local settings. A plain `git worktree add` — and the
  [`git-worktree`](#git-worktree) skill that wraps it — only copies files that are **both** gitignored
  **and** listed in `.worktreeinclude`.
- **What it does:** Scans gitignored files, proposes `.worktreeinclude` patterns, and reports whether
  `.claude/worktrees/` is gitignored. By default it only prints the suggestion; `--write` writes the
  file (never overwriting an existing `.worktreeinclude`).
- **Example:**

  ```bash
  uv run "${CLAUDE_SKILL_DIR}/scripts/worktree_doctor.py"
  uv run "${CLAUDE_SKILL_DIR}/scripts/worktree_doctor.py" --write
  ```

- **Source:** [`skills/worktree-doctor/SKILL.md`](../skills/worktree-doctor/SKILL.md)

---

## Release notes

### `release-notes-generator`

> Generate release notes in three formats (CHANGELOG, PR body, Slack) from git commits.

- **When to use:** Preparing a release, drafting a changelog or version notes, or writing a
  what's-new / ship announcement.
- **What it does:** Analyzes commits since the last release tag, fetches PR metadata via `gh api`,
  categorizes changes (feat/fix/perf/security/refactor/chore/docs/test/style), and emits three
  outputs: a technical CHANGELOG section, a semi-technical PR release body (using the repo's release
  template if present), and a product-focused Slack message — translating jargon into user-friendly
  language (e.g. "N+1 query optimization" → "Faster list loading"). Detects new migration files and
  surfaces a prominent run-command warning.
- **Reference files:** `assets/changelog-template.md`, `assets/slack-template.md`,
  `references/tech-to-product-mappings.md`, `references/commit-categories.md`.
- **Source:** [`skills/release-notes-generator/SKILL.md`](../skills/release-notes-generator/SKILL.md)

---

## Content & supply-chain hygiene

### `stop-slop`

> Remove predictable AI writing patterns from prose.

- **Invocation:** model-invoked. **Adapted from:** Hardik Pandya (<https://hvpandya.com>).
- **When to use:** Drafting, editing, or reviewing text to eliminate the tells that mark writing as
  AI-generated.
- **What it does:** Applies a rule set — cut filler phrases and adverbs, break formulaic structures
  (binary contrasts, negative listings, rhetorical setups), use active voice with a human subject, be
  specific, vary sentence rhythm, drop em dashes, and cut quotable-sounding lines. Detailed pattern
  lists live in the skill's `references/phrases.md` and `references/structures.md`.
- **Source:** [`skills/stop-slop/SKILL.md`](../skills/stop-slop/SKILL.md)

### `unicode-hygiene`

> Scan skill, plugin, command, agent, and marketplace files for invisible or visually-spoofed
> Unicode.

- **Invocation:** model-invoked. Allowed tool:
  `Bash(uv run scripts/validate-unicode-hygiene.py:*)`.
- **When to use:** Before committing or publishing a skill/plugin/command/agent, when reviewing an
  untrusted `SKILL.md`/`plugin.json`/agent/command, or when auditing
  `.claude-plugin/marketplace.json` for hidden-instruction supply-chain payloads.
- **What it does:** Documents and drives the repo-root, stdlib-only script
  `scripts/validate-unicode-hygiene.py` (the same script CI and pre-commit run). Severities:
  **BLOCKER** — invisible tag characters (U+E0000–U+E007F) and bidirectional controls
  (U+202A–U+202E, U+2066–U+2069), which fail the default scan; **MAJOR** — other zero-width / format
  (`Cf`) characters, reported but only failing under `--strict`; **MINOR** — mixed-script (homoglyph)
  identifiers on install-command lines, which never fail. A leading BOM (U+FEFF at offset 0) is
  allowed. Pairs with the [`validate-unicode-hygiene`](./commands.md#validate-unicode-hygiene)
  command.
- **Example:**

  ```bash
  uv run scripts/validate-unicode-hygiene.py
  ```

- **Source:** [`skills/unicode-hygiene/SKILL.md`](../skills/unicode-hygiene/SKILL.md)

---

## Machine setup

### `setup-second-brain`

> Install and configure the "second brain": the obsidian-wiki uv tool plus optional
> [QMD](https://github.com/tobi/qmd) semantic search, with a backup before any config write.

- **Invocation:** explicit (`disable-model-invocation: true`). Arguments:
  `[--apply | --dry-run]` — ask for it by name or `/agent-harness:setup-second-brain`.
- **When to use:** Bootstrapping a machine's second brain — installing
  `obsidian-wiki[graph,ast]` as a uv tool, running `obsidian-wiki setup` against a vault,
  and (optionally) enabling QMD semantic search so `wiki-query`/`wiki-ingest` use on-device
  semantic matching instead of Grep.
- **What it does:** Owns all user interaction (install choices, vault path, QMD yes/no,
  transport, indexing) and drives a stdlib-only PEP 723 script
  (`scripts/setup_second_brain.py`) for the deterministic config work:
  1. `detect` — read-only JSON report: config + vault state, which `QMD_*` keys are set,
     whether a `qmd` MCP server is present, and env readiness (`uv`, `node` ≥ 22, `npm`,
     `obsidian-wiki`, `qmd`).
  2. `apply --dry-run` — returns a git-style unified `diff` per touched file
     (`~/.obsidian-wiki/config`, and `settings.json` for `mcp` transport) **without writing**.
  3. `apply` — backs up each file, writes the `QMD_*` variables (and, for `mcp` transport,
     merges an additive `qmd` MCP server), then re-parses `settings.json` to confirm validity.

  The installs and vault indexing themselves are run by the skill via Bash after confirmation.

- **Example:**

  ```text
  /agent-harness:setup-second-brain --dry-run
  ```

  ```bash
  # preview the QMD config write without touching anything
  uv run "${CLAUDE_SKILL_DIR}/scripts/setup_second_brain.py" apply --qmd-config --transport cli --search-mode quality --dry-run
  ```

- **Source:** [`skills/setup-second-brain/SKILL.md`](../skills/setup-second-brain/SKILL.md) ·
  script [`scripts/setup_second_brain.py`](../skills/setup-second-brain/scripts/setup_second_brain.py)
- **Tutorial:** [Set up your second brain](../../../../docs/tutorials/agent-harness/second-brain.md)

#### Script CLI reference

The stdlib script has two subcommands. `detect` is read-only; `apply` does the
backup → edit → validate work. Paths default to `~/.obsidian-wiki/config` and
`~/.claude/settings.json`.

| Subcommand / flag | Applies to | Description |
| --- | --- | --- |
| `detect` | — | Print the current state as JSON (read-only). |
| `apply` | — | Backup, then write the requested changes. |
| `--config-path PATH` | both | Override the obsidian-wiki config path. |
| `--settings-path PATH` | both | Override the Claude settings.json path. |
| `--qmd-config` | apply | Write the `QMD_*` variables into the config. |
| `--transport {cli,mcp}` | apply | QMD transport; `mcp` also merges the `qmd` MCP server into settings.json (default `cli`). |
| `--wiki-collection NAME` | apply | `QMD_WIKI_COLLECTION` value (default `wiki`). |
| `--papers-collection NAME` | apply | `QMD_PAPERS_COLLECTION` value (default `papers`). |
| `--search-mode {quality,balanced,fast}` | apply | `QMD_CLI_SEARCH_MODE` value, cli transport only (default `quality`). |
| `--dry-run` | apply | Report intended changes as a unified diff without writing. |

#### `~/.obsidian-wiki/config` schema

One `KEY="value"` per line. `obsidian-wiki setup` writes `OBSIDIAN_VAULT_PATH`; this
skill writes only the `QMD_*` keys (idempotently, in place):

```text
OBSIDIAN_VAULT_PATH="~/Documents/obsidian/personal.vault"
QMD_TRANSPORT="cli"
QMD_WIKI_COLLECTION="wiki"
QMD_PAPERS_COLLECTION="papers"
QMD_CLI_SEARCH_MODE="quality"
```

See [Second brain (obsidian-wiki) environment](./getting-started.md#second-brain-obsidian-wiki-environment)
for the full `OBSIDIAN_*`/`QMD_*` variable tables.

---

## Type checking

### `pyrefly-typing`

> Adopt [Pyrefly](https://pyrefly.org/) into a *target* `uv` Python project as a non-blocking,
> agent-driven typing feedback loop — alongside whatever type checker it already uses, never
> replacing it.

- **Invocation:** explicit (`disable-model-invocation: true`). Arguments:
  `<target-repo-path> [--with-stop-hook] [--dry-run]` — ask for it by name or
  `/agent-harness:pyrefly-typing`.
- **When to use:** Adopting Pyrefly in a repo for the first time, adding the Stop-hook feedback
  loop from Pyrefly's own agentic-loop post, or burning down a batch of baseline type errors.
  **This skill configures the target repo it's pointed at — never `boss-skills` itself.**
- **What it does:** Drives a stdlib-only PEP 723 script (`scripts/pyrefly_setup.py`) with
  `detect`/`apply` subcommands:
  1. `detect` — read-only JSON report: Python version floor, real `src`/`tests` layout, every
     existing type-checker table already configured (`ty`, `basedpyright`, `mypy`, `pyright` — all
     left untouched), a migratable legacy config, and the detected task runner
     (`just`/`make`/`npm`).
  2. `apply --dry-run` — a unified `diff` per changed file (or the exact command for `uv add` /
     `pyrefly init` / baseline generation), without writing.
  3. `apply` — backs up each touched file, then runs `uv add --dev pyrefly`, writes or migrates
     `[tool.pyrefly]`, adds standalone `check-pyrefly`/`pyrefly-baseline`/`pyrefly-coverage`
     targets to the detected task runner, optionally merges a `Stop` hook into the target's own
     `.claude/settings.json`, and generates the initial committed baseline.
- **Example:**

  ```text
  /agent-harness:pyrefly-typing ~/dev/example-project --dry-run
  ```

- **Source:** [`skills/pyrefly-typing/SKILL.md`](../skills/pyrefly-typing/SKILL.md) · script
  [`scripts/pyrefly_setup.py`](../skills/pyrefly-typing/scripts/pyrefly_setup.py)

---

## Security review

### `boss-security-review`

- **Invocation:** model-invoked (or `/agent-harness:boss-security-review`). Triggers on requests
  like "run a security review", "audit this for vulnerabilities", "is this code secure", or
  "review my changes for security" before merging.
- **What it does:** Reviews a target against a security rubric and writes a structured,
  severity-graded findings report — each finding cites the specific rule it triggered, plus
  location, impact, remediation, and a re-check step. Advisory only: it documents issues, it does
  not edit code unless asked.
- **Target:** changed code by default (`git diff` vs. the default branch + working tree); the
  request can override to a named path or the whole repo. Large targets fan out to parallel
  review subagents; small ones review in one pass.
- **Rubric (portable):** prefers the target repo's `.cursor/rules/security-*` when present, else
  the 18 verbatim rule files bundled at `references/security-rules/`, else a built-in OWASP/CWE
  checklist. So it works in any repo, not just this one.
- **Output:** `specs/security-review.md` by default (path overridable from the request).
- **Source:** [`skills/boss-security-review/SKILL.md`](../skills/boss-security-review/SKILL.md) ·
  references [`rubric-map.md`](../skills/boss-security-review/references/rubric-map.md),
  [`severity-model.md`](../skills/boss-security-review/references/severity-model.md),
  [`fanout.md`](../skills/boss-security-review/references/fanout.md)

---

## cmux orchestration

Drive [cmux](https://cmux.com) — a native macOS terminal (Homebrew cask `manaflow-ai/cmux`) that
exposes a CLI + Unix socket so every window/workspace/pane/surface is a scriptable object — from
natural language, and spawn/orchestrate a team of terminal agents on top of it. Ported and generalized
from [learning-cmux-with-agents](https://github.com/disler/learning-cmux-with-agents) (see
[`specs/cmux.md`](../../../../specs/cmux.md)). Both skills trigger anywhere but only function on macOS
with cmux installed. New to cmux? Start with the hands-on [cmux tutorial](./cmux-tutorial.md).

### `boss-cmux`

> Drive cmux windows/workspaces/panes/surfaces and the agents inside them from natural language.

- **Invocation:** model-invoked (or prefix a prompt with `/boss-cmux`). Allowed tools: `Bash`.
- **When to use:** Opening, inspecting, prompting, reading, or tearing down cmux surfaces / agent
  sessions; deterministic multi-pane placement and routing.
- **What it does:** Documents the cmux control loop (`send` types, `send-key enter` submits,
  `read-screen` observes, `close-surface` tears down), credential injection via `--env-file`, the
  push-notification wait channel (`cmux events`, matched on `workspace_id`), launching pi/Codex/Claude
  Code in bypass modes, and the settings/reload discipline (`cmux reload-config`, back up `cmux.json`).
  Ships four topology references (handles, windows/workspaces, panes/surfaces, flash & health).
- **Prerequisites:** `brew install --cask cmux` (macOS 14+), `cmux hooks setup`,
  `automation.socketControlMode: allowAll`.
- **Source:** [`skills/boss-cmux/SKILL.md`](../skills/boss-cmux/SKILL.md) · references under
  [`skills/boss-cmux/references/`](../skills/boss-cmux/references/)

---

### `boss-cmux-team`

> Spawn, orient, and drive a config-driven multi-agent team (lead + workers) as a cmux workspace.

- **Invocation:** model-invoked. Allowed tools: `Bash`. Arguments: `[team-name] [feature description...]`.
- **When to use:** Booting a team of terminal agents on one feature, standing up a "full-stack team" /
  "agent fleet", or attaching to and driving a team that was just spawned.
- **What it does:** A generalized spawner (`scripts/spawn_team.py`, PEP 723) boots every role's pane in
  one `cmux workspace create --layout` call (lead left-half, workers in a balanced grid), from a
  **team-config JSON** — roles, models, launcher, role prompts, app path, and completion sentinel are
  all data (no hardcoded app/models). Supports `--dry-run` (CI-safe). Pairs with the `/cmux-spawn-team`
  and `/cmux-did-spawn` commands.
- **Example:**

  ```bash
  uv run "${CLAUDE_PLUGIN_ROOT}/skills/boss-cmux-team/scripts/spawn_team.py" cc my-feature --dry-run
  ```

- **Source:** [`skills/boss-cmux-team/SKILL.md`](../skills/boss-cmux-team/SKILL.md) · config
  [`assets/team-config.example.json`](../skills/boss-cmux-team/assets/team-config.example.json), role
  templates under [`assets/roles/`](../skills/boss-cmux-team/assets/roles/)

---

## Dependencies

- **`uv`** — runs the PEP 723 scripts behind `fetch-diff`, `fetch-unresolved-comments`,
  `pr-review`, `worktree-doctor`, the `unicode-hygiene` scanner, `setup-second-brain`, and
  `pyrefly-typing` (also invokes `uv add`/`uv run pyrefly` in the target repo). Their
  dependencies (`aiohttp`, `pydantic`, `jsonschema`) resolve on demand, so the skills work right after
  `/plugin install` with no setup step. (The unicode scanner and `setup-second-brain` are stdlib-only
  — no dependencies to resolve.)
- **`node` ≥ 22 + `npm`** — only for the optional QMD step of `setup-second-brain`
  (`npm install -g @tobilu/qmd`). Everything else works without Node; QMD degrades to Grep.
- **`gh`** (authenticated) or **`GH_TOKEN`** — for all GitHub-touching skills.
- **`git` 2.5.0+** — for the worktree suite.

`${CLAUDE_SKILL_DIR}` in the examples is set by Claude Code to the skill's own directory at runtime.
</content>
