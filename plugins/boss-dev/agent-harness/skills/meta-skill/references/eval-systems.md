# Evaluation Systems (full menu)

This repo has **three** ways to evaluate a skill. The eval step in `SKILL.md` interviews the
user for *which* system and *how deep* — it never assumes. This file is the full reference for
that menu. Match depth to maturity: **first draft → fastest/cheapest**; **improvement loop →
deeper**.

## Quick chooser

| Situation | Reach for | Depth |
| --- | --- | --- |
| First draft, "does it trigger / is it structurally sane?" | PluginEval or skillgrade | PluginEval `quick`, or skillgrade `smoke` |
| Tuning a description so the skill activates reliably | skill-creator loop | benchmark + description optimizer |
| Improvement loop before merge | PluginEval | `standard` → `deep` |
| Regression gate / CI confidence | skillgrade | `reliable` → `regression` |
| Certification with a badge | PluginEval | `certify` (always deep) |

## 1. skill-creator loop (conversational benchmark)

A with-skill-vs-baseline benchmark plus a description/trigger optimizer. Best when the problem
is **activation** — the skill exists but doesn't fire, or fires when it shouldn't. Invoke the
`skill-creator` skill and ask for its benchmark / Description Optimization loop. It writes scratch
output to a sibling `<skill-name>-workspace/` directory (git-ignored; recognized by
`scripts/verify-structure.py`).

## 2. PluginEval (wshobson, vendored)

Static + LLM-judge + Monte-Carlo scoring. Reports go to `docs/evals/<plugin>/<skill>.md`
(repo-internal skills → `docs/evals/<skill>.md`) — **not** inside the skill directory.

Invocations (all routed through `scripts/eval-skills.py`, which builds `plugin-eval` on demand
via `uvx`):

```bash
# One skill, standard depth, Markdown report
make eval-skill SKILL=<skill-dir> DEPTH=standard

# Full certification (deep + badge)
make eval-certify SKILL=<skill-dir>

# The repo quality gate (all skills, static layer, fails under the threshold)
make eval-ci
```

Or invoke the `skill-evals` skill (`/skill-evals [--review | --fix | --certify]
[--depth quick|standard|deep|thorough]`), which fans out one subagent per skill and writes the
reports.

### Depths

| Depth | Layers | Confidence | Time | Cost |
| --- | --- | --- | --- | --- |
| `quick` | static only | Estimated | <2s | free (no LLM) |
| `standard` | static + judge | Assessed | ~30s | ~4 LLM calls |
| `deep` | static + judge + Monte-Carlo (50) | Certified | ~3 min | ~54 LLM calls |
| `thorough` | static + judge + Monte-Carlo (100) | Certified+ | ~6 min | ~104 LLM calls |

`quick`/static is **deterministic** and needs no auth — ideal for a tight first-draft loop.
`standard`+ need Claude Code Max (`--auth max`, default) or `--auth api-key`
(`BOSS_SKILL_ANTHROPIC_API_KEY`). The quality gate (`make eval-ci`) runs the static layer only.

## 3. skillgrade suites (fixture-based)

Versioned test suites that live at `<skill-dir>/eval/` (this directory **is** committed skill
content — distinct from the generated reports above). Best for **regression** confidence and CI.

```bash
# Generate the eval/ suite (fixtures, graders, eval.yaml, runner)
#   → invoke the scaffold-skill-eval skill

# Run the suite locally (one trial per task — a smoke signal, not a CI guarantee)
#   → invoke the run-skill-eval skill, or:
<skill-dir>/eval/run_eval.sh
```

Presets escalate the same suite: **smoke** (fast sanity) → **reliable** (more trials) →
**regression** (full gate; CI runs `trials: 5`). `claude-config-validation` Check #22 asserts the
`eval/` directory exists at `<skill-dir>/eval/`.

## Maturity → depth, concretely

- **First draft**: PluginEval `quick` (deterministic, free) or skillgrade `smoke`.
- **Improvement loop**: PluginEval `standard`/`deep`, or skillgrade `reliable`.
- **Pre-merge / regression gate**: PluginEval `deep`/`thorough` or `certify`; skillgrade
  `regression`.
