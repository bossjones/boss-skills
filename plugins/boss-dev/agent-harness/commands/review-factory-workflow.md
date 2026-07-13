---
description: Run the multi-agent code review factory using the Workflow tool — a risk-tiered specialist fan-out, a judge pass, and a human-approved GitHub review. Reviews a PR or the current branch against its merge-base.
argument-hint: "[--pr <url> | --base <ref>] [--tier trivial|lite|full]"
allowed-tools:
  - Skill
---

# Review Factory — Workflow arm

Invoke the `review-factory-workflow` skill with `$ARGUMENTS` and follow it exactly.

The skill owns the procedure; this command only routes to it. With no arguments, review the
current branch against `main`.

This is the **Workflow arm** of the cmux-vs-Workflow bake-off. For the visible-panes arm, use
`/review-factory-cmux`. Do not mix the two in one run, and do not tune one arm's prompts
without the other — both arms share a deterministic core on purpose, so that the only thing
under test is the substrate.
