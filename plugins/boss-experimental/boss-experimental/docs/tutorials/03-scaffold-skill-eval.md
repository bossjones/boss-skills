# Tutorial 3: Scaffold an eval for your own skill

**Time:** ~15 minutes
**You'll learn:** how `/scaffold-skill-eval` turns a bare `SKILL.md` into a runnable `eval/`
directory, how to read the generated files against the `eval.yaml` schema, and how to hand-edit a
task.

## What you'll build

A tiny skill of your own — `my-skill` — plus a complete, runnable eval suite for it:

```text
apps/example-app/
└── .claude/
    └── skills/
        └── my-skill/
            ├── SKILL.md
            └── eval/
                ├── eval.yaml
                ├── run_eval.sh
                ├── README.md
                ├── .gitignore
                ├── graders/
                │   ├── check-fail-present.js
                │   └── check-no-fails.js
                └── test-fixtures/
                    ├── valid-docs/
                    ├── missing-heading/
                    └── wrong-heading-level/
```

This can live in **any** repo — `/scaffold-skill-eval` only needs a directory containing a
`SKILL.md`. We use a project-scoped path (`apps/example-app/.claude/skills/my-skill`) here so the
example matches a real project layout, not this plugin's own internal skills.

## Prerequisite

Complete [Tutorial 1](01-install-and-enable.md). No API key or Docker needed for this tutorial.

## Step 1: Write a skill worth evaluating

Create `apps/example-app/.claude/skills/my-skill/SKILL.md`:

```text
---
name: doc-heading-check
description: Validates that every markdown file in a project's docs/ directory starts with a top-level H1 heading
allowed-tools:
    - Read
    - Glob
---

# Doc Heading Check

## Input

- project_path: Path to the project directory. Defaults to cwd.

## Steps

### 1. Find markdown files

Glob {project_path}/docs/**/*.md.

### 2. Check each file's first heading

Read the first non-blank line of each file. It must be a single `#` followed by a space (a
top-level H1) — `##` or lower is a FAIL, and a missing heading is a FAIL.

### 3. Report results

Output a markdown table:

| File | Status | Detail |
|------|--------|--------|
| docs/example.md | PASS | |
| docs/bad.md | FAIL | no top-level H1 heading found |

Then a summary line: `{passed}/{total} files passed`.
```

This is a real, if small, skill: it has a clear input, a deterministic PASS/FAIL output format,
and at least one obvious failure mode (missing or demoted heading) — exactly what
`/scaffold-skill-eval` needs to design fixtures against.

## Step 2: Run the scaffolder

```text
/scaffold-skill-eval apps/example-app/.claude/skills/my-skill
```

Per `skills/scaffold-skill-eval/SKILL.md`, this runs nine steps: validate the target skill, analyze
its contract, design fixtures (one positive control + a negative per failure mode), write grader
scripts (reusing the reference graders where the output format matches), write `eval.yaml` against
the schema, copy `run_eval.sh` verbatim, write `eval/README.md`, add `eval/.gitignore`, then clean
up its scratch `ANALYSIS.md`.

## Step 3: Read the report

Expected closing output (per the skill's `## Output` section):

```text
Eval scaffolded for: doc-heading-check
  Fixtures: 3
  Graders:  2
  Files created:
    apps/example-app/.claude/skills/my-skill/eval/eval.yaml
    apps/example-app/.claude/skills/my-skill/eval/run_eval.sh
    apps/example-app/.claude/skills/my-skill/eval/README.md
    apps/example-app/.claude/skills/my-skill/eval/.gitignore
    apps/example-app/.claude/skills/my-skill/eval/graders/check-fail-present.js
    apps/example-app/.claude/skills/my-skill/eval/graders/check-no-fails.js
    apps/example-app/.claude/skills/my-skill/eval/test-fixtures/valid-docs/
    apps/example-app/.claude/skills/my-skill/eval/test-fixtures/missing-heading/
    apps/example-app/.claude/skills/my-skill/eval/test-fixtures/wrong-heading-level/

  Run: cd apps/example-app/.claude/skills/my-skill/eval && ./run_eval.sh --smoke
  Or:  /run-skill-eval apps/example-app/.claude/skills/my-skill
```

Fixture and grader counts will vary with your actual `SKILL.md` — this is illustrative for the
skill above, not a guarantee.

## Step 4: Inspect the generated `eval.yaml`

Open `apps/example-app/.claude/skills/my-skill/eval/eval.yaml`. It should conform to the schema in
[`skillgrade-eval-yaml-schema.md`](../../references/skillgrade-eval-yaml-schema.md) — a `version`,
`defaults` (pinned to `agent: claude`, `provider: local` for keyless local iteration), and one
`tasks[]` entry per fixture:

```yaml
version: "1"

defaults:
    agent: claude
    provider: local
    trials: 5
    timeout: 300
    threshold: 0.8

tasks:
    - name: valid-docs
      instruction: |
          Run the doc-heading-check skill on the project at test-fixtures/valid-docs.
          Output the results table to output.md.
      workspace:
          - src: test-fixtures/valid-docs
            dest: test-fixtures/valid-docs
      graders:
          - type: deterministic
            run: node graders/check-no-fails.js output.md
            weight: 1.0

    - name: missing-heading
      instruction: |
          Run the doc-heading-check skill on the project at test-fixtures/missing-heading.
          Output the results table to output.md.
      workspace:
          - src: test-fixtures/missing-heading
            dest: test-fixtures/missing-heading
      graders:
          - type: deterministic
            run: node graders/check-fail-present.js "bad.md" output.md
            weight: 1.0

    - name: wrong-heading-level
      instruction: |
          Run the doc-heading-check skill on the project at test-fixtures/wrong-heading-level.
          Output the results table to output.md.
      workspace:
          - src: test-fixtures/wrong-heading-level
            dest: test-fixtures/wrong-heading-level
      graders:
          - type: deterministic
            run: node graders/check-fail-present.js "demoted.md" output.md
            weight: 1.0
```

Cross-check each field against the schema table:

| Field you're looking at | Schema says |
|---|---|
| `defaults.agent: claude` | `agent`: `gemini` \| `claude` \| `codex` — pinned to `claude` here for keyless local runs |
| `defaults.provider: local` | `provider`: `docker` \| `local` — `local` skips container setup entirely |
| `tasks[].workspace[].src`/`dest` | Paths relative to `eval.yaml`; `dest` is where it lands in the agent's workspace |
| `tasks[].graders[].weight` | Contributes to `sum(score * weight) / sum(weight)`; a trial only passes at `1.0` |

## Step 5: Hand-edit a task

Say you want a fourth fixture for a file with **no markdown files at all** in `docs/` (an edge
case the scaffolder's category sweep might not have generated). Add the fixture directory and a
new task by hand, following the same schema shape:

1. Create `apps/example-app/.claude/skills/my-skill/eval/test-fixtures/empty-docs/docs/.gitkeep`
   (an empty `docs/` directory — Git needs a placeholder file to track it).
2. Add a task to `eval.yaml`:

   ```yaml
       - name: empty-docs
         instruction: |
             Run the doc-heading-check skill on the project at test-fixtures/empty-docs.
             Output the results table to output.md.
         workspace:
             - src: test-fixtures/empty-docs
               dest: test-fixtures/empty-docs
         graders:
             - type: deterministic
               run: node graders/check-no-fails.js output.md
               weight: 0.7
             - type: llm_rubric
               rubric: |
                   The output should report 0/0 files passed (or an equivalent "no files found"
                   message) rather than silently omitting the summary line, and must not report
                   any FAIL.
               weight: 0.3
   ```

   Note the two-grader pattern from `skills/claude-config-validation/eval/eval.yaml`: a cheap
   `deterministic` grader for the hard invariant (no FAIL), plus a weighted `llm_rubric` grader for
   the softer "did it report the summary sensibly" check — reuse this split whenever a fixture's
   pass condition is partly structural and partly about output completeness.

3. Update `eval/README.md`'s fixture table to add the new row (the scaffolder's own convention —
   see `skills/claude-config-validation/eval/README.md` for the format to match).

## Step 6: Run it locally

```text
/run-skill-eval apps/example-app/.claude/skills/my-skill
```

Expected: a 4-row score table (or 3, if you skipped Step 5), each task at `1.0`, and a closing
`4/4 tasks passed` line — following the exact format from
[Tutorial 2](02-run-skill-eval-locally.md#step-3-read-the-score-table). Run it in your **main
session**, not a background subagent, for the same reason as Tutorial 2.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Scaffolder stops immediately, reporting "SKILL.md missing description" | Frontmatter incomplete | Add a `description:` field to the target `SKILL.md` and re-run |
| A grader always scores `0.0` even on the positive fixture | Output format doesn't match the grader's expectations (e.g. no `\| FAIL` literal table syntax) | Match your skill's output format to what `check-no-fails.js`/`check-fail-present.js` expect (markdown table cells), or write a custom grader |
| `eval.yaml` fails schema validation in CI (Tutorial 4) but works locally | Local `/run-skill-eval` doesn't strictly validate the schema — `skillgrade` does | Diff your `eval.yaml` against the schema table field by field |

## Next steps

Take this same `eval/` to CI: [Tutorial 4](04-ci-with-skillgrade.md).
