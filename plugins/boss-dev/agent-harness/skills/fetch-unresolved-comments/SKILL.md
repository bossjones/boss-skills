---
name: fetch-unresolved-comments
description: Fetch unresolved PR review comments via the GitHub GraphQL API, filtering out already-resolved feedback. Use when you need only the open review threads on a pull request — for example before addressing reviewer feedback or summarizing what still needs attention.
allowed-tools:
  - Bash(uv run:*)
---

# Fetch Unresolved PR Review Comments

Uses GitHub's GraphQL API to fetch only the unresolved review-thread comments
from a pull request, grouped by file.

## When to Use

- You need only the unresolved review comments from a PR.
- You want to filter out feedback that has already been resolved.

## Instructions

1. **Get the PR URL**:

   - First check for environment variables: if `PR_NUMBER` and
     `GITHUB_REPOSITORY` are set, construct the URL as
     `https://github.com/${GITHUB_REPOSITORY}/pull/${PR_NUMBER}`.
   - Otherwise, use `gh pr view --json url -q '.url'` to get the current
     branch's PR URL.

2. **Run the skill**:

   ```bash
   uv run "${CLAUDE_SKILL_DIR}/scripts/fetch_unresolved_comments.py" <pr_url>
   ```

   Example:

   ```bash
   uv run "${CLAUDE_SKILL_DIR}/scripts/fetch_unresolved_comments.py" https://github.com/owner/repo/pull/123
   ```

   The script is a self-contained PEP 723 script — `uv run` resolves its
   dependencies on demand. The GitHub token is auto-detected from the
   `GH_TOKEN` environment variable or `gh auth token`.

### Script contract

`scripts/fetch_unresolved_comments.py`:

- **Input**: one positional argument, the PR URL
  (`https://github.com/<owner>/<repo>/pull/<number>`).
- **Auth**: `GH_TOKEN` if set, otherwise the token from `gh auth token`.
  With neither, it exits non-zero with a `GH_TOKEN not found` message.
- **Output**: a single JSON object on stdout — `total` (count of open
  comments) plus `by_file`, mapping each file path to its still-open review
  threads. Resolved threads are filtered out via the GraphQL `isResolved`
  flag, which REST can't expose. A PR with no open feedback prints
  `{"total": 0, "by_file": {}}`.

See `references/graphql-and-output.md` for the query shape and the full schema.

## Example Output

```json
{
  "total": 3,
  "by_file": {
    ".github/workflows/resolve.yml": [
      {
        "thread_id": "PRRT_kwDOAL...",
        "line": 40,
        "startLine": null,
        "diffHunk": "@@ -0,0 +1,245 @@\n+name: resolve...",
        "comments": [
          {
            "id": 2437935275,
            "body": "We can remove this once we get the key.",
            "author": "reviewer-a",
            "createdAt": "2026-05-17T00:53:20Z"
          },
          {
            "id": 2437935276,
            "body": "Good catch, I'll update it.",
            "author": "contributor",
            "createdAt": "2026-05-17T01:10:15Z"
          }
        ]
      }
    ],
    ".gitignore": [
      {
        "thread_id": "PRRT_kwDOAL...",
        "line": 133,
        "startLine": null,
        "diffHunk": "@@ -130,0 +133,2 @@\n+.claude/*",
        "comments": [
          {
            "id": 2437935280,
            "body": "Should we add this to .gitignore?",
            "author": "reviewer-b",
            "createdAt": "2026-05-17T01:15:42Z"
          }
        ]
      }
    ]
  }
}
```

## Reference Files

- `references/graphql-and-output.md` — consult when you need the exact GraphQL
  query shape, why GraphQL (not REST) is required, or the full output JSON
  schema field by field.
- `references/troubleshooting.md` — consult when a run fails or surprises you:
  auth/token errors, PR-not-found, private-repo permissions, empty results, the
  resolved-vs-unresolved distinction, pagination on large PRs, or rate limiting.

## Related skills

Part of the PR-review family in this plugin; a typical loop:

- [`../fetch-diff/SKILL.md`](../fetch-diff/SKILL.md) — pull the PR diff to see
  what changed.
- [`../add-review-comment/SKILL.md`](../add-review-comment/SKILL.md) — post a
  review comment on a specific line.
- [`../pr-review/SKILL.md`](../pr-review/SKILL.md) — run a structured review pass
  over a PR.
- **fetch-unresolved-comments** (this skill) — read the still-open threads
  before addressing feedback, and again afterward to confirm nothing was missed.
