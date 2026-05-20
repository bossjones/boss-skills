---
name: add-review-comment
description: Post a single inline review comment to a GitHub pull request. Use when you need to leave one comment on a specific line or line range of a PR via the GitHub API — supports single-line and multi-line anchors and one-click suggestion blocks.
allowed-tools:
  - Bash(gh api:*)
  - Bash(gh pr view:*)
  - Skill
---

# Add Review Comment

Posts one inline review comment to a specific line in a GitHub pull request
using the GitHub REST API via the `gh` CLI.

## When to Use

- You have a single finding and want to anchor a comment to the exact line.
- You need a multi-line comment spanning a range of changed lines.
- You want to attach a one-click `suggestion` block to a PR line.

For reviewing a whole PR and emitting a full set of comments, use the
[`pr-review`](../pr-review/SKILL.md) skill instead.

## Step 1: Locate the line to comment on

Invoke the [`fetch-diff`](../fetch-diff/SKILL.md) skill to fetch the PR diff with
line numbers, then identify the `path`, `line`, and `side` to anchor to:

- `side=RIGHT` — added or context lines (the post-merge file). The common case.
- `side=LEFT` — deleted lines (the pre-change file).

## Step 2: Post the comment

**Single-line comment** — the body must end with the
`🤖 Generated with Claude` footer on its own line:

```bash
gh api repos/<owner>/<repo>/pulls/<pr_number>/comments \
  -f body=<comment> \
  -f path=<file_path> \
  -F line=<line_number> \
  -f side=<side> \
  -f commit_id="$(gh pr view <pr_number> --repo <owner>/<repo> --json headRefOid -q .headRefOid)" \
  --jq '.html_url'
```

**Multi-line comment** — anchors a range from `start_line` to `line`:

```bash
gh api repos/<owner>/<repo>/pulls/<pr_number>/comments \
  -f body=<comment> \
  -f path=<file_path> \
  -F start_line=<first_line> \
  -f start_side=<side> \
  -F line=<last_line> \
  -f side=<side> \
  -f commit_id="$(gh pr view <pr_number> --repo <owner>/<repo> --json headRefOid -q .headRefOid)" \
  --jq '.html_url'
```

## Parameters

| Parameter | Meaning |
|-----------|---------|
| `path` | File path relative to the repo root; must have a hunk in the PR diff |
| `line` | Anchor line (for multi-line comments, the last line of the range) |
| `side` | `RIGHT` for added/modified lines, `LEFT` for deleted lines |
| `start_line` / `start_side` | First line of the range (multi-line comments only) |
| `commit_id` | Head commit SHA — resolved inline via `gh pr view` above |

## Best Practices

- Use suggestion blocks for simple fixes maintainers can apply in one click —
  fence with triple backticks and the word `suggestion`, and preserve the
  original indentation exactly:

  ````text
  ```suggestion
  <suggested code here>
  ```
  ````

- For a repeated issue, leave one representative comment rather than flagging
  every instance.
- For bugs, state the problem, why it matters, and a concrete fix.
- Always end the comment body with `🤖 Generated with Claude` on its own line.
