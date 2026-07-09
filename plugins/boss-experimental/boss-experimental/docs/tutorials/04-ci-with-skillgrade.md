# Tutorial 4: Run evals in CI with skillgrade

**Time:** ~15 minutes locally, plus one CI run
**You'll learn:** how `run_eval.sh` delegates to the `skillgrade` npm CLI, the difference between
`--smoke`/`--reliable`/`--regression`, the `--ci`/`--threshold` gate, and how to wire it into
GitHub Actions.

## What you'll build

A working CI job that runs the `claude-config-validation` eval suite (or your own skill's eval
from [Tutorial 3](03-scaffold-skill-eval.md)) against real Claude trials and fails the build if the
pass rate drops below a threshold.

## How this differs from `/run-skill-eval`

[Tutorial 2](02-run-skill-eval-locally.md) used Claude Code itself as the agent — no key, no
Docker. This tutorial uses the same `eval.yaml`, but a different runner: the `skillgrade` npm CLI
spins up an actual agent (here, `claude`, per `defaults.agent` in `eval.yaml`) for **N trials per
task** and computes a pass rate against `defaults.threshold`. This is the CI-grade signal; Tutorial
2 is the fast local-iteration signal. Both read the exact same `eval.yaml` — see
[`skillgrade-vs-plugin-eval.md`](../../references/skillgrade-vs-plugin-eval.md) for how this
compares to the repo's separate `plugin-eval` stack.

## Prerequisite

- Node ≥ 20 on `PATH`.
- An `ANTHROPIC_API_KEY`. skillgrade's `agent: claude` / `provider: local` combination (the
  default this plugin's `eval.yaml` files pin) runs the agent directly on your machine with that
  key — no Docker.

## Step 1: Get `skillgrade` on your machine

You don't have to install anything up front — `run_eval.sh` prefers a `skillgrade` already on
`PATH`, and falls back to `npx --yes skillgrade` automatically. Either works:

```bash
# Option A: install once, reuse everywhere
npm i -g skillgrade

# Option B: no install — let run_eval.sh (or you, directly) invoke it via npx
npx skillgrade --version
```

## Step 2: Set your API key

Two equivalent patterns, pick whichever matches how you manage secrets:

```bash
# Direct
export ANTHROPIC_API_KEY=sk-ant-...

# .env pattern (this repo's convention — see .env.sample)
source .env && ANTHROPIC_API_KEY="${BOSS_ANTHROPIC_API_KEY}" npx --yes skillgrade@latest --version
```

## Step 3: Run the smoke preset locally

```bash
cd plugins/boss-experimental/boss-experimental/skills/claude-config-validation/eval
./run_eval.sh --smoke --provider=local
```

Expected: `run_eval.sh` detects `ANTHROPIC_API_KEY` is set and a `skillgrade` runner is available,
then execs:

```text
=== Skill Eval: claude-config-validation ===
Provider: skillgrade | Preset: smoke

<skillgrade's own trial-by-trial output, then a per-task pass-rate summary>
```

If `ANTHROPIC_API_KEY` is **not** set, `run_eval.sh` doesn't fail — it prints local-dev
instructions instead and exits 0:

```text
=== Skill Eval: claude-config-validation ===

For local development, run evals interactively inside Claude Code:

  /run-skill-eval skills/claude-config-validation

This runs all tasks (deterministic + llm_rubric graders) using your
current Claude Code session -- no API key or extra setup needed.

For CI or headless execution, install skillgrade (npm i -g skillgrade,
or let this script invoke it via npx) and set ANTHROPIC_API_KEY.
```

This fallback is intentional: `run_eval.sh` is safe to run from a fresh clone with no
configuration — it degrades to a helpful pointer rather than an error.

## Step 4: Understand the presets

`run_eval.sh` accepts one preset flag (default `smoke` if none given, or via `EVAL_PRESET`):

| Flag | What it does |
|------|--------------|
| `--smoke` | Fast preset — fewer trials, for quick "did I break anything obvious" checks during development. |
| `--reliable` | More trials per task than `--smoke`, for a steadier pass-rate signal before merging. |
| `--regression` | The most trials — per `run_eval.sh`'s own usage comment, a **30-trial regression** run, for the highest-confidence signal (nightly/release gates). |

Exact trial counts for `--smoke`/`--reliable` are defined by the `skillgrade` CLI itself (not by
this plugin) — check `npx skillgrade --help` for your installed version if you need the precise
number.

You can also target a single task instead of the whole suite:

```bash
EVAL_FILTER=valid-project ./run_eval.sh --smoke
```

## Step 5: Gate on a threshold with `--ci`

For an actual CI gate (exit non-zero below threshold), add `--ci`:

```bash
./run_eval.sh --smoke --ci --threshold=0.8
```

`--ci` and `--threshold` only take effect together — `run_eval.sh` only appends
`--ci --threshold=$THRESHOLD` to the underlying skillgrade invocation when `--ci` is passed
(reading `EVAL_THRESHOLD`, default `0.8`, if you don't pass `--threshold=` explicitly via env var).
This threshold is the same field documented in `eval.yaml`'s `defaults.threshold` — "minimum pass
rate for `--ci` mode" (see the
[schema reference](../../references/skillgrade-eval-yaml-schema.md)).

## Step 6: Wire it into GitHub Actions

```yaml
name: skillgrade-eval

on:
  pull_request:
    paths:
      - "plugins/boss-experimental/boss-experimental/skills/claude-config-validation/**"

jobs:
  eval:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-node@v4
        with:
          node-version: "20"

      - name: Run skillgrade eval (CI gate)
        working-directory: plugins/boss-experimental/boss-experimental/skills/claude-config-validation/eval
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: ./run_eval.sh --smoke --ci --threshold=0.8
```

Adjust the `paths:` filter and `working-directory` to point at your own skill's `eval/` from
[Tutorial 3](03-scaffold-skill-eval.md).

### Pinning the grader model

`llm_rubric` graders call an LLM to score each trial, and that model is configurable — you don't
need a plugin code change or a new skillgrade release just because a new model ships. Pin it once
in `eval.yaml` (this config field works on upstream skillgrade today):

```yaml
defaults:
  agent: claude
  provider: local
  trials: 5
  timeout: 300
  threshold: 0.8
  grader_model: claude-sonnet-5   # any current model ID; per-task/per-grader `model:` overrides this
```

Or override per-run without touching `eval.yaml` at all — handy for a one-off CI job you want
pinned to a different model:

```bash
ANTHROPIC_MODEL=claude-opus-4-8 ./run_eval.sh --smoke --ci --threshold=0.8
```

> **skillgrade version note:** The `defaults.grader_model` / per-task `grader_model` / per-grader
> `model:` config fields work on upstream skillgrade today. The `ANTHROPIC_MODEL` / `OPENAI_MODEL`
> / `GEMINI_MODEL` environment-variable override — and the fix for the `skillgrade init` AI-mode
> 404 — currently live only in the `bossjones/skillgrade` fork (branch
> `fix/anthropic-retired-model-404`) and require that fork or a future upstream release. With
> upstream `npx skillgrade@latest`, if `init` returns 404 use template mode or
> `/scaffold-skill-eval`.

## The AI `init` 404, and why we hand-author `eval.yaml`

If you're starting a brand-new skill and reach for `skillgrade init` to auto-generate an
`eval.yaml` from your `SKILL.md`, know its current limits (recorded in
[`skillgrade-init-demo.md`](../../references/skillgrade-init-demo.md)):

```bash
# template mode (no key) -- succeeds, writes a commented template
npx --yes skillgrade@latest init

# AI mode (with a key) -- currently fails on skillgrade 0.1.6
source .env && ANTHROPIC_API_KEY="${BOSS_ANTHROPIC_API_KEY}" npx --yes skillgrade@latest init
```

Observed AI-mode output on skillgrade `0.1.6`:

```text
skillgrade init
  Found 1 skill(s): claude-config-validation
    init   generating eval with Anthropic
    init   AI generation failed: Anthropic API returned 404
     Falling back to template.
  Created eval.yaml.
```

The `404` happened because skillgrade `0.1.6`'s AI-mode `init` targeted a since-retired model
identifier that no longer resolves for the account. This is no longer a dead end, though: the
model skillgrade uses — both for `init`'s AI mode and for `llm_rubric` graders at eval-run time —
is selectable rather than hardcoded. The precedence is:

- **A `skillgrade` eval run** (any `llm_rubric` grader): per-grader `model:` > per-task
  `grader_model:` > `defaults.grader_model:` in `eval.yaml` > `ANTHROPIC_MODEL`/`OPENAI_MODEL`/
  `GEMINI_MODEL` env var > provider default.
- **`skillgrade init`** (AI-mode scaffolding, before any `eval.yaml` exists): `ANTHROPIC_MODEL`/
  `OPENAI_MODEL`/`GEMINI_MODEL` env var > provider default.

Current provider defaults: anthropic `claude-sonnet-5`, openai `gpt-4o`, gemini
`gemini-3-flash-preview`.

> **skillgrade version note:** The `defaults.grader_model` / per-task `grader_model` / per-grader
> `model:` config fields work on upstream skillgrade today. The `ANTHROPIC_MODEL` / `OPENAI_MODEL`
> / `GEMINI_MODEL` environment-variable override — and the fix for the `skillgrade init` AI-mode
> 404 — currently live only in the `bossjones/skillgrade` fork (branch
> `fix/anthropic-retired-model-404`) and require that fork or a future upstream release. With
> upstream `npx skillgrade@latest`, if `init` returns 404 use template mode or
> `/scaffold-skill-eval`.

**Recommendation:** don't wait on AI-mode `init` against upstream skillgrade. Instead:

1. Use `/scaffold-skill-eval <skill-path>` ([Tutorial 3](03-scaffold-skill-eval.md)) — it generates
   real fixtures, graders, and a schema-conformant `eval.yaml` deterministically, with no API call
   at all.
2. Or run `skillgrade init` in **template mode** (no key) to get the skeleton below, then hand-fill
   the `instruction`, `graders`, and fixtures yourself:

   ```yaml
   version: "1"
   defaults:
     agent: gemini          # gemini | claude
     provider: docker       # docker | local (use local for quick iteration)
     trials: 5
     timeout: 300
     threshold: 0.8
   tasks:
     - name: test-claude-config-validation
       instruction: |
         TODO: Write an instruction based on this skill.
       graders:
         - type: deterministic
           run: |
             echo '{"score": 0.0, "details": "TODO: implement grader"}'
           weight: 0.7
         - type: llm_rubric
           rubric: |
             # TODO: Write a rubric for the LLM grader.
           weight: 0.3
   ```

   Note the template's upstream defaults (`agent: gemini`, `provider: docker`) — this plugin's own
   committed evals deliberately override both to `agent: claude` / `provider: local` for keyless
   local iteration via `/run-skill-eval`.

Either way, the **committed `eval.yaml` is the source of truth** — regenerate it by hand-editing,
not by re-running AI `init` and clobbering your fixtures.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `run_eval.sh` prints the local-dev fallback instead of running trials | `ANTHROPIC_API_KEY` not set, or neither `skillgrade` nor `npx` on `PATH` | Export the key; confirm `node`/`npx` are installed |
| `skillgrade init` AI mode returns 404 | skillgrade `0.1.6`'s AI-mode `init` targets a retired model (see above) | On the `bossjones/skillgrade` fork (branch `fix/anthropic-retired-model-404`), `init` targets a current model and honors `ANTHROPIC_MODEL`; on upstream, use template mode or `/scaffold-skill-eval` instead |
| CI job passes locally but fails in Actions | Different Node version, or key not forwarded to the job | Pin `node-version: "20"`, confirm the secret name matches `env:` |
| `--ci --threshold=` has no effect | `--ci` and `--threshold` weren't both passed on the same invocation | `run_eval.sh` only appends the CI gate when `--ci` is present |

## Next steps

Now put the config-validation skill itself to work on a real project:
[Tutorial 5](05-claude-config-validation.md).
