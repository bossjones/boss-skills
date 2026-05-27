---
description: Fetch unresolved PR review comments via gh CLI, evaluate each one, apply fixes locally, validate, push, reply per-thread, and poll for new comments. Supports up to 3 outer cycles.
allowed-tools: [Bash, Read, Edit, Write, Glob, Grep, Agent]
---

# Fix GitHub PR Review Comments

You are a PR-review responder. Your job is to take the inline review comments on a pull request, evaluate each one technically, apply the fixes the project actually needs, push a single conventional commit, reply to each thread with what was done, and then poll for any new comments triggered by your push.

Argument: optional PR number (`/fix-gh-pr-comments 42`). If omitted, resolve the PR from the current branch.

## Guardrails — READ FIRST

- **Verify before implementing.** Read each affected file region before applying a fix. Treat reviewer suggestions as suggestions, not commands. If a suggestion is technically wrong, breaks existing functionality, or violates YAGNI, push back with technical reasoning in the thread reply instead of silently complying.
- **Never `git add -A` or `git add .`** — stage only the specific files you edited.
- **Never amend or force-push.** Always create a new commit.
- **Conventional commit prefix required**: `fix:` for security/bug fixes, `docs:` for doc-only changes, `style:` for formatting, `refactor:` if restructuring. If a single commit covers multiple categories, use the highest-priority one (`fix` > `refactor` > `docs` > `style`).
- **Max 3 outer cycles** (fetch → fix → push → reply → poll). If reviewers keep returning new actionable comments after 3 cycles, stop and ask the user for direction.
- **Max 3 inner iterations** for local validation per cycle.
- **Reply on each thread**, not as a top-level PR comment. The endpoint is `POST /repos/{owner}/{repo}/pulls/{pr}/comments/{id}/replies`.
- **No performative agreement** in replies. Acknowledge what was fixed (or push back) with the commit SHA. Never write "Thanks", "Great catch", or similar — actions speak via the diff.
- **Filter out comments authored by the current GitHub user** when polling, to avoid self-reply loops.

## Phase 0: Resolve PR + Repo

```bash
gh auth status || { echo "Run 'gh auth login' first"; exit 1; }

OWNER_REPO=$(gh repo view --json owner,name --jq '.owner.login + "/" + .name')

if [ -n "$ARG" ]; then
  PR_NUMBER="$ARG"
else
  PR_NUMBER=$(gh pr view --json number --jq .number 2>/dev/null) || {
    echo "No PR found for current branch and no PR number given."; exit 1;
  }
fi

ME=$(gh api user --jq .login)
echo "Resolved: $OWNER_REPO PR #$PR_NUMBER  (me: $ME)"
```

If `$ARG` is empty here, fall back to the PR for the current branch. Bail with a clear message if neither resolves.

## Phase 1: Fetch & Triage Comments

```bash
gh api --paginate "repos/$OWNER_REPO/pulls/$PR_NUMBER/comments" > /tmp/pr_comments.json
```

Pull out **actionable, unresolved, top-level** comments — exclude reply chains and your own comments:

```bash
jq '[.[] | select(.in_reply_to_id == null and .user.login != "'"$ME"'")]' /tmp/pr_comments.json > /tmp/pr_top_comments.json
jq 'length' /tmp/pr_top_comments.json
```

For each comment, record: `id`, `path`, `line`, `user.login`, `body`, `original_commit_id`. Group by file path. Within each file, prioritize:

1. **Security** (auth, injection, secrets exposure) — fix first.
2. **Bugs / robustness** (crashes, race conditions, data corruption).
3. **Correctness in docs/configs** (wrong project names, broken examples).
4. **Style / nits** — last; sometimes skip if YAGNI applies.

If a reviewer flags something whose fix is unclear, surface that comment to the user with the relevant body text and ask before guessing.

## Phase 2: Evaluate Each Comment

For each comment, follow the receiving-code-review discipline:

1. **Restate the technical requirement** in your own words (silently — used to drive the next step).
2. **Read the file region** referenced (use `Read` with offset/limit around `line`).
3. **Check the codebase reality**:
   - Does the issue still exist on the current branch?
   - Has it already been addressed by a later commit?
   - Does the suggestion break existing functionality, tests, or callers? (`Grep` for usages.)
4. **Decide**:
   - **Apply** — the fix is correct and worth doing.
   - **Push back** — the fix is wrong / breaks things / violates YAGNI. Document the technical reasoning; this will become the thread reply.
   - **Defer** — the fix is correct but out of scope for this PR. Document why; thread reply explains and links a follow-up issue if appropriate.

Surface any push-back decisions to the user before posting them so they can override.

## Phase 3: Apply Fixes (one file at a time)

For each file that has accepted fixes:

1. `Read` the current contents of the affected region.
2. Apply minimal `Edit`s — change only what's needed. Do not refactor, rename, or "clean up" unrelated code.
3. If multiple comments touch the same file, apply them in a single coherent edit pass so the file stays self-consistent.
4. Re-read the file (only if needed to verify the edit applied to the right hunk) — don't speculate.

For repetitive, mechanical changes across many files (e.g., a renamed identifier flagged in 5 places), consider one `Edit ... replace_all: true` per file, or `Grep` first to make sure you haven't missed locations.

## Phase 4: Local Validation

Run the project's quality gates **in order**, with up to 3 inner retry iterations if something fails:

```bash
make lint   # codespell + ruff + basedpyright
make check  # ty type check (if separate from lint)
make test   # pytest with coverage
```

If a check fails:
1. Read the error output.
2. Apply the fix.
3. Re-run the failing check.
4. Repeat ≤ 3 times. After 3 failed iterations, stop and surface the error to the user.

For changes that aren't covered by `make` targets (e.g., standalone `uv run` scripts under `.claude/hooks/`, status lines, or PEP 723 utility scripts), exercise them manually with representative input before pushing. Examples:

```bash
# Hook smoke test
echo '{"hook_event_name":"PostToolUse","tool_name":"Read"}' | uv run .claude/hooks/post_tool_use.py
```

## Phase 5: Commit & Push

Stage **only** the files you edited, then create one conventional commit using a HEREDOC body that summarizes what was fixed and why (one bullet per comment is fine):

```bash
git add <file1> <file2> ...   # never -A or .
git status --short            # confirm only intended files are staged

git commit -m "$(cat <<'EOF'
<prefix>: address <reviewer> review feedback on PR #<n>

- <one-line summary of fix 1>
- <one-line summary of fix 2>
- ...

Co-Authored-By: Claude <current-model-name> <noreply@anthropic.com>
EOF
)"

git push
PUSH_SHA=$(git rev-parse HEAD)
echo "PUSH_SHA=$PUSH_SHA"
```

Use the **current model name** from the system prompt in the `Co-Authored-By` line.

## Phase 6: Reply to Each Thread

For every comment you addressed (or pushed back on), POST a reply on its thread. **Do not** post a top-level PR comment.

```bash
gh api -X POST "repos/$OWNER_REPO/pulls/$PR_NUMBER/comments/<id>/replies" \
  -f body="Addressed in $PUSH_SHA: <one-line summary of fix>"
```

For push-backs:

```bash
gh api -X POST "repos/$OWNER_REPO/pulls/$PR_NUMBER/comments/<id>/replies" \
  -f body="Not applying this: <technical reason>. Keeping current behavior. (HEAD $PUSH_SHA)"
```

Keep replies short and technical. No "thanks", no "great catch", no apologies.

## Phase 7: Poll for New Comments

Reviewers (humans and bots like `gemini-code-assist`) may take a moment to re-review the new commit. Wait, then re-fetch:

```bash
sleep 60

gh api --paginate "repos/$OWNER_REPO/pulls/$PR_NUMBER/comments" > /tmp/pr_comments.json

# New comments are ones whose ORIGINAL anchor is your push SHA.
# (commit_id may be your SHA for re-anchored old comments — don't be fooled.)
NEW_COUNT=$(jq --arg sha "$PUSH_SHA" --arg me "$ME" \
  '[.[] | select(.original_commit_id == $sha and .in_reply_to_id == null and .user.login != $me)] | length' \
  /tmp/pr_comments.json)

echo "new actionable comments: $NEW_COUNT"
```

- **`$NEW_COUNT == 0`**: take one more 60s wait and re-poll. If still zero, declare success and stop.
- **`$NEW_COUNT > 0`**: this is a new actionable batch. Loop back to **Phase 2** using these new comments. Increment the outer cycle counter; bail after 3 outer cycles.

Also re-check the reviews endpoint for fresh top-level review bodies (e.g., a bot may post a summary review without inline comments):

```bash
gh api "repos/$OWNER_REPO/pulls/$PR_NUMBER/reviews" \
  --jq --arg me "$ME" --arg sha "$PUSH_SHA" \
  '.[] | select(.user.login != $me and .commit_id == $sha)'
```

## Output Format

At each phase, give the user a terse status update. Cycle headers help when the loop runs more than once:

```
## Cycle 1/3

### Phase 1: Fetch
Found 9 top-level comments from gemini-code-assist[bot]
- security/critical: 1  (.claude/hooks/permission_request.py)
- bug/medium: 3        (subagent_stop.py, status_line_v10.py, post_tool_use.py)
- docs/medium: 5       (prime.md, debug-ci.md, CLAUDE.md, evals.json, pre_tool_use.py)

### Phase 2: Triage
All 9 comments accepted — fixes apply cleanly.

### Phase 3-4: Apply + Validate
✓ make lint passed
✓ make test passed (149 passed)

### Phase 5: Push
Committed: fix: address gemini-code-assist review feedback on PR #2
Pushed: abc1234

### Phase 6: Reply
Posted 9 thread replies.

### Phase 7: Poll
Sleep 60s... 0 new actionable comments.
Sleep 60s... 0 new actionable comments.
✓ PR clean. Done after 1 cycle.
```

## Failure Modes & Stop Conditions

- **No PR resolved** → bail with instructions to pass a PR number or push the branch first.
- **`gh auth status` fails** → ask user to run `gh auth login` and stop.
- **All checks still failing after 3 inner iterations** → stop, surface error.
- **Same reviewer keeps re-flagging the same issue across cycles** → stop, ask user — likely a misunderstanding of the suggestion.
- **3 outer cycles exhausted** → stop, summarize what's still open, hand back to user.
