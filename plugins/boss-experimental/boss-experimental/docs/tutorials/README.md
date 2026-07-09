# boss-experimental tutorials

Hands-on, copy-pasteable walkthroughs for the `boss-experimental` plugin. Where the
[plugin README](../../README.md) describes *what's inside*, these tutorials show *how to actually
use it*, end to end, on a real codebase.

> **Reminder:** this plugin is experimental. Nothing here is a dependency of the rest of
> `boss-skills`, and the skillgrade AI-`init` path currently 404s (see
> [Tutorial 4](04-ci-with-skillgrade.md#the-ai-init-404-and-why-we-hand-author-evalyaml)) — the
> committed `eval.yaml` files are the source of truth, not generated output.

## Prerequisites (all tutorials)

- Claude Code, with this repo's marketplace added (Tutorial 1 covers this from scratch).
- **Node ≥ 20** on `PATH` — the eval graders shell out to `node`, and `skillgrade` runs on Node.
  Check with:

  ```bash
  node --version
  ```

- No API key and no Docker are needed for local work (Tutorials 2, 3, 5, 6). An
  `ANTHROPIC_API_KEY` is only needed for the CI/headless `skillgrade` path (Tutorial 4).

## Tutorials

| # | Tutorial | What you'll do |
|---|----------|-----------------|
| 1 | [Install & enable the plugin](01-install-and-enable.md) | Add the `boss-skills` marketplace, install `boss-experimental`, confirm its skills and agents appear |
| 2 | [Evaluate an existing skill locally](02-run-skill-eval-locally.md) | Run `/run-skill-eval` against `claude-config-validation` in the main session, read the score table |
| 3 | [Scaffold an eval for your own skill](03-scaffold-skill-eval.md) | Run `/scaffold-skill-eval` on a sample skill, inspect the generated `eval/`, edit a task, run it |
| 4 | [Run evals in CI with skillgrade](04-ci-with-skillgrade.md) | Install `skillgrade`, run `--smoke`/`--reliable`/`--regression` locally, wire up GitHub Actions |
| 5 | [Validate a project's Claude config](05-claude-config-validation.md) | Run `/claude-config-validation` against a sample project, interpret PASS/WARN/FAIL |
| 6 | [Using the dev-workflow agents](06-dev-workflow-agents.md) | Invoke architect/coder/reviewer/etc., and the `pr-submission` `CONFIRM PUSH` gate |

## The sample project used throughout

Tutorials 3 and 5 reference a small, self-contained sample project so the commands are
copy-pasteable against something concrete:

```text
apps/example-app/
├── CLAUDE.md
└── .claude/
    └── skills/
        └── my-skill/
            └── SKILL.md
```

You don't need this project to exist in advance — each tutorial that uses it tells you exactly
what to create.

## Where things actually live

| Thing | Path |
|-------|------|
| The three skills | `plugins/boss-experimental/boss-experimental/skills/{run-skill-eval,scaffold-skill-eval,claude-config-validation}/SKILL.md` |
| The eight dev-workflow agents | `plugins/boss-experimental/boss-experimental/agents/*.md` |
| eval.yaml schema reference | `plugins/boss-experimental/boss-experimental/references/skillgrade-eval-yaml-schema.md` |
| skillgrade vs. plugin-eval | `plugins/boss-experimental/boss-experimental/references/skillgrade-vs-plugin-eval.md` |
| Worked reference eval (13 fixtures) | `plugins/boss-experimental/boss-experimental/skills/claude-config-validation/eval/` |
