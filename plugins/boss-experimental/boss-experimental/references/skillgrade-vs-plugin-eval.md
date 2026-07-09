# skillgrade vs. plugin-eval — how this plugin relates to the repo's existing eval stack

`boss-experimental` ships a **skillgrade**-based skill-eval system. This repo (`boss-skills`)
already has a **different** eval stack. This document explains the difference and states the
boundary: **boss-experimental does not modify, replace, or depend on the existing stack.**

## The two systems at a glance

| | **skillgrade** (this plugin, experimental) | **plugin-eval** (existing repo stack) |
|---|---|---|
| Origin | `skillgrade` npm CLI (mgechev), ported from the `hz` repo | wshobson `plugin-eval`, vendored at `scripts/plugin_eval/` |
| Core question | "When an agent actually runs this skill against a task, does the outcome pass?" | "How good is this SKILL.md?" (structure + LLM-judge scoring) |
| Unit of evaluation | A **task**: an instruction + a workspace fixture the agent operates on | A **skill directory** (primarily its `SKILL.md`) |
| How it scores | An **agent runs the skill**, produces output; **Node graders** (`{"score","details"}`) + optional `llm_rubric` grade the transcript; N trials → pass rate vs. threshold | A composite score across weighted dimensions (triggering, orchestration, output quality, progressive disclosure, …); static layer + optional LLM judge |
| Config artifact | `eval.yaml` (per skill, in `eval/`) | none per-skill; central config + `EVALS.md` reports |
| Local run | `/run-skill-eval <skill>` — **Claude Code is the agent**, no API key | `make eval-skill SKILL=… DEPTH=…` / `/skill-evals` |
| CI run | `run_eval.sh` → `skillgrade --smoke/--reliable/--regression` (needs `ANTHROPIC_API_KEY`) | `make eval` (LLM judge needs a key) |
| Where evals live | inside each skill: `skills/<name>/eval/` | not inside plugins; driven centrally |
| Toolchain | **Node** (`npx skillgrade`) | **Python** (`uvx` / vendored package) |

## Why both exist

They answer complementary questions. plugin-eval asks *"is this skill well-authored?"* —
a static/judge quality score you can run over every skill cheaply. skillgrade asks *"does
the skill actually work when an agent follows it end-to-end?"* — a behavioral, trial-based
signal with deterministic graders over real output. A skill can score well on plugin-eval
and still fail a skillgrade task (e.g. a step that reads fine but produces the wrong artifact),
and vice-versa.

`boss-experimental` is the place to try skillgrade **without disrupting** the established
plugin-eval workflow, so the two can be compared side-by-side on real skills.

## The boundary (what this plugin does NOT touch)

- Does **not** modify `.claude/skills/skill-evals/`, `scripts/plugin_eval/`, `Makefile`,
  `make eval` / `make eval-skill`, or any `EVALS.md`.
- Does **not** add `skillgrade` to `pyproject.toml` / `uv` — it is a Node CLI, invoked via
  `npx skillgrade` (or a global `npm i -g skillgrade`).
- Its skills carry their own `eval/` directories; this is local to the plugin and does not
  change the repo convention that other plugins are evaluated centrally.

## When to reach for which

- **Authoring / merging a skill in this repo** → keep using `plugin-eval` (`make eval-skill`,
  `/skill-evals`); it is the repo's gate and the `version-bump-reviewer` skill consumes its
  score deltas.
- **Checking that a skill's procedure actually produces the right result** → try skillgrade:
  `/scaffold-skill-eval <skill>` to generate an `eval/`, then `/run-skill-eval <skill>` locally
  or `run_eval.sh --smoke` in CI.
