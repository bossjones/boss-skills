# PluginEval reference

Canonical doc: <https://github.com/wshobson/agents/blob/main/docs/plugin-eval.md>

PluginEval is a three-layer quality framework for Claude Code plugins and skills. It
combines deterministic static analysis, LLM-based semantic judging, and Monte Carlo
simulation into a calibrated composite score with a confidence label and a quality badge.

This repo does **not** vendor it — `scripts/eval-skills.py` and the `make eval-*` targets
pull `plugin-eval` on demand via `uvx` from the `wshobson/agents` git subdirectory.

## Commands (as wired in this repo)

| Goal | This repo | Raw plugin-eval |
|------|-----------|-----------------|
| Init corpus | `./scripts/eval-skills.py --command init plugins/ --corpus-dir ~/.plugineval/corpus` | `plugin-eval init plugins/ --corpus-dir …` |
| Score one skill | `make eval-skill SKILL=<path>` | `plugin-eval score <path> --depth standard --output markdown` |
| Certify one skill | `make eval-certify SKILL=<path>` | `plugin-eval certify <path> --output markdown` |
| Score all / gate | `make eval` / `make eval-ci` | — |
| LLM-judge / Monte Carlo | `make eval-llm-judge` / `make eval-monte-carlo` | — |
| Compare two skills | `./scripts/eval-skills.py --command compare <a> <b>` | `plugin-eval compare <a> <b>` |

`certify` always runs at `deep` depth (all three layers) and emits a badge.

## Depths

| Depth | Layers | Confidence | Time | Cost |
|-------|--------|-----------|------|------|
| `quick` | static only | Estimated | <2s | free |
| `standard` | static + judge | Assessed | ~30s | 4 LLM calls |
| `deep` | static + judge + Monte Carlo (50) | Certified | ~3 min | ~54 LLM calls |
| `thorough` | static + judge + Monte Carlo (100) | Certified+ | ~6 min | ~104 LLM calls |

The repo's `--layer` alias maps `static→quick`, `llm-judge→standard`, `monte-carlo→deep`,
`all→thorough`. `make eval-skill` and `scripts/eval-skills.py` also accept `--depth`
directly (it wins over `--layer` when both are set).

## Flags (`score` / `certify` / `compare`)

The full upstream `plugin-eval score` surface — `certify` and `compare` accept the same LLM
knobs (`--concurrency`, `--auth`), confirmed via `plugin-eval … --help`:

| Flag | Values (default) | Notes |
|------|------------------|-------|
| `--depth` | `quick`\|`standard`\|`deep`\|`thorough` (`standard`) | Layer selection (see table above). `certify` is always `deep` and ignores it. |
| `--concurrency` | int `1`–`20` (`4`) | Max parallel LLM calls within one score. |
| `--auth` | `max`\|`api-key` (`max`) | `max` = Claude Code Max via `claude-agent-sdk`; `api-key` = `ANTHROPIC_API_KEY` via the `anthropic` SDK. |
| `--output` | `json`\|`markdown`\|`html` (`markdown`) | This repo uses `json` for the score table, `markdown` for reports. |
| `--verbose` / `-v` | flag | Verbose plugin-eval output. |
| `--threshold` | float | Exit code 1 if the composite is below it. |

**When the judge silently no-ops:** a report whose Model Usage reads "No model usage
(static-only evaluation)" with a flat `0.500` judge layer means the `--auth max` backend
wasn't reachable (no Claude Code Max / `claude-agent-sdk` session). Re-run with
`--auth api-key` and `ANTHROPIC_API_KEY` set so the judge dimensions actually score.

## The three layers

1. **Static analysis** (<2s, free, deterministic) — seven structural sub-checks against the
   parsed `SKILL.md`: `frontmatter_quality` (32%), `orchestration_wiring` (23%),
   `progressive_disclosure` (14%), `structural_completeness` (10%), `token_efficiency` (9%),
   `ecosystem_coherence` (6%), `harness_portability` (6%). Anti-patterns apply a
   multiplicative penalty.
2. **LLM judge** (~30s, 4 calls) — `triggering_accuracy` (Haiku, F1 over 10 synthetic
   prompts), `orchestration_fitness`, `output_quality`, `scope_calibration` (Sonnet, anchored rubrics).
3. **Monte Carlo** (~2–5 min, 50–100 calls) — activation rate (Wilson CI), output
   consistency (bootstrap CI), failure rate (Clopper-Pearson), token efficiency.

## Badges

Bronze → Silver → Gold → Platinum, awarded at `certify`. A "No Badge" result means the
composite score did not clear the Bronze threshold — common for skills whose logic lives in
scripts rather than the SKILL.md body (the static layer reads the SKILL.md).

## Reading a report

Each report starts with `# PluginEval Report` and contains: Overall Score (score /
confidence / badge), Layer Breakdown (per-layer score + anti-pattern count), Dimension
scores with letter grades, an Anti-Patterns section, and model usage. When triaging a low
score, sort dimensions ascending and start with the lowest — see `fix-playbook.md`.
