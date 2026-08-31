# boss-experimental

> **Experimental. Not ready for prime time.** A staging ground for Claude Code tooling that's
> still being tested. Things here may change, move, or be removed. Nothing in this plugin is a
> dependency of the rest of `boss-skills`.

Its first tenant is a **genericized port** of skill-eval + Claude-config tooling originally
built in a large internal monorepo — stripped of all project-specific assumptions so it works
in any repo.

## What's inside

Three independent subsystems:

### A. Skillgrade skill-eval system

Run evals against a skill two ways, sharing one `eval.yaml`:

- **Locally** — `/run-skill-eval <skill-path>`: Claude Code itself acts as the agent, runs the
  skill against each task's fixture, and scores the output with the skill's graders. **No API
  key, no Docker.** Must run in the **main session** (a background subagent auto-denies `Bash`
  and silently breaks graders).
- **CI / headless** — `run_eval.sh` shells out to the [`skillgrade`](https://www.npmjs.com/package/skillgrade)
  npm CLI for N trials against a pass-rate threshold (needs `ANTHROPIC_API_KEY`).

Skills:

- **`/scaffold-skill-eval <skill-path>`** — generates a complete `eval/` (fixtures + Node
  graders + `eval.yaml` + `run_eval.sh`) from a target `SKILL.md`.
- **`/run-skill-eval <skill-path>`** — executes a skill's `eval/` locally, prints a per-task
  score table.

Reusable, zero-dependency Node graders ship under
`skills/scaffold-skill-eval/references/graders/` (each prints one JSON line
`{"score","details"}`, handles missing files, always exits 0). The `eval.yaml` schema is
documented in [`references/skillgrade-eval-yaml-schema.md`](references/skillgrade-eval-yaml-schema.md).

### B. Config validation + knowledge architecture

- **`/claude-config-validation <path>`** — a read-only skill that runs a catalog of checks over
  a project's `.claude/` config (agent frontmatter, knowledge placement, skill quality,
  discoverability, loading/registration). It ships its own worked `eval/` (13 fixtures) as the
  reference example of "a well-formed skill with a proper eval."
- **References** (portable docs the skill + agents point at):
  [`knowledge-architecture.md`](references/knowledge-architecture.md) (the placement doctrine),
  [`config-validation-checks.md`](references/config-validation-checks.md) (the check catalog),
  [`config-pr-checklist.md`](references/config-pr-checklist.md) (the two-step mechanical +
  judgment PR workflow).
- **`rules/claude-config-authoring.md`** — an auto-loading anti-pattern guardrail. **See the
  caveat below** — plugins have no auto-loading `rules/` mechanism, so this is a *template*.

Opinionated constants are **config-driven, not hardcoded**: the canonical agent-role set and
the monorepo-root marker set are documented defaults you can override; the "every skill needs
an `eval/`" rule and the "pipeline-declared custom agent" mechanism are opt-in extension points.

### C. Dev-workflow agents

Eight genericized subagents: `architect` (TRD/design only), `coder`, `test-writer`, `tester`,
`reviewer` (emits `## Verdict: APPROVE / REQUEST_CHANGES`), `pr-submission` (hard `CONFIRM PUSH`
human gate), `learner` (self-improvement), and the read-only `config-reviewer` (which runs the
Component-B validation skill as its mechanical floor).

> **Overlap note.** These overlap with `agent-harness`'s existing team agents (`builder`,
> `validator`). Treat this canonical set as **experimental/optional** — it is not a repo
> mandate, and you don't need to adopt it to use Components A or B.

## Requirements

- **Node ≥ 20** — the Node graders shell out to `node`; skillgrade runs on Node.
- **`skillgrade`** only for the CI path — `run_eval.sh` invokes the `bossjones/skillgrade` fork
  (which carries the model-override + `init` 404 fix this plugin relies on) via
  `npx --yes github:bossjones/skillgrade#fix/anthropic-retired-model-404-bossjones`, or a
  `skillgrade` on `PATH`. The local `/run-skill-eval` path needs neither skillgrade nor an API key.
- Not a Python dependency — do **not** add `skillgrade` to `pyproject.toml`/`uv`.

## Usage examples

Generate and run an eval for a skill locally (main session):

    /scaffold-skill-eval plugins/boss-experimental/boss-experimental/skills/claude-config-validation
    /run-skill-eval plugins/boss-experimental/boss-experimental/skills/claude-config-validation

Run the CI path with real skillgrade trials (needs a key in your environment):

    export ANTHROPIC_API_KEY=...      # or: source .env && ANTHROPIC_API_KEY="${BOSS_ANTHROPIC_API_KEY}"
    cd plugins/boss-experimental/boss-experimental/skills/claude-config-validation/eval
    ./run_eval.sh --smoke --provider=local

Validate a project's Claude config:

    /claude-config-validation path/to/some/project

## Caveat: the authoring rule does not auto-load

Claude Code plugins auto-discover skills, agents, hooks, MCP/LSP servers, and monitors — but
there is **no plugin-level `rules/` component**. Path-scoped rules only auto-load from a
*project's* `.claude/rules/*.md`. So `rules/claude-config-authoring.md` here is a **template**:
to get the auto-loading "coach me while I edit `.claude` config" behavior in your own repo,
copy or symlink it into your project's `.claude/rules/`:

    ln -s "$PWD/plugins/boss-experimental/boss-experimental/rules/claude-config-authoring.md" \
      .claude/rules/claude-config-authoring.md

## Positioning: self-contained & parallel

This plugin's skillgrade evals are **independent of** this repo's existing `plugin-eval` stack
(`/skill-evals`, `make eval-skill`, `scripts/plugin_eval/`) — nothing here modifies it. The two
approaches answer complementary questions and can be compared side-by-side. See
[`references/skillgrade-vs-plugin-eval.md`](references/skillgrade-vs-plugin-eval.md).

## Layout

    boss-experimental/
    ├── .claude-plugin/plugin.json
    ├── skills/
    │   ├── run-skill-eval/SKILL.md
    │   ├── scaffold-skill-eval/         SKILL.md + references/{graders/,run_eval.sh}
    │   └── claude-config-validation/    SKILL.md + eval/ (eval.yaml, graders, 13 fixtures)
    ├── agents/                          8 dev-workflow agents
    ├── references/                      knowledge-architecture, checks catalog, PR checklist,
    │                                    skillgrade schema, skillgrade-vs-plugin-eval
    ├── rules/claude-config-authoring.md (template — copy into your .claude/rules/)
    └── docs/                            generated coding docs + tutorials
