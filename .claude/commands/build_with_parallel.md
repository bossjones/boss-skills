---
model: opus
description: Build a feature in parallel by dispatching one worktree-isolated builder subagent per independent track, then merging and validating.
argument-hint: <parallel-plan-path-or-prompt>
hooks:
  Stop:
    - hooks:
        - type: command
          command: "uv run \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/validators/ty_validator.py"
        - type: command
          command: "uv run \"$CLAUDE_PROJECT_DIR\"/.claude/hooks/validators/ruff_validator.py"
---

# Build With Parallel

## Purpose

Execute a user prompt — or a plan produced by `/plan_for_parallel` — by splitting it into independent tracks and building each in its own git worktree, in parallel, then merging the results.

## Variables

USER_PROMPT: $ARGUMENTS

## Instructions

- If USER_PROMPT is a path to a parallel plan under `specs/`, read its **Parallelization Strategy** (track table, dependency graph, file ownership) and **Integration Plan**. Otherwise, decompose USER_PROMPT into independent tracks using the isolation rule below.
- **Isolation rule:** two tracks may run concurrently ONLY if their file-ownership sets are disjoint. Never let two concurrently-running tracks edit the same file. If ownership can't be made disjoint, serialize the offenders or factor the shared change into a foundation track.
- Run **Track 0 (Foundation)**, if present, first and to completion before dispatching parallel tracks — they build on it.
- Dispatch each independent track as its own builder subagent launched with `isolation: worktree`, so it operates in an auto-managed git worktree at `.claude/worktrees/<repo>-<name>/` on branch `worktree-<name>`. Send all independent dispatches in a single message (multiple Agent calls) so they run concurrently. Scope each subagent strictly to its track's file-ownership globs.
- Respect the dependency graph: only dispatch a track after every track it depends on has completed. Use background dispatch and monitor with `TaskOutput`/`TaskList` (see `/plan_w_team` for the orchestration pattern).
- `.worktreeinclude` carries local files into each worktree (`.env`, `.env.local`, `**/.claude/settings.local.json`). Never read, print, or log the contents of `.env`/`.envrc`.
- Focus on clean, well-typed Python. If validation fails, fix the issues and try again.

## Workflow

1. Read USER_PROMPT. Load the parallel plan if a path was given; otherwise decompose the prompt into tracks with the isolation rule in mind.
2. If a foundation track exists, execute and verify it first.
3. Dispatch the remaining independent tracks in parallel as worktree-isolated builder subagents (single message, multiple Agent calls, `isolation: worktree`). For dependent tracks, wait for their blockers to complete, then dispatch.
4. Monitor each subagent to completion; collect the worktree branch and result for each track.
5. Integrate: merge each track's branch back in dependency order (foundation first). Resolve any conflicts (minimal by construction, since ownership is disjoint).
6. Validate: the Stop hooks run `ty_validator` + `ruff_validator`; also run `make lint` and `make test`.
7. Report the results of your work.

## Report

After completing the task:

## Build Complete

**Task**: [brief summary of what was built]

**Tracks**: [per track — name → worktree/branch → status]

**Files modified**: [list of files]

**Validation**: [lint + test results]

## Notes

- Explicit / human-driven alternative to the subagent dispatch above: create each worktree with the `/git-worktree <name>` skill, then run `/autobuild specs/<track>.md` inside it (build + commit + push + PR). Clean up with `/git-worktree-remove` / `/git-worktree-clean`; check background jobs with `/git-worktree-status`.
- Headless / unattended re-entry into a worktree: `claude -p --permission-mode acceptEdits "<task>"` (see `specs/refactor-git-worktree-skills.md` → "Running Unattended").
