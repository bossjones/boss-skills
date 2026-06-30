# Workflows & Recipes

The agent-harness pieces are designed to chain together. This page shows the common end-to-end flows
so you can see how commands, agents, and skills combine.

## Table of Contents

- [Plan → Build](#plan--build)
- [Autobuild (spec → shipped PR)](#autobuild-spec--shipped-pr)
- [PR review loop](#pr-review-loop)
- [Worktree lifecycle](#worktree-lifecycle)
- [Team orchestration (`plan_w_team`)](#team-orchestration-plan_w_team)
- [CI recovery](#ci-recovery)

## Plan → Build

The simplest development loop: turn a request into a reviewable spec, then implement it.

```text
/agent-harness:plan add Redis-backed rate limiting to the public API
  → writes specs/add-redis-backed-rate-limiting.md

# review the spec, then:
/agent-harness:build specs/add-redis-backed-rate-limiting.md
  → implements the plan, reports the Report section
```

**Why two steps:** the plan is a checkpoint. You (or a teammate) can read and adjust the spec before
any code is written, and the same spec can later feed `build` or `autobuild`.

See [`plan`](./commands.md#plan) · [`build`](./commands.md#build).

## Autobuild (spec → shipped PR)

When you trust a spec and want it implemented and shipped without babysitting, run `autobuild` inside
an isolated worktree. It chains the git/PR commands so nothing is reimplemented.

> [!IMPORTANT]
> `autobuild`, `fix-gh-pr-comments`, and `debug-ci` are autonomous, multi-cycle, code-changing
> commands. Launch them with plan mode + an Opus-level model
> (`claude --model 'claude-opus-4-8[1m]' --permission-mode plan`), then approve into auto mode. See
> [Running autonomous commands](./getting-started.md#running-autonomous-commands-plan-mode--opus).

```text
# 1. Create an isolated worktree (or launch with claude --worktree)
/agent-harness:git-worktree add-rate-limiter --from main

# 2. Inside that worktree session:
/agent-harness:autobuild specs/add-redis-backed-rate-limiting.md
```

`autobuild` then:

```text
verify worktree → implement spec → make lint / make test
  → /agent-harness:commit-push-pr        (commit + push + open PR)
  → /agent-harness:fix-gh-pr-comments    (address review, up to 3 cycles)
```

See [`autobuild`](./commands.md#autobuild) · [`git-worktree`](./skills.md#git-worktree) ·
[`commit-push-pr`](./commands.md#commit-push-pr) ·
[`fix-gh-pr-comments`](./commands.md#fix-gh-pr-comments).

## PR review loop

Review someone else's PR, then respond to feedback on your own — built from the PR-review skills plus
the responder command.

**Reviewing a PR (no posting until you decide):**

```text
fetch-diff                 → annotated diff with line numbers
fetch-unresolved-comments  → only the open review threads
pr-review octocat/repo 42  → schema-validated payload at /tmp/review-payload.json
add-review-comment         → post individual inline comments / suggestions
```

**Responding to review on your PR:**

```text
/agent-harness:fix-gh-pr-comments 42
  → triage by severity → fix → make lint/test → push one commit
  → reply per-thread with the SHA → poll for new comments (≤ 3 cycles)
```

See [skills.md → PR review workflow](./skills.md#pr-review-workflow) ·
[`fix-gh-pr-comments`](./commands.md#fix-gh-pr-comments).

## Worktree lifecycle

Keep feature work isolated and tidy from creation to cleanup.

```text
/agent-harness:worktree-doctor                      # suggest a .worktreeinclude (once per repo)
/agent-harness:git-worktree feature-x --from main   # create + symlink deps + background verify
/agent-harness:git-worktree-status                  # check type-check/test/build (non-blocking)
# … do the work, open a PR …
/agent-harness:git-worktree-remove feature-x        # safe single removal + branch cleanup
# periodically:
/agent-harness:git-worktree-clean --dry-run         # preview stale/merged cleanup, then run for real
```

See [skills.md → Git worktree lifecycle](./skills.md#git-worktree-lifecycle).

## Team orchestration (`plan_w_team`)

For larger work split across multiple agents with explicit dependencies.

```text
/agent-harness:plan_w_team migrate auth to JWT  one builder per endpoint, validate at the end
  → writes a spec with a Team Members section and tasks (IDs, blockedBy, owners)
```

The planning command acts as **team lead** and uses the Task tools to coordinate:

```text
TaskCreate  → one task per step
TaskUpdate  → set blockedBy dependencies + assign owners
Task        → deploy agent-harness:team:builder per task (parallel where allowed)
            → deploy agent-harness:team:validator to verify against acceptance criteria
TaskList / TaskOutput → monitor progress
```

The lead never edits code directly — [`team/builder`](./agents.md#teambuilder) executes single tasks
and [`team/validator`](./agents.md#teamvalidator) (read-only) verifies them.

See [`plan_w_team`](./commands.md#plan_w_team) · [agents.md → The team](./agents.md#the-team-used-by-plan_w_team).

## CI recovery

When the PR's CI goes red:

```text
/agent-harness:debug-ci
  → find the failed run → categorize (ruff/ty/pytest/uv-lock/…) → fix → validate locally
  → push → poll the NEW run by commit SHA until green (≤ 3 cycles)
```

See [`debug-ci`](./commands.md#debug-ci).
</content>
