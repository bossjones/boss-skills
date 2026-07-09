# Component Reference

## Component A: skillgrade eval skills

### `scaffold-skill-eval`

[`skills/scaffold-skill-eval/SKILL.md`](../skills/scaffold-skill-eval/SKILL.md)

| | |
|---|---|
| **Trigger** | `/scaffold-skill-eval <skill-path>`, or auto-invoked on phrases like "scaffold an eval", "generate an eval suite for a skill", "create test fixtures and graders for a skill", "add skillgrade tests" (from its `description` frontmatter) |
| **`allowed-tools`** | `Read`, `Write`, `Bash`, `Glob`, `Grep` |
| **Input** | `skill_path` — path to a skill directory containing a `SKILL.md` |
| **Output** | A complete `{skill_path}/eval/` directory: `eval.yaml`, `run_eval.sh`, `README.md`, `graders/*.js`, `test-fixtures/*/`, `.gitignore` |

**Hard constraints** (from the SKILL.md's Constraints section):

- MUST NOT create files outside the target skill's `eval/` directory.
- MUST NOT add fenced code blocks with language identifiers inside `SKILL.md` files (this is the
  parser-execution hazard the repo's own `skill-development` rule documents — see
  `.claude/rules/skill-development.md`).
- MUST follow the `{skill-name}/SKILL.md` directory convention.
- Every generated grader script MUST output valid JSON: `{"score": 0.0-1.0, "details": "..."}`.
- `run_eval.sh` MUST be copied **verbatim** from
  [`references/run_eval.sh`](../skills/scaffold-skill-eval/references/run_eval.sh) — it
  auto-detects the skill name from the directory, no edits needed.
- Test fixtures MUST be minimal — only the files the skill actually reads.

**Procedure** (9 steps):

1. **Validate the target skill** — read `SKILL.md`, confirm it exists with a `description` field
   in frontmatter. If invalid, stop and report — don't scaffold for a broken skill.
2. **Analyze the skill's contract** — extract inputs, outputs, checks/steps, and pass/fail
   signal keywords. Write this analysis to a scratch `{skill_path}/eval/ANALYSIS.md` (deleted in
   step 9 — not checked in).
3. **Design test fixtures** — one directory per failure mode under `test-fixtures/{name}/`, named
   after what they test. Selection strategy: identify categories → cover every category with at
   least one negative fixture → prioritize checks that catch real-world mistakes over easy edge
   cases → include exactly one positive control → target 3–12 fixtures total.
4. **Write grader scripts** under `eval/graders/` — reusing the reference graders in
   `references/graders/` wherever the pattern fits (see
   [`03-grader-api.md`](03-grader-api.md)); only write a new one when nothing reusable fits.
   Add `llm_rubric` graders as a *weighted complement* (not replacement) when detection alone
   isn't enough — positive-control format completeness, recommendation quality, or genuinely
   subjective output.
5. **Write `eval.yaml`** conforming to
   [`references/skillgrade-eval-yaml-schema.md`](../references/skillgrade-eval-yaml-schema.md),
   one task per fixture, with `agent: claude`, `provider: local`, `trials: 5`, `timeout: 300`,
   `threshold: 0.8` as defaults.
6. **Copy the unified runner** — `references/run_eval.sh` → `{skill_path}/eval/run_eval.sh`,
   verbatim.
7. **Write `README.md`** — what the eval tests, a fixture table, how to run it (both modes), how
   to add fixtures.
8. **Add `.gitignore`** for `output-*.md` (transient files `/run-skill-eval` produces).
9. **Clean up and verify** — delete `ANALYSIS.md`, sanity-check each grader emits valid JSON via
   `node graders/check-*.js` (no execute permission needed — invoked via `node`, not directly),
   list created files, report fixture count.

**Reusable graders it points at** (all under `references/graders/` relative to this skill):
`check-fail-present.js`, `check-no-fails.js`, `check-warn-or-fail-present.js`,
`check-no-fail-for-pattern.js`, `check-eval-structure.js`, `check-eval-yaml-tasks.js`,
`check-fixture-count.js`, `check-stopped-early.js`. Full contract in
[`03-grader-api.md`](03-grader-api.md).

### `run-skill-eval`

[`skills/run-skill-eval/SKILL.md`](../skills/run-skill-eval/SKILL.md)

| | |
|---|---|
| **Trigger** | `/run-skill-eval <skill-path>` (default: `plugins/boss-experimental/boss-experimental/skills/claude-config-validation`), or auto-invoked on phrases like "run skill evals", "run the eval suite", "score a skill against its fixtures", "check if a skill passes its evals" |
| **`allowed-tools`** | `Read`, `Bash`, `Glob`, `Grep` |
| **Input** | Skill path via `$ARGUMENTS` |
| **Output** | `eval/output-{task-name}.md` per task, a printed per-task score table, and an overall pass rate |

**Hard constraint — main session only.** This skill requires `Bash` to run grader scripts and
**must not be delegated to a background subagent** — a background subagent auto-denies `Bash`
prompts, which silently breaks grading (the grader never runs, or runs against stale output).

**Other constraints:** run every task in `eval.yaml`, no skipping; actually execute the full
skill procedure per task (no shortcuts); write output in the exact format the skill specifies so
graders can parse it; a grader that fails to run scores `0.0` with the error noted; `llm_rubric`
scoring must be strict — 1.0 only if the output *clearly* meets the rubric.

**Procedure** (5 steps):

1. Delete stale `eval/output-*.md` from a previous run.
2. Read `eval/eval.yaml`, parse all tasks (`name`, `instruction`, `workspace`, `graders`).
3. For each task: read the target `SKILL.md`, follow its steps against the fixture at
   `workspace`'s `src` path, write full output to `eval/output-{task-name}.md`, then run every
   grader —
   - `deterministic`: run the `run` command via `Bash` from the `eval/` directory, substituting
     `output-{task-name}.md` for the literal `output.md` the command references.
   - `llm_rubric`: read the `rubric` text and the output file directly; Claude itself judges and
     returns `{"score": 1.0 | 0.0, "details": "reason"}`.

   Then compute the task's weighted score: `sum(score * weight) / sum(weight)`; the task passes
   only if that equals `1.0`.
4. Print a summary table (`Task | Score | Details`).
5. Report the overall pass rate as `{passed}/{total} tasks passed`.

### The `eval.yaml` schema

Full reference: [`references/skillgrade-eval-yaml-schema.md`](../references/skillgrade-eval-yaml-schema.md)
(source of truth: `skillgrade/src/core/config.types.ts` upstream). Summary:

**Top level**

| Field | Required | Notes |
|---|---|---|
| `version` | yes | Currently `"1"` |
| `skill` | no | Path to `SKILL.md`, auto-detected if omitted |
| `defaults` | yes | Global defaults, see below |
| `tasks` | yes | Array, at least one |

**`defaults`**

| Field | Default | Notes |
|---|---|---|
| `agent` | `gemini` | `gemini` \| `claude` \| `codex` — **this plugin's evals pin `claude`** |
| `provider` | `docker` | `docker` \| `local` — **this plugin's evals pin `local`** for keyless iteration |
| `trials` | `5` | Independent runs per task |
| `timeout` | `300` | Seconds per trial |
| `threshold` | `0.8` | Minimum pass rate for `--ci` mode |
| `grader_model` | provider default | Default LLM model for `llm_rubric` graders — set this (or a `*_MODEL` env var) to adopt a newly released model with no code change; see [Selecting the skillgrade model](04-configuration.md#selecting-the-skillgrade-model) |
| `docker` | `{base: "node:20-slim"}` | CI-only |
| `environment` | `{cpus: 2, memory_mb: 2048}` | CI-only |

**`tasks[]`**: `name`, `instruction` (inline text or `.md` path), `workspace[]` (maps fixture
files into the agent's workspace via `src`/`dest`/optional `chmod`), `graders[]`, optional
`solution`, and per-task overrides of `agent`/`provider`/`trials`/`timeout`/`grader_model`.

**`tasks[].graders[]`**: `type` (`deterministic` | `llm_rubric`), `weight`, `run` (shell command,
required for `deterministic`), `rubric` (text or file path, required for `llm_rubric`), optional
`setup` (install grader deps), `provider` (`gemini`/`anthropic`/`openai`), and `model` (per-grader
LLM override — highest-precedence model source; see
[Selecting the skillgrade model](04-configuration.md#selecting-the-skillgrade-model)).

**Scoring**: a trial's score is `sum(grader_score * weight) / sum(weight)`; a trial *passes*
only if every grader scores `1.0`. A task's pass rate is passed trials ÷ total trials; the task
passes if that rate meets `threshold`.

### Local vs. CI modes, side by side

| | Local (`/run-skill-eval`) | CI (`run_eval.sh` → `skillgrade`) |
|---|---|---|
| Agent | Claude Code itself | Real `gemini`/`claude`/`codex` agent, via `skillgrade` |
| API key | None | `ANTHROPIC_API_KEY` required |
| Container | None | Optional Docker provider (`defaults.docker`) |
| Trials | Effectively 1 pass per task (deterministic + Claude self-judging `llm_rubric`) | N trials per task per `trials`, statistical pass rate |
| Gate | Pass/fail per task, `weighted score == 1.0` | Pass rate ≥ `threshold`, `--ci` sets the process exit code |
| Where invoked | Main session only (never a background subagent) | Any CI runner with Node ≥ 20 and network access |

## Component B: config validation + knowledge architecture

### `claude-config-validation`

[`skills/claude-config-validation/SKILL.md`](../skills/claude-config-validation/SKILL.md)

| | |
|---|---|
| **Trigger** | `/claude-config-validation <path>`, or auto-invoked on phrases like "validate CLAUDE.md", "check my .claude config", "audit agent/skill/rule placement", "lint the knowledge architecture", or before merging Claude config changes |
| **`allowed-tools`** | `Read`, `Glob`, `Grep` — **no `Bash`, no `Write`/`Edit`: this skill is strictly read-only** |
| **Input** | `project_path` (defaults to cwd) |
| **Output** | A markdown report: a 23-row check table, an `## Issues` section split into `### FAIL` / `### WARN`, and `## Recommendations` |

**Procedure** (Steps 0–8, each reading the shared check catalog):

- **Step 0 — Resolve project path.** If no `project_path` was given and cwd is the monorepo
  root, do **not** silently validate root — detect the root via the configurable marker set
  (see [`04-configuration.md`](04-configuration.md#monorepo-root-markers)), then list candidate
  projects with `.claude/` directories and ask which to validate. Root is validated only when
  explicitly requested.
- **Step 1 — Locate configuration**: `CLAUDE.md`, `.claude/agents/*.md`, `.claude/skills/*/SKILL.md`,
  `.claude/commands/*.md`, `.claude/rules/*.md`. No `.claude/` at all → report and stop.
- **Step 2 — Project Structure checks (1–3)**: config exists; canonical agents are root-owned
  and not shadowed/renamed at a config-home level (see
  [`04-configuration.md`](04-configuration.md#canonical-agent-roles) for the pipeline-declared
  exception); agent frontmatter is valid and tool-permission-consistent.
- **Step 3 — Knowledge Placement checks (4–7)**: conventions live in rules, not agent bodies;
  CLAUDE.md isn't duplicated into agents; CLAUDE.md line count; rules frontmatter (`paths`
  required at root, recommended at config-home level).
- **Step 4 — Skill Quality checks (10–14, 22)**: no fenced code blocks with language identifiers
  or external deps; skill frontmatter validity; `{skill-name}/SKILL.md` directory convention;
  cross-skill duplication; skill size/separation; **Check 22 is opt-in** (see
  [`04-configuration.md`](04-configuration.md#check-22-opt-in-skill-eval-coverage)).
- **Step 5 — Discoverability & Reference checks (8–9, 15–18, 23)**: skill references resolve;
  routing-table paths resolve; routing-table completeness (with the path-scoped-rule exception);
  routing-table context discipline (Check 23 — flags multi-doc rows and rule/routing-table
  duplication); cross-file references; routing table never points at another `CLAUDE.md`;
  domain-doc self-containment (essential steps and decision predicates must be inline, not
  behind a second hop).
- **Step 6 — Compliance Placement check (19)**: a skill whose body is mostly "must/always/never"
  constraint statements (≥2:1 ratio over procedural steps) would be more effective as a rule.
- **Step 7 — Loading & Registration checks (20–21)**: no nested `.claude/` below the config-home
  root (dead config); no CLAUDE.md `@import` of `.claude/` artifacts (text-only, no harness
  registration).
- **Step 8 — Format output** as the 23-row table + Issues + Recommendations.

Full check-by-check pass/warn/fail criteria live in the standalone catalog:
[`references/config-validation-checks.md`](../references/config-validation-checks.md) — the
skill's `SKILL.md` deliberately doesn't inline them (Compliance Placement discipline applied to
itself: procedure in the skill, reference data in a doc).

### The knowledge-architecture doctrine

[`references/knowledge-architecture.md`](../references/knowledge-architecture.md) is the
long-form reference this skill validates against. Highlights relevant to using this plugin:

- **Five knowledge facilities**: CLAUDE.md (context), Rules (path-scoped), Agent (role), Skill
  (procedure), Domain Doc (recipe) — plus Hooks (enforcement) and Plugins/MCP (capability).
- **The Placement Test** — seven ordered yes/no questions; first "yes" wins.
- **Three-Occurrence Rule** — don't encode knowledge permanently until the third occurrence.
- **Monorepo Scoping** — `.claude/` lives at exactly two kinds of place: the monorepo root and a
  "config home" (an independently built/versioned/owned unit). Never deeper.
- **Standard Agent Set** — the seven canonical roles Component C implements, and the rule that a
  config home inherits them via discovery rather than redefining them.
- **Eval** section — describes the same three-part eval anatomy (fixtures, graders, `eval.yaml`)
  that Component A implements mechanically, and explicitly frames it as **opt-in**.

### `config-pr-checklist.md`

[`references/config-pr-checklist.md`](../references/config-pr-checklist.md) packages Component B
into a two-step self-service PR workflow:

1. **Step 1 (mechanical)** — run `/claude-config-validation <project_path>`; treat FAIL as
   blocking, WARN as fix-or-justify.
2. **Step 2 (judgment)** — ask a Claude session to review the diff against the architecture doc
   directly (things a checklist can't enumerate: is this skill *worth having*, is the
   description good enough to auto-route, does it duplicate something conceptually).
3. **Step 3** — paste both results into the PR description under a `## Claude KA Compliance`
   heading.

### `rules/claude-config-authoring.md` (template)

[`rules/claude-config-authoring.md`](../rules/claude-config-authoring.md) is a condensed
anti-pattern list (conventions in agent prompts, CLAUDE.md duplication/oversizing, non-writing
agents with write tools, dangling skill references, code blocks in skills, external deps in
skills, platform-variant agents, flat skill files, missing frontmatter, cross-file duplication,
oversized skills, unreferenced skills, commands instead of skills, missing evals when opted in),
each traceable back to a principle in the architecture doc. Its frontmatter declares
`paths: [".claude/**/*.md", "**/CLAUDE.md", "**/.claude/**/*.md"]` — but as the plugin README
states, **plugins have no auto-loading `rules/` mechanism**. This file only activates for real
once copied or symlinked into a project's own `.claude/rules/`.

## Component C: dev-workflow agents

All eight agents are genericized: no hardcoded project paths, package names, or languages. Each
expects to read the invoking project's own `CLAUDE.md` for build/test/lint commands and
conventions. All use `permissionMode: bypassPermissions` except `config-reviewer`
(`permissionMode: read-only`) — per the knowledge-architecture doctrine, the **tool list is the
real permission boundary**, since these agents are designed for orchestrated (subagent)
execution where interactive approval prompts don't work. Each agent frontmatter also declares a
`capabilities: [...]` array — a short tag list summarizing its role (used for discovery/routing
purposes, not enforced by the harness).

| Agent | Capabilities | Tools | permissionMode | model | maxTurns | Output |
|---|---|---|---|---|---|---|
| [`architect`](../agents/architect.md) | `planning`, `technical-design` | Read, Bash, Glob, Grep, Write | bypassPermissions | opus | 50 | Technical Requirements Document (TRD) |
| [`coder`](../agents/coder.md) | `implementation`, `coding` | Read, Write, Edit, Bash, Glob, Grep | bypassPermissions | opus | 50 | Code changes |
| [`test-writer`](../agents/test-writer.md) | `test-authoring` | Read, Write, Edit, Bash, Glob, Grep | bypassPermissions | opus | 40 | Test files |
| [`tester`](../agents/tester.md) | `test-execution` | Read, Bash, Glob, Grep | bypassPermissions | opus | 30 | Structured pass/fail report |
| [`reviewer`](../agents/reviewer.md) | `code-review` | Read, Bash, Glob, Grep | bypassPermissions | opus | 25 | Verdict + structured review |
| [`pr-submission`](../agents/pr-submission.md) | `git`, `pull-request` | Read, Bash, Glob, Grep | bypassPermissions | opus | 20 | Commit, branch, PR |
| [`learner`](../agents/learner.md) | `self-improvement`, `documentation` | Read, Write, Edit, Bash, Glob, Grep | bypassPermissions | opus | 40 | Updated CLAUDE.md/agents/skills |
| [`config-reviewer`](../agents/config-reviewer.md) | `config-review`, `read-only-audit` | Read, Glob, Grep, Bash, **Agent** | **read-only** | (unset) | (unset) | Architectural review report |

### `architect` — TRD-only, no production code

Produces a **Technical Requirements Document** through five phases (Discovery → Design →
Specification → Risk & Open Questions → Write the Document), following a fixed output template
(Overview, Current State, Technical Design, Implementation Plan, File Change Summary, Testing
Strategy, Risks & Open Questions, Success Criteria).

**Behavioral contract:** "You do NOT write production code — you write the document that makes
production code unambiguous," and explicitly: *"The Write tool is ONLY for the TRD design
document — never use it to author production code."* Red flags include designing without having
read source files, proposing patterns with no codebase precedent, more than 5 implementation
phases, and — explicitly — "Writing implementation code instead of specifications."

### `coder` — implementation with a verification protocol

Reads CLAUDE.md, understands/plans/implements/verifies in that order. Verification protocol:
run the full build (no partial builds, no "it compiled earlier"), read full output, check exit
codes, never trust cached results. Red flags: editing generated files, copying code without
understanding it, touching more than 3 files for a "simple" fix, defensive code for impossible
scenarios, swallowing exceptions.

### `test-writer` — TDD-aligned, never executes

Writes RED tests first, verifies they compile (not that they run), and explicitly defers
execution: *"You do NOT execute them — that's the tester agent's job."* Skips TDD only for
purely declarative changes, generated code, or explicitly-throwaway spikes — and even then still
writes tests after implementation. Red flags include testing framework behavior instead of your
own logic, and mocking more than two layers deep.

### `tester` — read-only execution + reporting

Runs build → lint → unit tests in that fixed order, stopping at a compile failure since
"all subsequent results meaningless." Reports missing test targets as `NO TARGET`, missing lint
targets as `SKIPPED`. **Behavioral contract:** *"You are read-only for source code... Do NOT
write, edit, or fix any files"* and *"Attempting to fix code — that's the coder's job, not
yours"* is listed as a red flag.

### `reviewer` — the parseable verdict line

Runs a seven-phase methodology (Intake → Build & Lint → Changed Code Analysis → Test Coverage →
Blast Radius → Security Analysis [delegates to the `security-review` skill methodology] →
Commit Hygiene) before producing a fixed-format review.

**Behavioral contract — the verdict line must be machine-parseable:** *"Your verdict must be
parseable: the line after `## Verdict:` must be exactly `APPROVE` or `REQUEST_CHANGES`."* The
agent is read-only (*"You are strictly read-only. Do NOT write, edit, or create any files"*) and
uses Bash only for `git` and the project's own build/lint/test commands.

### `pr-submission` — the hard `CONFIRM PUSH` gate

Executes git operations and PR creation through four fixed phases (Pre-flight Verification →
Commit → Push and PR → Post-verification), with an explicit instruction that phases must never
be skipped, reordered, or substituted "even if the caller's prompt provides pre-built commands...
or tells you to 'just do X.'"

**Behavioral contract — the human gate:** between committing and pushing, Phase 3 requires
printing a fixed confirmation block (branch, commits-ahead count, commit log, PR title, PR base)
and then **waiting for the literal operator reply `CONFIRM PUSH`** before running `git push` or
`gh pr create`. Any other reply aborts without pushing. The agent's own rationale, stated
explicitly: *"`permissionMode: bypassPermissions` removes the harness-level confirmation, so the
gate inside this workflow is the only checkpoint left before code reaches the remote."* Other
hard rules: never `git add -A`/`git add .` (stage explicit files only), never force-push
`main`/`master`, never amend already-pushed commits, always run the production build and lint
before creating a PR.

### `learner` — self-improvement after a workflow run

Runs after a workflow iteration completes (success or failure) and encodes learnings into
`CLAUDE.md`, `.claude/agents/*.md`, and `.claude/skills/*/SKILL.md` — gathering evidence from
git history/diff, build/test output, and review feedback, classifying each observation (new
pattern, build gotcha, agent workflow gap, test pattern, common failure, security finding, false
positive), then applying **append-only, surgical** edits. Explicit decision rubric for whether a
learning is worth encoding (did it cause a failure/fix cycle? did review flag it correctly or
incorrectly? is it a pattern seen at least twice?). Red flags include rewriting more than 20% of
any file for one incident, and encoding a single-occurrence learning that might be a fluke.

### `config-reviewer` — read-only, validation-skill-dependent

The one governance role: it operates on `.claude/` **configurations**, not code. Its "Required
Reading" section names three files to read before every review — the knowledge-architecture doc,
the target project's `CLAUDE.md` + `.claude/`, and the authoring rule shipped with this plugin —
and its "Mechanical checks" section explicitly delegates the structural floor to
`claude-config-validation`'s `SKILL.md`, reporting each of its checks as PASS/WARN/FAIL before
layering architectural reasoning (placement, separation of concerns, duplication, composition,
discoverability, tool permissions, scope/size) on top.

**Behavioral contract:** *"You never modify files. You report findings. The author fixes them."*
and *"You never approve or merge. You evaluate. Approval is a human decision."* Its `tools` list
includes `Agent` (it may spawn subagents, e.g. to run the validation skill), but `permissionMode:
read-only` is a hard mode — distinct from the `bypassPermissions` every other agent in this
plugin uses.

> **Overlap note** (from the plugin README): these eight agents overlap in role with
> `agent-harness`'s existing `builder`/`validator` team agents. This canonical set is
> experimental and optional — nothing in Components A or B requires it.
