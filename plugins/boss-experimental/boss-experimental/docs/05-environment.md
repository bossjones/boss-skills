# Environment, Requirements & Known Limitations

## Runtime requirements

| Requirement | Needed for | Notes |
|---|---|---|
| **Node ≥ 20** | Every grader invocation (`node graders/*.js`), and the `skillgrade` CLI itself | The Node graders are zero-dependency (only `fs`/`path` builtins), so no `npm install` step is required beyond having a Node binary on `PATH`. |
| **`skillgrade` (npm CLI)** | The **CI/headless** path only (`run_eval.sh` delegating to real trials) | Either `npm i -g skillgrade` (resolved via `command -v skillgrade`) or, with no global install, `npx --yes skillgrade` — `run_eval.sh` tries the former first and falls back to the latter automatically. |
| **`ANTHROPIC_API_KEY`** | The **CI/headless** path only | `run_eval.sh` only invokes `skillgrade` when both a resolvable `skillgrade` runner **and** `ANTHROPIC_API_KEY` are present; otherwise it prints local-dev instructions and exits without delegating. |
| **Nothing extra** | The **local** path (`/run-skill-eval`, `/scaffold-skill-eval`, `/claude-config-validation`) | Claude Code itself is the agent. No API key, no Docker, no `skillgrade` install. |

**Not a Python dependency.** `skillgrade` is a Node CLI. It must never be added to
`pyproject.toml` or installed via `uv` — the plugin README states this explicitly, and
[`references/skillgrade-vs-plugin-eval.md`](../references/skillgrade-vs-plugin-eval.md)
reiterates the toolchain split: this plugin's eval system is Node-based; the repo's existing
`plugin-eval` stack (`/skill-evals`, `make eval-skill`) is Python-based. **The two toolchains are
independent — using this plugin's evals never touches the repo's Python eval stack, and vice
versa.**

## Where `ANTHROPIC_API_KEY` matters (and where it doesn't)

This is worth stating precisely because it's easy to assume every eval-shaped tool needs a key:

- `/run-skill-eval` (local): **no key**. Claude Code's own session plays both the agent-under-test
  and the `llm_rubric` grader.
- `/scaffold-skill-eval`: **no key**. It only reads/writes files and runs grader scripts to
  sanity-check their JSON output.
- `/claude-config-validation`: **no key**, and no `Bash` at all — it's `Read`/`Glob`/`Grep` only.
- `run_eval.sh` in CI mode (real `skillgrade` trials against `gemini`/`claude`/`codex`): **key
  required** — this is the only path in the whole plugin that costs an API call.

**Selecting the model (not just the key).** On the CI path, which *model* the `llm_rubric` grader
uses is separate from the API key. Pin it in `eval.yaml` via `defaults.grader_model` (works on
upstream skillgrade today), or override per-run with the provider's `*_MODEL` env var
(`ANTHROPIC_MODEL`, `OPENAI_MODEL`, `GEMINI_MODEL`; fork-only — see the version note below). Either
way, adopting a newly released model needs **no code change** — see
[`references/skillgrade-eval-yaml-schema.md`](../references/skillgrade-eval-yaml-schema.md) →
Model selection.

## `skillgrade init` — the AI-mode 404

Recorded in [`references/skillgrade-init-demo.md`](../references/skillgrade-init-demo.md), from
a real run against this plugin's `claude-config-validation` skill:

```text
skillgrade init
  Found 1 skill(s): claude-config-validation
    init   generating eval with Anthropic
    init   AI generation failed: Anthropic API returned 404
     Falling back to template.
  Created eval.yaml.
```

- `npx skillgrade@latest --version` reports **`0.1.6`**, and it installs/runs cleanly under
  Node 20.
- **Template-mode `init`** (no API key) works and writes a valid, commented `eval.yaml`
  scaffold — `agent: gemini`, `provider: docker`, one placeholder task with a `deterministic`
  grader stub and an `llm_rubric` stub.
- **AI-mode `init`** (with `ANTHROPIC_API_KEY` set) attempts to generate a real eval via the
  Anthropic API. On upstream `skillgrade 0.1.6` it fails with a **404** because the model
  identifier it requests internally has been retired and no longer resolves. The model **is**
  selectable, though — resolution precedence is the `*_MODEL` env var (`ANTHROPIC_MODEL`,
  `OPENAI_MODEL`, `GEMINI_MODEL`) → provider default:

  ```bash
  ANTHROPIC_MODEL=claude-opus-4-8 skillgrade init
  ```

> **skillgrade version note:** The `defaults.grader_model` / per-task `grader_model` / per-grader
> `model:` config fields work on upstream skillgrade today. The `ANTHROPIC_MODEL` / `OPENAI_MODEL`
> / `GEMINI_MODEL` environment-variable override — and the fix for the `skillgrade init` AI-mode
> 404 — currently live only in the `bossjones/skillgrade` fork (branch
> `fix/anthropic-retired-model-404`) and require that fork or a future upstream release. With
> upstream `npx skillgrade@latest`, if `init` returns 404 use template mode or `/scaffold-skill-eval`.

**Practical consequence: hand-author `eval.yaml`, don't rely on AI-mode `init`.** The committed,
working suite at
[`skills/claude-config-validation/eval/`](../skills/claude-config-validation/eval/) — a filled-in
`eval.yaml`, four zero-dependency Node graders, and 13 fixtures — is the plugin's actual source
of truth, produced by hand (via the `scaffold-skill-eval` procedure) rather than by AI-mode
`init`. For a brand-new skill, the recommended path is: run template-mode `skillgrade init` (or
just `/scaffold-skill-eval`) to get the file skeletons, then fill in real `instruction`s,
`workspace` fixtures, and graders by hand, following
[`references/skillgrade-eval-yaml-schema.md`](../references/skillgrade-eval-yaml-schema.md).

## Defaults this plugin pins vs. upstream `skillgrade` defaults

| Field | Upstream `skillgrade init` default | This plugin's hand-authored evals |
|---|---|---|
| `agent` | `gemini` | `claude` |
| `provider` | `docker` | `local` |
| `grader_model` | provider default (e.g. `anthropic` → `claude-sonnet-5`) | left unset (provider default) — override via `grader_model` or a `*_MODEL` env var when needed |

The plugin deliberately diverges from the upstream template defaults so that its own eval
(`claude-config-validation/eval/eval.yaml`) can run keylessly via `/run-skill-eval` during local
iteration, while still being CI-capable (`provider: local` is also valid for `skillgrade`'s CI
runner — it just skips the Docker sandbox).

## Positioning reminder

None of the above changes anything about this repo's **existing** eval stack. `boss-experimental`
does not modify, wrap, or gate `make eval`, `make eval-skill`, `/skill-evals`, or
`scripts/plugin_eval/`. The two stacks can be run side by side on the same skill and answer
different questions — see
[`references/skillgrade-vs-plugin-eval.md`](../references/skillgrade-vs-plugin-eval.md) for the
full comparison.
