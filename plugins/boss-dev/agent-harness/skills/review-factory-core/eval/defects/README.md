# Suite 2 — seeded defects

> ⚠️ **This suite spawns real agents and costs real money.** Five specialists plus a judge per
> fixture, roughly **$0.50–1.00 each**, so ~$4–8 for a full pass on one arm. It lives in its own
> directory precisely so `/run-skill-eval <skill>` — which resolves `eval/eval.yaml` — can never
> pick it up by accident. Run it deliberately. Never in CI.

Suite 1 proves the factory **hires the right agents**. Only suite 2 proves those agents can
actually **find a bug** — and, far more importantly, that they **stay quiet on correct code**.

## The planted defects

Each fixture is an annotated diff of added lines, so a defect's anchor is simply its line number
in the new file. The exact planted line is recorded in
[`test-fixtures/planted.json`](test-fixtures/planted.json), which is generated alongside the
fixtures so the two can never drift apart.

| Task | Planted defect | Anchor | Expect |
| :--- | :--- | :--- | :--- |
| **`clean-no-defects`** | **none — the control** | — | **zero findings** |
| `planted-sql-injection` | f-string interpolated into `cursor.execute` | `src/db/queries.py:7` | `critical` |
| `planted-shell-injection` | `subprocess.run(..., shell=True)` with an interpolated tag | `scripts/deploy.py:6` | `critical` |
| `planted-missing-authz` | `DELETE` route with no `@require_auth`, directly below a `GET` route that has one | `src/api/routes.py:13` | `critical` |
| `planted-perf-quadratic` | O(n²) scan of `orders` inside a loop over `users` | `src/report/aggregate.py:6` | `moderate` |
| `planted-stale-claude-md` | `CLAUDE.md` documents a `make bundle` target that does not exist | `CLAUDE.md:9` | `moderate` |
| `planted-skill-backtick-bug` | a `SKILL.md` using the backtick-bang pattern that GitHub #12781 makes the parser **execute on load** | `skills/example/SKILL.md:11` | `critical` |

### `clean-no-defects` is the whole ballgame

Every other task in this table *rewards finding things*. A factory that flagged every line would
score 6/7 and be completely worthless. `clean-no-defects` is the only task that can tell the
difference between a real reviewer and a plausible-sounding noisy one. **If it fails, the suite
has failed, regardless of the other six.**

That is also why it runs at `--tier full`: five specialists staring at a correct, boring diff is
the harshest possible test of restraint.

### A note on `planted-skill-backtick-bug`

The fixture contains the exact pattern GitHub #12781 causes the skill parser to **execute** — even
inside a fenced code block. It is safe *here* because a `.diff` fixture is not a `SKILL.md` and is
never parsed as skill content. **Never copy that line into a real `SKILL.md`,** and note that the
generator assembles it from parts so the literal pattern appears in no source file of its own.

## Why every task forces `--tier full`

These fixtures are small. Left to natural tiering, a 10-line diff lands `trivial` — roster
`[generalist]` — and the specialist that owns the planted defect would never be hired. The task
would then be measuring the wrong reviewer and failing for the wrong reason. `--tier full` hires
the whole roster so the test is about *detection*, not *staffing* (staffing is suite 1's job).

## Running it

The arm under test is read from `$REVIEW_ARM`, so the same suite drives **both** sides of the
bake-off without editing a single prompt — which is the entire point of the comparison.

```bash
cd plugins/boss-dev/agent-harness/skills/review-factory-core/eval/defects

# One fixture, one arm (the cheap smoke test)
REVIEW_ARM=review-factory-workflow ./../run_eval.sh --eval=clean-no-defects

# The other arm, same fixtures, same prompts
REVIEW_ARM=review-factory-cmux ./../run_eval.sh --eval=clean-no-defects
```

Scorecard for any run (cost, cache hit rate, cost-per-finding **per specialist**):

```bash
uv run ../../scripts/score_run.py report ws/replay-<fixture> --arm workflow
```

Snapshot **before** the run or the cost will be overstated — `score_run.py` works by diffing the
set of session transcripts, so it needs to know which ones already existed:

```bash
uv run ../../scripts/score_run.py snapshot ws/replay-<fixture>
```
