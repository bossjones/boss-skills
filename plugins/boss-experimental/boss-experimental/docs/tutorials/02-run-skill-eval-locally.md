# Tutorial 2: Evaluate an existing skill locally (no API key)

**Time:** ~10 minutes (Claude Code actually executes all 13 tasks)
**You'll learn:** how `/run-skill-eval` works, why it must run in the main session, and how to
read its score table.

## What you'll build

Nothing new — you'll run the plugin's own worked example, `claude-config-validation`, against its
13 committed test fixtures and see a full pass/fail report.

## Why this needs no API key and no Docker

`/run-skill-eval` doesn't shell out to anything external. **Claude Code itself is the agent**: it
reads the skill's `eval/eval.yaml`, actually executes the skill's procedure against each fixture,
writes the output, and then grades that output itself (running the `deterministic` grader scripts
with `Bash`, and self-scoring the `llm_rubric` graders). That's the whole loop — no network calls,
no containers.

## Prerequisite

Complete [Tutorial 1](01-install-and-enable.md) so `/run-skill-eval` is available.

## Step 1: Run it

In your **main Claude Code session** (not a background task — see the callout below), run:

```text
/run-skill-eval plugins/boss-experimental/boss-experimental/skills/claude-config-validation
```

If you omit the argument, it defaults to this same skill path (see
`skills/run-skill-eval/SKILL.md`).

## Step 2: Watch what happens

Per `skills/run-skill-eval/SKILL.md`, Claude Code will, for each of the 13 tasks in
`skills/claude-config-validation/eval/eval.yaml`:

1. Delete any leftover `eval/output-*.md` from a previous run.
2. Read the task's `instruction` and `workspace` fixture path.
3. Actually run the `claude-config-validation` skill against that fixture (all 23 checks — no
   shortcuts).
4. Write the full output to `eval/output-{task-name}.md`.
5. Run every grader for that task:
   - `deterministic` graders execute a Node script with `Bash` (e.g.
     `node graders/check-fail-present.js "Config exists" output-missing-claude-dir.md`).
   - `llm_rubric` graders are scored by Claude itself reading the rubric and the output file.
6. Compute the weighted score: `sum(score * weight) / sum(weight)`. A task passes only if that
   score is exactly `1.0`.

## Step 3: Read the score table

Expected final output (from the 13 fixtures documented in
`skills/claude-config-validation/eval/README.md`):

```text
| Task                      | Score | Details                                          |
|---------------------------|-------|---------------------------------------------------|
| valid-project             | 1.0   | deterministic(0.7): 1.0, llm_rubric(0.3): 1.0      |
| missing-claude-dir        | 1.0   | deterministic(1.0): 1.0                            |
| misplaced-canonical-agent | 1.0   | deterministic(1.0): 1.0                            |
| custom-pipeline-agent     | 1.0   | deterministic(1.0): 1.0                            |
| bad-agent-frontmatter     | 1.0   | deterministic(1.0): 1.0                            |
| convention-in-agent       | 1.0   | deterministic(1.0): 1.0                            |
| duplicated-content        | 1.0   | deterministic(1.0): 1.0                            |
| oversized-claude-md       | 1.0   | deterministic(1.0): 1.0                            |
| skill-with-code-blocks    | 1.0   | deterministic(1.0): 1.0                            |
| oversized-skill           | 1.0   | deterministic(1.0): 1.0                            |
| missing-skill-ref         | 1.0   | deterministic(1.0): 1.0                            |
| broken-cross-ref          | 1.0   | deterministic(1.0): 1.0                            |
| rule-doc-in-routing-table | 1.0   | deterministic(0.7): 1.0, llm_rubric(0.3): 1.0      |

13/13 tasks passed
```

Exact wording and score values can vary trial to trial (this is a live agent run, not a fixed
fixture replay) — what should stay stable is **all 13 tasks passing**, because these fixtures are
the plugin's own regression suite.

> **Info box — why `valid-project` and `rule-doc-in-routing-table` have two graders.** Every other
> task uses a single `deterministic` grader that greps for a specific `FAIL`/`WARN` string (cheap,
> exact). These two also carry an `llm_rubric` grader (weight `0.3`) because their pass condition
> is about *overall shape* (a well-formed table covering all categories; two specific checks
> agreeing with each other), which a keyword grep alone can't verify.

## Constraint: main session only

> **Warning.** Do not delegate `/run-skill-eval` to a background subagent (e.g. via the `Agent`
> tool). Background subagents auto-deny `Bash` permission prompts, so every `deterministic` grader
> silently fails — you'll see a wall of `0.0` scores with no clear cause. Run it directly in the
> session you're typing into.

## Step 4: Run a single task

To iterate faster while debugging one fixture, ask Claude to run just that task, e.g.:

```text
Run only the "misplaced-canonical-agent" task from /run-skill-eval plugins/boss-experimental/boss-experimental/skills/claude-config-validation
```

(There's no `--eval=<name>` flag for the *local* `/run-skill-eval` path — that filter exists on
the CI `run_eval.sh` side, covered in [Tutorial 4](04-ci-with-skillgrade.md). Locally, you ask in
plain language and Claude scopes the run.)

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Every grader scores `0.0` | Ran inside a background subagent | Re-run in the main session |
| A grader errors "file not found" | Output file wasn't written before the grader ran, or wrong task name in the `run` command | Confirm `eval/output-{task-name}.md` was created; `run-skill-eval` replaces `output.md` in the grader command with the per-task filename |
| Scores are non-deterministic across runs | `llm_rubric` graders are inherently judgment-based | Expected — this is why CI trials (Tutorial 4) run multiple trials against a pass-rate `threshold`, not a single pass/fail |

## Next steps

Now scaffold an eval for a skill of your own: [Tutorial 3](03-scaffold-skill-eval.md).
