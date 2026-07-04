# The 5-step feedback loop

Adapted from the original `specs/pyrefly.md` adoption spec and Pyrefly's own
[agentic-loop post](https://pyrefly.org/blog/pyrefly-agentic-loop/). Drivable both as a one-shot
"adopt Pyrefly here" run and as a repeatable "burn down N more errors" run.

## 1. See regressions

Run the baseline-diffed check — it passes clean and only fails on errors *new* since the committed
baseline:

```text
$ uv run pyrefly check --baseline pyrefly-baseline.json --summarize-errors
```

(Or via the task-runner target `pyrefly_setup.py` added: `just check-pyrefly` / `make check-pyrefly`
/ `npm run check-pyrefly`.)

## 2. Fix

For each new error, either:

- Hand-fix the annotation, or
- Run `uv run pyrefly infer <path>` and **review the diff in small batches** — the docs warn that
  `infer` can surface new errors of its own, so don't blindly accept a large infer diff.

Re-run step 1 after each batch.

## 3. Burn down

Once fixes land, regenerate the baseline so the committed error count shrinks:

```text
$ uv run pyrefly check --baseline pyrefly-baseline.json --update-baseline
```

The shrinking `pyrefly-baseline.json` is the visible progress signal in git history — commit it
alongside the fixes.

## 4. Coverage

Track `strict_coverage` climbing over time as a delta per run, not a single global threshold gate:

```text
$ uv run pyrefly coverage report <project-includes> | jq .summary.strict_coverage
```

Report the delta (before vs. after a batch), not just the absolute number — a single global coverage
threshold would make this loop blocking, which contradicts the non-blocking posture.

## 5. Automate

The Stop hook (see `hook-setup.md`) runs step 1 after every agent turn in the target repo, so new
errors surface immediately instead of accumulating silently across many turns. This is opt-in
(`--with-stop-hook`), not applied by default.
