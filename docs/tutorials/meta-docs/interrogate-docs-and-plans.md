# Tutorial: Stress-test docs and plans with `interrogate`

Use `interrogate` when clean prose is not enough and you need to prove whether a specification,
tutorial, README, or code change contains broken commands, invalid flags, missing prerequisites, or
unhandled edge cases.

Unlike style reviewers, `interrogate` spawns parallel adversary subagents and enforces a strict
**challenge gate**: a finding survives only when an executed command or reproducible check proves
it.

## Prerequisites

- Claude Code, GitHub Copilot CLI, or Codex with the `meta-docs` plugin installed from `boss-skills`.
- A target specification (`specs/*.md`), documentation page (`docs/**/*.md`), or branch diff.

## Step 1: Run `interrogate` on a specification or documentation page

Point `interrogate` at the file or directory you want to challenge:

```text
/interrogate Challenge specs/meta-docs.md and plugins/meta/meta-docs/README.md. Verify every documented
file path, Makefile target, validation script, and relative link against the repository.
```

## Step 2: How `interrogate` executes the review

1. **Frame & restate intent**: `interrogate` reads the target files and restates the author's goal
   and public contract in its own words.
2. **Fan out adversaries**: It launches parallel `general-purpose` subagents (using isolated
   worktrees or `/tmp/interrogate-*` scratch directories for mutating probes) using your session's
   configured model(s):
   - **Adversary 1 (Command & Path Verifier)** extracts and tests every CLI command, script flag,
     manifest key, and relative link.
   - **Adversary 2 (Workflow & Boundary Breaker)** traces the step-by-step instructions to find
     missing prerequisites or inputs rejected by repository validators.
3. **Challenge gate verification**: The coordinator re-runs each adversary's reproducer command.
   Speculative claims, style preferences, and unreproducible issues are dropped and tallied under
   **Dropped claims**.

## Step 3: Review the report

`interrogate` returns a structured verdict:

```text
Intent: Ship a cross-runtime meta-docs plugin with validated skills, subagent, and documentation.

Verified findings:
- No verified findings (all documented scripts, flags, and relative links resolved with exit code 0).

Dropped claims:
- Adversary 1: 1 dropped (style_only — suggested renaming a section heading).
- Adversary 2: 0 dropped.
```

If `interrogate` reports verified findings, each entry includes the exact command run, the actual
output printed, and why it breaks the stated contract so you can fix the root cause immediately.

See the [Meta Docs plugin reference](../../plugins/meta-docs.md) and the
[Adversary protocol reference](../../../plugins/meta/meta-docs/skills/interrogate/references/adversary-protocol.md)
for details.
