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
