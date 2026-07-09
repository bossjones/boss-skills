# boss-experimental — Technical Reference

> **Experimental.** This plugin is a staging ground for Claude Code tooling under active
> testing. Nothing in `boss-skills` depends on it. See the plugin's own
> [`README.md`](../README.md) for the user-facing overview; this `docs/` set is the deeper
> technical reference — architecture, component contracts, and extension points.

## Executive summary

`boss-experimental` bundles three independent subsystems under one plugin:

| Subsystem | What it does | Entry points |
|---|---|---|
| **A. Skillgrade skill-eval system** | Behavioral, trial-based testing for *any* Claude Code skill: an agent runs the skill against a fixture, deterministic/LLM graders score the output. | `/scaffold-skill-eval`, `/run-skill-eval` |
| **B. Config validation + knowledge architecture** | A read-only auditor for a project's `.claude/` configuration, backed by a documented placement doctrine (the "knowledge architecture"). | `/claude-config-validation`, `references/knowledge-architecture.md` |
| **C. Dev-workflow agents** | Eight genericized subagents (architect → coder → test-writer → tester → reviewer → pr-submission, plus learner and config-reviewer) modeling an orchestrated implementation pipeline. | `agents/*.md` |

They are **loosely coupled, not layered**: Component B dogfoods Component A (its own `eval/`
is the worked reference example); the `config-reviewer` agent in Component C treats Component
B's validation skill as its mechanical floor; Components A and C otherwise have no dependency
on each other. See [`skillgrade-vs-plugin-eval.md`](../references/skillgrade-vs-plugin-eval.md)
for how Component A relates to (and stays independent of) this repo's existing `plugin-eval`
stack (`/skill-evals`, `make eval-skill`) — **boss-experimental does not modify, replace, or
depend on that stack.**

## Document map

| Doc | Covers |
|---|---|
| [`01-architecture.md`](01-architecture.md) | The three subsystems in depth, how they relate, and the eval data-flow diagram |
| [`02-components.md`](02-components.md) | Every skill and agent: inputs, outputs, contracts, behavioral guarantees |
| [`03-grader-api.md`](03-grader-api.md) | The Node grader contract, the shipped reusable graders, how to write a new one |
| [`04-configuration.md`](04-configuration.md) | Config-driven canonical agent set, monorepo-root markers, opt-in Check 22, pipeline extension point |
| [`05-environment.md`](05-environment.md) | Node/npm requirements, `ANTHROPIC_API_KEY` scope, the `skillgrade init` AI-mode 404 |

## Layout reference

```text
boss-experimental/
├── .claude-plugin/plugin.json
├── skills/
│   ├── run-skill-eval/SKILL.md
│   ├── scaffold-skill-eval/         SKILL.md + references/{graders/,run_eval.sh}
│   └── claude-config-validation/    SKILL.md + eval/ (eval.yaml, graders, 13 fixtures)
├── agents/                          8 dev-workflow agents
├── references/                      knowledge-architecture, checks catalog, PR checklist,
│                                     skillgrade schema, skillgrade-vs-plugin-eval, init-demo
├── rules/claude-config-authoring.md (template — copy into your .claude/rules/)
└── docs/                            this technical reference
```
