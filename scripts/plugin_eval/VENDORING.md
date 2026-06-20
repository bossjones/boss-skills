# Vendoring notes

This directory is a **vendored, locally-patched copy** of the `plugin-eval` package from
[`wshobson/agents`](https://github.com/wshobson/agents), specifically the
[`plugins/plugin-eval`](https://github.com/wshobson/agents/tree/main/plugins/plugin-eval)
subdirectory.

- **Upstream:** https://github.com/wshobson/agents/tree/main/plugins/plugin-eval
- **Vendored:** 2026-06-20 (from a local clone of `origin/main`).
- **License:** MIT — see [`LICENSE`](LICENSE) (Copyright (c) 2024 Seth Hobson). Copied verbatim
  from the upstream repository root; the package itself ships no per-package license file.

## What was copied

Only the buildable Python package — `src/plugin_eval/`, `pyproject.toml`, `tests/`, `README.md` —
plus the upstream `LICENSE`. The Claude/Codex plugin wrappers (`.claude-plugin/`, `.codex-plugin/`,
`agents/`, `commands/`, `skills/`, the plugin-level `scripts/`), `uv.lock`, and all caches/venvs
were intentionally left out: the eval tooling builds this package on demand with `uvx --from`, so
none of that wrapper material is needed.

## The local patch (temporary — pending an upstream PR)

Upstream's LLM judge documents `--auth api-key` but never wired it up: `query_llm()` only ever
called the Claude Agent SDK (the Max-plan path), which returns empty inside a `uvx` subprocess.
JSON parsing then fails and the judge silently falls back to static-only scoring (`"No model
usage (static-only evaluation)"`), freezing ~72% of the score weight at heuristic defaults.

The patch restores the documented behaviour and is confined to two files, each clearly commented:

- **`src/plugin_eval/layers/judge.py`** — `query_llm()` now dispatches on `auth`: `api-key` routes
  to the new `_query_via_api()` (the `anthropic` `AsyncAnthropic` SDK, keyed from
  `ANTHROPIC_API_KEY`); `max` keeps the original Agent SDK path. `_query_via_api()` also appends
  per-call token usage to an optional `usage_sink`.
- **`src/plugin_eval/engine.py`** — threads the judge layer's `model_usage` onto the
  `PluginEvalResult` so the report shows real `## Model Usage` instead of "static-only".

This vendoring is **temporary**. The honest, durable fix is a PR to `wshobson/agents` carrying
just the `judge.py` + `engine.py` diff. To keep that PR a clean extract, the vendored
`pyproject.toml` is left **identical to upstream** (separate `llm` / `api` extras); the decision
to request *both* extras for the api-key path lives in this repo's wrapper
(`scripts/eval-skills.py: resolve_source`), not in the package.
