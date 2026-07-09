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
| `grader_model` | string | no | — | Default LLM model for `llm_rubric` graders. |
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
| `model` | string | no | LLM model override for this grader. |

## Scoring

A trial's score = `sum(grader_score * weight) / sum(weight)`. A trial passes if every grader scores 1.0. A task's pass rate = passed trials / total trials. The task passes if the pass rate meets `threshold`.
