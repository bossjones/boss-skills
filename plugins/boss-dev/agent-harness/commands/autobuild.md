---
model: opus
description: Implement a spec inside a git worktree, then commit, push, open a PR, and address review comments. Must run inside a linked git worktree.
argument-hint: <spec-path>
hooks:
  PostToolUse:
    - matcher: "Write|Edit|MultiEdit"
      hooks:
        - type: command
          command: "uv run \"${CLAUDE_PLUGIN_ROOT}\"/hooks/validators/ty_validator.py"
        - type: command
          command: "uv run \"${CLAUDE_PLUGIN_ROOT}\"/hooks/validators/ruff_validator.py"
---

# Autobuild Command

Implement the spec at the given path, then ship it: verify, commit, push, open a PR, and address review comments — all from inside an isolated git worktree.

## Guardrails — READ FIRST

- **MUST run inside a linked git worktree.** If this session is on the main checkout (or not a git repo), hard-stop in Phase 0 and tell the user how to relaunch. Implementing a spec on `main` defeats the isolation this workflow exists to provide.
- **Require a valid spec path.** If `$1` is empty or the file does not exist, stop and ask the user for a valid spec path. Do nothing else.
- **Stay within the spec's scope.** Implement what the spec describes — do not invent features, refactors, or abstractions beyond it.
- **Reuse, don't reimplement.** Phases 4 and 5 invoke the existing `/agent-harness:commit-push-pr` and `/agent-harness:fix-gh-pr-comments` commands. Do not duplicate their staging, commit, push, PR, or review-reply logic here.
- **Never force-push, never `git add -A`, never amend.** The chained commands enforce this too; do not work around it.
- **Verification gates the commit.** Do not advance to Phase 4 while lint/type/tests are failing.

## Variables

SPEC_PATH: $1

## Phase 0: Verify git worktree (hard stop)

Detect whether this session is in a *linked* worktree by comparing the per-worktree git dir against the shared common git dir — they differ only in a linked worktree:

```bash
git_dir=$(git rev-parse --git-dir 2>/dev/null)
common_dir=$(git rev-parse --git-common-dir 2>/dev/null)
if [ -z "$git_dir" ]; then
  echo "NOT_A_GIT_REPO"
elif [ "$git_dir" = "$common_dir" ]; then
  echo "MAIN_CHECKOUT"
else
  echo "LINKED_WORKTREE: $(pwd)"
fi
```

Only `LINKED_WORKTREE` may proceed to Phase 1.

On `MAIN_CHECKOUT` or `NOT_A_GIT_REPO`: **stop immediately** (make no edits, no commits). Derive a short slug from the spec filename (e.g. `specs/01-label-studio-tweet-region-annotation.md` -> `label-studio`) and print relaunch instructions:

```
You're not in a worktree. /agent-harness:autobuild must run in an isolated worktree.

Open a new terminal and run:

  cd <repo-root> && export PREFIX="spec-"
  claude --worktree "${PREFIX}<slug-from-spec-filename>"

Then inside that new session, run:

  /agent-harness:autobuild <spec-path>
```

`claude --worktree` creates the worktree and branch for you — do not pre-create them here (that would collide on the branch name).

## Phase 1: Load the spec

Read the spec contents:

@$1

If the file is missing or `SPEC_PATH` is empty, stop and ask for a valid path. Otherwise extract and briefly restate, from the spec:

- The **objective** (what "done" means)
- **Relevant files** to touch
- The **step-by-step tasks**
- **Acceptance criteria**
- Any **validation commands** the spec specifies
- Any **TDD / testing instruction** the spec carries (follow it if present)

boss-skills specs follow the `/agent-harness:plan` format, so look for `## Objective`, `## Relevant Files`, `## Step by Step Tasks`, `## Acceptance Criteria`, and `## Validation Commands` headings.

## Phase 2: Implement

Execute the spec's tasks in order. Write clean, fully-typed Python that follows the project conventions in `CLAUDE.md` (absolute imports, modern union syntax, `pathlib.Path`, no `Optional`, `from __future__ import annotations`). Satisfy every acceptance criterion. If the spec mandates TDD, write the failing test first, then the implementation.

## Phase 3: Verify before shipping

Run the spec's `## Validation Commands` if it lists any. Otherwise run the project defaults:

```bash
make lint
make test
```

Fix any failures and re-run until both are clean. **Do not proceed to Phase 4 while verification is red.**

## Phase 4: Commit, push, open PR

Invoke the existing command — do not reimplement its logic:

```
/agent-harness:commit-push-pr
```

Capture the resulting PR URL for the final report.

## Phase 5: Address review comments

Invoke the existing command once — it self-polls for new comments up to 3 cycles:

```
/agent-harness:fix-gh-pr-comments
```

If it reports it stopped after 3 cycles with actionable comments still open, surface that to the user rather than silently finishing.

## Report

After completing the chain:

```
## Autobuild Complete
**Worktree**: <path>
**Spec**: <spec-path>
**Implemented**: <1-2 line summary of what was built>
**Verification**: make lint ✓ / make test ✓
**PR**: <url from /agent-harness:commit-push-pr>
**Review**: <result from /agent-harness:fix-gh-pr-comments>
```
