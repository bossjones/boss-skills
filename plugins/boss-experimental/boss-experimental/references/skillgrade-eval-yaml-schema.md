# eval.yaml Schema Reference

Schema for `eval.yaml` as defined by [skillgrade](https://github.com/mgechev/skillgrade). This is the contract between the scaffold skill, `/run-skill-eval`, and CI.

Source: `skillgrade/src/core/config.types.ts`

## Top-level

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `version` | string | yes | — | Schema version. Currently `"1"`. |
| `skill` | string | no | auto-detect | Path to SKILL.md. |
| `defaults` | object | yes | — | Global defaults (see below). |
| `tasks` | array | yes | — | At least one task. |

## `defaults`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `agent` | string | yes | `gemini` | Agent type: `gemini`, `claude`, `codex`. |
| `provider` | string | yes | `docker` | Execution provider: `docker`, `local`. |
| `trials` | number | yes | `5` | Number of independent runs per task. |
| `timeout` | number | yes | `300` | Timeout in seconds per trial. |
| `threshold` | number | yes | `0.8` | Minimum pass rate for `--ci` mode. |
| `grader_model` | string | no | provider default | Default LLM model for `llm_rubric` graders (see [Model selection](#model-selection)). |
| `grader_provider` | string | no | `gemini` | Default LLM provider for `llm_rubric` graders: `gemini`, `anthropic`, `openai`. |
| `docker` | object | no | `{base: "node:20-slim"}` | Docker configuration (CI only). |
| `environment` | object | no | `{cpus: 2, memory_mb: 2048}` | Resource limits (CI only). |

## `tasks[]`

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | yes | — | Task identifier (used in output and filtering). |
| `instruction` | string | yes | — | Inline text or path to `.md` file. |
| `workspace` | array | no | — | Files to map into the agent's workspace. |
| `graders` | array | yes | — | At least one grader. |
| `solution` | string | no | — | Path to reference solution script. |
| `agent` | string | no | inherited | Override `defaults.agent` for this task. |
| `provider` | string | no | inherited | Override `defaults.provider` for this task. |
| `trials` | number | no | inherited | Override `defaults.trials` for this task. |
| `timeout` | number | no | inherited | Override `defaults.timeout` for this task. |
| `grader_model` | string | no | inherited | Override `defaults.grader_model` for this task. |

## `tasks[].workspace[]`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `src` | string | yes | Path relative to eval.yaml. |
| `dest` | string | yes | Path in the agent's workspace. |
| `chmod` | string | no | Permission modifier (e.g., `"+x"`). |

## `tasks[].graders[]`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `type` | string | yes | `deterministic` or `llm_rubric`. |
| `weight` | number | yes | Contribution to weighted score. |
| `run` | string | conditional | Shell command (required for `deterministic`). |
| `rubric` | string | conditional | Rubric text or file path (required for `llm_rubric`). |
| `setup` | string | no | Shell commands to install grader dependencies. |
| `model` | string | no | LLM model override for this grader (see [Model selection](#model-selection)). |
| `provider` | string | no | LLM provider for this grader: `gemini`, `anthropic`, `openai`. |

## Model selection

Which model the `llm_rubric` grader uses is resolved by this precedence (highest first), so
adopting a newly released model needs **no code change**:

1. A grader's own `model:`
2. A task's `grader_model:`
3. `defaults.grader_model:`
4. The provider's `*_MODEL` environment variable — `ANTHROPIC_MODEL`, `OPENAI_MODEL`, `GEMINI_MODEL`
5. The provider's built-in default (`anthropic` → `claude-sonnet-5`, `openai` → `gpt-4o`,
   `gemini` → `gemini-3-flash-preview`)

Point `grader_model` (or the env var) at any current model ID — e.g. `grader_model: claude-sonnet-5`,
or `ANTHROPIC_MODEL=claude-opus-4-8 skillgrade`.

> **skillgrade version note:** The `defaults.grader_model` / per-task `grader_model` / per-grader
> `model:` config fields work on upstream skillgrade today. The `ANTHROPIC_MODEL` / `OPENAI_MODEL`
> / `GEMINI_MODEL` environment-variable override — and the fix for the `skillgrade init` AI-mode
> 404 — currently live only in the `bossjones/skillgrade` fork (branch
> `fix/anthropic-retired-model-404`) and require that fork or a future upstream release. With
> upstream `npx skillgrade@latest`, if `init` returns 404 use template mode or `/scaffold-skill-eval`.

## Scoring

A trial's score = `sum(grader_score * weight) / sum(weight)`. A trial passes if every grader scores 1.0. A task's pass rate = passed trials / total trials. The task passes if the pass rate meets `threshold`.
