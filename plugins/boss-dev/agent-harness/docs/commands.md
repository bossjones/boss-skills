# Commands Reference

Seventeen slash commands under `commands/*.md`, auto-discovered on `/plugin install` and namespaced as
`/agent-harness:<name>`. Commands are **user-invoked** — you type them; Claude runs the workflow.

> [!IMPORTANT]
> **Run the autonomous, code-changing commands with Plan mode + an Opus-level model.**
> `fix-gh-pr-comments`, `autobuild`, `debug-ci`, and `plan_w_team` edit code and loop across
> multiple cycles. Launch Claude in plan mode with a strong model, review the proposed plan, then
> choose **"Approve and start in auto mode"** for hands-off execution:
>
> ```bash
> claude --model 'claude-opus-4-8[1m]' --permission-mode plan
> ```
>
> Model variants and the full rationale are in
> [Running autonomous commands](./getting-started.md#running-autonomous-commands-plan-mode--opus).

## Table of Contents

- [At a glance](#at-a-glance)
- [Planning & building](#planning--building)
  - [`plan`](#plan)
  - [`plan_w_team`](#plan_w_team)
  - [`build`](#build)
  - [`autobuild`](#autobuild)
- [Context & inspection](#context--inspection)
  - [`prime`](#prime)
  - [`question`](#question)
  - [`all_tools`](#all_tools)
- [Git & CI shipping](#git--ci-shipping)
  - [`commit-push-pr`](#commit-push-pr)
  - [`fix-gh-pr-comments`](#fix-gh-pr-comments)
  - [`debug-ci`](#debug-ci)
- [Hygiene & validation](#hygiene--validation)
  - [`validate-unicode-hygiene`](#validate-unicode-hygiene)
- [Status line & demos](#status-line--demos)
  - [`update_status_line`](#update_status_line)
  - [`sentient`](#sentient)
- [Documentation](#documentation)
  - [`docs-tutorial`](#docs-tutorial)
- [cmux orchestration](#cmux-orchestration)
  - [`cmux-fresh`](#cmux-fresh)
  - [`cmux-spawn-team`](#cmux-spawn-team)
  - [`cmux-did-spawn`](#cmux-did-spawn)

## At a glance

| Command | Arguments | When to use | Needs |
| --- | --- | --- | --- |
| [`plan`](#plan) | `[user prompt]` | Turn a request into a saved spec under `specs/` | — |
| [`plan_w_team`](#plan_w_team) | `[prompt] [orchestration]` | Plan multi-agent work with task dependencies | `uv` |
| [`build`](#build) | `[path-to-plan]` | Implement an existing plan file | — |
| [`autobuild`](#autobuild) | `<spec-path>` | Implement → commit → PR → address review, in a worktree | `git`, `gh` |
| [`prime`](#prime) | — | Load project context into a fresh session | — |
| [`question`](#question) | `[question]` | Ask about the project without editing code | — |
| [`all_tools`](#all_tools) | — | List every available tool as TS signatures | — |
| [`commit-push-pr`](#commit-push-pr) | — | Commit current changes and open/update a PR | `gh` |
| [`fix-gh-pr-comments`](#fix-gh-pr-comments) | `[PR number]` | Resolve unresolved PR review comments | `gh` |
| [`debug-ci`](#debug-ci) | `[run ID]` | Diagnose and fix a failing GitHub Actions run | `gh` |
| [`validate-unicode-hygiene`](#validate-unicode-hygiene) | `[paths...] [--strict] [--warn-only]` | Scan files for invisible / spoofed Unicode | `uv` |
| [`update_status_line`](#update_status_line) | `<session_id> <key> <value>` | Write custom data into a session status line | — |
| [`sentient`](#sentient) | — | Demo the `rm -rf` hook guard | — |
| [`docs-tutorial`](#docs-tutorial) | `[what to document]` | Generate a tutorial/doc via the right tutorial-engineer subagent | — |
| [`cmux-fresh`](#cmux-fresh) | — | Clear cmux's saved session so it boots blank | cmux (macOS) |
| [`cmux-spawn-team`](#cmux-spawn-team) | `[team-name] [feature...] [--config PATH]` | Boot a multi-agent team as a cmux workspace | `uv`, cmux (macOS) |
| [`cmux-did-spawn`](#cmux-did-spawn) | `<spawn-file path>` | Orient onto a just-spawned team and drive its lead | cmux (macOS) |

---

## Planning & building

### `plan`

> Create a concise engineering implementation plan from a request and save it to `specs/`.

- **Arguments:** `[user prompt]` — the requirement to plan (`$1`). Stops and asks if omitted.
- **When to use:** You have a feature/fix/refactor request and want a reviewable blueprint before
  any code is written. Output is a single markdown spec another developer (or `build`) can follow.
- **What it does:** Classifies the task (chore/feature/refactor/fix/enhancement) and complexity,
  studies the codebase directly, then writes a structured spec (Objective, Relevant Files, Step by
  Step Tasks, Acceptance Criteria, Validation Commands) to `specs/<kebab-name>.md`.
- **Example:**

  ```text
  /agent-harness:plan add Redis-backed rate limiting to the public REST API
  ```

- **Source:** [`commands/plan.md`](../commands/plan.md)

### `plan_w_team`

> Produce a team-orchestrated plan with task dependencies and builder/validator assignments.

- **Arguments:** `[user prompt]` (`$1`) and optional `[orchestration prompt]` (`$2`) to steer team
  composition and parallel/sequential structure. Model: **opus**.
- **When to use:** Larger work you want broken into discrete tasks with explicit dependencies and
  owners, executed by multiple agents. This command **plans only** — it does not build.
- **What it does:** Adds a `## Team Orchestration` and `### Team Members` section on top of the
  standard plan, defining tasks with IDs, `blockedBy` dependencies, and assignments to the
  [`team/builder`](./agents.md#teambuilder) and [`team/validator`](./agents.md#teamvalidator)
  subagents (or `general-purpose`). A Stop hook validates the spec contains the required sections.
- **Example:**

  ```text
  /agent-harness:plan_w_team migrate the auth service to JWT  Use one builder per endpoint, validate at the end
  ```

- **Source:** [`commands/plan_w_team.md`](../commands/plan_w_team.md)

> [!IMPORTANT]
> Orchestrates Opus subagents — launch with plan mode + an Opus-level model:
> `claude --model 'claude-opus-4-8[1m]' --permission-mode plan`, then approve into auto mode. See
> [Running autonomous commands](./getting-started.md#running-autonomous-commands-plan-mode--opus).

### `build`

> Read a plan file and implement it step by step.

- **Arguments:** `[path-to-plan]` (`$ARGUMENTS`). Stops and asks if omitted.
- **When to use:** You already have a plan (from `plan` or `plan_w_team`) and want it implemented.
- **What it does:** Reads the plan, implements it into the codebase, then presents the plan's
  `## Report` section.
- **Example:**

  ```text
  /agent-harness:build specs/add-redis-rate-limiting.md
  ```

- **Source:** [`commands/build.md`](../commands/build.md)

### `autobuild`

> Implement a spec inside a git worktree, then commit, push, open a PR, and address review comments.

- **Arguments:** `<spec-path>` (`$1`). Model: **opus**.
- **When to use:** End-to-end "ship this spec" automation. **Must run inside a linked git worktree**
  (it hard-stops on the main checkout) — pair it with the [`git-worktree`](./skills.md#git-worktree)
  skill or `claude --worktree`.
- **What it does:** Verifies it's in a linked worktree → loads and restates the spec → implements it
  with project conventions (and TDD if the spec asks) → runs `make lint` / `make test` → then chains
  the existing [`commit-push-pr`](#commit-push-pr) and [`fix-gh-pr-comments`](#fix-gh-pr-comments)
  commands rather than reimplementing them. Carries its own PostToolUse `ty`/`ruff` validator hooks.
- **Example:**

  ```text
  /agent-harness:autobuild specs/add-redis-rate-limiting.md
  ```

- **Source:** [`commands/autobuild.md`](../commands/autobuild.md)

> [!IMPORTANT]
> Autonomous and multi-cycle (implements → ships → addresses review) — launch with plan mode + an
> Opus-level model: `claude --model 'claude-opus-4-8[1m]' --permission-mode plan`, then approve into
> auto mode. See
> [Running autonomous commands](./getting-started.md#running-autonomous-commands-plan-mode--opus).

---

## Context & inspection

### `prime`

> Load context for a new session by scanning the codebase, README, and docs.

- **Arguments:** none. Allowed tools: `Bash`, `Read`.
- **When to use:** First thing in a fresh session on an unfamiliar repo — gives Claude a working
  mental model before you ask for changes.
- **What it does:** Runs `git ls-files`, reads `README.md` and the `ai_docs/*` references, and
  reports a summary of the project's purpose and structure.
- **Example:**

  ```text
  /agent-harness:prime
  ```

- **Source:** [`commands/prime.md`](../commands/prime.md)

### `question`

> Answer questions about project structure and documentation without writing code.

- **Arguments:** `[question]` (`$ARGUMENTS`). Allowed tools: `Bash(git ls-files:*)`, `Read` — it
  cannot edit files.
- **When to use:** You want an explanation or orientation and explicitly do **not** want changes.
- **What it does:** Inspects structure via `git ls-files` and the README, then answers with
  supporting evidence and references. If a real answer needs code changes, it explains them
  conceptually instead of doing them.
- **Example:**

  ```text
  /agent-harness:question how does the hook logging pipeline write to logs/?
  ```

- **Source:** [`commands/question.md`](../commands/question.md)

### `all_tools`

> List every available tool as TypeScript-style signatures with their purpose.

- **Arguments:** none.
- **When to use:** You want a quick inventory of the tools available in the current session.
- **What it does:** Prints each tool as a TypeScript function signature suffixed with its purpose.
- **Example:**

  ```text
  /agent-harness:all_tools
  ```

- **Source:** [`commands/all_tools.md`](../commands/all_tools.md)

---

## Git & CI shipping

These three require an authenticated `gh` CLI and hard-stop with instructions if `gh auth status`
fails.

### `commit-push-pr`

> Stage changes, write a conventional commit, push, and open or update a PR.

- **Arguments:** none. Allowed tools: `Bash`, `Read`, `Glob`, `Grep`.
- **When to use:** Your changes are ready to ship and you want a clean conventional commit plus a PR
  without doing the git dance by hand.
- **What it does:** Inspects `git status`/`diff`, stages **only specific files** (never `-A`/`.`,
  never secrets), writes a `<prefix>(scope): subject` commit with a `Co-Authored-By` footer, pushes
  (setting upstream if needed), then reuses the branch's PR if one exists or creates one with a
  Summary + Test plan body.
- **Guardrails:** never amends, never force-pushes, never stages `.env`/keys/credentials.
- **Example:**

  ```text
  /agent-harness:commit-push-pr
  ```

- **Source:** [`commands/commit-push-pr.md`](../commands/commit-push-pr.md)

### `fix-gh-pr-comments`

> Fetch unresolved PR review comments, evaluate each, fix, push, reply per-thread, and re-poll.

- **Arguments:** optional PR number (`/agent-harness:fix-gh-pr-comments 42`); otherwise resolves the
  PR from the current branch.
- **When to use:** A PR has review feedback (from humans or bots like `gemini-code-assist`) and you
  want it triaged and addressed systematically.
- **What it does:** A 7-phase loop — fetch top-level unresolved comments, triage by severity
  (security → bugs → correctness → nits), verify each against the current code, apply minimal fixes,
  run `make lint`/`test`, push one conventional commit, reply on each thread with the SHA (pushing
  back with technical reasoning where a suggestion is wrong), then poll for new comments. **Up to 3
  outer cycles.**
- **Example:**

  ```text
  /agent-harness:fix-gh-pr-comments 128
  ```

- **Source:** [`commands/fix-gh-pr-comments.md`](../commands/fix-gh-pr-comments.md)

> [!IMPORTANT]
> Autonomous and multi-cycle (≤ 3 fetch → fix → push → reply loops) — launch with plan mode + an
> Opus-level model: `claude --model 'claude-opus-4-8[1m]' --permission-mode plan`, then approve into
> auto mode. See
> [Running autonomous commands](./getting-started.md#running-autonomous-commands-plan-mode--opus).

### `debug-ci`

> Diagnose a failed GitHub Actions run, fix it locally, push, and verify the new run passes.

- **Arguments:** optional run ID; otherwise picks the most recent failed run on the current branch.
- **When to use:** CI is red and you want the failure categorized, fixed, and re-verified end to end.
- **What it does:** A 6-phase loop — diagnose via `gh run view --log-failed`, categorize (uv-lock,
  pre-commit, ruff-check, ruff-format, ty, deptry, pytest, mkdocs), fix each, validate locally
  mirroring the CI jobs, push, then **smart-poll the new run by matching the commit SHA** (never the
  old run). **Up to 3 outer cycles**, max 10 minutes polling per run.
- **Example:**

  ```text
  /agent-harness:debug-ci
  ```

- **Source:** [`commands/debug-ci.md`](../commands/debug-ci.md)

> [!IMPORTANT]
> Autonomous and multi-cycle (diagnose → fix → push → poll, ≤ 3 cycles) — launch with plan mode + an
> Opus-level model: `claude --model 'claude-opus-4-8[1m]' --permission-mode plan`, then approve into
> auto mode. See
> [Running autonomous commands](./getting-started.md#running-autonomous-commands-plan-mode--opus).

---

## Hygiene & validation

### `validate-unicode-hygiene`

> Scan files for invisible or visually-spoofed Unicode and report findings by severity.

- **Arguments:** `[paths...]` plus `--strict` / `--warn-only`. Allowed tool:
  `Bash(uv run scripts/validate-unicode-hygiene.py:*)`.
- **When to use:** Before committing or publishing skills/plugins, or when reviewing an untrusted
  `SKILL.md`, `plugin.json`, agent, or command file for hidden-instruction payloads.
- **What it does:** Runs the repo-root validator (`scripts/validate-unicode-hygiene.py`) over the
  given paths — or the default target globs (skills, plugins, commands, agents, marketplace) when
  none are passed — and prints per-file findings plus a `Scanned N file(s): X BLOCKER, Y MAJOR,
  Z MINOR` summary. It exits non-zero on a BLOCKER (invisible tag characters or bidirectional
  controls), or on a MAJOR under `--strict`; MINOR (homoglyph) findings never fail. Pairs with the
  [`unicode-hygiene`](./skills.md#unicode-hygiene) skill, which documents the severity model.
- **Example:**

  ```text
  /agent-harness:validate-unicode-hygiene skills/ --strict
  ```

- **Source:** [`commands/validate-unicode-hygiene.md`](../commands/validate-unicode-hygiene.md)

---

## Status line & demos

### `update_status_line`

> Upsert a key/value pair into a session's status-line data file.

- **Arguments:** `<session_id> <key> <value>`.
- **When to use:** You want a custom field (project name, current status, ticket) to show up in a
  status line that renders the `extras` object.
- **What it does:** Loads `.claude/data/sessions/{session_id}.json`, creates an `extras` object if
  needed, upserts `extras[key] = value`, and writes it back — then reports old/new values and the
  file path.
- **Example:**

  ```text
  /agent-harness:update_status_line 4c932bd7-ee06-46e3-b26b-f32f52cc0862 status debugging
  ```

- **Source:** [`commands/update_status_line.md`](../commands/update_status_line.md) · pairs with
  [status-lines.md](./status-lines.md)

### `sentient`

> Demo command that triggers the `rm -rf` guard in the PreToolUse hook.

- **Arguments:** none. Allowed tools: `Bash`. **Demo only.**
- **When to use:** To see the dangerous-command guard in `pre_tool_use.py` block destructive Bash —
  a safe way to confirm the hook is active.
- **What it does:** Attempts three `rm -rf` variations against the repo; the PreToolUse hook blocks
  them and the command reports the results.
- **Example:**

  ```text
  /agent-harness:sentient
  ```

- **Source:** [`commands/sentient.md`](../commands/sentient.md) · see [hooks.md](./hooks.md)

---

## Documentation

### `docs-tutorial`

> Generate a tutorial (or other doc) by delegating to `/documentation-generation:doc-generate`,
> routing to the correct fully-qualified tutorial-engineer subagent.

- **Arguments:** `[what to document]` — optional. With no prompt, defaults to a tutorial about the
  features introduced on the current git branch.
- **When to use:** You want a tutorial/guide written and keep forgetting the exact subagent name.
  This command pins the two correct names and picks between them.
- **What it does:** Resolves the topic (or the current-branch default), classifies the request as
  documentation-related (→ `documentation-generation:documentation-generation-tutorial-engineer`) or
  code-related (→ `code-documentation:code-documentation-tutorial-engineer`), asks clarifying
  questions (existing material, new-vs-update, scope) before writing, then hands the work to
  `/documentation-generation:doc-generate` naming the chosen subagent.
- **Example:**

  ```text
  /agent-harness:docs-tutorial a tutorial on the cmux and cmux-team skills
  ```

- **Source:** [`commands/docs-tutorial.md`](../commands/docs-tutorial.md)

---

## cmux orchestration

Drive [cmux](https://cmux.com) and orchestrate a team of terminal agents on top of it. macOS-only
(Homebrew cask `manaflow-ai/cmux`). See the [`boss-cmux`](./skills.md#boss-cmux) and
[`boss-cmux-team`](./skills.md#boss-cmux-team) skills for the underlying model. For a hands-on, step-by-step
walkthrough, see the [cmux tutorial](./cmux-tutorial.md).

### `cmux-fresh`

> Clear cmux's persisted session so the next launch opens with fresh/blank windows.

- **Arguments:** none. Allowed tools: `Bash`.
- **When to use:** cmux restores a stale window/pane layout on launch and you want a clean slate.
- **What it does:** Quits cmux (so the clear sticks), backs up each session file to a `.bak-<epoch>`,
  then empties the top-level `windows` array in `session-com.cmuxterm.app.json` and its `-previous`
  sibling. Only touches those two files.
- **Source:** [`commands/cmux-fresh.md`](../commands/cmux-fresh.md)

---

### `cmux-spawn-team`

> Boot a multi-agent team (lead + workers) as a new workspace in the cmux window.

- **Arguments:** `[team-name] [feature description...] [--config PATH]`.
- **When to use:** Standing up a team of terminal agents on one feature. Reuses the open window; one
  team = one workspace = one feature.
- **What it does:** Runs the generalized `spawn_team.py` fast path (or drives cmux by hand) to boot
  every role's pane from a team-config JSON, label/color the workspace, and hand command to an
  orchestrator oriented via `/cmux-did-spawn`. No app/models hardcoded — all from config.
- **Example:**

  ```text
  /agent-harness:cmux-spawn-team api-team "add a health endpoint"
  ```

- **Source:** [`commands/cmux-spawn-team.md`](../commands/cmux-spawn-team.md) · uses the
  [`boss-cmux-team`](./skills.md#boss-cmux-team) skill

---

### `cmux-did-spawn`

> Orient onto a just-spawned team and stand ready to drive its lead.

- **Arguments:** `<spawn-file path>` (`.team/<feature>.spawn.json`).
- **When to use:** Right after `spawn_team.py` execs an orchestrator — take command of the team.
- **What it does:** Reads the spawn file, locates the team's workspace by the stable window UUID +
  workspace name, rediscovers current surface refs, confirms the workers reported ready, and drives
  only the lead.
- **Source:** [`commands/cmux-did-spawn.md`](../commands/cmux-did-spawn.md)
</content>
