---
description: Creates a worktree-aware engineering plan that segments work into independent parallel tracks and saves it to specs/
argument-hint: [user prompt]
---

# Plan for Parallel

Create a detailed, **parallelizable** implementation plan based on the user's requirements in the `USER_PROMPT` variable. This keeps the ethos of `/plan` — a concise, executable spec saved to `PLAN_OUTPUT_DIRECTORY` — but adds a decomposition pass that segments the work into independent **tracks**, each scoped to a disjoint set of files so it can run in its own git worktree without merge conflicts. Follow the `Instructions` and work through the `Workflow`.

## Variables

USER_PROMPT: $1
PLAN_OUTPUT_DIRECTORY: `specs/`
WORKTREE_ROOT: `.claude/worktrees/`

## Instructions

- IMPORTANT: If no `USER_PROMPT` is provided, stop and ask the user to provide it.
- Carefully analyze the user's requirements provided in the USER_PROMPT variable.
- Determine the task type (chore|feature|refactor|fix|enhancement) and complexity (simple|medium|complex).
- Think deeply (ultrathink) about the best approach, then about how to **partition** that approach into independent tracks.
- Understand the codebase directly without subagents — focus especially on the file-level boundaries between subsystems, since those boundaries determine what can run in parallel.
- **Isolation rule:** two tracks may run concurrently ONLY if their file-ownership sets are disjoint. If two tracks must edit the same file, either serialize them (express via `Depends On`) or extract the shared change into a foundation track (Track 0) the others depend on.
- Factor shared scaffolding (types, interfaces, schemas, shared config, migrations) into **Track 0: Foundation** so parallel tracks build on a stable base.
- Map each track to a worktree at `WORKTREE_ROOT<repo>-<name>/` on branch `worktree-<name>`. Use short, descriptive `<name>` values.
- Keep each track self-contained enough to hand to a single builder agent operating only within its worktree.
- Produce a dependency graph and an integration (merge) order.
- Follow the Plan Format below; include all required sections plus the conditional ones based on task type and complexity.
- Generate a descriptive, kebab-case filename and save to `PLAN_OUTPUT_DIRECTORY/<descriptive-name>.md`.
- Consider edge cases, error handling, and scalability concerns.

## Workflow

1. Analyze Requirements - THINK HARD and parse the USER_PROMPT to understand the core problem and desired outcome.
2. Understand Codebase - Without subagents, directly understand existing patterns, architecture, relevant files, and the file boundaries between subsystems.
3. Design Solution - Develop the technical approach including architecture decisions and implementation strategy.
4. Decompose into Parallel Tracks - Partition the work by disjoint file ownership; extract shared work into Track 0 (Foundation); build the dependency graph; assign a worktree name + branch per track.
5. Document Plan - Structure the markdown document using the Plan Format, including the Parallelization Strategy and Integration Plan sections.
6. Generate Filename - Create a descriptive kebab-case filename based on the plan's main topic.
7. Save & Report - Follow the `Report` section to write the plan and summarize the tracks.

## Plan Format

Follow this format when creating implementation plans:

```md
# Plan: <task name>

## Task Description
<describe the task in detail based on the prompt>

## Objective
<clearly state what will be accomplished when this plan is complete>

<if task_type is feature or complexity is medium/complex, include these sections:>
## Problem Statement
<clearly define the specific problem or opportunity this task addresses>

## Solution Approach
<describe the proposed solution approach and how it addresses the objective>
</if>

## Relevant Files
Use these files to complete the task:

<list files relevant to the task with bullet points. Include new files under an h3 'New Files' section if needed>

## Parallelization Strategy

### Track Table
| Track | Scope | Worktree | Branch | Depends On | File Ownership (globs this track may edit) |
| --- | --- | --- | --- | --- | --- |
| 0 (Foundation) | <shared scaffolding> | `.claude/worktrees/<repo>-<name>/` | `worktree-<name>` | — | <globs> |
| A | <feature slice> | `.claude/worktrees/<repo>-<name>/` | `worktree-<name>` | 0 | <globs> |
| B | <feature slice> | `.claude/worktrees/<repo>-<name>/` | `worktree-<name>` | 0 | <globs> |

### Dependency Graph
<show which tracks are parallel vs sequential, e.g.:>
Track 0 (Foundation)
  ├─ Track A ─┐  (A and B run in parallel)
  └─ Track B ─┘

### Conflict Boundaries
<list any file/dir more than one track needs and how it is serialized or factored into Track 0. Overlapping ownership = NOT parallel.>

<if complexity is medium/complex, include this section:>
## Implementation Phases
### Phase 1: Foundation
### Phase 2: Core Implementation
### Phase 3: Integration & Polish
</if>

## Step by Step Tasks
IMPORTANT: Execute every step in order within a track. Tracks with no dependency on each other may execute concurrently in separate worktrees; respect the Depends On column.

### Track 0: Foundation (if any)
#### 0.1 <task>
- <specific action>

### Track A: <name> (parallel with Track B; depends on Track 0)
#### A.1 <task>
- <specific action>

### Track B: <name> (parallel with Track A; depends on Track 0)
#### B.1 <task>
- <specific action>

## Integration Plan
<merge order (dependency order, foundation first), how to reconcile shared scaffolding, conflict-resolution notes (should be minimal given disjoint ownership), and post-merge validation>

<if task_type is feature or complexity is medium/complex, include this section:>
## Testing Strategy
<testing approach, including unit tests and edge cases as applicable>
</if>

## Acceptance Criteria
<specific, measurable criteria for completion, including: tracks have disjoint file ownership; the dependency graph is acyclic; the integration order is stated>

## Validation Commands
Execute these commands to validate the task is complete:

<list specific commands to validate the work>
- Example: `make lint` - lint passes clean
- Example: `make test` - full suite passes

## Notes
<optional additional context. If new libraries are needed, specify using `uv add`. Build this plan with `/build_with_parallel PLAN_OUTPUT_DIRECTORY/<filename>.md`.>
```

## Report

After creating and saving the implementation plan, provide a concise report with the following format:

```
✅ Parallel Implementation Plan Created

File: PLAN_OUTPUT_DIRECTORY/<filename>.md
Topic: <brief description of what the plan covers>
Tracks: <N> total (<P> run in parallel; foundation track: yes/no)
Worktrees: .claude/worktrees/<repo>-<name>/ × <N>
Key Components:
- <main component 1>
- <main component 2>
- <main component 3>
Next: /build_with_parallel PLAN_OUTPUT_DIRECTORY/<filename>.md
```
