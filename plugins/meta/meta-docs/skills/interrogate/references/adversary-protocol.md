# Adversary Protocol Reference

This reference provides the operational templates and isolation guardrails for the `interrogate`
skill across Claude Code, GitHub Copilot CLI, and Codex.

## 1. Worktree and scratch isolation

Adversaries must never mutate the user's primary working tree:

- **Read-only probes** (checking whether documented files, CLI flags, symbols, JSON keys, or links
  exist in the repository) may run directly against the repository root using read-only commands.
- **Mutating probes** (writing reproducer scripts, running test cases, testing build/lint failures,
  or prototyping a design flaw) must use either:
  - Subagent worktree isolation (`isolation: worktree` in Claude Code), or
  - A dedicated scratch directory under `/tmp/interrogate-<slug>/adversary-<n>/` that is removed
    before `interrogate` finishes.

## 2. Adversary prompt template for documentation and specifications

When the target is a `README.md`, tutorial, `SKILL.md`, architecture doc, or `specs/*.md` plan,
assign adversaries distinct angles of attack:

### Adversary 1: Command, flag, and path verifier

```text
You are Adversary 1 (Command & Path Verifier).
Scope: <target files>
Restated Intent: <intent>

Break the documented contract by verifying every concrete claim against the live repository:
1. Extract every CLI command, Makefile target, script path, flag, environment variable, JSON
   manifest key, and relative link in the scope.
2. Run read-only checks (`--help`, `make -n`, file/symbol lookups, JSON schema checks, link
   checks) to see if any documented command, flag, or path fails or does not exist.
3. Report only findings backed by exact command output.
```

### Adversary 2: Boundary, prerequisite, and workflow breaker

```text
You are Adversary 2 (Workflow & Boundary Breaker).
Scope: <target files>
Restated Intent: <intent>

Break the documented workflow or specification by probing ordering, prerequisites, and edge cases:
1. Trace the step-by-step instructions from a clean state. Does step N rely on a file, directory,
   environment variable, or state that step 1..N-1 never created?
2. Compare the documented behavior against the implementation scripts, validators, or manifests.
   Does the code reject an input that the documentation claims is valid?
3. Prove every finding with an executable command and its exact output.
```

## 3. Adversary prompt template for code and configuration changes

```text
You are Adversary <N> (Execution Breaker).
Scope: <target files or git diff>
Restated Intent: <intent>
Scratch Directory: /tmp/interrogate-<slug>/adversary-<N>

Break this change. Prove each finding with a run against the real code:
- A failing test or one-liner repro command
- A boundary input (empty, malformed, missing key, concurrent or repeated invocation) that triggers
  an unhandled exception, silent data loss, or wrong exit code
- A cross-runtime or validator regression (for example `make lint`, `make test`, or the repository's
  manifest and skill validators such as `make verify-structure`)

Report each finding with:
1. Title and `file:line`
2. Exact command run
3. Exact output printed
4. Why that output violates the stated intent

Leave out anything you did not execute. "No findings" is a valid result.
```

## 4. Challenge gate rejection reasons

When auditing adversary reports in Phase 3, classify rejected claims using clear categories:

- `not_executed`: The adversary speculated about a risk without running a command to prove it.
- `unreproducible`: Re-running the adversary's command did not produce the claimed failure.
- `style_only`: The finding is about prose tone, formatting preference, or naming rather than a
  broken contract.
- `pre_existing_unrelated`: The failure exists outside the target scope and is unaffected by the
  change or document under review.
- `matches_intent`: The observed behavior is explicitly documented and intended by the contract.
