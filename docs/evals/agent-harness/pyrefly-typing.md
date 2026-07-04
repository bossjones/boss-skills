# PluginEval Report

**Path:** `/Users/bossjones/dev/bossjones/boss-skills/plugins/boss-dev/agent-harness/skills/pyrefly-typing`
**Timestamp:** 2026-07-04T03:40:05.600229+00:00
**Depth:** deep

## Overall Score

| Metric | Value |
|--------|-------|
| Score | **50.6/100** |
| Confidence | Certified |
| Badge | No Badge |

## Layer Breakdown

| Layer | Score | Anti-Patterns |
|-------|-------|---------------|
| static | 0.782 | 0 |
| judge | 0.643 | 0 |
| monte_carlo | 0.600 | 0 |

## Dimension Scores

| Dimension | Weight | Score | Grade |
|-----------|--------|-------|-------|
| Triggering Accuracy | 25% | 0.334 | F |
| Orchestration Fitness | 20% | 0.344 | F |
| Output Quality | 15% | 0.248 | F |
| Scope Calibration | 12% | 0.750 | C |
| Progressive Disclosure | 10% | 0.650 | D |
| Token Efficiency | 6% | 0.987 | A+ |
| Robustness | 5% | 1.000 | A+ |
| Structural Completeness | 3% | 0.850 | B |
| Code Template Quality | 2% | 0.000 | — |
| Ecosystem Coherence | 2% | 0.830 | B |

## Anti-Patterns Detected

_No anti-patterns detected._

## Model Usage

| Model | Tokens |
|-------|--------|
| claude-sonnet-4-6 | 4,653 |
| claude-haiku-4-5-20251001 | 849 |

## Note on this report

This is the first `deep`-depth (Monte Carlo-included) report generated for this skill.
The Monte Carlo layer (`plugin_eval/layers/monte_carlo.py`) simulates invocation with
`allowed_tools=[]` — no Bash/Read/Write available to the simulated agent — against
synthetic natural-language prompts, and does not special-case
`disable-model-invocation: true` (slash-command-only) skills the way the static layer
does (see `static.py`'s `_skill_uses_description_trigger`). `pyrefly-typing`'s workflow
is inherently tool-execution-driven (`uv run .../pyrefly_setup.py detect`, `git
rev-parse`, `uv add`), so a tool-less simulation cannot exercise it, which likely
explains why Triggering Accuracy / Orchestration Fitness / Output Quality score much
lower here than in the `standard`-depth run for the same commit (67.3/100 — see
`docs/evals/agent-harness/pyrefly-typing.md`'s prior revision / git history). Robustness
and Code Template Quality are, however, real, non-placeholder numbers for the first
time at this depth. Treat the 50.6 composite as a known-noisy measurement for
tool-execution-driven, command-only skills rather than a content regression — the
`standard`-depth score (with the judge fix applied) is the more representative number
for this skill's actual quality.
