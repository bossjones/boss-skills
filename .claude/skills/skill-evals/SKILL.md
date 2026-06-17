---
name: skill-evals
description: >
  Run wshobson PluginEval over this repo's skills and write a `# PluginEval Report`
  to an `EVALS.md` in each skill's folder. Use when the user wants to evaluate,
  score, grade, benchmark, or certify skills; (re)generate or refresh EVALS.md files;
  check skill quality after editing a SKILL.md; or improve skills based on their eval
  results. Defaults to `--review` (score/standard depth, report only); `--fix` also edits
  the weakest skills' SKILL.md in place to raise their scores; `--certify` runs the full
  deep certification with a badge. Reach for this skill even when the user only says
  "run the evals", "score these skills", or "make EVALS.md" without naming PluginEval.
argument-hint: "[--review | --fix | --certify] [skill-path ...]"
allowed-tools: Bash(make *) Bash(git diff *) Bash(git status *) Bash(./scripts/eval-skills.py *) Bash(test *) Bash(ls *) Read Edit Task
metadata:
  version: "0.2.0"
---

# Skill Evals

Evaluate this repo's skills with [PluginEval](references/plugin-eval.md) (pulled on demand
via `uvx` from `wshobson/agents` — nothing is vendored) and drop a Markdown report into
each skill's own folder as `EVALS.md`. The work fans out across **one subagent per skill**
so reports are produced in parallel and each subagent's verbose `uvx`/LLM output stays out
of the main context.

The upstream docs are bundled so you can look them up without network access:

- [`references/plugin-eval.md`](references/plugin-eval.md) — the eval framework
  (commands, depths, layers, dimensions, badges).
- [`references/agent-skills-how-skills-work.md`](references/agent-skills-how-skills-work.md)
  — what a good skill looks like (progressive disclosure, triggering, spec rules).
- [`references/fix-playbook.md`](references/fix-playbook.md) — translating a weak
  dimension into a concrete SKILL.md edit (used by `--fix`).

## What was requested

This run was invoked with:

> `$ARGUMENTS`

Parse it before anything else (when invoked automatically rather than via `/skill-evals`,
this is empty — fall back to the defaults):

- **Mode** — `--certify` and/or `--fix` if present, otherwise `--review` (the default).
- **Targets** — any token that is not a `--flag` is an explicit skill directory path. If
  none are given, auto-detect from the branch diff (Step 1).

Echo the resolved mode and target list back to the user before running anything — e.g.
"Evaluating 5 skills in `--review` mode: …" — so the scope is confirmed up front.

## Arguments

| Argument | Meaning |
|----------|---------|
| `--review` | **Default.** Score each skill at standard depth (static + LLM judge) and write `EVALS.md`. No skill edits. |
| `--fix` | Do `--review`, then improve the weakest skills' `SKILL.md` in the working tree (uncommitted) and re-run to confirm the gain. |
| `--certify` | Run the full e2e `certify` (deep, all three layers, badge) instead of `score`. Slow. |
| `<path> ...` | One or more explicit skill directories. If omitted, targets are auto-detected by diffing against `main`. |

`--fix` and `--certify` compose: certify first, then fix off the certified report.

This skill always evaluates **one skill at a time** through the per-skill `make eval-skill`
(standard depth) and `make eval-certify` (deep) targets. It never uses the repo-wide
`make eval`, which runs every skill at quick/static depth — a different, shallower report.

## Step 0 — Ensure the corpus exists

PluginEval keeps a corpus index (used for Elo ranking). It is created once and is
idempotent. `make eval-skill`/`make eval-certify` discover the default corpus location on
their own, so this step is a one-time setup rather than a hard precondition for each
`score` run — but running it keeps ranking-aware output available. Only run it if the
corpus is missing:

```bash
test -d ~/.plugineval/corpus || ./scripts/eval-skills.py --command init plugins/ --corpus-dir ~/.plugineval/corpus
```

## Step 1 — Resolve the target skills

If the user passed explicit skill paths, use those. Otherwise auto-detect what changed on
this branch:

```bash
git diff --name-only main...HEAD
```

Reduce the changed files to the set of skill **directories** (the parent dir that contains
a `SKILL.md`), and drop duplicates. Print the resolved list back to the user before
running anything — e.g. "Evaluating 5 skills: …" — so they can confirm the scope.

If nothing is detected and no paths were given, say so and ask which skill(s) to evaluate
rather than guessing.

## Step 2 — Fan out one subagent per skill (parallel)

Dispatch the subagents in a **single message** so they run concurrently. Use a generic
task subagent (the `builder` type in Claude Code; the equivalent general-purpose subagent
in other harnesses). Give each subagent exactly one skill and this task:

- **Review mode (default):** run `make eval-skill SKILL=<path>` from the repo root.
- **Certify mode (`--certify`):** run `make eval-certify SKILL=<path>` instead.

Each subagent then:

1. Captures stdout (use a generous timeout — standard ≈30s–2min per skill; certify ≈15–20 min).
2. **Strips the leading noise** — the `🚀 Evaluating…`/`🚀 Certifying…` make echo line and
   the `uvx` download/build/install lines — keeping the report from `# PluginEval Report`
   onward. For the expected report shape (Overall Score → Layer Breakdown → Dimensions →
   Anti-Patterns), see "Reading a report" in [`references/plugin-eval.md`](references/plugin-eval.md).
3. Writes the clean report to `<path>/EVALS.md`.
4. Does **not** edit the skill itself in review/certify mode.
5. Reports back the composite score, badge, and any anti-patterns.

Tell each subagent the exact `<path>` and its exact `EVALS.md` destination so there is no
ambiguity. (This mirrors the manual run this skill was built from.)

## Step 3 — Report

Summarise the results as a table: skill, composite score, badge, anti-pattern count, and
the lowest-scoring dimension per skill. Confirm each `EVALS.md` was written (e.g.
`git status --porcelain | grep EVALS.md`).

## Step 4 — Improve (`--fix` only)

Only when `--fix` was requested. For each evaluated skill, in priority order of lowest
score first:

1. Read the skill's `EVALS.md` and pull out the **lowest-scoring dimensions** and any
   anti-patterns.
2. Map each weakness to a concrete remedy using [`references/fix-playbook.md`](references/fix-playbook.md),
   cross-checking against [`references/agent-skills-how-skills-work.md`](references/agent-skills-how-skills-work.md)
   so the change reflects what actually makes skills better — not just what nudges a metric.
3. Apply **targeted edits to the skill's `SKILL.md`** (and add `references/` files if the
   weakness is progressive disclosure). Edit the working tree only — **do not commit**.
   Keep changes principled: explain *why* in the prose, generalise rather than overfit to
   the score, and avoid piling on rigid MUST/NEVER directives.
4. Re-run that skill's eval (`make eval-skill SKILL=<path>`), overwrite its `EVALS.md`,
   and record the before→after composite score.

Report the score deltas and leave all edits staged-but-uncommitted for the user to review.

## Examples

```bash
$ /skill-evals                                                    # review skills changed vs. main (default)
$ /skill-evals --fix                                              # review, then improve the weakest skill's SKILL.md, then re-run
$ /skill-evals --certify .claude/skills/doc-generator            # deep certification (badge) for one skill
$ /skill-evals .claude/skills/doc-generator .claude/skills/twitter-media-downloader  # explicit targets
```

## Cost & notes

- `--review` (standard depth) ≈ 4 LLM calls / ~30s per skill via Claude Code Max (`claude-agent-sdk`).
- `--certify` (deep) ≈ 54 LLM calls / ~15–20 min per skill — confirm with the user before
  certifying more than one or two skills.
- `EVALS.md` files are intentionally untracked output; they are regenerated each run.
- All commands run from the repo root.
