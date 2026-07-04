# Subagent fan-out for the fix-verify loop

Modeled on
[`boss-security-review/references/fanout.md`](../../boss-security-review/references/fanout.md)'s
size heuristic, adapted from "review effort" to "fix effort."

## When to stay single-context

Fix directly in the current context (no subagents) when a batch of new baseline errors is small
enough to hold and reason about carefully — roughly a handful of errors, or errors confined to one
or two files. Fix, re-run `pyrefly check --baseline pyrefly-baseline.json`, repeat until clean, then
regenerate the baseline (`feedback-loop.md` steps 2–3).

## When to fan out

Fan out to parallel fix subagents when a batch is large enough that fixing serially in one context
would be slow or error-prone — a big burn-down pass across many files, or errors clustered into
distinct kinds (e.g. a batch of `missing-return-type` errors vs. a batch of `bad-assignment`
errors). Split one of two ways:

- **By file** — one subagent per file (or small file cluster) with new errors. Best when errors are
  scattered across many unrelated files.
- **By error-kind cluster** — one subagent per Pyrefly error kind (see
  [error-kinds](https://pyrefly.org/en/docs/error-kinds/)). Best when the same kind of error repeats
  across many files and a single fix pattern applies everywhere.

## Subagent contract

Give each fix subagent:

- **Its exact file subset or error-kind cluster** — never let two subagents edit the same file
  concurrently.
- **The exact baseline-diffed errors it owns** (file:line + error text), not "fix everything."
- **A self-verification requirement**: after fixing, it must re-run `pyrefly check` scoped to just
  its own files (`pyrefly check <its files>`) and confirm no new errors were introduced before
  reporting back. Instruct it to report raw pass/fail + remaining error count — no prose preamble.

Keep fix subagents scoped to source edits only — they do not regenerate the baseline or touch the
task-runner config.

## Aggregating in the main context

After all subagents report:

1. Run the full aggregate baseline-diffed check (`pyrefly check --baseline pyrefly-baseline.json`)
   to confirm the whole batch is clean — a subagent's own self-verification only covered its files,
   not cross-file interactions.
2. If clean, regenerate the baseline (`feedback-loop.md` step 3) and report the coverage delta
   (step 4).
3. If not clean, identify which subagent's fix introduced the regression and re-dispatch just that
   piece — don't re-run the whole fleet.
