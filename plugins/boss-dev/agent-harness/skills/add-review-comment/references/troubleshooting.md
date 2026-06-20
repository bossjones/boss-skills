# Troubleshooting

Posting an inline review comment fails in a handful of predictable ways. Almost
every failure is either an auth problem or a bad line anchor. Match the symptom
below before retrying.

## Authentication

**Symptom:** `gh: To use GitHub CLI ... run: gh auth login`, or HTTP 401 from
`gh api`.

**Cause:** `gh` is not authenticated, or `GH_TOKEN`/`GITHUB_TOKEN` in the
environment is missing, expired, or lacks `repo` scope.

**Fix:** Run `gh auth status` to confirm a logged-in account, or ensure a token
with `repo` (write) scope is exported. The token must have write access to the
target repository — read-only tokens can fetch the diff but cannot post.

## 422: "line must be part of the diff"

**Symptom:** HTTP 422 with a message like *pull_request_review_thread.line must
be part of the diff* or *...path diff*.

**Cause:** The most common failure. The `line` (or `start_line`) you anchored to
does not appear in the PR's diff hunks. GitHub only allows inline comments on
lines that are actually shown in the diff — added lines, deleted lines, or the
few context lines inside a hunk. A line that the PR did not touch and that falls
outside every hunk cannot be anchored.

**Fix:** Re-fetch the diff with the `fetch-diff` skill and pick a line that is
inside a hunk. If you need to comment on surrounding code, anchor to the nearest
changed line and reference the other location in prose.

## Wrong `side` (LEFT vs RIGHT)

**Symptom:** 422 even though the line *number* looks right, or the comment lands
on a different line than intended.

**Cause:** `side` selects which file the line number refers to. A deleted line
exists only on `LEFT`; an added or context line exists on `RIGHT`. Using
`RIGHT` for a removed line (or vice versa) makes the anchor invalid or shifts it.

**Fix:** Use `RIGHT` for added/modified/context lines (the common case) and
`LEFT` only for deleted lines. For a multi-line range, `start_side` and `side`
should match.

## Stale or omitted `commit_id`

**Symptom:** 422, or the comment attaches to an outdated version of the file.

**Cause:** `commit_id` points at an old commit, or was left off so GitHub used a
default that no longer matches the diff you read. After a force-push or new
commits, an old SHA's line numbers no longer line up.

**Fix:** Always resolve the head SHA inline at post time:
`gh pr view <pr_number> --repo <owner>/<repo> --json headRefOid -q .headRefOid`.
Re-fetch the diff if the head moved since you computed line numbers.

## Multi-line range: `start_line` greater than `line`

**Symptom:** 422 about an invalid range, or `start_line must be less than line`.

**Cause:** For a multi-line comment the range runs from `start_line` to `line`,
so `start_line` must be the *smaller* number. Swapping them inverts the range.

**Fix:** Ensure `start_line <= line` and that both endpoints sit inside the same
diff hunk on the same `side`.

## Commenting on an unchanged line

**Symptom:** 422 "line must be part of the diff" on a file that *is* in the PR.

**Cause:** Even within a changed file, only the lines GitHub renders in the diff
(hunk lines plus their small context window) are commentable. An untouched line
far from any hunk is not.

**Fix:** Anchor to the closest changed or context line that the diff exposes,
and describe the unchanged location in the comment body instead.
