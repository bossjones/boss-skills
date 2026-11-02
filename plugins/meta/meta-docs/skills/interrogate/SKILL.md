---
name: interrogate
license: MIT
description: >-
  Run an adversarial, execution-backed review to break a documentation page, specification,
  design plan, or code change. Spawns parallel adversary subagents that probe claims, commands,
  edge cases, and contracts; only findings proven by an actual command run or reproducible check
  survive. Use when asked to interrogate, adversarially review, challenge, stress test, find blind
  spots in, or tear apart a doc, spec, plan, or diff before merging or implementing it.
---

# Interrogate

Adversaries try to break a documentation contract, specification, design plan, or code change. A
finding survives only when an executable command or reproducible verification proves it. Report the
verified findings. Do not apply fixes unless the user explicitly asks you to fix them after the
report.

## When to use

- Before merging documentation, a README, or a tutorial whose commands, flags, paths, or links must
  work as written.
- Before implementing a specification or design plan, to find missing prerequisites or steps that
  repository validators reject.
- On a branch diff, to find edge cases (empty, malformed, or repeated inputs) that break the change.

Do not use it for tone or wording cleanup; use `unslop` or `humanize-skills` instead. Do not use it
for a quick factual lookup that needs no adversarial probing.

## Example

```text
/interrogate Challenge docs/plugins/meta-docs.md. Verify every install command, relative link, and
Makefile target it documents.
```

For detailed adversary prompt templates, documentation-contract checks, and worktree isolation rules,
see [references/adversary-protocol.md](references/adversary-protocol.md).

## Phase 1: Frame & restate intent

1. **Determine the scope**:
   - Use the files, documentation pages, specifications, or directories the user explicitly names.
   - If the user names no target, use the branch diff from its merge base with the base branch
     through the current working tree (`$ git diff $(git merge-base HEAD main)`).
2. **Restate the intent in your own words**:
   - Read the user's message, recent commits, pull request description, or specification header.
   - State in plain language what the author's goals are, what problem the artifact solves, and what
     public contract or behavior it promises.
   - If the intent is genuinely ambiguous, ask the user a focused question before fanning out.

## Phase 2: Fan out adversaries

Spawn 2 to 3 parallel `general-purpose` subagents (or run distinct adversarial probes sequentially
if subagent spawning is unavailable in the current environment). Keep this skill model-agnostic:
allow subagents to use the session's configured default subagent models or any explicit model
requested by the user.

- When probing code, scripts, or mutating commands, isolate each adversary in its own temporary git
  worktree or scratch directory (`/tmp/interrogate-<slug>/adversary-<n>/`) and copy uncommitted
  scope changes into that workspace so probes never dirty the user's working tree.
- Give every adversary the **Scope**, the restated **Intent**, and the following brief (see
  [references/adversary-protocol.md](references/adversary-protocol.md) for specialized code vs.
  documentation prompts):

> Break this change, document, or design. Prove each finding with a real run against the repository,
> such as a failing test, a repro script, a CLI flag/schema check, a broken relative link check, or
> command output that contradicts the documented contract. For a design or specification, run a
> probe against the current tree or a minimal prototype in your scratch directory. Report each
> finding with a title, the exact command you ran, the output it printed, and the output or behavior
> the intent requires. Leave out anything you did not run or verify. That excludes style opinions,
> prose tone, naming preferences, and hypothetical risks that require a future change to matter.
> "No findings" is a valid result.

## Phase 3: Independent verification (challenge gate)

Treat every adversary report as an unverified claim until you confirm it yourself:

1. **Re-run the command**: Execute each adversary's reported command or verification check yourself.
2. **Evaluate against intent**:
   - **KEEP** a finding only when the command output reproduces the failure **and** the failure
     breaks the stated intent or contradicts the documented contract.
   - **DROP** any finding whose command passes, cannot be reproduced, relies on an invalid test
     setup, or is a stylistic opinion disguised as a bug.
3. **Deduplicate**: Merge surviving findings that share the same root cause, crediting all
   adversaries that discovered it.
4. **Clean up**: Remove any temporary worktrees or `/tmp/interrogate-*` scratch directories created
   during Phase 2 and Phase 3.

## Phase 4: Output

Present the final report in this structure:

- **Intent**: Your plain-language restatement of the goal and contract.
- **Verified findings**: For each surviving finding, include:
  - **Title & location**: `file:line` or section heading
  - **Command**: The exact verification command run
  - **Actual output**: What the command printed
  - **Expected contract**: Why this breaks the stated intent
  - **Found by**: Which adversary seat(s) proved it
  - Say `"No verified findings"` when none survive.
- **Dropped claims**: For each adversary, the count of dropped findings and the reason each was
  rejected (for example, `unreproducible`, `not_executed`, `style_only`, or `matches_intent`).

## Failure handling

- **Command cannot run** (missing tool, no network, missing credentials): record the claim as
  `not_executed` under **Dropped claims** and name the missing prerequisite. Never promote it to a
  verified finding.
- **Subagents unavailable**: run the adversary seats sequentially in this session and say so in the
  report.
- **Scope is empty** (no named target and no diff from the base branch): stop and ask the user which
  file, spec, or branch to interrogate.
- **Probe would mutate the user's tree**: move it into the scratch worktree first; if that is not
  possible, skip the probe and list it as `not_executed`.
