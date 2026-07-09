# Plan: Create the `boss-experimental` plugin (genericized skillgrade + Claude-config tooling)

> **Self-contained spec.** Authored for a fresh agent with **zero prior conversation context**.
> Read top to bottom, then work the phases in order. Detailed research backing this spec lives
> in [`specs/boss-experimental/`](boss-experimental/) — read those four findings files first
> (`00-overview.md`, `01-skillgrade-eval-system.md`, `02-config-validation-and-knowledge-arch.md`,
> `03-agents-and-conventions.md`).

## Task Description

Create a new Claude Code plugin, **`boss-experimental`**, in this repo (`boss-skills`). It is a
home for experimental / not-ready-for-prime-time capabilities the maintainer is still testing.
Its **first tenant** is a **genericized port** of three subsystems from the Adobe `hz` repo
(cloned locally at `/Users/malcolm/dev/adobe-claude-creative-mcps/hz`):

- **A — Skillgrade eval system**: run skill evals via the `skillgrade` npm CLI (CI) or via
  Claude Code as the agent (local), sharing one `eval.yaml`.
- **B — Config validation + knowledge architecture**: a `claude-config-validation` skill, a
  knowledge-architecture doctrine doc, an auto-loading authoring rule, a two-step PR checklist.
- **C — Dev-workflow agents**: 8 agents (architect, coder, test-writer, tester, reviewer,
  pr-submission, learner, config-reviewer).

**Every Adobe/hz specific must be stripped** so the plugin is reusable in any project.

## Objective

When complete, `plugins/boss-experimental/boss-experimental/` exists as a valid, registered
plugin containing genericized versions of all three subsystems, with **no leaked hz/Adobe
specifics** in any live instruction, and the plugin registered in
`.claude-plugin/marketplace.json` at version `0.1.0`.

## Problem Statement

The maintainer wants to experiment with `hz`'s skillgrade-based, agent-driven eval approach
**without disrupting** this repo's established eval stack (wshobson `plugin-eval` via
`/skill-evals`, `make eval-skill`, `scripts/plugin_eval/`). The two approaches are genuinely
different (skillgrade = agent runs the skill and graders score the transcript; plugin-eval =
LLM-judge scores the SKILL.md statically/with a judge). An "experimental" plugin lets both
coexist for side-by-side comparison. The `hz` sources are also heavily coupled to Bazel,
Adobe Bedrock/Coder infra, and Horizon-monorepo vocabulary that must be removed.

## Solution Approach

Copy each `hz` source file into the new plugin, then **strip specifics and rewire paths**
(copy-then-modify, never rewrite from scratch). Keep skillgrade **self-contained**: nothing
under `.claude/skills/skill-evals/`, `scripts/plugin_eval/`, `Makefile`, or the existing
`/skill-evals` flow may be modified. Make hz's opinionated constants (the canonical-7 agent
set, monorepo-root markers, the "every skill needs an eval" mandate) **config-driven or
optional** so the tooling works in repos that don't share hz's conventions. Drop all Bazel
build wiring in favor of the plain `run_eval.sh` dual-mode runner (+ an optional GitHub
Actions example).

## Relevant Files

**Read for context (do not modify):**
- `specs/boss-experimental/*.md` — the research findings (primary source of truth).
- `.claude-plugin/marketplace.json` — where the new plugin registers; mirror an existing entry.
- `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json` — richest `plugin.json` example.
- `plugins/boss-dev/python-dev/` and `plugins/boss-homelab/proxmox-infra/` — minimal plugin
  layouts.
- `.claude/skills/version-bump-reviewer/SKILL.md` — versioning/marketplace-parity rules.
- `.claude/skills/skill-evals/SKILL.md` + `scripts/plugin_eval/` — the EXISTING eval stack
  that must be left untouched (read only to understand the boundary).
- `CLAUDE.md` — repo code standards, skill-authoring rules (e.g. the GitHub #12781 backtick
  parser bug: never use `!`-backtick patterns in SKILL.md; use `$ command`).

**hz source files (local paths under `/Users/malcolm/dev/adobe-claude-creative-mcps/hz`):**
- `.claude/skills/run-skill-eval/SKILL.md`
- `.claude/skills/scaffold-skill-eval/` (`SKILL.md`, `BUILD.bazel.tpl`, `eval/`)
- `.claude/skills/claude-config-validation/` (`SKILL.md`, `eval/`)
- `.claude/agents/{architect,coder,config-reviewer,learner,pr-submission,reviewer,test-writer,tester}.md`
- `.claude/rules/claude-config-authoring.md`
- `docs/{claude-code-knowledge-architecture,claude-config-validation-checks,claude-code-skill-eval-guide,skillgrade-eval-yaml-schema,claude-code-self-service-pr-checklist}.md`
- `.claude/settings.json`, `.config/mise/config.coder.toml` (reference only; do NOT port infra)

### New Files (target)

```
plugins/boss-experimental/boss-experimental/
├── .claude-plugin/
│   └── plugin.json                       # name "boss-experimental", displayName, version "0.1.0",
│                                         #   MIT, author, homepage/repository, keywords, "skills":"./skills/"
├── skills/
│   ├── run-skill-eval/SKILL.md           # local runner (Claude-as-agent); ports ~verbatim
│   ├── scaffold-skill-eval/
│   │   ├── SKILL.md                      # 9-step scaffolder; Bazel steps removed
│   │   └── references/
│   │       ├── graders/                  # reusable Node graders (see Component A)
│   │       └── run_eval.sh               # dual-mode runner template
│   └── claude-config-validation/
│       ├── SKILL.md                      # 23 checks; canonical set + root markers config-driven
│       └── eval/                         # worked reference eval (eval.yaml + graders/*.js +
│                                         #   test-fixtures/ + run_eval.sh + README.md + .gitignore)
├── agents/                               # 8 genericized agents
│   ├── architect.md · coder.md · test-writer.md · tester.md
│   ├── reviewer.md · pr-submission.md · learner.md · config-reviewer.md
├── rules/                                # claude-config-authoring.md (SEE OPEN ITEM re: load path)
├── references/
│   ├── knowledge-architecture.md         # genericized KA "constitution"
│   ├── config-validation-checks.md       # the 23-check catalog
│   ├── skillgrade-eval-yaml-schema.md    # upstream schema, port ~as-is
│   ├── config-pr-checklist.md            # two-step (mechanical + judgment) checklist
│   └── skillgrade-vs-plugin-eval.md      # NEW: comparison to this repo's existing eval stack
└── README.md
```
Plus one appended entry in `.claude-plugin/marketplace.json`.

## Implementation Phases

### Phase 1: Foundation
- Create the plugin skeleton: directory tree, `.claude-plugin/plugin.json` (v `0.1.0`), stub
  `README.md`, and the `marketplace.json` entry (`category: "boss-experimental"`,
  `source: "./plugins/boss-experimental/boss-experimental"`, `version: "0.1.0"` matching
  `plugin.json`).
- Confirm `boss-experimental` as a new top-level category under `plugins/` (mirrors
  `boss-dev`/`boss-homelab`).

### Phase 2: Core Implementation
- Port Component A (skillgrade eval system), Component B (config validation + KA), and
  Component C (agents), applying the genericization transforms below.

### Phase 3: Integration & Polish
- Write the `skillgrade-vs-plugin-eval.md` comparison doc; write the full `README.md`; run the
  leaked-specifics grep gate; sanity-run the reference eval's Node graders; resolve the open
  items.

## Step by Step Tasks

IMPORTANT: Execute every step in order, top to bottom.

### 1. Scaffold the plugin and register it
- Create `plugins/boss-experimental/boss-experimental/` with subdirs `.claude-plugin/`,
  `skills/`, `agents/`, `rules/`, `references/`.
- Write `.claude-plugin/plugin.json` modeled on
  `plugins/boss-dev/agent-harness/.claude-plugin/plugin.json`: `$schema`
  `https://json.schemastore.org/claude-code-plugin-manifest.json`, `name`
  `"boss-experimental"`, `displayName`, `version` `"0.1.0"`, `description`, `author`
  (Malcolm Jones / bossjones@theblacktonystark.com / https://github.com/bossjones),
  `homepage` + `repository` `https://github.com/bossjones/boss-skills`, `license` `"MIT"`,
  `keywords` (e.g. experimental, skillgrade, skill-eval, config-validation, agents,
  claude-code), `"skills": "./skills/"`.
- Append a `plugins[]` entry to `.claude-plugin/marketplace.json` with matching `version`
  `0.1.0` and `category` `"boss-experimental"` (parity is enforced by `version-bump-reviewer`).

### 2. Component A — port the skillgrade eval system (self-contained)
- **`run-skill-eval/SKILL.md`**: copy from hz; change only the default `$ARGUMENTS` path
  (hz points at `.claude/skills/claude-config-validation`). Keep the constraint: **run in the
  main session, never a background subagent** (background agents auto-deny Bash → graders
  silently fail). Keep `allowed-tools: Read, Bash, Glob, Grep`.
- **`scaffold-skill-eval/SKILL.md`**: copy from hz; keep the 9-step flow; **delete every Bazel
  step** (the `copy BUILD.bazel.tpl` step and any `BUILD.bazel` references). Keep pinning
  `agent: claude`, `provider: local`, `trials: 5`, `timeout: 300`, `threshold: 0.8` in
  generated `eval.yaml`.
- **Graders + runner**: copy the reusable Node graders into
  `scaffold-skill-eval/references/graders/` — `check-fail-present.js`, `check-no-fails.js`,
  `check-warn-or-fail-present.js`, `check-no-fail-for-pattern.js`, `check-eval-structure.js`,
  `check-eval-yaml-tasks.js`, `check-fixture-count.js`, `check-stopped-early.js`. **Do NOT
  port `check-build-bazel.js`** (Bazel-only and buggy — it asserts an `"external"` tag the
  templates never emit). Copy `run_eval.sh` as a dual-mode template: if `skillgrade` +
  `ANTHROPIC_API_KEY` present → `exec skillgrade --<preset> --provider=local …`; else print
  instructions pointing at `/run-skill-eval`.
- **Schema doc**: copy `docs/skillgrade-eval-yaml-schema.md` → `references/skillgrade-eval-yaml-schema.md`
  ~as-is (it is pure upstream skillgrade schema; remove any hz doc cross-links).
- **Toolchain note in README**: document `node` + `npm i -g skillgrade` / `npx skillgrade`.
  Do **NOT** port any Bedrock/Coder/AWS/mise env. (If a `mise.toml` is desired later, pin only
  `node = "20"`.)
- **No fenced code blocks with language identifiers inside any `SKILL.md`** (hz "check 10" and
  this repo's parser-bug rule). Keep code samples in `references/` files, not in SKILL.md.

### 3. Component B — port config validation + knowledge architecture (genericized)
- **`claude-config-validation/SKILL.md`**: copy from hz (`allowed-tools: Read, Glob, Grep`).
  In Step 0, replace Bazel root-detection (`.bazelignore`, `MODULE.bazel`, multiple `apps/`)
  with a **configurable monorepo-root marker set** (default: `.git`, `pnpm-workspace.yaml`,
  `package.json` with `workspaces`, `lerna.json`, `nx.json`). Make **Check 2's** canonical
  agent set **config-driven** (documented default list, overridable) rather than hardcoding
  hz's 7; drop the `autopilot.manifest.yaml`/`cli.defaultFlowIds` machinery (make
  "pipeline-declared custom agent" an optional, documented extension point).
- **`references/config-validation-checks.md`**: copy the 23-check catalog; keep the checks,
  strip hz examples. Mark Check 22 ("skill has an `eval/`") as **opt-in**, not a repo mandate.
- **`references/knowledge-architecture.md`**: copy the KA doctrine; replace all hz examples
  (`apps/ai-nimbus`, `packages/bricks/`, Brick/MXP/Spectrum/Lit/Kotlin/Android, `@hz/*`,
  `squirrel-coder`) with neutral placeholders (`apps/example-app`, "component" not "brick").
  Keep the Placement Test, Three-Occurrence Rule, loading semantics, enforcement ladder, and
  the (now-configurable) canonical-agent concept.
- **`rules/claude-config-authoring.md`**: copy the auto-loading anti-pattern rule; re-point
  every doc link to the new `references/` paths. **SEE OPEN ITEM** on where this file must live.
- **`references/config-pr-checklist.md`**: copy the two-step (mechanical + judgment) checklist;
  strip `#hz-claude-governance` Slack, `@devex-team`/"Developer Experience team"/"Claude
  Governance team", CODEOWNERS, and PR `#291314`.
- **Worked reference `eval/`**: port `claude-config-validation/eval/` (its `eval.yaml`, the 4
  deterministic graders, the 13 test-fixtures, `README.md`, `run_eval.sh`); **drop `BUILD.bazel`**.
  This doubles as the canonical "how a well-formed skill + eval looks."

### 4. Component C — port the 8 dev-workflow agents (genericized)
- Copy each of `architect.md`, `coder.md`, `test-writer.md`, `tester.md`, `reviewer.md`,
  `pr-submission.md`, `learner.md`, `config-reviewer.md` into `agents/`.
- Strip: "Horizon monorepo" / "tenant application" → "this repo/project"; "brick" →
  "component"; Bazel-target assumptions in `tester.md` → "build/lint/test commands from
  CLAUDE.md"; the WTR example in `learner.md`; the Figma visual-QA delegation in `tester.md`;
  `autopilot.manifest.yaml`; any `teams/<team>/` references.
- Preserve behavior contracts: architect's Write-only-for-TRD, pr-submission's `CONFIRM PUSH`
  human gate, reviewer's `## Verdict: APPROVE / REQUEST_CHANGES`, config-reviewer's read-only
  mode + its dependency on the Component-B validation skill (re-point that reference to the
  new plugin path).
- In `README.md`, **flag the overlap** with `agent-harness`'s existing `builder`/`validator`
  team agents, and state the canonical-7 are experimental/optional here, not a repo mandate.

### 5. Write the comparison doc and README
- `references/skillgrade-vs-plugin-eval.md`: contrast skillgrade (agent-driven trials, Node
  graders over the transcript, `eval.yaml`) with this repo's wshobson `plugin-eval`
  (LLM-judge via `/skill-evals` / `make eval-skill` / `scripts/plugin_eval/`). State
  explicitly that boss-experimental does not modify or replace the existing stack.
- `README.md`: purpose, the three components, install/usage, toolchain (`node`, `skillgrade`),
  and the self-contained/parallel positioning.

### 6. Validate
- Run the leaked-specifics grep gate (see Validation Commands). Any hit outside an explicit
  "strip-list / what-we-removed" note is a failure to fix.
- Sanity-run the reference eval's Node graders with `node` to confirm they emit valid
  `{"score","details"}` JSON and handle the missing-file case.
- Run `make lint` (ruff excludes `.claude/`; confirm it does not choke on the new plugin) and
  `make markdown-lint` if configured.
- Confirm `plugin.json.version` == the `marketplace.json` entry version (both `0.1.0`).

## Testing Strategy
- **Structural**: the reference `eval/` graders are plain Node, zero-dep, and self-testable —
  invoke each `node references/.../graders/<name>.js` against a fixture `output.md` and against
  a missing file; assert one-line JSON and `exit 0`.
- **End-to-end (manual, main session)**: run `/run-skill-eval
  plugins/boss-experimental/boss-experimental/skills/claude-config-validation` and confirm the
  per-task table + overall pass count print. (This uses Claude-as-agent; no API key needed.)
- **Genericization**: the grep gate below is the regression test for leaked specifics.
- No unit-test framework changes; this is config/plugin content, not Python code.

## Acceptance Criteria
- `plugins/boss-experimental/boss-experimental/` exists with the structure above; a
  `plugins[]` entry is registered in `.claude-plugin/marketplace.json` at `0.1.0`.
- All three components are present and genericized; `check-build-bazel.js` is **absent**; no
  `BUILD.bazel`/`BUILD.bazel.tpl` anywhere in the plugin.
- No `SKILL.md` contains fenced code blocks with language identifiers.
- The existing eval stack is untouched: `git status` shows **no** changes under
  `.claude/skills/skill-evals/`, `scripts/plugin_eval/`, or `Makefile`.
- The leaked-specifics grep gate passes (matches only in explicit "removed/strip-list" notes).
- The reference eval's graders emit valid JSON and exit 0.

## Validation Commands
Execute these to validate the task is complete:

- `test -f plugins/boss-experimental/boss-experimental/.claude-plugin/plugin.json && echo OK`
  — plugin manifest exists.
- `python3 -c "import json;print(json.load(open('.claude-plugin/marketplace.json'))['plugins'][-1]['name'])"`
  — should print `boss-experimental`.
- `python3 - <<'PY'` … compare `plugin.json` version to the marketplace entry version (assert equal).
- **Leaked-specifics gate** (should return NOTHING outside strip-list notes):
  `grep -rniE 'bazel|bedrock|horizon|\bbrick\b|autopilot|git\.corp\.adobe\.com|devex|coder\.svc' plugins/boss-experimental/`
- `find plugins/boss-experimental -name 'BUILD.bazel*' -o -name 'check-build-bazel.js'` — must be empty.
- `git status --porcelain -- .claude/skills/skill-evals scripts/plugin_eval Makefile` — must be empty.
- `for g in $(find plugins/boss-experimental -path '*graders/*.js'); do node "$g" /nonexistent.md; done`
  — each prints a JSON line and exits 0.
- `make lint` and `make markdown-lint` — no new errors introduced.

## Notes
- **Open item 1 (rules load path)**: No existing plugin in `boss-skills` ships a `rules/`
  directory (rules live in the repo-level `/.claude/rules/`). Before relying on
  `plugins/boss-experimental/boss-experimental/rules/claude-config-authoring.md` auto-loading,
  **verify** plugin-local `rules/` are honored by the harness. If they are not, place the
  authoring rule in the repo-level `/.claude/rules/` instead and note it in the README.
- **Open item 2 (reference docs location)**: Docs are placed in the plugin's `references/`
  (portable, travels with the plugin). If the harness needs them elsewhere for
  `config-reviewer`/`claude-config-validation` to resolve at runtime, mirror or move to the
  repo `docs/` and re-point links.
- **External dependency**: `node` (for graders) + `skillgrade` (`npm i -g skillgrade`) + an
  LLM API key only for the CI/skillgrade path. The local `/run-skill-eval` path needs neither.
- **Do NOT** add `skillgrade` to `pyproject.toml`/`uv` — it is a Node CLI, not a Python dep.
- Building/using the plugin beyond creation is future work; this spec's deliverable is the
  plugin content itself.
