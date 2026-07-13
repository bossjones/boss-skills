---
description: Run the multi-agent code review factory as a visible cmux team — a judge pane plus risk-tiered specialist panes you can watch and intervene in, then a human-approved GitHub review. Reviews a PR or the current branch against its merge-base.
argument-hint: "[--pr <url> | --base <ref>] [--tier trivial|lite|full]"
allowed-tools:
  - Skill
---

# Review Factory — cmux arm

Invoke the `review-factory-cmux` skill with `$ARGUMENTS` and follow it exactly.

The skill owns the procedure; this command only routes to it. With no arguments, review the
current branch against `main`.

Requires cmux to be running — this arm spawns real panes. For a headless run (and the only
one that could be CI-triggered), use `/review-factory-workflow`.

This is the **cmux arm** of the cmux-vs-Workflow bake-off. Do not mix the two in one run, and
do not tune one arm's prompts without the other — both arms share a deterministic core on
purpose, so that the only thing under test is the substrate.
